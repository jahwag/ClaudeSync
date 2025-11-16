from pathlib import Path

import click
import click_completion
import click_completion.core
import json
import subprocess
import urllib.request
import importlib.metadata

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
from .sync import schedule
from .config import config
from .session import session
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
    current_version = importlib.metadata.version("claudesync")

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

    # Upgrade ClaudeSync
    click.echo(f"Upgrading ClaudeSync from v{current_version} to v{latest_version}...")
    try:
        subprocess.run(["pip", "install", "--upgrade", "claudesync"], check=True)
        click.echo("ClaudeSync has been successfully upgraded.")
    except subprocess.CalledProcessError:
        click.echo(
            "Failed to upgrade ClaudeSync. Please try manually: pip install --upgrade claudesync"
        )

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
@click.option(
    "--uberproject", is_flag=True, help="Include submodules in the parent project sync"
)
@click.option(
    "--dryrun", is_flag=True, default=False, help="Just show what files would be sent"
)
@click.pass_obj
@handle_errors
def push(config, category, uberproject, dryrun):
    """Synchronize the project files, optionally including submodules in the parent project."""
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

    # Detect if we're in a submodule
    current_dir = Path.cwd()
    submodules = config.get("submodules", [])
    current_submodule = next(
        (
            sm
            for sm in submodules
            if Path(local_path) / sm["relative_path"] == current_dir
        ),
        None,
    )

    if current_submodule:
        # We're in a submodule, so only sync this submodule
        click.echo(
            f"Syncing submodule {current_submodule['active_project_name']} [{current_dir}]"
        )
        sync_submodule(provider, config, current_submodule, category)
    else:
        # Sync main project
        sync_manager = SyncManager(provider, config, config.get_local_path())
        remote_files = provider.list_files(active_organization_id, active_project_id)

        if uberproject:
            # Include submodule files in the parent project
            local_files = get_local_files(
                config, local_path, category, include_submodules=True
            )
        else:
            # Exclude submodule files from the parent project
            local_files = get_local_files(
                config, local_path, category, include_submodules=False
            )

        if dryrun:
            for file in local_files.keys():
                click.echo(f"Would send file: {file}")
            click.echo("Not sending files due to dry run mode.")
            return

        sync_manager.sync(local_files, remote_files)
        click.echo(
            f"Main project '{active_project_name}' synced successfully: https://claude.ai/project/{active_project_id}"
        )

        # Always sync submodules to their respective projects
        for submodule in submodules:
            sync_submodule(provider, config, submodule, category)


def sync_submodule(provider, config, submodule, category):
    submodule_path = Path(config.get_local_path()) / submodule["relative_path"]
    submodule_files = get_local_files(config, str(submodule_path), category)
    remote_submodule_files = provider.list_files(
        submodule["active_organization_id"], submodule["active_project_id"]
    )

    # Create a new ConfigManager instance for the submodule
    submodule_config = InMemoryConfigManager()
    submodule_config.load_from_file_config(config)
    submodule_config.set(
        "active_project_id", submodule["active_project_id"], local=True
    )
    submodule_config.set(
        "active_project_name", submodule["active_project_name"], local=True
    )

    # Create a new SyncManager for the submodule
    submodule_sync_manager = SyncManager(
        provider, submodule_config, str(submodule_path)
    )

    submodule_sync_manager.sync(submodule_files, remote_submodule_files)
    click.echo(
        f"Submodule '{submodule['active_project_name']}' synced successfully: "
        f"https://claude.ai/project/{submodule['active_project_id']}"
    )


@cli.command()
@click.option("--category", help="Specify the file category to sync")
@click.option(
    "--uberproject", is_flag=True, help="Include submodules in the parent project sync"
)
@click.pass_obj
@handle_errors
def embedding(config, category, uberproject):
    """Generate a text embedding from the project. Does not require"""
    if not category:
        category = config.get_default_category()
        if category:
            click.echo(f"Using default category: {category}")

    local_path = config.get_local_path()

    if not local_path:
        click.echo(
            "No .claudesync directory found in this directory or any parent directories. "
            "Please run 'claudesync project create' or 'claudesync project set' first."
        )
        return

    # Sync main project
    sync_manager = SyncManager(None, config, config.get_local_path())

    if uberproject:
        # Include submodule files in the parent project
        local_files = get_local_files(
            config, local_path, category, include_submodules=True
        )
    else:
        # Exclude submodule files from the parent project
        local_files = get_local_files(
            config, local_path, category, include_submodules=False
        )

    output = sync_manager.embedding(local_files)
    click.echo(f"{output}")


cli.add_command(auth)
cli.add_command(organization)
cli.add_command(project)
cli.add_command(schedule)
cli.add_command(config)
cli.add_command(chat)
cli.add_command(session)

if __name__ == "__main__":
    cli()
