# web_graph.py
import json
from typing import Optional
import re
import html

def generate_web_graph(task_manager, output_path="index.html", central_node_id: Optional[str] = None):
    nodes, edges, task_ids = [], [], {task.id for task in task_manager.tasks.values()}
    full_node_data = {}

    for task in task_manager.tasks.values():
        # --- NEW NODE STYLING ---
        node = {
            "id": task.id,
            "label": task.title,
            "shape": "dot",  # Use 'dot' for a circle
            "size": 15,      # Default size for normal nodes
            "font": {
                "color": "#d3d3d3",
                "strokeWidth": 0,
                "align": "center"
            },
            "color": {
                "border": "#61afef",
                "background": "#61afef"
            }
        }

        # --- SUN STYLING FOR CENTRAL NODE ---
        if task.id == central_node_id:
            node["size"] = 40  # Make the central node bigger
            node["color"] = {
                "border": "#E6DB74",  # Yellow
                "background": "#E6DB74"
            }
            node["font"] = {"color": "#E6DB74", "size": 20}

        nodes.append(node)

        # Store all data for the sidebar
        full_node_data[task.id] = {
            "title": html.escape(task.title),
            "author": html.escape(getattr(task, 'author', None) or 'N/A'),
            "status": task.status.value,
            "priority": task.priority.value,
            "description": html.escape(task.description).replace('\n', '<br>'),
        }

        if task.parent_id and task.parent_id in task_ids:
            edges.append({"from": task.id, "to": task.parent_id, "arrows": "to"})

        link_pattern = re.compile(r'\[\[([a-f0-9\-]+)\]\]')
        for target_id in link_pattern.findall(task.description):
            if target_id in task_ids:
                edges.append({"from": task.id, "to": target_id, "arrows": "to", "dashes": True})

    nodes_json = json.dumps(nodes, indent=2)
    edges_json = json.dumps(edges, indent=2)
    full_data_json = json.dumps(full_node_data, indent=2)

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>TermiPlan - Graph View</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; background-color: #282c34; color: #abb2bf; font-family: monospace; overflow: hidden; }}
        #graph-container {{ position: absolute; left: 0; top: 0; width: 70%; height: 100%; }}
        #sidebar {{ position: absolute; right: 0; top: 0; width: 30%; height: 100%; background-color: #21252b; box-sizing: border-box; padding: 20px; overflow-y: auto; border-left: 2px solid #1c1e24; }}
        h2 {{ color: #61afef; }} p {{ line-height: 1.6; }} b {{ color: #c678dd; }}
    </style>
</head>
<body>
    <div id="graph-container"></div>
    <div id="sidebar"><h2>Select a Node</h2><p>Click on a task to see details.</p></div>
    <script>
        const nodes = new vis.DataSet({nodes_json});
        const edges = new vis.DataSet({edges_json});
        const fullData = {full_data_json};
        const container = document.getElementById('graph-container');
        const sidebar = document.getElementById('sidebar');
        const data = {{ nodes: nodes, edges: edges }};
        const options = {{
            edges: {{ color: '#5c6370' }},
            physics: {{ solver: 'forceAtlas2Based' }}
        }};
        const network = new vis.Network(container, data, options);

        network.on('click', function (params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const nodeData = fullData[nodeId];
                if (nodeData) {{
                    sidebar.innerHTML = `
                        <h2>${{nodeData.title}}</h2>
                        <p><b>Author:</b> ${{nodeData.author}}</p>
                        <p><b>Status:</b> ${{nodeData.status}}</p>
                        <p><b>Priority:</b> ${{nodeData.priority}}</p>
                        <hr>
                        <p>${{nodeData.description}}</p>
                    `;
                }}
            }} else {{
                 sidebar.innerHTML = '<h2>Select a Node</h2><p>Click on a task to see details.</p>';
            }}
        }});
    </script>
</body>
</html>
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)