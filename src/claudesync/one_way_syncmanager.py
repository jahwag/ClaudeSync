import time
import logging
from tqdm import tqdm
from .base_syncmanager import BaseSyncManager

logger = logging.getLogger(__name__)


class OneWaySyncManager(BaseSyncManager):
    """
    Manages one-way synchronization from local files to remote Claude.ai projects.
    """

    def sync(self, local_files, remote_files):
        """
        Main synchronization method for one-way sync (local to remote).

        Args:
            local_files (dict): Dictionary of local file names and their corresponding checksums.
            remote_files (list): List of dictionaries representing remote files.
        """
        remote_files_to_delete = set(rf["file_name"] for rf in remote_files)
        synced_files = set()

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

        # Delete remaining files that weren't synced
        if self.prune_remote_files:
            for file_to_delete in list(remote_files_to_delete):
                remote_file = next(
                    rf for rf in remote_files if rf["file_name"] == file_to_delete
                )
                self.delete_remote_file(remote_file)

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
