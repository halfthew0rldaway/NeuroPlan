# reminder.py
#
# Description:
# This file contains the logic for the reminder system. It has been simplified
# for the Curses UI. It checks for tasks that are due and can be used by the
# main UI to display a status message.
#

import datetime
from typing import List
from task_manager import TaskManager, Task

class ReminderManager:
    """Manages checking for and triggering reminders for tasks."""

    def __init__(self, task_manager: TaskManager):
        """
        Initializes the ReminderManager.
        
        Args:
            task_manager: An instance of TaskManager to get task data from.
        """
        self.task_manager = task_manager
        self.notified_task_ids = set()

    def check_reminders(self) -> List[Task]:
        """
        Checks all tasks for due dates and returns a list of tasks that
        are due and have not been notified about yet.
        
        Returns:
            A list of Task objects that are currently due.
        """
        now = datetime.datetime.now()
        due_tasks = []

        all_tasks = self.task_manager.tasks.values()
        for task in all_tasks:
            # Check if task is due, not done, and not already notified
            if (
                task.due_date
                and task.due_date <= now
                and task.id not in self.notified_task_ids
                and task.status != "DONE"
            ):
                due_tasks.append(task)
                self.notified_task_ids.add(task.id)
                
        return due_tasks