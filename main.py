# main.py
import curses
import sys
from ui import App
from task_manager import TaskManager
from storage import JsonStorage

def main(stdscr):
    """The main function managed by curses.wrapper."""
    curses.curs_set(0) # Hide the cursor
    stdscr.nodelay(True) # Make getch non-blocking to allow for resize events

    # Initialize backend components
    storage = JsonStorage("tasks.json")
    task_manager = TaskManager(storage)
    
    # Get initial screen dimensions
    height, width = stdscr.getmaxyx()

    # Create and run the App
    app = App(stdscr, task_manager, height, width)
    app.run()

if __name__ == "__main__":
    try:
        # curses.wrapper handles all setup, teardown, and fatal errors.
        curses.wrapper(main)
    except Exception as e:
        # Print a clean message on any unhandled error
        print(f"An error occurred: {e}")
    finally:
        print("NeuroPlan has shut down.")