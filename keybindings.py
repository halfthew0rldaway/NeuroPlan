# keybindings.py
#
# Description:
# This file defines the keybindings for the application.
# Keeping them in a separate file makes them easier to manage and customize.
# The format is a list of tuples: (key, action, description).
#

from textual.binding import Binding

# Bindings that are active across all screens
APP_BINDINGS = [
    Binding("q", "quit", "Quit"),
    Binding("v", "toggle_view", "Toggle View"),
]

# Bindings specific to the Planner screen
PLANNER_SCREEN_BINDINGS = [
    Binding("a", "add_task", "Add Task"),
    Binding("d", "delete_task", "Delete"),
    Binding("x", "toggle_done", "Toggle Done"),
    Binding("j", "cursor_down", "Cursor Down", show=False),
    Binding("k", "cursor_up", "Cursor Up", show=False),
]