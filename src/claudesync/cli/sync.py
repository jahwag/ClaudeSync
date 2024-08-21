import os
import shutil
import sys
import click
from crontab import CronTab

from ..utils import handle_errors, validate_and_get_provider


@click.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List files in the active remote project."""
    provider = validate_and_get_provider(config, require_project=True)
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


def validate_local_path(local_path):
    if not local_path:
        click.echo(
            "No local path set. Please select or create a project to set the local path."
        )
        sys.exit(1)
    if not os.path.exists(local_path):
        click.echo(f"The configured local path does not exist: {local_path}")
        click.echo("Please update the local path by selecting or creating a project.")
        sys.exit(1)


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
        setup_windows_task(claudesync_path, interval)
    else:
        setup_unix_cron(claudesync_path, interval)


def setup_windows_task(claudesync_path, interval):
    click.echo("Windows Task Scheduler setup:")
    command = f'schtasks /create /tn "ClaudeSync" /tr "{claudesync_path} sync" /sc minute /mo {interval}'
    click.echo(f"Run this command to create the task:\n{command}")
    click.echo('\nTo remove the task, run: schtasks /delete /tn "ClaudeSync" /f')


def setup_unix_cron(claudesync_path, interval):
    cron = CronTab(user=True)
    job = cron.new(command=f"{claudesync_path} sync")
    job.minute.every(interval)
    cron.write()
    click.echo(f"Cron job created successfully! It will run every {interval} minutes.")
    click.echo(
        "\nTo remove the cron job, run: crontab -e and remove the line for ClaudeSync"
    )
