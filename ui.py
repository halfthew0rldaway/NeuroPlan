# ui.py
import curses
import textwrap
import webbrowser
import http.server
import socketserver
import threading
import time

from task_manager import Task, Status, Priority
from web_graph import generate_web_graph

# Using only the 8 standard, universal colors with A_BOLD for neon effect
THEME_COLORS = {
    'border_fg': curses.COLOR_CYAN, 'border_bg': -1,
    'text_fg': curses.COLOR_GREEN, 'text_bg': -1,  # Changed to Green for Neon effect
    'selected_fg': curses.COLOR_BLACK, 'selected_bg': curses.COLOR_GREEN,
    'title_fg': curses.COLOR_YELLOW, 'title_bg': -1,
    'dim_fg': curses.COLOR_WHITE, 'dim_bg': -1,
    'priority_a_fg': curses.COLOR_RED, 'priority_a_bg': -1,
    'priority_b_fg': curses.COLOR_YELLOW, 'priority_b_bg': -1,
    'priority_c_fg': curses.COLOR_GREEN, 'priority_c_bg': -1,
    'priority_d_fg': curses.COLOR_WHITE, 'priority_d_bg': -1,
}

# --- NEW: Global variables to manage the server state ---
SERVER_THREAD = None
HTTPD_SERVER = None
# ---------------------------------------------------------

def start_server(port=8000, directory='.'):
    global SERVER_THREAD, HTTPD_SERVER
    if SERVER_THREAD and SERVER_THREAD.is_alive(): return
    
    socketserver.TCPServer.allow_reuse_address = True
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs): super().__init__(*args, directory=directory, **kwargs)

    # --- MODIFIED: Store the server instance in our global variable ---
    httpd = socketserver.TCPServer(("", port), Handler)
    HTTPD_SERVER = httpd
    # -----------------------------------------------------------------

    def serve_forever(h):
        with h: h.serve_forever()

    SERVER_THREAD = threading.Thread(target=serve_forever, args=(httpd,))
    SERVER_THREAD.daemon = True
    SERVER_THREAD.start()

class TextEditor:
    # ... (TextEditor class remains exactly the same as before) ...
    def __init__(self, window, initial_text=""):
        self.win = window; self.lines = initial_text.split('\n') if initial_text else [""]
        self.cursor_y, self.cursor_x = 0, 0; self.top_line, self.left_char = 0, 0
    def run(self):
        curses.curs_set(1); self.win.keypad(True)
        while True:
            self.draw();
            try:
                key = self.win.getch()
            except curses.error:
                time.sleep(0.01)
                continue
            if key == 24: return None
            if key == 19: return "\n".join(self.lines)
            if key == curses.KEY_RESIZE:
                continue
            self.handle_input(key)
    def handle_input(self, key):
        if key in [curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_BACKSPACE, 127, 8, 263, 10] or 32 <= key <= 126:
            if key == curses.KEY_UP:
                if self.cursor_y > 0: self.cursor_y -= 1
            elif key == curses.KEY_DOWN:
                if self.cursor_y < len(self.lines) - 1: self.cursor_y += 1
            elif key == curses.KEY_LEFT:
                if self.cursor_x > 0: self.cursor_x -= 1
            elif key == curses.KEY_RIGHT:
                if self.cursor_x < len(self.lines[self.cursor_y]): self.cursor_x += 1
            elif key in [curses.KEY_BACKSPACE, 127, 8, 263]:
                if self.cursor_x > 0:
                    line = self.lines[self.cursor_y]; self.lines[self.cursor_y] = line[:self.cursor_x-1] + line[self.cursor_x:]; self.cursor_x -= 1
                elif self.cursor_y > 0:
                    line = self.lines.pop(self.cursor_y); self.cursor_y -= 1; self.cursor_x = len(self.lines[self.cursor_y]); self.lines[self.cursor_y] += line
            elif key == 10:
                line = self.lines[self.cursor_y]; self.lines.insert(self.cursor_y + 1, line[self.cursor_x:]); self.lines[self.cursor_y] = line[:self.cursor_x]; self.cursor_y += 1; self.cursor_x = 0
            elif 32 <= key <= 126:
                char = chr(key); line = self.lines[self.cursor_y]; self.lines[self.cursor_y] = line[:self.cursor_x] + char + line[self.cursor_x:]; self.cursor_x += 1
            if self.cursor_y < len(self.lines): self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
            else: self.cursor_x = 0
    def draw(self):
        self.win.erase(); height, width = self.win.getmaxyx()
        if self.cursor_y < self.top_line: self.top_line = self.cursor_y
        if self.cursor_y >= self.top_line + height: self.top_line = self.cursor_y - height + 1
        if self.cursor_x < self.left_char: self.left_char = self.cursor_x
        if self.cursor_x >= self.left_char + width: self.left_char = self.cursor_x - width + 1
        for i in range(height -1):
            line_idx = self.top_line + i
            if line_idx < len(self.lines):
                safe_line = self.lines[line_idx][self.left_char:]
                self.win.addstr(i, 0, safe_line[:width-1])
        self.win.move(self.cursor_y - self.top_line, self.cursor_x - self.left_char); self.win.refresh()


