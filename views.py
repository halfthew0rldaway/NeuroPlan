# views.py
#
# Description:
# This file contains all the UI components of the application, built using
# the Textual TUI framework. It defines the main application class, screens for
# different views (Planner, Agenda, Graph), and custom widgets for displaying
# tasks and their details.
#

import datetime
import re
from typing import Optional
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Footer, Header, Static, Tree
from textual.widget import Widget
from rich.text import Text
from rich.panel import Panel
from rich.style import Style

# Local imports from other project files
from storage import JsonStorage
from task_manager import TaskManager, Task, Status, Priority
from keybindings import APP_BINDINGS, PLANNER_SCREEN_BINDINGS
from graph import generate_ascii_graph
from reminder import ReminderManager

# --- Custom Widgets ---

class TaskTree(Tree):
    """A Tree widget for displaying and interacting with tasks."""

    def __init__(self, task_manager: TaskManager, **kwargs):
        super().__init__("✅ Planner", **kwargs)
        self.task_manager = task_manager
        self.set_styles()

    def set_styles(self):
        """Set visual style for the tree."""
        self.guide_style = "dim"
        self.show_root = False

    def render_label(self, node) -> Text:
        """Render a custom label for each task in the tree."""
        task: Task = node.data
        if not task:
            return Text(node.label)

        # Style based on status
        style = Style()
        icon = "○"
        if task.status == Status.DONE:
            style = Style(strike=True, color="rgb(100,100,100)")
            icon = "✔"
        elif task.status == Status.WAITING:
            icon = "…"

        # Priority marker
        priority_marker = f"[{task.priority.value}]" if task.priority != Priority.NONE else ""

        # Compose label
        label = Text()
        label.append(f"{icon} ", style=style)
        if priority_marker:
            label.append(f"{priority_marker} ", style="yellow")
        label.append(task.title, style=style)
        if task.tags:
            label.append(f" #{' #'.join(task.tags)}", style="cyan dim")

        return label

    def _add_task_to_tree(self, task: Task, parent_node):
        """Recursively add a task and its children to the tree."""
        node = parent_node.add(task.title, data=task)
        for child in sorted(task.children, key=lambda t: (t.priority.value, t.created_at)):
            self._add_task_to_tree(child, node)

    def reload(self):
        """Clear and reload the tree from the TaskManager."""
        self.clear()
        task_tree = self.task_manager.get_task_tree()
        for task in task_tree:
            self._add_task_to_tree(task, self.root)
        self.root.expand_all()

class TaskDetail(Static):
    """A widget to display the details of a selected task."""

    def update_content(self, task: Optional[Task]):
        """Update the display with the details of the given task."""
        if task:
            content = Text()
            content.append(f"ID: {task.id}\n", style="dim")
            content.append(f"Status: {task.status.value}\n", style="bold")
            content.append(f"Priority: {task.priority.value}\n", style="bold")
            if task.due_date:
                content.append(f"Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}\n")
            if task.tags:
                content.append(f"Tags: {' '.join(task.tags)}\n", style="cyan")
            content.append("-" * 30)
            content.append(f"\n{task.description}")
            self.update(Panel(content, title=task.title, border_style="green"))
        else:
            self.update(Panel("Select a task to see details.", title="Details", border_style="dim"))


# --- Modal Screens for Input ---

class EditTaskScreen(ModalScreen):
    """A modal screen for adding or editing a task."""
    def __init__(self, task: Optional[Task] = None, parent_id: Optional[str] = None):
        super().__init__()
        self.task = task
        self.parent_id = parent_id

    def compose(self) -> ComposeResult:
        yield Container(
            Static("This is a placeholder for an edit/add form.\n"
                   "Press 's' to save a new sample task or 'escape' to cancel.", id="edit_form"),
            id="edit_dialog"
        )

    def on_key(self, event) -> None:
        if event.key == "s":
            # In a real app, you'd collect data from Input widgets.
            result_data = {
                "title": f"New Task @ {datetime.datetime.now().strftime('%H:%M')}",
                "description": "This is a sample description.",
                "tags": ["sample"],
                "parent_id": self.parent_id
            }
            self.dismiss(result_data)

# --- Main Application Screens ---

