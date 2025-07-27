# task_manager.py
#
# Description:
# This file contains the core logic for managing tasks. It defines the Task
# data structure and a TaskManager class that handles all CRUD (Create, Read,
# Update, Delete) operations. This decouples the task logic from the UI and
# storage.
#

import uuid
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

# Using Enum for controlled vocabulary for status and priority.
class Status(str, Enum):
    """Enumeration for task status."""
    TODO = "TODO"
    DONE = "DONE"
    WAITING = "WAITING"
    
class Priority(str, Enum):
    """Enumeration for task priority."""
    HIGH = "A"
    MEDIUM = "B"
    LOW = "C"
    NONE = "D" # Using D for None to allow sorting

@dataclass
class Task:
    """
    Represents a single task or note.
    
    Attributes:
        title: The main title of the task.
        id: A unique identifier for linking (e.g., [[id]]).
        description: A longer description, can contain links to other tasks.
        author: The person who created the task.
        status: The current state of the task (TODO, DONE, etc.).
        priority: The priority level of the task.
        due_date: An optional due date and time for the task.
        tags: A list of tags for filtering and organization.
        children: A list of sub-tasks for creating a tree structure.
        parent_id: The ID of the parent task, if it's a sub-task.
        created_at: The timestamp when the task was created.
    """
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    author: Optional[str] = None # NEW: Author field added
    status: Status = Status.TODO
    priority: Priority = Priority.NONE
    due_date: Optional[datetime.datetime] = None
    tags: List[str] = field(default_factory=list)
    children: List['Task'] = field(default_factory=list)
    parent_id: Optional[str] = None
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)

class TaskManager:
    """
    Handles all business logic for tasks.
    It holds the tasks in memory and provides methods to manipulate them.
    """
    def __init__(self, storage):
        """
        Initializes the TaskManager with a storage backend.
        
        Args:
            storage: An instance of a storage class (e.g., JsonStorage)
                     that has load() and save() methods.
        """
        self.storage = storage
        # Tasks are stored in a dictionary for quick O(1) lookups by ID.
        self.tasks: Dict[str, Task] = {}
        self.load_tasks()

    def load_tasks(self):
        """Loads tasks from the storage backend and organizes them into a tree."""
        all_tasks_data = self.storage.load()
        temp_tasks = {data['id']: Task(**data) for data in all_tasks_data}
        
        # Clear current state
        self.tasks = {}
        top_level_tasks = []

        # Reconstruct the tree structure from parent_id references
        for task_id, task in temp_tasks.items():
            # Clear any stale children data from the stored file
            task.children = []
            if task.parent_id and task.parent_id in temp_tasks:
                parent = temp_tasks[task.parent_id]
                parent.children.append(task)
            else:
                # If no parent, it's a top-level task
                task.parent_id = None # Ensure parent_id is clean
                top_level_tasks.append(task)

        # The self.tasks dict should contain all tasks, for easy lookup
        self.tasks = temp_tasks

    def save_tasks(self):
        """Saves all tasks to the storage backend."""
        # We save a flat list of all tasks; the tree is reconstructed on load.
        self.storage.save(list(self.tasks.values()))

    def add_task(
        self,
        title: str,
        parent_id: Optional[str] = None,
        **kwargs
    ) -> Task:
        """
        Adds a new task.
        
        Args:
            title: The title of the new task.
            parent_id: The ID of the parent task to nest this task under.
            **kwargs: Other task attributes like description, due_date, etc.
            
        Returns:
            The newly created Task object.
        """
        new_task = Task(title=title, parent_id=parent_id, **kwargs)
        self.tasks[new_task.id] = new_task
        
        if parent_id and parent_id in self.tasks:
            parent_task = self.tasks[parent_id]
            parent_task.children.append(new_task)
            
        self.save_tasks()
        return new_task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieves a task by its ID."""
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs: Any):
        """
        Updates an existing task's attributes.
        
        Args:
            task_id: The ID of the task to update.
            **kwargs: The attributes to update (e.g., title="New Title").
        """
        task = self.get_task(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            self.save_tasks()

    def delete_task(self, task_id: str):
        """

        Deletes a task and all its sub-tasks recursively.
        
        Args:
            task_id: The ID of the task to delete.
        """
        task_to_delete = self.get_task(task_id)
        if not task_to_delete:
            return

        # Recursively delete all children first
        for child in list(task_to_delete.children):
            self.delete_task(child.id)

        # Remove from parent's children list
        if task_to_delete.parent_id and task_to_delete.parent_id in self.tasks:
            parent = self.tasks[task_to_delete.parent_id]
            parent.children = [c for c in parent.children if c.id != task_id]

        # Remove from the main task dictionary
        if task_id in self.tasks:
            del self.tasks[task_id]
        
        self.save_tasks()

    def get_task_tree(self) -> List[Task]:
        """
        Returns a list of top-level tasks (tasks without a parent).
        The full tree can be traversed from these tasks via their `children` attribute.
        """
        return sorted(
            [task for task in self.tasks.values() if not task.parent_id],
            key=lambda t: (t.priority.value, t.created_at)
        )

    def get_all_tasks_flat(self) -> List[Task]:
        """Returns a flat list of all tasks, sorted by due date."""
        return sorted(
            [task for task in self.tasks.values() if task.due_date],
            key=lambda t: t.due_date if t.due_date else datetime.datetime.max
        )