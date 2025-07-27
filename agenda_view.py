#!/usr/bin/env python3
"""
Agenda View - Calendar and scheduling logic for Doom Planner

Provides org-mode style agenda views with daily, weekly, and monthly
organization of tasks. Handles time-based task grouping and scheduling.

Author: Claude
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict, OrderedDict
from calendar import monthrange
import calendar

from task_manager import Task, TaskStatus, TaskPriority


class AgendaView:
    """
    Manages agenda views and time-based task organization.
    
    Provides multiple calendar views similar to org-mode agenda,
    with support for scheduling, deadlines, and recurring tasks.
    """
    
    def __init__(self):
        """Initialize the agenda view manager."""
        self.current_date = date.today()
        self.view_mode = "week"  # day, week, month
        self.show_completed = False
        self.show_scheduled_only = False
        
    def get_agenda_view(self, tasks: List[Task], days: int = 7, 
                       base_date: Optional[date] = None) -> Dict[str, List[Task]]:
        """
        Get agenda view organized by time periods.
        
        Args:
            tasks: List of tasks to organize
            days: Number of days to show (for daily/weekly view)
            base_date: Base date for the view (defaults to today)
            
        Returns:
            Dictionary with time period keys and task lists
        """
        if base_date is None:
            base_date = self.current_date
            
        if self.view_mode == "day":
            return self._get_daily_view(tasks, base_date)
        elif self.view_mode == "week":
            return self._get_weekly_view(tasks, base_date, days)
        elif self.view_mode == "month":
            return self._get_monthly_view(tasks, base_date)
        else:
            return self._get_weekly_view(tasks, base_date, days)
    
    def _get_daily_view(self, tasks: List[Task], target_date: date) -> Dict[str, List[Task]]:
        """Get agenda view for a single day."""
        agenda = OrderedDict()
        
        # Filter tasks for the target date
        relevant_tasks = self._get_tasks_for_date(tasks, target_date)
        
        # Organize by time of day
        morning_tasks = []
        afternoon_tasks = []
        evening_tasks = []
        all_day_tasks = []
        
        for task in relevant_tasks:
            if task.scheduled_date:
                hour = task.scheduled_date.hour
                if hour < 12:
                    morning_tasks.append(task)
                elif hour < 17:
                    afternoon_tasks.append(task)
                else:
                    evening_tasks.append(task)
            else:
                all_day_tasks.append(task)
        
        # Build agenda sections
        date_str = target_date.strftime("%A, %B %d, %Y")
        
        if all_day_tasks:
            agenda[f"{date_str} - All Day"] = self._sort_tasks_by_priority(all_day_tasks)
        
        if morning_tasks:
            agenda[f"{date_str} - Morning"] = self._sort_tasks_by_time(morning_tasks)
        
        if afternoon_tasks:
            agenda[f"{date_str} - Afternoon"] = self._sort_tasks_by_time(afternoon_tasks)
        
        if evening_tasks:
            agenda[f"{date_str} - Evening"] = self._sort_tasks_by_time(evening_tasks)
        
        return agenda
    
    def _get_weekly_view(self, tasks: List[Task], start_date: date, days: int = 7) -> Dict[str, List[Task]]:
        """Get agenda view for a week or custom day range."""
        agenda = OrderedDict()
        
        # Get start of week (Monday)
        if self.view_mode == "week":
            days_since_monday = start_date.weekday()
            week_start = start_date - timedelta(days=days_since_monday)
        else:
            week_start = start_date
        
        # Add overdue tasks first
        overdue_tasks = self._get_overdue_tasks(tasks, week_start)
        if overdue_tasks:
            agenda["⚠️  OVERDUE"] = self._sort_tasks_by_due_date(overdue_tasks)
        
        # Add each day of the period
        for i in range(days):
            current_date = week_start + timedelta(days=i)
            day_tasks = self._get_tasks_for_date(tasks, current_date)
            
            if day_tasks or current_date == date.today():
                # Format day header
                if current_date == date.today():
                    day_header = f"📅 TODAY - {current_date.strftime('%A, %b %d')}"
                elif current_date == date.today() + timedelta(days=1):
                    day_header = f"📅 TOMORROW - {current_date.strftime('%A, %b %d')}"
                else:
                    day_header = f"📅 {current_date.strftime('%A, %b %d')}"
                
                if day_tasks:
                    agenda[day_header] = self._sort_tasks_for_day(day_tasks)
                else:
                    agenda[day_header] = []
        
        # Add upcoming deadlines (beyond the current view)
        upcoming_deadlines = self._get_upcoming_deadlines(tasks, week_start + timedelta(days=days))
        if upcoming_deadlines:
            agenda["⏰ UPCOMING DEADLINES"] = self._sort_tasks_by_due_date(upcoming_deadlines)
        
        # Add unscheduled but important tasks
        unscheduled = self._get_unscheduled_important_tasks(tasks)
        if unscheduled:
            agenda["📋 UNSCHEDULED"] = self._sort_tasks_by_priority(unscheduled)
        
        return agenda
    
    def _get_monthly_view(self, tasks: List[Task], target_date: date) -> Dict[str, List[Task]]:
        """Get agenda view for a month."""
        agenda = OrderedDict()
        
        # Get month boundaries
        month_start = target_date.replace(day=1)
        days_in_month = monthrange(target_date.year, target_date.month)[1]
        month_end = month_start + timedelta(days=days_in_month - 1)
        
        # Group tasks by week within the month
        current_date = month_start
        week_num = 1
        
        while current_date <= month_end:
            # Get week start (Monday)
            days_since_monday = current_date.weekday()
            week_start = current_date - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            
            # Collect tasks for this week
            week_tasks = []
            for task in tasks:
                task_date = self._get_task_date(task)
                if task_date and week_start <= task_date <= week_end:
                    week_tasks.append(task)
            
            if week_tasks:
                week_header = f"Week {week_num} ({week_start.strftime('%b %d')} - {week_end.strftime('%b %d')})"
                agenda[week_header] = self._sort_tasks_by_due_date(week_tasks)
            
            # Move to next week
            current_date = week_end + timedelta(days=1)
            week_num += 1
        
        return agenda
    
    def _get_tasks_for_date(self, tasks: List[Task], target_date: date) -> List[Task]:
        """Get all tasks relevant for a specific date."""
        relevant_tasks = []
        
        for task in tasks:
            if not self.show_completed and task.status == TaskStatus.DONE:
                continue
            
            # Check if task is relevant for this date
            if self._is_task_relevant_for_date(task, target_date):
                relevant_tasks.append(task)
        
        return relevant_tasks
    
    def _is_task_relevant_for_date(self, task: Task, target_date: date) -> bool:
        """Check if a task is relevant for a specific date."""
        # Due date matches
        if task.due_date and task.due_date.date() == target_date:
            return True
        
        # Scheduled date matches
        if task.scheduled_date and task.scheduled_date.date() == target_date:
            return True
        
        # Deadline is approaching
        if task.deadline and task.deadline.date() == target_date:
            return True
        
        # For unscheduled tasks, show if they're high priority and not done
        if (not task.due_date and not task.scheduled_date and 
            task.priority in [TaskPriority.HIGH, TaskPriority.URGENT] and
            task.status != TaskStatus.DONE and
            target_date == date.today()):
            return True
        
        return False
    
    def _get_overdue_tasks(self, tasks: List[Task], before_date: date) -> List[Task]:
        """Get tasks that are overdue before a specific date."""
        overdue = []
        
        for task in tasks:
            if (task.due_date and 
                task.due_date.date() < before_date and 
                task.status not in [TaskStatus.DONE, TaskStatus.CANCELLED]):
                overdue.append(task)
        
        return overdue
    
    def _get_upcoming_deadlines(self, tasks: List[Task], after_date: date, 
                               days_ahead: int = 14) -> List[Task]:
        """Get tasks with deadlines in the near future."""
        upcoming = []
        cutoff_date = after_date + timedelta(days=days_ahead)
        
        for task in tasks:
            if (task.deadline and 
                after_date <= task.deadline.date() <= cutoff_date and
                task.status not in [TaskStatus.DONE, TaskStatus.CANCELLED]):
                upcoming.append(task)
        
        return upcoming
    
    def _get_unscheduled_important_tasks(self, tasks: List[Task]) -> List[Task]:
        """Get important tasks that aren't scheduled."""
        unscheduled = []
        
        for task in tasks:
            if (not task.due_date and 
                not task.scheduled_date and
                task.priority in [TaskPriority.HIGH, TaskPriority.URGENT] and
                task.status == TaskStatus.TODO):
                unscheduled.append(task)
        
        return unscheduled[:5]  # Limit to top 5
    
    def _get_task_date(self, task: Task) -> Optional[date]:
        """Get the primary date associated with a task."""
        if task.scheduled_date:
            return task.scheduled_date.date()
        elif task.due_date:
            return task.due_date.date()
        elif task.deadline:
            return task.deadline.date()
        else:
            return None
    
    def _sort_tasks_for_day(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks appropriately for daily view."""
        # First by time (if scheduled), then by priority
        def sort_key(task):
            time_priority = 0
            if task.scheduled_date:
                time_priority = task.scheduled_date.hour * 60 + task.scheduled_date.minute
            else:
                time_priority = 9999  # Unscheduled tasks go to end
            
            return (time_priority, -task.get_priority_value(), task.title.lower())
        
        return sorted(tasks, key=sort_key)
    
    def _sort_tasks_by_time(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by scheduled time."""
        return sorted(tasks, key=lambda t: t.scheduled_date or datetime.max)
    
    def _sort_tasks_by_due_date(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by due date."""
        return sorted(tasks, key=lambda t: t.due_date or datetime.max)
    
    def _sort_tasks_by_priority(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by priority (high to low)."""
        return sorted(tasks, key=lambda t: (-t.get_priority_value(), t.title.lower()))
    
    def get_calendar_grid(self, target_date: date) -> List[List[Optional[int]]]:
        """
        Get a calendar grid for the month containing target_date.
        
        Returns:
            List of weeks, each week is a list of day numbers (or None for empty cells)
        """
        # Get month info
        year, month = target_date.year, target_date.month
        first_day = date(year, month, 1)
        days_in_month = monthrange(year, month)[1]
        
        # Get starting weekday (0=Monday, 6=Sunday)
        start_weekday = first_day.weekday()
        
        # Build calendar grid
        calendar_grid = []
        current_week = [None] * start_weekday  # Empty cells before month starts
        
        for day in range(1, days_in_month + 1):
            current_week.append(day)
            
            # If week is complete or it's the last day, add to grid
            if len(current_week) == 7 or day == days_in_month:
                # Pad end of month if needed
                while len(current_week) < 7:
                    current_week.append(None)
                
                calendar_grid.append(current_week)
                current_week = []
        
        return calendar_grid
    
    def get_task_counts_by_date(self, tasks: List[Task], target_month: date) -> Dict[int, int]:
        """
        Get count of tasks for each day in the target month.
        
        Args:
            tasks: List of all tasks
            target_month: Date within the target month
            
        Returns:
            Dictionary mapping day numbers to task counts
        """
        counts = defaultdict(int)
        
        year, month = target_month.year, target_month.month
        
        for task in tasks:
            task_date = self._get_task_date(task)
            
            if (task_date and 
                task_date.year == year and 
                task_date.month == month and
                (self.show_completed or task.status != TaskStatus.DONE)):
                counts[task_date.day] += 1
        
        return dict(counts)
    
    def get_week_summary(self, tasks: List[Task], week_start: date) -> Dict[str, Any]:
        """
        Get a summary of the week's tasks.
        
        Args:
            tasks: List of all tasks
            week_start: Start date of the week (should be Monday)
            
        Returns:
            Dictionary with week summary information
        """
        week_end = week_start + timedelta(days=6)
        week_tasks = []
        
        # Collect tasks for the week
        for task in tasks:
            task_date = self._get_task_date(task)
            if task_date and week_start <= task_date <= week_end:
                week_tasks.append(task)
        
        # Calculate statistics
        total_tasks = len(week_tasks)
        completed_tasks = len([t for t in week_tasks if t.status == TaskStatus.DONE])
        high_priority = len([t for t in week_tasks if t.priority in [TaskPriority.HIGH, TaskPriority.URGENT]])
        overdue = len([t for t in week_tasks if t.is_overdue()])
        
        # Get daily breakdown
        daily_counts = {}
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_tasks = [t for t in week_tasks if self._get_task_date(t) == day]
            daily_counts[day.strftime('%A')] = len(day_tasks)
        
        return {
            'week_start': week_start,
            'week_end': week_end,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            'high_priority_tasks': high_priority,
            'overdue_tasks': overdue,
            'daily_counts': daily_counts,
            'busiest_day': max(daily_counts, key=daily_counts.get) if daily_counts else None
        }
    
    def set_view_mode(self, mode: str):
        """Set the agenda view mode."""
        if mode in ['day', 'week', 'month']:
            self.view_mode = mode
    
    def set_current_date(self, target_date: date):
        """Set the current date for agenda views."""
        self.current_date = target_date
    
    def navigate_date(self, direction: str):
        """Navigate to different dates based on current view mode."""
        if self.view_mode == "day":
            delta = timedelta(days=1)
        elif self.view_mode == "week":
            delta = timedelta(weeks=1)
        elif self.view_mode == "month":
            # Navigate by month
            if direction == "forward":
                if self.current_date.month == 12:
                    self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
                else:
                    self.current_date = self.current_date.replace(month=self.current_date.month + 1)
                return
            else:  # backward
                if self.current_date.month == 1:
                    self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
                else:
                    self.current_date = self.current_date.replace(month=self.current_date.month - 1)
                return
        else:
            delta = timedelta(days=1)
        
        if direction == "forward":
            self.current_date += delta
        elif direction == "backward":
            self.current_date -= delta
    
    def go_to_today(self):
        """Navigate to today's date."""
        self.current_date = date.today()
    
    def toggle_completed_tasks(self):
        """Toggle showing completed tasks in agenda."""
        self.show_completed = not self.show_completed
    
    def toggle_scheduled_only(self):
        """Toggle showing only scheduled tasks."""
        self.show_scheduled_only = not self.show_scheduled_only
    
    def get_time_block_view(self, tasks: List[Task], target_date: date, 
                           start_hour: int = 6, end_hour: int = 22) -> Dict[str, List[Task]]:
        """
        Get agenda view organized by time blocks for detailed daily planning.
        
        Args:
            tasks: List of tasks
            target_date: Date to show
            start_hour: Starting hour for time blocks
            end_hour: Ending hour for time blocks
            
        Returns:
            Dictionary with time blocks as keys
        """
        time_blocks = OrderedDict()
        day_tasks = self._get_tasks_for_date(tasks, target_date)
        
        # Create hourly time blocks
        for hour in range(start_hour, end_hour + 1):
            time_key = f"{hour:02d}:00"
            hour_tasks = []
            
            for task in day_tasks:
                if task.scheduled_date and task.scheduled_date.hour == hour:
                    hour_tasks.append(task)
            
            if hour_tasks:
                time_blocks[time_key] = self._sort_tasks_by_time(hour_tasks)
        
        # Add unscheduled tasks for the day
        unscheduled_today = [t for t in day_tasks if not t.scheduled_date]
        if unscheduled_today:
            time_blocks["Unscheduled"] = self._sort_tasks_by_priority(unscheduled_today)
        
        return time_blocks
    
    def get_agenda_statistics(self, tasks: List[Task]) -> Dict[str, Any]:
        """Get comprehensive agenda statistics."""
        today = date.today()
        
        return {
            'today_tasks': len(self._get_tasks_for_date(tasks, today)),
            'overdue_tasks': len(self._get_overdue_tasks(tasks, today)),
            'week_tasks': len(self._get_tasks_for_date(tasks, today + timedelta(days=7))),
            'upcoming_deadlines': len(self._get_upcoming_deadlines(tasks, today)),
            'unscheduled_important': len(self._get_unscheduled_important_tasks(tasks)),
            'completion_rate_week': self._calculate_week_completion_rate(tasks, today),
            'average_daily_tasks': self._calculate_average_daily_tasks(tasks),
            'busiest_day_this_week': self._get_busiest_day_this_week(tasks, today)
        }
    
    def _calculate_week_completion_rate(self, tasks: List[Task], base_date: date) -> float:
        """Calculate completion rate for the current week."""
        week_start = base_date - timedelta(days=base_date.weekday())
        week_tasks = []
        
        for i in range(7):
            day = week_start + timedelta(days=i)
            week_tasks.extend(self._get_tasks_for_date(tasks, day))
        
        if not week_tasks:
            return 0.0
        
        completed = len([t for t in week_tasks if t.status == TaskStatus.DONE])
        return (completed / len(week_tasks)) * 100
    
    def _calculate_average_daily_tasks(self, tasks: List[Task]) -> float:
        """Calculate average number of tasks per day over the last 7 days."""
        today = date.today()
        total_tasks = 0
        
        for i in range(7):
            day = today - timedelta(days=i)
            day_tasks = self._get_tasks_for_date(tasks, day)
            total_tasks += len(day_tasks)
        
        return total_tasks / 7
    
    def _get_busiest_day_this_week(self, tasks: List[Task], base_date: date) -> str:
        """Get the busiest day of the current week."""
        week_start = base_date - timedelta(days=base_date.weekday())
        day_counts = {}
        
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_name = day.strftime('%A')
            day_tasks = self._get_tasks_for_date(tasks, day)
            day_counts[day_name] = len(day_tasks)
        
        if not day_counts:
            return "None"
        
        return max(day_counts, key=day_counts.get)