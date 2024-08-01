import os
import time
from datetime import datetime, timezone

import click
from tqdm import tqdm

from claudesync.utils import compute_md5_hash


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
        self.local_path = config.get("local_path")
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

        with tqdm(total=len(local_files), desc="Syncing local to remote") as pbar:
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

        if self.two_way_sync:
            with tqdm(total=len(remote_files), desc="Syncing remote to local") as pbar:
                for remote_file in remote_files:
                    self.sync_remote_to_local(
                        remote_file, remote_files_to_delete, synced_files
                    )
                    pbar.update(1)

        with tqdm(
            total=len(remote_files_to_delete), desc="Deleting remote files"
        ) as pbar:
            for file_to_delete in list(remote_files_to_delete):
                self.delete_remote_files(file_to_delete, remote_files)
                pbar.update(1)

    def update_existing_file(
        self,
        local_file,
        local_checksum,
        remote_file,
        remote_files_to_delete,
        synced_files,
    ):
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
        remote_checksum = compute_md5_hash(remote_file["content"])
        if local_checksum != remote_checksum:
            click.echo(f"Updating {local_file} on remote...")
            with tqdm(total=2, desc=f"Updating {local_file}", leave=False) as pbar:
                self.provider.delete_file(
                    self.active_organization_id,
                    self.active_project_id,
                    remote_file["uuid"],
                )
                pbar.update(1)
                with open(
                    os.path.join(self.local_path, local_file), "r", encoding="utf-8"
                ) as file:
                    content = file.read()
                self.provider.upload_file(
                    self.active_organization_id,
                    self.active_project_id,
                    local_file,
                    content,
                )
                pbar.update(1)
            time.sleep(self.upload_delay)
            synced_files.add(local_file)
        remote_files_to_delete.remove(local_file)

    def upload_new_file(self, local_file, synced_files):
        """
        Upload a new file to the remote project.

        This method reads the content of the local file and uploads it to the remote project.

        Args:
            local_file (str): Name of the local file to be uploaded.
            synced_files (set): Set of file names that have been synchronized.
        """
        click.echo(f"Uploading new file {local_file} to remote...")
        with open(
            os.path.join(self.local_path, local_file), "r", encoding="utf-8"
        ) as file:
            content = file.read()
        with tqdm(total=1, desc=f"Uploading {local_file}", leave=False) as pbar:
            self.provider.upload_file(
                self.active_organization_id, self.active_project_id, local_file, content
            )
            pbar.update(1)
        time.sleep(self.upload_delay)
        synced_files.add(local_file)

    def update_local_timestamps(self, remote_files, synced_files):
        """
        Update local file timestamps to match the remote timestamps.

        This method updates the modification timestamps of local files to match their corresponding
        remote file timestamps if they have been synchronized.

        Args:
            remote_files (list): List of dictionaries representing remote files.
            synced_files (set): Set of file names that have been synchronized.
        """
        with tqdm(total=len(synced_files), desc="Updating local timestamps") as pbar:
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
                        click.echo(f"Updated timestamp on local file {local_file_path}")
                    pbar.update(1)

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
        local_file_path = os.path.join(self.local_path, remote_file["file_name"])
        if os.path.exists(local_file_path):
            self.update_existing_local_file(
                local_file_path, remote_file, remote_files_to_delete, synced_files
            )
        else:
            self.create_new_local_file(
                local_file_path, remote_file, remote_files_to_delete, synced_files
            )

    def update_existing_local_file(
        self, local_file_path, remote_file, remote_files_to_delete, synced_files
    ):
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
            click.echo(f"Updating local file {remote_file['file_name']} from remote...")
            with tqdm(
                total=1, desc=f"Updating {remote_file['file_name']}", leave=False
            ) as pbar:
                with open(local_file_path, "w", encoding="utf-8") as file:
                    file.write(remote_file["content"])
                pbar.update(1)
            synced_files.add(remote_file["file_name"])
            if remote_file["file_name"] in remote_files_to_delete:
                remote_files_to_delete.remove(remote_file["file_name"])

    def create_new_local_file(
        self, local_file_path, remote_file, remote_files_to_delete, synced_files
    ):
        """
        Create a new local file from a remote file.

        This method creates a new local file with the content from the remote file.

        Args:
            local_file_path (str): Path to the new local file.
            remote_file (dict): Dictionary representing the remote file.
            remote_files_to_delete (set): Set of remote file names to be considered for deletion.
            synced_files (set): Set of file names that have been synchronized.
        """
        click.echo(f"Creating new local file {remote_file['file_name']} from remote...")
        with tqdm(
            total=1, desc=f"Creating {remote_file['file_name']}", leave=False
        ) as pbar:
            with open(local_file_path, "w", encoding="utf-8") as file:
                file.write(remote_file["content"])
            pbar.update(1)
        synced_files.add(remote_file["file_name"])
        if remote_file["file_name"] in remote_files_to_delete:
            remote_files_to_delete.remove(remote_file["file_name"])

    def delete_remote_files(self, file_to_delete, remote_files):
        """
        Delete a file from the remote project that no longer exists locally.

        This method deletes a remote file that is not present in the local directory.

        Args:
            file_to_delete (str): Name of the remote file to be deleted.
            remote_files (list): List of dictionaries representing remote files.
        """
        click.echo(f"Deleting {file_to_delete} from remote...")
        remote_file = next(
            rf for rf in remote_files if rf["file_name"] == file_to_delete
        )
        with tqdm(total=1, desc=f"Deleting {file_to_delete}", leave=False) as pbar:
            self.provider.delete_file(
                self.active_organization_id, self.active_project_id, remote_file["uuid"]
            )
            pbar.update(1)
        time.sleep(self.upload_delay)
