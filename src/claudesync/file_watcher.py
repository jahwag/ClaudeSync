import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .checksum_manager import ChecksumManager
from .config_manager import ConfigManager

class ClaudeSyncHandler(FileSystemEventHandler):
    def __init__(self, project_id, local_path):
        self.project_id = project_id
        self.local_path = local_path
        self.checksum_manager = ChecksumManager()

    def on_modified(self, event):
        if not event.is_directory:
            self.process_file_event(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self.process_file_event(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            relative_path = os.path.relpath(event.src_path, self.local_path)
            self.checksum_manager.delete_checksum(self.project_id, relative_path, 'local')

    def process_file_event(self, file_path):
        if self.should_ignore(file_path):
            return
        relative_path = os.path.relpath(file_path, self.local_path)
        self.checksum_manager.update_local_checksum(self.project_id, file_path)

    def should_ignore(self, file_path):
        # Implement .gitignore rules here
        # For simplicity, we'll just ignore .git folder and files over 200 KB
        if '.git' in file_path:
            return True
        if os.path.getsize(file_path) > 200 * 1024:
            return True
        return False

class FileWatcher:
    def __init__(self):
        self.config = ConfigManager()
        self.observers = []

    def start(self):
        projects = self.config.get('projects', {})
        for project_id, local_path in projects.items():
            event_handler = ClaudeSyncHandler(project_id, local_path)
            observer = Observer()
            observer.schedule(event_handler, local_path, recursive=True)
            observer.start()
            self.observers.append(observer)

    def stop(self):
        for observer in self.observers:
            observer.stop()
        for observer in self.observers:
            observer.join()