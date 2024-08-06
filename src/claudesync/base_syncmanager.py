import os
import json
import logging
import time
from datetime import datetime
from tqdm import tqdm
from claudesync.utils import compute_md5_hash

logger = logging.getLogger(__name__)

CLAUDESYNC_PATH_COMMENT = "// CLAUDESYNC_PATH: {}\n"


class BaseSyncManager:
    """
    Base class for managing synchronization between local files and remote Claude.ai projects.
    """

    def __init__(self, provider, config):
        """
        Initialize the BaseSyncManager with the given provider and configuration.

        Args:
            provider (Provider): The provider instance to interact with the remote storage.
            config (dict): Configuration dictionary containing sync settings.
        """
        self.provider = provider
        self.config = config
        self.active_organization_id = config.get("active_organization_id")
        self.active_project_id = config.get("active_project_id")
        self.local_path = config.get("local_path")
        self.upload_delay = config.get("upload_delay", 0.5)
        self.autocrlf = config.get("autocrlf", "true")
        self.last_known_times_file = os.path.join(
            self.local_path, ".claudesync", "last_known_times.json"
        )
        self.prune_remote_files = config.get("prune_remote_files", False)

    def load_last_known_times(self):
        """
        Load the last known modification times of files from a JSON file.

        Returns:
            dict: A dictionary of file names to their last known modification times.
        """
        os.makedirs(os.path.dirname(self.last_known_times_file), exist_ok=True)
        if os.path.exists(self.last_known_times_file):
            with open(self.last_known_times_file, "r") as f:
                return {k: datetime.fromisoformat(v) for k, v in json.load(f).items()}
        return {}

    def save_last_known_times(self, last_known_times):
        """
        Save the last known modification times of files to a JSON file.

        Args:
            last_known_times (dict): A dictionary of file names to their last known modification times.
        """
        os.makedirs(os.path.dirname(self.last_known_times_file), exist_ok=True)
        with open(self.last_known_times_file, "w") as f:
            json.dump({k: v.isoformat() for k, v in last_known_times.items()}, f)

    def normalize_line_endings(self, content, for_local=True):
        """
        Normalize line endings based on the autocrlf setting.

        Args:
            content (str): The content to normalize.
            for_local (bool): True if normalizing for local file, False for remote.

        Returns:
            str: The content with normalized line endings.
        """
        # First, standardize to LF
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        if for_local:
            if self.autocrlf == "true" and os.name == "nt":
                # Convert to CRLF for Windows when autocrlf is true
                content = content.replace("\n", "\r\n")
        else:  # for remote
            if self.autocrlf == "input":
                # Keep LF for remote when autocrlf is input
                pass
            elif self.autocrlf == "true":
                # Convert to LF for remote when autocrlf is true
                content = content.replace("\r\n", "\n")

        return content

    def _add_path_comment(self, content, file_path):
        """
        Add a path comment to the content if it doesn't already exist.

        Args:
            content (str): The file content.
            file_path (str): The full path of the file.

        Returns:
            str: The content with the path comment added.
        """
        relative_path = os.path.relpath(file_path, self.local_path)
        if not content.startswith("// CLAUDESYNC_PATH:"):
            return CLAUDESYNC_PATH_COMMENT.format(relative_path) + content
        return content

    def _remove_path_comment(self, content):
        """
        Remove the path comment from the content if it exists.

        Args:
            content (str): The file content.

        Returns:
            str: The content with the path comment removed.
        """
        lines = content.split("\n", 1)
        if lines and lines[0].startswith("// CLAUDESYNC_PATH:"):
            return lines[1] if len(lines) > 1 else ""
        return content

    def _extract_path_from_comment(self, content):
        """
        Extract the file path from the path comment if it exists.

        Args:
            content (str): The file content.

        Returns:
            str or None: The extracted file path, or None if no path comment is found.
        """
        lines = content.split("\n", 1)
        if lines and lines[0].startswith("// CLAUDESYNC_PATH:"):
            return lines[0].split(": ", 1)[1].strip()
        return None

    def sync(self, local_files, remote_files):
        """
        Main synchronization method that orchestrates the sync process.
        This method should be implemented by derived classes.

        Args:
            local_files (dict): Dictionary of local file names and their corresponding checksums.
            remote_files (list): List of dictionaries representing remote files.
        """
        raise NotImplementedError("Sync method must be implemented by derived classes.")

    def get_all_local_files(self):
        """
        Get a set of all files in the local directory.

        Returns:
            set: A set of all file paths relative to the local_path.
        """
        all_files = set()
        for root, _, files in os.walk(self.local_path):
            for file in files:
                relative_path = os.path.relpath(
                    os.path.join(root, file), self.local_path
                )
                all_files.add(relative_path)
        return all_files

    def update_existing_file(
        self,
        local_file,
        local_checksum,
        remote_file,
        remote_files_to_delete,
        synced_files,
    ):
        """
        Update an existing file on the remote if it has changed locally or if the path comment needs to be added.

        Args:
            local_file (str): Name of the local file.
            local_checksum (str): MD5 checksum of the local file content.
            remote_file (dict): Dictionary representing the remote file.
            remote_files_to_delete (set): Set of remote file names to be considered for deletion.
            synced_files (set): Set of file names that have been synchronized.
        """
        file_path = os.path.join(self.local_path, local_file)
        with open(file_path, "r", encoding="utf-8") as file:
            local_content = file.read()

        local_content_with_comment = self._add_path_comment(local_content, file_path)
        local_content_normalized = self.normalize_line_endings(
            local_content_with_comment, for_local=False
        )
        local_checksum_with_comment = compute_md5_hash(local_content_normalized)

        remote_content = remote_file["content"]
        remote_checksum = compute_md5_hash(remote_content)

        if local_checksum_with_comment != remote_checksum:
            logger.debug(f"Updating {local_file} on remote...")
            with tqdm(total=2, desc=f"Updating {local_file}", leave=False) as pbar:
                self.provider.delete_file(
                    self.active_organization_id,
                    self.active_project_id,
                    remote_file["uuid"],
                )
                pbar.update(1)
                self.provider.upload_file(
                    self.active_organization_id,
                    self.active_project_id,
                    local_file,
                    local_content_normalized,
                )
                pbar.update(1)
            time.sleep(self.upload_delay)
            synced_files.add(local_file)
        remote_files_to_delete.remove(local_file)

    def upload_new_file(self, local_file, synced_files):
        """
        Upload a new file to the remote project.

        Args:
            local_file (str): Name of the local file to be uploaded.
            synced_files (set): Set of file names that have been synchronized.
        """
        logger.debug(f"Uploading new file {local_file} to remote...")
        file_path = os.path.join(self.local_path, local_file)
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        content_with_comment = self._add_path_comment(content, file_path)
        normalized_content = self.normalize_line_endings(
            content_with_comment, for_local=False
        )
        with tqdm(total=1, desc=f"Uploading {local_file}", leave=False) as pbar:
            self.provider.upload_file(
                self.active_organization_id,
                self.active_project_id,
                local_file,
                normalized_content,
            )
            pbar.update(1)
        time.sleep(self.upload_delay)
        synced_files.add(local_file)
