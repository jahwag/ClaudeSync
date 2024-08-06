import os
import time
import json
import logging
from datetime import datetime, timezone
from tqdm import tqdm
from claudesync.utils import compute_md5_hash

logger = logging.getLogger(__name__)

CLAUDESYNC_PATH_COMMENT = "// CLAUDESYNC_PATH: {}\n"


class SyncManager:
    """
    Manages the synchronization process between local files and remote Claude.ai projects.
    Implements timestamp-based deletion for two-way sync.
    """

    def __init__(self, provider, config):
        """
        Initialize the SyncManager with the given provider and configuration.

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
        self.two_way_sync = config.get("two_way_sync", False)
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

    def sync(self, local_files, remote_files):
        """
        Main synchronization method that orchestrates the sync process.

        Args:
            local_files (dict): Dictionary of local file names and their corresponding checksums.
            remote_files (list): List of dictionaries representing remote files.
        """
        last_known_times = self.load_last_known_times()
        remote_files_to_delete = set(rf["file_name"] for rf in remote_files)
        synced_files = set()

        # Update last known times for existing local files
        for local_file in local_files:
            file_path = os.path.join(self.local_path, local_file)
            last_known_times[local_file] = datetime.fromtimestamp(
                os.path.getmtime(file_path), tz=timezone.utc
            )

        # Sync local files to remote
        with tqdm(total=len(local_files), desc="Local → Remote") as pbar:
            for local_file, local_checksum in local_files.items():
                remote_file = next(
                    (rf for rf in remote_files if rf["file_name"] == local_file), None
                )
                if remote_file:
                    self.update_existing_file(
                        local_file,
                        local_checksum,
                        remote_file,
                        remote_files_to_delete,
                        synced_files,
                    )
                else:
                    self.upload_new_file(local_file, synced_files)
                pbar.update(1)

        self.update_local_timestamps(remote_files, synced_files)

        # Two-way sync: handle remote files
        if self.two_way_sync:
            with tqdm(total=len(remote_files), desc="Local ← Remote") as pbar:
                for remote_file in remote_files:
                    if remote_file["file_name"] not in local_files:
                        remote_time = datetime.fromisoformat(
                            remote_file["created_at"].replace("Z", "+00:00")
                        )
                        last_known_time = last_known_times.get(remote_file["file_name"])
                        if last_known_time and remote_time <= last_known_time:
                            # File was deleted locally, delete from remote
                            self.delete_remote_file(remote_file)
                            remote_files_to_delete.remove(remote_file["file_name"])
                        else:
                            # New remote file, sync to local
                            self.sync_remote_to_local(
                                remote_file, remote_files_to_delete, synced_files
                            )
                    else:
                        self.sync_remote_to_local(
                            remote_file, remote_files_to_delete, synced_files
                        )
                    pbar.update(1)

        # Delete remaining files that weren't synced or already deleted
        if self.prune_remote_files:
            for file_to_delete in list(remote_files_to_delete):
                remote_file = next(
                    rf for rf in remote_files if rf["file_name"] == file_to_delete
                )
                self.delete_remote_file(remote_file)

        # Save the updated last known times
        self.save_last_known_times(last_known_times)

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

    def update_local_timestamps(self, remote_files, synced_files):
        """
        Update local file timestamps to match the remote timestamps.

        Args:
            remote_files (list): List of dictionaries representing remote files.
            synced_files (set): Set of file names that have been synchronized.
        """
        for remote_file in remote_files:
            if remote_file["file_name"] in synced_files:
                local_file_path = os.path.join(
                    self.local_path, remote_file["file_name"]
                )
                if os.path.exists(local_file_path):
                    remote_timestamp = datetime.fromisoformat(
                        remote_file["created_at"].replace("Z", "+00:00")
                    ).timestamp()
                    os.utime(local_file_path, (remote_timestamp, remote_timestamp))
                    logger.debug(f"Updated timestamp on local file {local_file_path}")

    def sync_remote_to_local(self, remote_file, remote_files_to_delete, synced_files):
        """
        Synchronize a remote file to the local project (two-way sync).

        Args:
            remote_file (dict): Dictionary representing the remote file.
            remote_files_to_delete (set): Set of remote file names to be considered for deletion.
            synced_files (set): Set of file names that have been synchronized.
        """
        content = remote_file["content"]
        file_path = self._extract_path_from_comment(content)
        if file_path:
            local_file_path = os.path.join(self.local_path, file_path)
        else:
            # If no path comment, use the remote file name
            local_file_path = os.path.join(self.local_path, remote_file["file_name"])

        content_without_comment = self._remove_path_comment(content)
        normalized_content = self.normalize_line_endings(
            content_without_comment, for_local=True
        )

        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

        if os.path.exists(local_file_path):
            self.update_existing_local_file(
                local_file_path,
                remote_file,
                remote_files_to_delete,
                synced_files,
                normalized_content,
            )
        else:
            self.create_new_local_file(
                local_file_path,
                remote_file,
                remote_files_to_delete,
                synced_files,
                normalized_content,
            )

    def update_existing_local_file(
        self,
        local_file_path,
        remote_file,
        remote_files_to_delete,
        synced_files,
        content,
    ):
        """
        Update an existing local file if the remote version is newer.

        Args:
            local_file_path (str): Path to the local file.
            remote_file (dict): Dictionary representing the remote file.
            remote_files_to_delete (set): Set of remote file names to be considered for deletion.
            synced_files (set): Set of file names that have been synchronized.
            content (str): Content of the remote file without the path comment.
        """
        local_mtime = datetime.fromtimestamp(
            os.path.getmtime(local_file_path), tz=timezone.utc
        )
        remote_mtime = datetime.fromisoformat(
            remote_file["created_at"].replace("Z", "+00:00")
        )
        if remote_mtime > local_mtime:
            logger.debug(
                f"Updating local file {remote_file['file_name']} from remote..."
            )
            with open(local_file_path, "w", newline="", encoding="utf-8") as file:
                file.write(content)
            synced_files.add(remote_file["file_name"])
            if remote_file["file_name"] in remote_files_to_delete:
                remote_files_to_delete.remove(remote_file["file_name"])

    def create_new_local_file(
        self,
        local_file_path,
        remote_file,
        remote_files_to_delete,
        synced_files,
        content,
    ):
        """
        Create a new local file from a remote file.

        Args:
            local_file_path (str): Path to the new local file.
            remote_file (dict): Dictionary representing the remote file.
            remote_files_to_delete (set): Set of remote file names to be considered for deletion.
            synced_files (set): Set of file names that have been synchronized.
            content (str): Content of the remote file without the path comment.
        """
        logger.debug(
            f"Creating new local file {remote_file['file_name']} from remote..."
        )
        with tqdm(
            total=1, desc=f"Creating {remote_file['file_name']}", leave=False
        ) as pbar:
            with open(local_file_path, "w", newline="", encoding="utf-8") as file:
                file.write(content)
            pbar.update(1)
        synced_files.add(remote_file["file_name"])
        if remote_file["file_name"] in remote_files_to_delete:
            remote_files_to_delete.remove(remote_file["file_name"])

    def delete_remote_file(self, remote_file):
        """
        Delete a file from the remote project.

        Args:
            remote_file (dict): Dictionary representing the remote file to be deleted.
        """
        logger.debug(f"Deleting {remote_file['file_name']} from remote...")
        with tqdm(
            total=1, desc=f"Deleting {remote_file['file_name']}", leave=False
        ) as pbar:
            self.provider.delete_file(
                self.active_organization_id, self.active_project_id, remote_file["uuid"]
            )
            pbar.update(1)
        time.sleep(self.upload_delay)

        # Remove the file from last_known_times
        last_known_times = self.load_last_known_times()
        last_known_times.pop(remote_file["file_name"], None)
        self.save_last_known_times(last_known_times)

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
