import os
from watchdog.events import FileSystemEventHandler
from debounce import DebounceHandler
from gitignore_utils import load_gitignore, should_ignore
import requests

class FileUploadHandler(FileSystemEventHandler):
    def __init__(self, api_endpoint, session_key, base_path, delay=5):
        self.api_endpoint = api_endpoint
        self.session_key = session_key
        self.base_path = os.path.abspath(base_path)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
            'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Content-Type': 'application/json',
            'Referer': f'https://claude.ai/project/{api_endpoint.split("/")[-2]}',
            'Origin': 'https://claude.ai', 'Connection': 'keep-alive'
        }
        self.cookies = {'sessionKey': session_key, 'lastActiveOrg': api_endpoint.split("/")[4]}
        self.debouncer = DebounceHandler(delay)
        self.gitignore = load_gitignore(self.base_path)
        self.log_callback = None

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def on_modified(self, event):
        if not event.is_directory and not self.should_ignore_file(event.src_path):
            self.debouncer.debounce(self.upload_file, event.src_path)

    def on_created(self, event):
        if not event.is_directory and not self.should_ignore_file(event.src_path):
            self.debouncer.debounce(self.upload_file, event.src_path)

    def should_ignore_file(self, file_path):
            # Check if the file is in the .git directory
            rel_path = os.path.relpath(file_path, self.base_path)
            if rel_path.startswith('.git' + os.path.sep) or rel_path == '.git':
                return True

            # Check if the file should be ignored based on .gitignore
            return should_ignore(self.gitignore, file_path, self.base_path)

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
        if not os.path.isfile(file_path) or self.should_ignore_file(file_path):
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
                self.log(f"Uploaded: {file_name}")
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")

