# claudesync/sync_manager.py

import os
import time
import threading
from pathlib import Path
from .config_manager import ConfigManager
from .checksum_manager import ChecksumManager
from .providers.claude_ai import ClaudeAIProvider
from .utils import calculate_checksum

class SyncManager:
    def __init__(self):
        self.config = ConfigManager()
        self.checksum_manager = ChecksumManager()
        self.provider = ClaudeAIProvider()
        self.running = False
        self.thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._sync_loop)
            self.thread.start()

    def stop(self):
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()

    def _sync_loop(self):
        while self.running:
            self._sync_all_projects()
            time.sleep(self.config.get('sync_interval', 300))  # Default to 5 minutes

    def _sync_all_projects(self):
        projects = self.config.get('projects', {})
        for project_id, local_path in projects.items():
            self._sync_project(project_id, Path(local_path))

    def _sync_project(self, project_id, local_path):
        organization_id = self.config.get('active_organization_id')
        if not organization_id:
            print(f"No active organization set. Skipping sync for project {project_id}")
            return

        try:
            remote_files = self.provider.list_files(organization_id, project_id)
            local_files = self._get_local_files(local_path)

            for remote_file in remote_files:
                filename = remote_file['name']
                remote_checksum = remote_file['content']  # Assuming content is the checksum
                local_checksum = self.checksum_manager.get_checksum(project_id, filename, 'local')

                if local_checksum != remote_checksum:
                    if filename in local_files:
                        # Update remote file
                        self.provider.upload_file(organization_id, project_id, local_path / filename)
                        print(f"Updated remote file: {filename}")
                    else:
                        # Delete remote file
                        self.provider.delete_file(organization_id, project_id, remote_file['uuid'])
                        print(f"Deleted remote file: {filename}")

            for filename, local_checksum in local_files.items():
                if not any(remote_file['name'] == filename for remote_file in remote_files):
                    # Upload new local file
                    self.provider.upload_file(organization_id, project_id, local_path / filename)
                    print(f"Uploaded new file: {filename}")

        except Exception as e:
            print(f"Error syncing project {project_id}: {str(e)}")

    def _get_local_files(self, local_path):
        files = {}
        for root, _, filenames in os.walk(local_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                if not self._should_ignore(file_path):
                    files[filename] = calculate_checksum(file_path)
        return files

    def _should_ignore(self, file_path):
        # Implement .gitignore rules here
        # For simplicity, we'll just ignore .git folder and files over 200 KB
        if '.git' in file_path:
            return True
        if os.path.getsize(file_path) > 200 * 1024:
            return True
        return False