class App:
    def __init__(self, stdscr, task_manager, height, width):
        self.stdscr = stdscr; self.task_manager = task_manager; self.height, self.width = height, width
        self.running = True; self.theme = {}
        self.active_pane = 'list'
        self.list_scroll_offset = 0; self.detail_scroll_offset = 0; self.selected_index = 0
        self.planner_tasks = []

    def setup_colors(self):
        self.theme = {}
        if curses.has_colors():
            try:
                curses.start_color()
                color_id = 1
                for name, fg_color in THEME_COLORS.items():
                    if name.endswith('_fg'):
                        bg_name = name.replace('_fg', '_bg')
                        bg_color = THEME_COLORS.get(bg_name, -1)
                        try:
                            curses.init_pair(color_id, fg_color, bg_color)
                            self.theme[name.replace('_fg', '')] = curses.color_pair(color_id)
                        except curses.error:
                            self.theme[name.replace('_fg', '')] = curses.A_NORMAL
                        color_id += 1
            except curses.error:
                pass

    def _get_color(self, name, attr=curses.A_NORMAL):
        return self.theme.get(name, curses.A_NORMAL) | attr

    def _handle_resize(self):
        self.height, self.width = self.stdscr.getmaxyx()
        self.stdscr.clear()
        self.stdscr.refresh()
        self.main_win.resize(self.height, self.width)
        self.main_win.mvwin(0, 0)

    # --- NEW: Method to shut down the server gracefully ---
    def _shutdown_server(self):
        global HTTPD_SERVER, SERVER_THREAD
        if HTTPD_SERVER:
            try:
                HTTPD_SERVER.shutdown()
                HTTPD_SERVER.server_close()
            except Exception as e:
                # Failsafe in case of any error during shutdown
                pass
            HTTPD_SERVER = None
            SERVER_THREAD = None
    # ----------------------------------------------------

    def run(self):
        self.setup_colors()
        self.main_win = curses.newwin(self.height, self.width, 0, 0)
        self.main_win.keypad(True)
        self.main_win.nodelay(True)

        while self.running:
            self.draw()
            try:
                key = self.main_win.getch()
            except curses.error:
                time.sleep(0.01)
                key = -1

            if key != -1:
                if key == curses.KEY_RESIZE:
                    self._handle_resize()
                else:
                    self.handle_input(key)
        
        # --- MODIFIED: Call the shutdown method on exit ---
        self._shutdown_server()
        # --------------------------------------------------

    def get_text_input(self, prompt):
        popup_h, popup_w = 3, self.width // 2
        popup_y, popup_x = (self.height - popup_h) // 2, (self.width - popup_w) // 2
        popup = curses.newwin(popup_h, popup_w, popup_y, popup_x)
        popup.attron(self._get_color('border')); popup.box(); popup.attroff(self._get_color('border'))
        popup.addstr(0, 2, f" {prompt} ", self._get_color('title'))
        curses.curs_set(1); curses.echo(); popup.keypad(True)
        
        input_win = popup.derwin(1, popup_w - 4, 1, 2)
        input_str = input_win.getstr().decode('utf-8')

        curses.noecho(); curses.curs_set(0)
        return input_str

    def run_editor(self, initial_text):
        editor_h, editor_w = self.height - 4, self.width - 4
        editor_y, editor_x = 2, 2
        editor_win = curses.newwin(editor_h, editor_w, editor_y, editor_x)
        editor_win.attron(self._get_color('border')); editor_win.box(); editor_win.attroff(self._get_color('border'))
        editor_win.addstr(0, 2, " Editor (Ctrl+S Save, Ctrl+X Cancel) ", self._get_color('title'))
        content_win = editor_win.derwin(editor_h - 2, editor_w - 2, 1, 1)
        
        editor = TextEditor(content_win, initial_text)
        result = editor.run()
        
        curses.curs_set(0)
        self.stdscr.clear(); self.stdscr.refresh()
        return result

    def handle_input(self, key):
        num_tasks = len(self.planner_tasks)
        if key == ord('q'): 
            self.running = False # This will trigger the shutdown
        elif key == 9: self.active_pane = 'detail' if self.active_pane == 'list' else 'list'
        elif key in [curses.KEY_DOWN, ord('j')]:
            if self.active_pane == 'list':
                if self.selected_index < num_tasks - 1: self.selected_index += 1; self.detail_scroll_offset = 0
            else: self.detail_scroll_offset += 1
        elif key in [curses.KEY_UP, ord('k')]:
            if self.active_pane == 'list':
                if self.selected_index > 0: self.selected_index -= 1; self.detail_scroll_offset = 0
            else:
                if self.detail_scroll_offset > 0: self.detail_scroll_offset -= 1
        elif key == ord('x'):
            if num_tasks > 0: self.task_manager.delete_task(self.planner_tasks[self.selected_index]['id']); self.selected_index = max(0, self.selected_index - 1)
        elif key == ord('d'):
            if num_tasks > 0:
                task = self.planner_tasks[self.selected_index]['task']
                new_desc = self.run_editor(task.description)
                if new_desc is not None: self.task_manager.update_task(task.id, description=new_desc)
        elif key == ord('a'):
            parent_id = self.planner_tasks[self.selected_index]['id'] if num_tasks > 0 else None
            new_title = self.get_text_input("New Task Title")
            if new_title:
                new_desc = self.run_editor("")
                if new_desc is not None:
                    new_author = self.get_text_input("Author Name")
                    self.task_manager.add_task(title=new_title, description=new_desc, author=new_author, parent_id=parent_id)
        elif key == ord('e'):
            if num_tasks > 0:
                task = self.planner_tasks[self.selected_index]['task']
                new_title = self.get_text_input(f"Edit Title")
                if new_title: self.task_manager.update_task(task.id, title=new_title)
        elif key == ord('g'):
            if num_tasks > 0:
                generate_web_graph(self.task_manager, central_node_id=self.planner_tasks[self.selected_index]['id'])
                start_server(); webbrowser.open('http://localhost:8000/index.html')

    def draw(self):
        self.main_win.erase()
        self.main_win.attron(self._get_color('border')); self.main_win.box(); self.main_win.attroff(self._get_color('border'))
        self.draw_header(); self.draw_footer(); self.draw_planner_view(); self.main_win.refresh()

    def draw_header(self): self.main_win.addstr(0, 2, " NeuroPlan ", self._get_color('title', curses.A_BOLD))
    def draw_footer(self):
        footer_text = " (q)uit (Tab)pane (j/k)scroll (a)dd (d)esc (x)del (g)raph "
        self.main_win.addstr(self.height - 1, 2, footer_text[:self.width - 3], self._get_color('dim', curses.A_DIM))
    
    def _flatten_tasks(self, tasks, indent=0):
        flat_list = []
        for task in sorted(tasks, key=lambda t: t.created_at):
            flat_list.append({"task": task, "indent": indent, "id": task.id})
            if task.children: flat_list.extend(self._flatten_tasks(task.children, indent + 1))
        return flat_list

