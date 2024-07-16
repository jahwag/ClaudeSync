import time
import os
import argparse
import sys
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests
from threading import Timer

class DebounceHandler:
    def __init__(self, delay):
        self.delay = delay
        self.timer = None

    def debounce(self, func, *args):
        def debounced_func():
            self.timer = None
            func(*args)

        if self.timer is not None:
            self.timer.cancel()
        self.timer = Timer(self.delay, debounced_func)
        self.timer.start()

class FileUploadHandler(FileSystemEventHandler):
    def __init__(self, api_endpoint, session_key, base_path, delay=5):
        self.api_endpoint = api_endpoint
        self.session_key = session_key
        self.base_path = base_path
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
            'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Content-Type': 'application/json',
            'Referer': f'https://claude.ai/project/{api_endpoint.split("/")[-2]}',
            'Origin': 'https://claude.ai', 'Connection': 'keep-alive'
        }
        self.cookies = {'sessionKey': session_key, 'lastActiveOrg': api_endpoint.split("/")[4]}
        self.debouncer = DebounceHandler(delay)

    def on_modified(self, event):
        if not event.is_directory:
            self.debouncer.debounce(self.upload_file, event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self.debouncer.debounce(self.upload_file, event.src_path)

    def api_request(self, method, url, **kwargs):
        try:
            response = requests.request(method, url, headers=self.headers, cookies=self.cookies, **kwargs)
            response.raise_for_status()
            return response.json() if response.text else None
        except requests.RequestException as e:
            print(f"API request error: {str(e)}")
            return None

    def get_documents(self):
        return self.api_request('GET', self.api_endpoint) or []

    def delete_document(self, uuid):
        if self.api_request('DELETE', f"{self.api_endpoint}/{uuid}"):
            print(f"Deleted document: {uuid}")

    def delete_all_documents(self):
        for doc in self.get_documents():
            self.delete_document(doc['uuid'])
        print("All documents deleted.")

    def upload_file(self, file_path):
        if not os.path.isfile(file_path):
            return
        if os.path.getsize(file_path) == 0:
            print(f"Skipping empty file: {file_path}")
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            if not content.strip():
                print(f"Skipping file with only whitespace: {file_path}")
                return

            rel_path = os.path.relpath(file_path, self.base_path)
            file_name = rel_path.replace(os.path.sep, '/')

            for doc in self.get_documents():
                if doc['file_name'] == file_name:
                    self.delete_document(doc['uuid'])
            payload = {"file_name": file_name, "content": content}
            if self.api_request('POST', self.api_endpoint, json=payload):
                print(f"Uploaded: {file_name}")
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")

def watch_directory(path, api_endpoint, session_key, delay):
    observer = Observer()
    handler = FileUploadHandler(api_endpoint, session_key, path, delay)
    observer.schedule(handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print("Invalid JSON in config.json. Please check the file format.")
        sys.exit(1)

def main():
    config = load_config()

    parser = argparse.ArgumentParser(description="Sync local files with Claude.ai projects.")
    parser.add_argument("--session-key", required=True, help="Session key for authentication")
    parser.add_argument("--watch-dir", required=True, help="Directory to watch for changes")
    parser.add_argument("--user-id", help="User ID for Claude API")
    parser.add_argument("--project-id", help="Project ID for Claude API")
    parser.add_argument("--delete-all", action="store_true", help="Delete all documents in the project")
    parser.add_argument("--delay", type=int, default=5, help="Delay in seconds before uploading (default: 5)")
    args = parser.parse_args()

    user_id = args.user_id or config.get('user_id')
    project_id = args.project_id or config.get('project_id')

    if not user_id or not project_id:
        print("Error: user_id and project_id must be provided either in config.json or as command-line arguments.")
        sys.exit(1)

    api_endpoint = f"https://claude.ai/api/organizations/{user_id}/projects/{project_id}/docs"

    handler = FileUploadHandler(api_endpoint, args.session_key, args.watch_dir, args.delay)

    if args.delete_all:
        handler.delete_all_documents()
        print("All documents deleted.")
        sys.exit(0)
    else:
        print(f"Watching directory: {args.watch_dir}")
        print(f"Upload delay: {args.delay} seconds")
        observer = Observer()
        observer.schedule(handler, args.watch_dir, recursive=True)
        observer.start()
        try:
            while True:
                pass
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

if __name__ == "__main__":
    main()