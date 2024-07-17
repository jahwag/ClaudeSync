import os
from .config_manager import ConfigManager
from .utils import calculate_checksum

class ChecksumManager:
    def __init__(self):
        self.config = ConfigManager()

    def get_checksum(self, project_id, filename, location):
        checksums = self.config.get('project_checksums', {}).get(project_id, {}).get(location, {})
        return checksums.get(filename)

    def save_checksum(self, project_id, filename, location, checksum):
        project_checksums = self.config.get('project_checksums', {})
        if project_id not in project_checksums:
            project_checksums[project_id] = {}
        if location not in project_checksums[project_id]:
            project_checksums[project_id][location] = {}
        project_checksums[project_id][location][filename] = checksum
        self.config.set('project_checksums', project_checksums)

    def delete_checksum(self, project_id, filename, location):
        project_checksums = self.config.get('project_checksums', {})
        if project_id in project_checksums and location in project_checksums[project_id]:
            if filename in project_checksums[project_id][location]:
                del project_checksums[project_id][location][filename]
                self.config.set('project_checksums', project_checksums)

    def update_local_checksum(self, project_id, local_path):
        if os.path.exists(local_path):
            checksum = calculate_checksum(local_path)
            self.save_checksum(project_id, os.path.basename(local_path), 'local', checksum)
        else:
            self.delete_checksum(project_id, os.path.basename(local_path), 'local')