import click
import click_completion
import click_completion.core
import json
import os
import subprocess
import urllib.request
from pkg_resources import get_distribution

from claudesync.cli.chat import chat
from claudesync.config_manager import ConfigManager
from claudesync.syncmanager import SyncManager
from claudesync.utils import (
    handle_errors,
    validate_and_get_provider,
    detect_submodules,
    get_local_files,
)
from .api import api
from .organization import organization
from .project import project
from .sync import ls, schedule
from .config import config
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

click_completion.init()


@click.group()
@click.pass_context
def cli(ctx):
    """ClaudeSync: Synchronize local files with AI projects."""
    ctx.obj = ConfigManager()


@cli.command()
@click.argument(
    "shell", required=False, type=click.Choice(["bash", "zsh", "fish", "powershell"])
)
def install_completion(shell):
    """Install completion for the specified shell."""
    if shell is None:
        shell = click_completion.get_auto_shell()
        click.echo("Shell is set to '%s'" % shell)
    click_completion.install(shell=shell)
    click.echo("Completion installed.")


@cli.command()
@click.pass_obj
def status(config):
    """Display current configuration status."""
    for key in [
        "active_provider",
        "active_organization_id",
        "active_project_id",
        "active_project_name",
        "log_level",
    ]:
        value = config.get(key)
        click.echo(f"{key.replace('_', ' ').capitalize()}: {value or 'Not set'}")

    local_path = config.get_local_path()
    click.echo(f"Local path: {local_path or 'Not set'}")


@cli.command()
@click.pass_context
def upgrade(ctx):
    """Upgrade ClaudeSync to the latest version and reset configuration, preserving sessionKey."""
    config = ctx.obj
    current_version = get_distribution("claudesync").version

    # Check for the latest version
    try:
        with urllib.request.urlopen(
            "https://pypi.org/pypi/claudesync/json"
        ) as response:
            data = json.loads(response.read())
            latest_version = data["info"]["version"]

        if current_version == latest_version:
            click.echo(
                f"You are already on the latest version of ClaudeSync (v{current_version})."
            )
            return
    except Exception as e:
        click.echo(f"Unable to check for the latest version: {str(e)}")
        click.echo("Proceeding with the upgrade process.")

    session_key = config.get_session_key()
    session_key_expiry = config.get("session_key_expiry")

    # Upgrade ClaudeSync
    click.echo(f"Upgrading ClaudeSync from v{current_version} to v{latest_version}...")
    try:
        subprocess.run(["pip", "install", "--upgrade", "claudesync"], check=True)
        click.echo("ClaudeSync has been successfully upgraded.")
    except subprocess.CalledProcessError:
        click.echo(
            "Failed to upgrade ClaudeSync. Please try manually: pip install --upgrade claudesync"
        )

    # Preserve the session key and its expiry
    if session_key and session_key_expiry:
        config.set_session_key(session_key, session_key_expiry)
        click.echo("Session key preserved in the new configuration.")
    else:
        click.echo("No valid session key found in the old configuration.")

    # Inform user about the upgrade process
    click.echo("\nUpgrade process completed:")
    click.echo(
        f"1. ClaudeSync has been upgraded from v{current_version} to v{latest_version}."
    )
    click.echo("2. Your session key has been preserved (if it existed and was valid).")
    click.echo(
        "\nPlease run 'claudesync api login' to complete your configuration setup if needed."
    )


@cli.command()
@click.option("--category", help="Specify the file category to sync")
@click.pass_obj
@handle_errors
def sync(config, category):
    """Synchronize the project files, including submodules if they exist remotely."""
    provider = validate_and_get_provider(config, require_project=True)

    if not category:
        category = config.get_default_category()
        if category:
            click.echo(f"Using default category: {category}")

    active_organization_id = config.get("active_organization_id")
    active_project_id = config.get("active_project_id")
    active_project_name = config.get("active_project_name")
    local_path = config.get_local_path()

    if not local_path:
        click.echo(
            "No .claudesync directory found in this directory or any parent directories. "
            "Please run 'claudesync project create' or 'claudesync project select' first."
        )
        return

    # Detect local submodules
    submodule_detect_filenames = config.get("submodule_detect_filenames", [])
    local_submodules = detect_submodules(local_path, submodule_detect_filenames)

    # Fetch all remote projects
    all_remote_projects = provider.get_projects(
        active_organization_id, include_archived=False
    )

    # Find remote submodule projects
    remote_submodule_projects = [
        project
        for project in all_remote_projects
        if project["name"].startswith(f"{active_project_name}-SubModule-")
    ]

    # Sync main project
    sync_manager = SyncManager(provider, config)
    remote_files = provider.list_files(active_organization_id, active_project_id)
    local_files = get_local_files(local_path, category)
    sync_manager.sync(local_files, remote_files)
    click.echo(
        f"Main project '{active_project_name}' synced successfully: https://claude.ai/project/{active_project_id}"
    )

    # Sync submodules
    for local_submodule, detected_file in local_submodules:
        submodule_name = os.path.basename(local_submodule)
        remote_project = next(
            (
                proj
                for proj in remote_submodule_projects
                if proj["name"].endswith(f"-{submodule_name}")
            ),
            None,
        )

        if remote_project:
            click.echo(f"Syncing submodule '{submodule_name}'...")
            submodule_path = os.path.join(local_path, local_submodule)
            submodule_files = get_local_files(submodule_path, category)
            remote_submodule_files = provider.list_files(
                active_organization_id, remote_project["id"]
            )

            # Create a new SyncManager for the submodule
            submodule_config = config.config.copy()
            submodule_config["active_project_id"] = remote_project["id"]
            submodule_config["active_project_name"] = remote_project["name"]
            submodule_config["local_path"] = submodule_path
            submodule_sync_manager = SyncManager(provider, submodule_config)

            submodule_sync_manager.sync(submodule_files, remote_submodule_files)
            click.echo(
                f"Submodule '{submodule_name}' synced successfully: "
                f"https://claude.ai/project/{remote_project['id']}"
            )
        else:
            click.echo(
                f"No remote project found for submodule '{submodule_name}'. Skipping sync."
            )

    if len(local_submodules) > 0:
        click.echo(
            "Project sync completed successfully, including available submodules."
        )


cli.add_command(api)
cli.add_command(organization)
cli.add_command(project)
cli.add_command(ls)
cli.add_command(schedule)
cli.add_command(config)
cli.add_command(chat)

if __name__ == "__main__":
    cli()