# In ui.py

    def draw_planner_view(self):
        pane_width = self.width // 2
        list_pane = self.main_win.derwin(self.height - 2, pane_width - 1, 1, 1)
        detail_pane = self.main_win.derwin(self.height - 2, self.width - pane_width - 2, 1, pane_width)
        
        # --- MODIFIED: Use more distinct colors for active/inactive panes ---
        is_list_active = self.active_pane == 'list'
        list_border_color = self._get_color('title') if is_list_active else self._get_color('border')
        detail_border_color = self._get_color('title') if not is_list_active else self._get_color('border')
        # -------------------------------------------------------------------

        list_pane.attron(list_border_color); list_pane.box(); list_pane.attroff(list_border_color)
        detail_pane.attron(detail_border_color); detail_pane.box(); detail_pane.attroff(detail_border_color)

        # --- NEW: Add titles to the panes ---
        list_title_color = self._get_color('title', curses.A_BOLD) if is_list_active else self._get_color('text')
        detail_title_color = self._get_color('title', curses.A_BOLD) if not is_list_active else self._get_color('text')
        
        list_pane.addstr(0, 2, " Tasks ", list_title_color)
        detail_pane.addstr(0, 2, " Details ", detail_title_color)
        # ------------------------------------
        
        self.planner_tasks = self._flatten_tasks(self.task_manager.get_task_tree())
        if self.selected_index >= len(self.planner_tasks): self.selected_index = max(0, len(self.planner_tasks) - 1)
        
        list_height, list_width = list_pane.getmaxyx()
        list_height -= 2
        
        if self.selected_index < self.list_scroll_offset: self.list_scroll_offset = self.selected_index
        if self.selected_index >= self.list_scroll_offset + list_height: self.list_scroll_offset = self.selected_index - list_height + 1
        
        for i in range(list_height):
            draw_idx = self.list_scroll_offset + i
            if draw_idx < len(self.planner_tasks):
                item = self.planner_tasks[draw_idx]
                prefix = '  ' * item['indent']
                icon = "✔" if item['task'].status == Status.DONE else "○"
                line = f"{prefix}{icon} {item['task'].title}"
                line = line[:list_width - 4] # Truncate
                
                color = self._get_color('selected') if draw_idx == self.selected_index else (self._get_color('dim', curses.A_DIM) if item['task'].status == Status.DONE else self._get_color('text'))
                list_pane.addstr(i + 1, 2, line, color)

        if self.planner_tasks:
            task = self.planner_tasks[self.selected_index]['task']
            y, x = 1, 2
            h, w = detail_pane.getmaxyx()
            
            all_lines = []
            all_lines.append( (task.title, self._get_color('title', curses.A_BOLD)) )
            all_lines.append( ("", self._get_color('text')) )
            p_key = f'priority_{task.priority.value.lower()}'
            p_color = self._get_color(p_key)
            metadata = [
                ("ID:", task.id, self._get_color('text')),
                ("Author:", getattr(task, 'author', 'N/A'), self._get_color('text')),
                ("Status:", task.status.value, self._get_color('text')),
                ("Priority:", task.priority.value, p_color),
                ("Created:", task.created_at.strftime('%Y-%m-%d %H:%M'), self._get_color('text'))
            ]
            all_lines.extend(metadata)
            all_lines.append( ("", self._get_color('text')) )
            all_lines.append( ("Description", self._get_color('title')) )
            desc_lines = textwrap.wrap(task.description, w - 4)
            for line in desc_lines: all_lines.append((line, self._get_color('text')))
            
            if len(all_lines) > h - 2:
                if self.detail_scroll_offset > len(all_lines) - (h - 2): self.detail_scroll_offset = len(all_lines) - (h - 2)
            else: self.detail_scroll_offset = 0

            for i in range(h - 2):
                draw_idx = self.detail_scroll_offset + i
                if draw_idx < len(all_lines):
                    line_data = all_lines[draw_idx]
                    if len(line_data) == 3:
                        label, value, color = line_data
                        detail_pane.addstr(y + i, x, f"{label:<10}", self._get_color('dim', curses.A_DIM))
                        detail_pane.addstr(str(value), color)
                    else:
                        line, color = line_data
                        detail_pane.addstr(y + i, x, line, color)
        
        list_pane.refresh(); detail_pane.refresh()