import os
import shutil
import sys
import time

import click
from crontab import CronTab

from claudesync.utils import compute_md5_hash, get_local_files
from ..utils import handle_errors, validate_and_get_provider


@click.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List files in the active remote project."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    active_project_id = config.get("active_project_id")
    files = provider.list_files(active_organization_id, active_project_id)
    if not files:
        click.echo("No files found in the active project.")
    else:
        click.echo(
            f"Files in project '{config.get('active_project_name')}' (ID: {active_project_id}):"
        )
        for file in files:
            click.echo(
                f"  - {file['file_name']} (ID: {file['uuid']}, Created: {file['created_at']})"
            )


@click.command()
@click.pass_obj
@handle_errors
def sync(config):
    """Synchronize local files with the active remote project."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    active_project_id = config.get("active_project_id")
    local_path = config.get("local_path")
    upload_delay = config.get("upload_delay", 0.5)

    if not local_path:
        click.echo(
            "No local path set. Please select or create a project to set the local path."
        )
        sys.exit(1)

    if not os.path.exists(local_path):
        click.echo(f"The configured local path does not exist: {local_path}")
        click.echo("Please update the local path by selecting or creating a project.")
        sys.exit(1)

    remote_files = provider.list_files(active_organization_id, active_project_id)
    local_files = get_local_files(local_path)

    # Track remote files to delete
    remote_files_to_delete = set(rf["file_name"] for rf in remote_files)

    for local_file, local_checksum in local_files.items():
        remote_file = next(
            (rf for rf in remote_files if rf["file_name"] == local_file), None
        )
        if remote_file:
            remote_checksum = compute_md5_hash(remote_file["content"])
            if local_checksum != remote_checksum:
                click.echo(f"Updating {local_file} on remote...")
                provider.delete_file(
                    active_organization_id, active_project_id, remote_file["uuid"]
                )
                with open(
                    os.path.join(local_path, local_file), "r", encoding="utf-8"
                ) as file:
                    content = file.read()
                provider.upload_file(
                    active_organization_id, active_project_id, local_file, content
                )
                time.sleep(upload_delay)  # Add delay after upload
            remote_files_to_delete.remove(local_file)
        else:
            click.echo(f"Uploading new file {local_file} to remote...")
            with open(
                os.path.join(local_path, local_file), "r", encoding="utf-8"
            ) as file:
                content = file.read()
            provider.upload_file(
                active_organization_id, active_project_id, local_file, content
            )
            time.sleep(upload_delay)  # Add delay after upload

    # Delete remote files that no longer exist locally
    for file_to_delete in remote_files_to_delete:
        click.echo(f"Deleting {file_to_delete} from remote...")
        remote_file = next(
            rf for rf in remote_files if rf["file_name"] == file_to_delete
        )
        provider.delete_file(
            active_organization_id, active_project_id, remote_file["uuid"]
        )
        time.sleep(upload_delay)  # Add delay after deletion

    click.echo("Sync completed successfully.")


@click.command()
@click.pass_obj
@click.option(
    "--interval", type=int, default=5, prompt="Enter sync interval in minutes"
)
@handle_errors
def schedule(config, interval):
    """Set up automated synchronization at regular intervals."""
    claudesync_path = shutil.which("claudesync")
    if not claudesync_path:
        click.echo(
            "Error: claudesync not found in PATH. Please ensure it's installed correctly."
        )
        sys.exit(1)

    if sys.platform.startswith("win"):
        click.echo("Windows Task Scheduler setup:")
        command = f'schtasks /create /tn "ClaudeSync" /tr "{claudesync_path} sync" /sc minute /mo {interval}'
        click.echo(f"Run this command to create the task:\n{command}")
        click.echo('\nTo remove the task, run: schtasks /delete /tn "ClaudeSync" /f')
    else:
        # Unix-like systems (Linux, macOS)
        cron = CronTab(user=True)
        job = cron.new(command=f"{claudesync_path} sync")
        job.minute.every(interval)

        cron.write()
        click.echo(
            f"Cron job created successfully! It will run every {interval} minutes."
        )
        click.echo(
            "\nTo remove the cron job, run: crontab -e and remove the line for ClaudeSync"
        )
