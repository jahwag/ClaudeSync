import functools
import os
import time
import logging
from datetime import datetime, timezone
import io

from tqdm import tqdm

from claudesync.utils import compute_md5_hash
from claudesync.exceptions import ProviderError
from .compression import compress_content, decompress_content

logger = logging.getLogger(__name__)


def retry_on_403(max_retries=3, delay=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self = args[0] if len(args) > 0 else None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except ProviderError as e:
                    if "403 Forbidden" in str(e) and attempt < max_retries - 1:
                        if self and hasattr(self, "logger"):
                            self.logger.warning(
                                f"Received 403 error. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})"
                            )
                        else:
                            logger.warning(
                                f"Received 403 error. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})"
                            )
                        time.sleep(delay)
                    else:
                        raise

        return wrapper

    return decorator


class SyncManager:
    def __init__(self, provider, config, local_path):
        self.provider = provider
        self.config = config
        self.active_organization_id = config.get("active_organization_id")
        self.active_project_id = config.get("active_project_id")
        self.local_path = local_path
        self.upload_delay = config.get("upload_delay", 0.5)
        self.two_way_sync = config.get("two_way_sync", False)
        self.max_retries = 3
        self.retry_delay = 1
        self.compression_algorithm = config.get("compression_algorithm", "none")
        self.synced_files = {}

    def sync(self, local_files, remote_files):
        self.synced_files = {}  # Reset synced files at the start of sync
        if self.compression_algorithm == "none":
            self._sync_without_compression(local_files, remote_files)
        else:
            self._sync_with_compression(local_files, remote_files)

    def _sync_without_compression(self, local_files, remote_files):
        remote_files_to_delete = set(rf["file_name"] for rf in remote_files)
        synced_files = set()

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

        if self.two_way_sync:
            with tqdm(total=len(remote_files), desc="Local ← Remote") as pbar:
                for remote_file in remote_files:
                    self.sync_remote_to_local(
                        remote_file, remote_files_to_delete, synced_files
                    )
                    pbar.update(1)

        self.prune_remote_files(remote_files, remote_files_to_delete)

    def _sync_with_compression(self, local_files, remote_files):
        packed_content = self._pack_files(local_files)
        compressed_content = compress_content(
            packed_content, self.compression_algorithm
        )

        remote_file_name = (
            f"claudesync_packed_{datetime.now().strftime('%Y%m%d%H%M%S')}.dat"
        )
        self._upload_compressed_file(compressed_content, remote_file_name)

        if self.two_way_sync:
            remote_compressed_content = self._download_compressed_file()
            if remote_compressed_content:
                remote_packed_content = decompress_content(
                    remote_compressed_content, self.compression_algorithm
                )
                self._unpack_files(remote_packed_content)

        self._cleanup_old_remote_files(remote_files)

    def _pack_files(self, local_files):
        packed_content = io.StringIO()
        for file_path, file_hash in local_files.items():
            full_path = os.path.join(self.local_path, file_path)
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            packed_content.write(f"--- BEGIN FILE: {file_path} ---\n")
            packed_content.write(content)
            packed_content.write(f"\n--- END FILE: {file_path} ---\n")
        return packed_content.getvalue()

    @retry_on_403()
    def _upload_compressed_file(self, compressed_content, file_name):
        logger.debug(f"Uploading compressed file {file_name} to remote...")
        self.provider.upload_file(
            self.active_organization_id,
            self.active_project_id,
            file_name,
            compressed_content,
        )
        time.sleep(self.upload_delay)

    @retry_on_403()
    def _download_compressed_file(self):
        logger.debug("Downloading latest compressed file from remote...")
        remote_files = self.provider.list_files(
            self.active_organization_id, self.active_project_id
        )
        compressed_files = [
            rf
            for rf in remote_files
            if rf["file_name"].startswith("claudesync_packed_")
        ]
        if compressed_files:
            latest_file = max(compressed_files, key=lambda x: x["file_name"])
            return latest_file["content"]
        return None

    def _unpack_files(self, packed_content):
        current_file = None
        current_content = io.StringIO()

        for line in packed_content.splitlines():
            if line.startswith("--- BEGIN FILE:"):
                if current_file:
                    self._write_file(current_file, current_content.getvalue())
                    current_content = io.StringIO()
                current_file = line.split("--- BEGIN FILE:")[1].strip()
            elif line.startswith("--- END FILE:"):
                if current_file:
                    self._write_file(current_file, current_content.getvalue())
                    current_file = None
                    current_content = io.StringIO()
            else:
                current_content.write(line + "\n")

        if current_file:
            self._write_file(current_file, current_content.getvalue())

    def _write_file(self, file_path, content):
        full_path = os.path.join(self.local_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _cleanup_old_remote_files(self, remote_files):
        for remote_file in remote_files:
            if remote_file["file_name"].startswith("claudesync_packed_"):
                self.provider.delete_file(
                    self.active_organization_id,
                    self.active_project_id,
                    remote_file["uuid"],
                )

    @retry_on_403()
    def update_existing_file(
        self,
        local_file,
        local_checksum,
        remote_file,
        remote_files_to_delete,
        synced_files,
    ):
        remote_content = remote_file["content"]
        remote_checksum = compute_md5_hash(remote_content)
        if local_checksum != remote_checksum:
            logger.debug(f"Updating {local_file} on remote...")
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

    @retry_on_403()
    def upload_new_file(self, local_file, synced_files):
        logger.debug(f"Uploading new file {local_file} to remote...")
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
            content = remote_file["content"]
            with open(local_file_path, "w", encoding="utf-8") as file:
                file.write(content)
            synced_files.add(remote_file["file_name"])
            if remote_file["file_name"] in remote_files_to_delete:
                remote_files_to_delete.remove(remote_file["file_name"])

    def create_new_local_file(
        self, local_file_path, remote_file, remote_files_to_delete, synced_files
    ):
        logger.debug(
            f"Creating new local file {remote_file['file_name']} from remote..."
        )
        content = remote_file["content"]
        with tqdm(
            total=1, desc=f"Creating {remote_file['file_name']}", leave=False
        ) as pbar:
            with open(local_file_path, "w", encoding="utf-8") as file:
                file.write(content)
            pbar.update(1)
        synced_files.add(remote_file["file_name"])
        if remote_file["file_name"] in remote_files_to_delete:
            remote_files_to_delete.remove(remote_file["file_name"])

    def prune_remote_files(self, remote_files, remote_files_to_delete):
        if not self.config.get("prune_remote_files"):
            logger.info("Remote pruning is not enabled.")
            return

        for file_to_delete in list(remote_files_to_delete):
            self.delete_remote_files(file_to_delete, remote_files)

    @retry_on_403()
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

    def embedding(self, local_files):
        packed_content = self._pack_files(local_files)
        compressed_content = compress_content(
            packed_content, self.compression_algorithm
        )
        return compressed_content
