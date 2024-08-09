import os
import time
import logging
from datetime import datetime, timezone
from tqdm import tqdm
from claudesync.utils import compute_md5_hash

logger = logging.getLogger(__name__)

class SyncManager:
    def __init__(self, provider, config):
        """
        Initialize the SyncManager with the given provider and configuration.

        Args:
            provider (Provider): The provider instance to interact with the remote storage.
            config (dict): Configuration dictionary containing sync settings such as:
                           - active_organization_id (str): ID of the active organization.
                           - active_project_id (str): ID of the active project.
                           - local_path (str): Path to the local directory to be synchronized.
                           - upload_delay (float, optional): Delay between upload operations in seconds. Defaults to 0.5.
                           - two_way_sync (bool, optional): Flag to enable two-way synchronization. Defaults to False.
        """
        self.provider = provider
        self.config = config
        self.active_organization_id = config.get("active_organization_id")
        self.active_project_id = config.get("active_project_id")
        self.local_paths = config.get_local_paths()
        self.upload_delay = config.get("upload_delay", 0.5)
        self.two_way_sync = config.get("two_way_sync", False)

    def sync(self, local_files, remote_files):
        """
        Main synchronization method that orchestrates the sync process.

        This method manages the synchronization between local and remote files. It handles the
        synchronization from local to remote, updates local timestamps, performs two-way sync if enabled,
        and deletes remote files that are no longer present locally.

        Args:
            local_files (dict): Dictionary of local file names and their corresponding checksums.
            remote_files (list): List of dictionaries representing remote files, each containing:
                                 - "file_name" (str): Name of the file.
                                 - "content" (str): Content of the file.
                                 - "created_at" (str): Timestamp when the file was created in ISO format.
                                 - "uuid" (str): Unique identifier of the remote file.
        """
        remote_files_to_delete = set(rf["file_name"] for rf in remote_files)
        synced_files = set()

        with tqdm(total=len(local_files), desc="Local → Remote") as pbar:
            for full_path, local_checksum in local_files.items():
                remote_file = next(
                    (rf for rf in remote_files if rf["file_name"] == full_path), None
                )
                if remote_file:
                    self.update_existing_file(
                        full_path,
                        local_checksum,
                        remote_file,
                        remote_files_to_delete,
                        synced_files,
                    )
                else:
                    self.upload_new_file(full_path, synced_files)
                pbar.update(1)

        self.update_local_timestamps(remote_files, synced_files)

        if self.two_way_sync:
            with tqdm(total=len(remote_files), desc="Local ← Remote") as pbar:
                for remote_file in remote_files:
                    self.sync_remote_to_local(
                        remote_file, remote_files_to_delete, synced_files
                    )
                    pbar.update(1)
        for file_to_delete in list(remote_files_to_delete):
            self.delete_remote_files(file_to_delete, remote_files)
            pbar.update(1)

    def upload_new_file(self, full_path, synced_files):
        """
        Update an existing file on the remote if it has changed locally.

        This method compares the local and remote file checksums. If they differ, it deletes the old remote file
        and uploads the new version from the local file.

        Args:
            local_file (str): Name of the local file.
            local_checksum (str): MD5 checksum of the local file content.
            remote_file (dict): Dictionary representing the remote file.
            remote_files_to_delete (set): Set of remote file names to be considered for deletion.
            synced_files (set): Set of file names that have been synchronized.
        """        
        logger.debug(f"Uploading new file {full_path} to remote...")
        with open(full_path, "r", encoding="utf-8") as file:
            content = file.read()
        with tqdm(total=1, desc=f"Uploading {full_path}", leave=False) as pbar:
            self.provider.upload_file(
                self.active_organization_id, self.active_project_id, full_path, content
            )
            pbar.update(1)
        time.sleep(self.upload_delay)
        synced_files.add(full_path)

    def update_existing_file(self, full_path, local_checksum, remote_file, remote_files_to_delete, synced_files):
        remote_checksum = compute_md5_hash(remote_file["content"])
        if local_checksum != remote_checksum:
            logger.debug(f"Updating {full_path} on remote...")
            with tqdm(total=2, desc=f"Updating {full_path}", leave=False) as pbar:
                self.provider.delete_file(
                    self.active_organization_id,
                    self.active_project_id,
                    remote_file["uuid"],
                )
                pbar.update(1)
                with open(full_path, "r", encoding="utf-8") as file:
                    content = file.read()
                self.provider.upload_file(
                    self.active_organization_id,
                    self.active_project_id,
                    full_path,
                    content,
                )
                pbar.update(1)
            time.sleep(self.upload_delay)
            synced_files.add(full_path)
        remote_files_to_delete.remove(full_path)

    def update_local_timestamps(self, remote_files, synced_files):
        """
        Update local file timestamps to match the remote timestamps.

        This method updates the modification timestamps of local files to match their corresponding
        remote file timestamps if they have been synchronized.

        Args:
            remote_files (list): List of dictionaries representing remote files.
            synced_files (set): Set of file names that have been synchronized.
        """
        for remote_file in remote_files:
            if remote_file["file_name"] in synced_files:
                local_file_path = remote_file["file_name"]
                if os.path.exists(local_file_path):
                    remote_timestamp = datetime.fromisoformat(
                        remote_file["created_at"].replace("Z", "+00:00")
                    ).timestamp()
                    os.utime(local_file_path, (remote_timestamp, remote_timestamp))
                    logger.debug(f"Updated timestamp on local file {local_file_path}")

    def sync_remote_to_local(self, remote_file, remote_files_to_delete, synced_files):
        """
        Synchronize a remote file to the local project (two-way sync).

        This method checks if the remote file exists locally. If it does, it updates the file
        if the remote version is newer. If it doesn't exist locally, it creates a new local file.

        Args:
            remote_file (dict): Dictionary representing the remote file.
            remote_files_to_delete (set): Set of remote file names to be considered for deletion.
            synced_files (set): Set of file names that have been synchronized.
        """
        local_file_path = remote_file["file_name"]
        if os.path.exists(local_file_path):
            self.update_existing_local_file(
                local_file_path, remote_file, remote_files_to_delete, synced_files
            )
        else:
            self.create_new_local_file(
                local_file_path, remote_file, remote_files_to_delete, synced_files
            )

    def update_existing_local_file(self, local_file_path, remote_file, remote_files_to_delete, synced_files):
        """
        Update an existing local file if the remote version is newer.

        This method compares the local file's modification time with the remote file's creation time.
        If the remote file is newer, it updates the local file with the remote content.

        Args:
            local_file_path (str): Path to the local file.
            remote_file (dict): Dictionary representing the remote file.
            remote_files_to_delete (set): Set of remote file names to be considered for deletion.
            synced_files (set): Set of file names that have been synchronized.
        """
        local_mtime = datetime.fromtimestamp(
            os.path.getmtime(local_file_path), tz=timezone.utc
        )
        remote_mtime = datetime.fromisoformat(
            remote_file["created_at"].replace("Z", "+00:00")
        )
        if remote_mtime > local_mtime:
            logger.debug(f"Updating local file {local_file_path} from remote...")
            with open(local_file_path, "w", encoding="utf-8") as file:
                file.write(remote_file["content"])
            synced_files.add(local_file_path)
            if local_file_path in remote_files_to_delete:
                remote_files_to_delete.remove(local_file_path)

    def create_new_local_file(self, local_file_path, remote_file, remote_files_to_delete, synced_files):
        """
        Create a new local file from a remote file.

        This method creates a new local file with the content from the remote file.

        Args:
            local_file_path (str): Path to the new local file.
            remote_file (dict): Dictionary representing the remote file.
            remote_files_to_delete (set): Set of remote file names to be considered for deletion.
            synced_files (set): Set of file names that have been synchronized.
        """
        logger.debug(f"Creating new local file {local_file_path} from remote...")
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        with tqdm(total=1, desc=f"Creating {local_file_path}", leave=False) as pbar:
            with open(local_file_path, "w", encoding="utf-8") as file:
                file.write(remote_file["content"])
            pbar.update(1)
        synced_files.add(local_file_path)
        if local_file_path in remote_files_to_delete:
            remote_files_to_delete.remove(local_file_path)

    def delete_remote_files(self, file_to_delete, remote_files):
        logger.debug(f"Deleting {file_to_delete} from remote...")
        remote_file = next(
            rf for rf in remote_files if rf["file_name"] == file_to_delete
        )
        with tqdm(total=1, desc=f"Deleting {file_to_delete}", leave=False) as pbar:
            self.provider.delete_file(
                self.active_organization_id, self.active_project_id, remote_file["uuid"]
            )
            pbar.update(1)
        time.sleep(self.upload_delay)