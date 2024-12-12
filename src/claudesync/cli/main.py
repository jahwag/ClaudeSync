from pathlib import Path

import click
import click_completion
import click_completion.core
import json
import subprocess
import urllib.request
from pkg_resources import get_distribution

from claudesync.cli.chat import chat
from claudesync.configmanager import FileConfigManager, InMemoryConfigManager
from claudesync.syncmanager import SyncManager
from claudesync.utils import (
    handle_errors,
    validate_and_get_provider,
    get_local_files,
)
from .auth import auth
from .organization import organization
from .project import project
from .simulate import simulate_push
from .sync import schedule
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
    if ctx.obj is None:
        ctx.obj = FileConfigManager()  # InMemoryConfigManager() for testing with mock


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
        "\nPlease run 'claudesync auth login' to complete your configuration setup if needed."
    )


@cli.command()
@click.option("--category", help="Specify the file category to sync")
@click.pass_obj
@handle_errors
def push(config, category):
    """Synchronize the project files."""
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
            "Please run 'claudesync project create' or 'claudesync project set' first."
        )
        return

    # Sync main project
    sync_manager = SyncManager(provider, config, config.get_local_path())
    remote_files = provider.list_files(active_organization_id, active_project_id)

    local_files = get_local_files(
        config, local_path, category
    )

    sync_manager.sync(local_files, remote_files)
    click.echo(
        f"Main project '{active_project_name}' synced successfully: https://claude.ai/project/{active_project_id}"
    )


cli.add_command(auth)
cli.add_command(organization)
cli.add_command(project)
cli.add_command(schedule)
cli.add_command(config)
cli.add_command(chat)
cli.add_command(simulate_push)

if __name__ == "__main__":
    cli()
