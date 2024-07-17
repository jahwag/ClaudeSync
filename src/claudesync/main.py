import blessed
import time
import argparse
import json
import os
import sys
from watchdog.observers import Observer
from .file_handler import FileUploadHandler
from .api_utils import fetch_user_id, fetch_projects, select_project, create_project

from .manual_auth import get_session_key

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

    def add_log_message(self, message):
        self.log_messages.append(message)
        if len(self.log_messages) > 10:
            self.log_messages.pop(0)

    def draw(self):
        print(self.term.clear())
        print(self.term.move_y(0) + self.term.black_on_skyblue(self.term.center('ClaudeSync TUI')))

        print(self.term.move_y(2) + f"Watching directory: {self.watch_dir}")
        print(f"Upload delay: {self.delay} seconds")
        print(f"User ID: {self.user_id}")
        print(f"Project ID: {self.project_id}")

        print(self.term.move_y(7) + self.term.black_on_skyblue(self.term.center('Recent Activity')))
        for i, message in enumerate(self.log_messages):
            print(self.term.move_y(9 + i) + message)

        print(self.term.move_y(20) + "Press 'q' to quit")

    def run(self):
        with self.term.cbreak(), self.term.hidden_cursor():
            self.observer.start()
            while True:
                self.draw()
                inp = self.term.inkey(timeout=1)
                if inp == 'q':
                    break
        self.observer.stop()
        self.observer.join()

def main():
    parser = argparse.ArgumentParser(description="Sync local files with Claude.ai projects.")
    parser.add_argument("--session-key", help="Session key for authentication")
    parser.add_argument("--watch-dir", default=".", help="Directory to watch for changes")
    parser.add_argument("--user-id", help="User ID for Claude API (optional, will be fetched if not provided)")
    parser.add_argument("--project-id", help="Project ID for Claude API")
    parser.add_argument("--delay", type=int, default=5, help="Delay in seconds before uploading (default: 5)")
    args = parser.parse_args()

    # Load config from file if it exists
    config = {}
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            config = json.load(f)

    # If session key is not provided, use the manual input method
    session_key = args.session_key
    if not session_key:
        session_key = get_session_key()

    watch_dir = args.watch_dir
    user_id = args.user_id or config.get('user_id')
    project_id = args.project_id or config.get('project_id')
    delay = args.delay

    tui = ClaudeSyncTUI(session_key, watch_dir, user_id, project_id, delay)
    tui.setup()
    tui.run()

if __name__ == "__main__":
    main()
