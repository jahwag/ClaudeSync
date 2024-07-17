import os
import mimetypes
import time
from watchdog.events import FileSystemEventHandler
from .debounce import DebounceHandler
from .gitignore_utils import load_gitignore, should_ignore
import requests

class FileUploadHandler(FileSystemEventHandler):
    def __init__(self, api_endpoint, session_key, base_path, delay=5, max_file_size=1024*320):  # 320 KB limit or roughly 4k lines
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
        self.max_file_size = max_file_size
        self.backoff_time = 1
        self.max_backoff_time = 60
        self.session_expiration_time = 180  # 3 minutes
        self.session_expiration_start = None

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

        # Check file size
        if os.path.getsize(file_path) > self.max_file_size:
            self.log(f"Ignoring large file: {file_path}")
            return True

        # Check file type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and not mime_type.startswith('text/'):
            self.log(f"Ignoring non-text file: {file_path}")
            return True

        # Check if the file should be ignored based on .gitignore
        return should_ignore(self.gitignore, file_path, self.base_path)

    def api_request(self, method, url, **kwargs):
        while True:
            try:
                response = requests.request(method, url, headers=self.headers, cookies=self.cookies, **kwargs)
                if response.status_code == 403:
                    if self.session_expiration_start is None:
                        self.session_expiration_start = time.time()
                    elif time.time() - self.session_expiration_start > self.session_expiration_time:
                        self.log("Session key has likely expired. Please restart ClaudeSync with a new session key.")
                        raise SystemExit(1)

                    self.log(f"Received 403 error. Backing off for {self.backoff_time} seconds.")
                    time.sleep(self.backoff_time)
                    self.backoff_time = min(self.backoff_time * 2, self.max_backoff_time)
                else:
                    self.session_expiration_start = None
                    self.backoff_time = 1
                    response.raise_for_status()
                    return response.json() if response.text else None
            except requests.RequestException as e:
                if response.status_code != 403:
                    self.log(f"API request error: {str(e)}")
                    return None

    def get_documents(self):
        return self.api_request('GET', self.api_endpoint) or []

    def delete_document(self, uuid):
        if self.api_request('DELETE', f"{self.api_endpoint}/{uuid}"):
            self.log(f"Deleted document: {uuid}")

    def delete_all_documents(self):
        for doc in self.get_documents():
            self.delete_document(doc['uuid'])
        self.log("All documents deleted.")

    def upload_file(self, file_path):
        if not os.path.isfile(file_path) or self.should_ignore_file(file_path):
            return
        if os.path.getsize(file_path) == 0:
            self.log(f"Skipping empty file: {file_path}")
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            if not content.strip():
                self.log(f"Skipping file with only whitespace: {file_path}")
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
            self.log(f"Error processing file {file_path}: {str(e)}")