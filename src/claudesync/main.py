import blessed
import time
import argparse
import json
import os
import sys
from watchdog.observers import Observer
from .manual_auth import get_session_key, get_or_update_config_value, get_config, save_config
from .file_handler import FileUploadHandler
from .api_utils import fetch_user_id, fetch_projects, select_project

class ClaudeSyncTUI:
    def __init__(self, session_key, watch_dir, user_id, project_id, delay):
        self.term = blessed.Terminal()
        self.session_key = session_key
        self.watch_dir = watch_dir
        self.user_id = user_id
        self.project_id = project_id
        self.delay = delay
        self.log_messages = []
        self.observer = None
        self.handler = None
        self.scroll_position = 0
        self.max_log_lines = 1000
        self.auto_scroll = True
        self.is_syncing = False

    def setup(self):
        if not self.user_id:
            self.user_id = fetch_user_id(self.session_key)
        if not self.project_id:
            projects = fetch_projects(self.user_id, self.session_key)
            self.project_id = select_project(projects, self.user_id, self.session_key)

        api_endpoint = f"https://claude.ai/api/organizations/{self.user_id}/projects/{self.project_id}/docs"
        self.handler = FileUploadHandler(api_endpoint, self.session_key, self.watch_dir, self.delay)
        self.handler.log_callback = self.add_log_message

        self.observer = Observer()
        self.observer.schedule(self.handler, self.watch_dir, recursive=True)

    def initial_sync(self):
        self.is_syncing = True
        self.add_log_message("Starting initial synchronization...")
        for root, dirs, files in os.walk(self.watch_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if not self.handler.should_ignore_file(file_path):
                    self.handler.upload_file(file_path)
                    self.draw()  # Redraw the TUI after each file upload
        self.add_log_message("Initial synchronization completed.")
        self.is_syncing = False

    def add_log_message(self, message):
        self.log_messages.append(message)
        if len(self.log_messages) > self.max_log_lines:
            self.log_messages.pop(0)
        if self.auto_scroll:
            self.scroll_to_bottom()

    def scroll_to_bottom(self):
        self.scroll_position = max(0, len(self.log_messages) - (self.term.height - 11))

    def draw(self):
        print(self.term.clear())
        print(self.term.move_y(0) + self.term.black_on_skyblue(self.term.center('ClaudeSync TUI')))

        print(self.term.move_y(2) + f"Watching directory: {self.watch_dir}")
        print(f"Upload delay: {self.delay} seconds")
        print(f"User ID: {self.user_id}")
        print(f"Project ID: {self.project_id}")
        print(f"Auto-scroll: {'ON' if self.auto_scroll else 'OFF'}")

        if self.is_syncing:
            print(self.term.move_y(7) + self.term.red("Initial sync in progress..."))

        print(self.term.move_y(8) + self.term.black_on_skyblue(self.term.center('Recent Activity')))

        log_height = self.term.height - 12
        visible_logs = self.log_messages[self.scroll_position:self.scroll_position + log_height]
        for i, message in enumerate(visible_logs):
            print(self.term.move_y(10 + i) + message)

        print(self.term.move_y(self.term.height - 1) + "Press 'q' to quit, 'j'/'k' to scroll, 'a' to toggle auto-scroll")

    def run(self):
        with self.term.cbreak(), self.term.hidden_cursor():
            self.draw()  # Initial draw before starting sync
            self.initial_sync()
            self.observer.start()
            while True:
                self.draw()
                inp = self.term.inkey(timeout=0.1)
                if inp == 'q':
                    break
                elif inp == 'j':
                    self.auto_scroll = False
                    self.scroll_position = min(len(self.log_messages) - 1, self.scroll_position + 1)
                elif inp == 'k':
                    self.auto_scroll = False
                    self.scroll_position = max(0, self.scroll_position - 1)
                elif inp == 'a':
                    self.auto_scroll = not self.auto_scroll
                    if self.auto_scroll:
                        self.scroll_to_bottom()

        self.observer.stop()
        self.observer.join()


def main():
    parser = argparse.ArgumentParser(description="Sync local files with Claude.ai projects.")
    parser.add_argument("--session-key", help="Session key for authentication")
    parser.add_argument("--watch-dir", default=".", help="Directory to watch for changes")
    parser.add_argument("--user-id", help="User ID for Claude API")
    parser.add_argument("--project-id", help="Project ID for Claude API")
    parser.add_argument("--delay", type=int, help="Delay in seconds before uploading")
    args = parser.parse_args()

    config = get_config()

    # Get or update session key
    session_key = args.session_key or get_session_key()

    # Get or update watch directory
    watch_dir = args.watch_dir or get_or_update_config_value('watch_dir', "Enter the directory to watch", ".")

    # Get or fetch user ID
    user_id = args.user_id or config.get('user_id')
    if not user_id:
        print("Fetching user ID...")
        user_id = fetch_user_id(session_key)
        config['user_id'] = user_id
        save_config(config)
        print(f"User ID fetched and stored: {user_id}")

    # Get or select project ID
    project_id = args.project_id or config.get('project_id')
    if not project_id:
        print("No project ID found. Fetching projects...")
        projects = fetch_projects(user_id, session_key)
        project_id = select_project(projects, user_id, session_key)
        config['project_id'] = project_id
        save_config(config)
        print(f"Project ID selected and stored: {project_id}")
    else:
        use_stored = input(f"Found stored project ID: {project_id}. Use it? (y/n): ").strip().lower()
        if use_stored != 'y':
            projects = fetch_projects(user_id, session_key)
            project_id = select_project(projects, user_id, session_key)
            config['project_id'] = project_id
            save_config(config)
            print(f"New project ID selected and stored: {project_id}")

    # Get or update delay
    delay = args.delay or int(get_or_update_config_value('delay', "Enter the delay in seconds before uploading", "5"))

    tui = ClaudeSyncTUI(session_key, watch_dir, user_id, project_id, delay)
    tui.setup()
    tui.run()

if __name__ == "__main__":
    main()