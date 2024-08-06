import json
import os
import time
import logging
from datetime import datetime, timezone
from tqdm import tqdm
from claudesync.utils import compute_md5_hash
from .base_syncmanager import BaseSyncManager


class TwoWaySyncManager(BaseSyncManager):
    """
    Manages two-way synchronization between local files and remote Claude.ai projects.
    """

    def __init__(self, provider, config):
        super().__init__(provider, config)
        self.logger = logging.getLogger(__name__)
        self._configure_logging()

    def _configure_logging(self):
        log_level = self.config.get("log_level", "INFO")
        logging.basicConfig(level=getattr(logging, log_level))
        self.logger.setLevel(getattr(logging, log_level))

    def sync(self, local_files, remote_files):
        """
        Main synchronization method for two-way sync.

        Args:
            local_files (dict): Dictionary of local file names and their corresponding checksums.
            remote_files (list): List of dictionaries representing remote files.
        """
        sync_state = self.load_sync_state()
        local_changes = self.detect_local_changes(local_files, sync_state)
        remote_changes = self.detect_remote_changes(remote_files, sync_state)

        self.apply_changes(
            local_changes, remote_changes, local_files, remote_files, sync_state
        )

        if self.prune_remote_files:
            remote_file_names = set(rf['file_name'] for rf in remote_files)
            files_to_delete = remote_file_names - set(local_files.keys())
            for file_to_delete in files_to_delete:
                remote_file = next(rf for rf in remote_files if rf['file_name'] == file_to_delete)
                self.delete_remote_file(remote_file['uuid'])
                self.logger.debug(f"Deleted remote file: {file_to_delete}")

        self.save_sync_state(sync_state)

    def load_sync_state(self):
        """Load the previous sync state from a file."""
        sync_state_file = os.path.join(
            self.local_path, ".claudesync", "sync_state.json"
        )
        if os.path.exists(sync_state_file):
            with open(sync_state_file, "r") as f:
                return json.load(f)
        return {}

    def save_sync_state(self, sync_state):
        """Save the current sync state to a file."""
        sync_state_file = os.path.join(
            self.local_path, ".claudesync", "sync_state.json"
        )
        os.makedirs(os.path.dirname(sync_state_file), exist_ok=True)
        with open(sync_state_file, "w") as f:
            json.dump(sync_state, f)

    def detect_local_changes(self, local_files, sync_state):
        """Detect changes in local files since the last sync."""
        changes = {}
        for file_name, checksum in local_files.items():
            if file_name not in sync_state:
                changes[file_name] = "new"
            elif sync_state[file_name]["local_checksum"] != checksum:
                changes[file_name] = "modified"

        for file_name in sync_state:
            if file_name not in local_files:
                changes[file_name] = "deleted"

        return changes

    def detect_remote_changes(self, remote_files, sync_state):
        """Detect changes in remote files since the last sync."""
        changes = {}
        remote_dict = {rf["file_name"]: rf for rf in remote_files}

        for file_name, remote_file in remote_dict.items():
            if file_name not in sync_state:
                changes[file_name] = "new"
            elif sync_state[file_name]["remote_checksum"] != compute_md5_hash(
                remote_file["content"]
            ):
                changes[file_name] = "modified"

        for file_name in sync_state:
            if file_name not in remote_dict:
                changes[file_name] = "deleted"

        return changes

    def apply_changes(
        self, local_changes, remote_changes, local_files, remote_files, sync_state
    ):
        """Apply the detected changes to both local and remote systems."""
        remote_dict = {rf["file_name"]: rf for rf in remote_files}

        with tqdm(
            total=len(set(local_changes.keys()) | set(remote_changes.keys())),
            desc="Syncing files",
        ) as pbar:
            for file_name in set(local_changes.keys()) | set(remote_changes.keys()):
                local_change = local_changes.get(file_name)
                remote_change = remote_changes.get(file_name)

                self._handle_file_changes(
                    file_name,
                    local_change,
                    remote_change,
                    local_files,
                    remote_dict,
                    sync_state,
                )

                self._update_sync_state(
                    file_name,
                    local_change,
                    remote_change,
                    local_files,
                    remote_dict,
                    sync_state,
                )

                pbar.update(1)

    def _handle_file_changes(
        self,
        file_name,
        local_change,
        remote_change,
        local_files,
        remote_dict,
        sync_state,
    ):
        if local_change == "deleted" and remote_change == "deleted":
            self._handle_both_deleted(file_name, sync_state)
        elif local_change == "new" and remote_change is None:
            self.upload_file(file_name, local_files[file_name])
        elif remote_change == "new" and local_change is None:
            self.download_file(remote_dict[file_name])
        elif local_change == "modified" and remote_change is None:
            self.upload_file(file_name, local_files[file_name])
        elif remote_change == "modified" and local_change is None:
            self._handle_remote_modified(file_name, remote_dict)
        elif local_change == "deleted" and remote_change is None:
            self.delete_remote_file(sync_state[file_name]["remote_uuid"])
        elif remote_change == "deleted" and local_change is None:
            self.delete_local_file(file_name)
        elif local_change and remote_change:
            self.resolve_conflict(
                file_name,
                local_files.get(file_name),
                remote_dict.get(file_name),
            )

    def _handle_both_deleted(self, file_name, sync_state):
        self.logger.debug(
            f"File {file_name} has been deleted from both local and remote. Removing from sync state."
        )
        sync_state.pop(file_name, None)

    def _handle_remote_modified(self, file_name, remote_dict):
        remote_file = remote_dict.get(file_name)
        if remote_file:
            self.download_file(remote_file)
        else:
            self.logger.warning(
                f"Remote file {file_name} not found, but marked as modified. Skipping download."
            )

    def _update_sync_state(
        self,
        file_name,
        local_change,
        remote_change,
        local_files,
        remote_dict,
        sync_state,
    ):
        if file_name in sync_state or (
            local_change != "deleted" or remote_change != "deleted"
        ):
            sync_state[file_name] = {
                "local_checksum": local_files.get(file_name, None),
                "remote_checksum": (
                    compute_md5_hash(remote_dict[file_name]["content"])
                    if file_name in remote_dict
                    else None
                ),
                "remote_uuid": (
                    remote_dict[file_name]["uuid"] if file_name in remote_dict else None
                ),
                "last_sync": datetime.now(timezone.utc).isoformat(),
            }

    def upload_file(self, file_name, checksum):
        """Upload a file to the remote project."""
        file_path = os.path.join(self.local_path, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        content_with_comment = self._add_path_comment(content, file_path)
        normalized_content = self.normalize_line_endings(
            content_with_comment, for_local=False
        )

        self.provider.upload_file(
            self.active_organization_id,
            self.active_project_id,
            file_name,
            normalized_content,
        )
        self.logger.debug(f"Uploaded file: {file_name}")
        time.sleep(self.upload_delay)

    def download_file(self, remote_file):
        """Download a file from the remote project."""
        content = remote_file["content"]
        file_path = self._extract_path_from_comment(content) or remote_file["file_name"]
        local_file_path = os.path.join(self.local_path, file_path)

        content_without_comment = self._remove_path_comment(content)
        normalized_content = self.normalize_line_endings(
            content_without_comment, for_local=True
        )

        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        with open(local_file_path, "w", newline="", encoding="utf-8") as f:
            f.write(normalized_content)

        self.logger.debug(f"Downloaded file: {file_path}")

    def delete_remote_file(self, file_uuid):
        """Delete a file from the remote project."""
        self.provider.delete_file(
            self.active_organization_id, self.active_project_id, file_uuid
        )
        self.logger.debug(f"Deleted remote file: {file_uuid}")
        time.sleep(self.upload_delay)

    def delete_local_file(self, file_name):
        """Delete a file from the local project."""
        file_path = os.path.join(self.local_path, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            self.logger.debug(f"Deleted local file: {file_name}")

    def resolve_conflict(self, file_name, local_checksum, remote_file):
        """Resolve conflicts when both local and remote files have changed."""
        if not local_checksum:
            if remote_file:
                self.download_file(remote_file)
            else:
                self.logger.debug(
                    f"Remote file {file_name} not found, skipping download"
                )
        elif not remote_file:
            self.upload_file(file_name, local_checksum)
        else:
            local_mtime = os.path.getmtime(os.path.join(self.local_path, file_name))
            remote_mtime = datetime.fromisoformat(
                remote_file["created_at"].replace("Z", "+00:00")
            ).timestamp()

            if local_mtime > remote_mtime:
                self.upload_file(file_name, local_checksum)
            else:
                self.download_file(remote_file)

        self.logger.debug(f"Resolved conflict for file: {file_name}")
