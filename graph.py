# graph.py
#
# Description:
# This module generates an ASCII art representation of the task graph.
# It identifies [[id]] links between tasks, uses a simple physics simulation
# (force-directed layout) to position the nodes, and then renders the result
# onto a 2D character grid. This version is updated to center the layout
# around a specific node.
#

import re
import math
from typing import List, Dict, Tuple, Optional
from task_manager import Task

# --- 1. Graph Construction ---
def find_links(tasks: List[Task]) -> List[Tuple[str, str]]:
    """Parse all task descriptions to find [[id]] links."""
    links = []
    task_ids = {task.id for task in tasks}
    link_pattern = re.compile(r'\[\[([a-f0-9\-]+)\]\]')

    for task in tasks:
        # Find links in the description
        found_ids = link_pattern.findall(task.description)
        for target_id in found_ids:
            if target_id in task_ids and task.id != target_id:
                links.append((task.id, target_id))
        # Also add parent-child links for structure
        if task.parent_id and task.parent_id in task_ids:
            links.append((task.id, task.parent_id))
            
    return list(set(links)) # Return unique links

# --- 2. Force-Directed Layout ---
def force_layout(
    nodes: Dict[str, Dict],
    edges: List[Tuple[str, str]],
    width: int,
    height: int,
    iterations: int = 100,
    central_node_id: Optional[str] = None
) -> Dict[str, Dict]:
    """A simple Fruchterman-Reingold-inspired force-directed layout algorithm."""
    if not nodes: return {}
    # Ideal distance between nodes
    k = math.sqrt((width * height) / len(nodes))
    
    for _ in range(iterations):
        # Calculate repulsive forces (all nodes push each other away)
        for i, node1 in nodes.items():
            node1['dx'] = 0.0
            node1['dy'] = 0.0
            for j, node2 in nodes.items():
                if i != j:
                    dx = node1['x'] - node2['x']
                    dy = node1['y'] - node2['y']
                    distance = math.sqrt(dx**2 + dy**2) + 0.01
                    if distance > 0:
                        force = k**2 / distance
                        node1['dx'] += dx / distance * force
                        node1['dy'] += dy / distance * force

        # Calculate attractive forces (edges pull nodes together)
        for source, target in edges:
            if source not in nodes or target not in nodes: continue
            node1 = nodes[source]
            node2 = nodes[target]
            dx = node1['x'] - node2['x']
            dy = node1['y'] - node2['y']
            distance = math.sqrt(dx**2 + dy**2) + 0.01
            force = distance**2 / k
            
            # Make central node's pull stronger
            if central_node_id and (source == central_node_id or target == central_node_id):
                 force *= 2.5

            node1['dx'] -= dx / distance * force
            node2['dx'] += dx / distance * force
            node1['dy'] -= dy / distance * force
            node2['dy'] += dy / distance * force

        # Apply forces and center graph
        for node_id, node in nodes.items():
            # If a central node is selected, pin it to the center
            if node_id == central_node_id:
                node['x'] = width / 2
                node['y'] = height / 2
                continue

            # Limit total displacement
            disp_x = node['dx'] * 0.01
            disp_y = node['dy'] * 0.01
            node['x'] += disp_x
            node['y'] += disp_y
            
            # Prevent nodes from escaping the canvas
            node['x'] = min(width - 1, max(0, node['x']))
            node['y'] = min(height - 1, max(0, node['y']))
            
    return nodes

# --- 3. ASCII Rendering ---
def draw_line(grid, x1, y1, x2, y2):
    """Draw a line on the grid using Bresenham's algorithm."""
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    
    while True:
        if 0 <= y1 < len(grid) and 0 <= x1 < len(grid[0]) and grid[y1][x1] == ' ':
            grid[y1][x1] = '.'
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x1 += sx
        if e2 <= dx:
            err += dx
            y1 += sy

def render_to_grid(nodes: Dict, edges: List, width: int, height: int, central_node_id: Optional[str]) -> List[List[str]]:
    """Render the positioned nodes and edges onto a character grid."""
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Draw edges first
    for source, target in edges:
        if source not in nodes or target not in nodes: continue
        n1, n2 = nodes[source], nodes[target]
        draw_line(grid, int(n1['x']), int(n1['y']), int(n2['x']), int(n2['y']))
    
    # Draw nodes on top
    for node_id, data in nodes.items():
        x, y = int(data['x']), int(data['y'])
        # Truncate title and add emphasis to central node
        is_central = node_id == central_node_id
        title = data['title'][:10]
        label = f"<{title}>" if is_central else f"[{title}]"
        
        if 0 <= y < height and 0 <= x < width - len(label):
            for i, char in enumerate(label):
                if x + i < width:
                    grid[y][x+i] = char
    return grid

# --- Main Function ---
def generate_ascii_graph(tasks: List[Task], width: int, height: int, central_node_id: Optional[str] = None) -> str:
    """
    The main function to generate the ASCII graph from a list of tasks.
    """
    if not tasks:
        return "No tasks to build a graph from."

    # 1. Build graph data structures
    nodes_map = {
        task.id: {
            "title": task.title,
            "x": width / 2 + (hash(task.id) % 10 - 5), # Start near center
            "y": height / 2 + (hash(task.title) % 10 - 5),
        } for task in tasks
    }
    edges = find_links(tasks)

    if not edges and len(tasks) > 1:
        return "No links or parent-child relationships found between tasks."

    # 2. Calculate layout
    positioned_nodes = force_layout(nodes_map, edges, width - 12, height - 4, central_node_id=central_node_id)

    # 3. Render to grid
    grid = render_to_grid(positioned_nodes, edges, width, height, central_node_id)

    # 4. Convert grid to string
    return "\n".join("".join(row) for row in grid)