class PlannerScreen(Screen):
    """The main screen showing the task tree and details."""
    BINDINGS = PLANNER_SCREEN_BINDINGS

    def compose(self) -> ComposeResult:
        # Use self.app to access managers
        self.task_tree = TaskTree(self.app.task_manager, id="task_tree")
        self.task_detail = TaskDetail("Select a task", id="task_detail")
        yield Header()
        yield Horizontal(
            VerticalScroll(self.task_tree, id="left-pane"),
            VerticalScroll(self.task_detail, id="right-pane"),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Load data when the screen is mounted."""
        self.task_tree.reload()
        self.task_tree.focus()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Update the detail view when a task is selected."""
        task: Optional[Task] = event.node.data
        self.task_detail.update_content(task)

    def _get_selected_task_id(self) -> Optional[str]:
        """Get the ID of the currently selected task in the tree."""
        if self.task_tree.cursor_node and self.task_tree.cursor_node.data:
            return self.task_tree.cursor_node.data.id
        return None

    def action_add_task(self) -> None:
        """Action to add a new task."""
        parent_id = self._get_selected_task_id()
        def after_add(data: Optional[dict]):
            if data:
                self.app.task_manager.add_task(**data)
                self.task_tree.reload()
        self.app.push_screen(EditTaskScreen(parent_id=parent_id), after_add)

    def action_delete_task(self) -> None:
        """Action to delete the selected task."""
        task_id = self._get_selected_task_id()
        if task_id:
            self.app.task_manager.delete_task(task_id)
            self.task_tree.reload()
            self.task_detail.update_content(None)
            self.app.notify(f"Task {task_id[:8]} deleted.", title="Deleted")

    def action_toggle_done(self) -> None:
        """Action to toggle the status of the selected task."""
        task_id = self._get_selected_task_id()
        if task_id:
            task = self.app.task_manager.get_task(task_id)
            if task:
                new_status = Status.DONE if task.status != Status.DONE else Status.TODO
                self.app.task_manager.update_task(task_id, status=new_status)
                self.task_tree.reload() # Reload to update style
                self.task_detail.update_content(self.app.task_manager.get_task(task_id))

class AgendaScreen(Screen):
    """A screen for viewing tasks in a time-based agenda."""
    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="agenda_table")
        yield Footer()

    def on_mount(self) -> None:
        """Populate the agenda table."""
        table = self.query_one(DataTable)
        table.add_columns("Due Date", "Priority", "Status", "Title")
        tasks = self.app.task_manager.get_all_tasks_flat()
        today = datetime.date.today()
        for task in tasks:
            if task.due_date and task.status != Status.DONE:
                row_style = ""
                if task.due_date.date() < today:
                    row_style = "red"
                elif task.due_date.date() == today:
                    row_style = "bold green"

                table.add_row(
                    task.due_date.strftime("%Y-%m-%d %H:%M"),
                    task.priority.value,
                    task.status.value,
                    task.title,
                    key=task.id,
                    style=row_style
                )

class GraphScreen(Screen):
    """A screen to display the ASCII graph of task connections."""
    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static(id="graph_view"))
        yield Footer()

    def on_mount(self) -> None:
        """Generate and display the graph."""
        graph_view = self.query_one("#graph_view")
        tasks = list(self.app.task_manager.tasks.values())
        try:
            ascii_graph = generate_ascii_graph(tasks, width=200, height=50)
            graph_view.update(Text(ascii_graph, justify="left"))
        except Exception as e:
            graph_view.update(f"Could not generate graph: {e}")

# --- The Main App ---

class ProductivityApp(App):
    """A terminal-based productivity application."""

    CSS_PATH = "style.tcss"
    BINDINGS = APP_BINDINGS

    # FIX: Removed parentheses () from screen classes.
    # The dictionary should hold the class types, not instances.
    SCREENS = {
        "planner": PlannerScreen,
        "agenda": AgendaScreen,
        "graph": GraphScreen,
    }
    
    SCREENS_CYCLE = ["planner", "agenda", "graph"]
    current_screen_index = 0

    def __init__(self):
        super().__init__()
        self.storage = JsonStorage("tasks.json")
        self.task_manager = TaskManager(self.storage)
        self.reminder_manager = ReminderManager(self.task_manager)
        self._create_dummy_css()

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        self.push_screen("planner")
        self.set_interval(60, self.check_reminders)

    def check_reminders(self) -> None:
        """Callback to check for and show reminders."""
        due_tasks = self.reminder_manager.check_reminders()
        for task in due_tasks:
            self.notify(
                f"'{task.title}' is due!",
                title="Reminder",
                severity="warning",
            )

    def action_toggle_view(self) -> None:
        """Cycle to the next screen."""
        self.current_screen_index = (self.current_screen_index + 1) % len(self.SCREENS_CYCLE)
        next_screen_name = self.SCREENS_CYCLE[self.current_screen_index]
        self.push_screen(next_screen_name)

    def _create_dummy_css(self):
        """Creates a default stylesheet if one doesn't exist."""
        try:
            with open(self.CSS_PATH, "x", encoding='utf-8') as f:
                f.write("""
/* style.tcss - A simple stylesheet for the productivity app */
Screen {
    background: #282c34;
    color: #abb2bf;
    layout: vertical;
}
Header {
    dock: top;
    height: 1;
    background: #21252b;
}
Footer {
    dock: bottom;
    height: 1;
    background: #21252b;
}
#left-pane {
    width: 40%;
    border-right: heavy #4b5263;
}
#right-pane {
    width: 60%;
    padding: 0 1;
}
Tree {
    padding: 1;
}
TaskDetail {
    padding: 1;
}
#edit_dialog {
    border: thick #5c6370;
    padding: 1 2;
    width: 60;
    height: 10;
    background: #3e4452;
    align: center middle;
}
DataTable {
    padding: 1;
}
#graph_view {
    padding: 1;
}
""")
        except FileExistsError:
            pass    