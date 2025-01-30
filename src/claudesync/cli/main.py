from pathlib import Path

import click
import click_completion
import click_completion.core
import json
import subprocess
import urllib.request
from pkg_resources import get_distribution

from claudesync.cli.export import export
from claudesync.cli.file import file
from claudesync.cli.chat import chat
from claudesync.configmanager import FileConfigManager
from claudesync.exceptions import ConfigurationError
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
from .config import config
from .zip import zip
from .tokens import tokens
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
@click.argument("project", required=False)
@click.pass_obj
@handle_errors
def push(config, project):
    """Synchronize the project files."""
    if not project:
        # Use the active project if no project specified
        active_project_path, active_project_id = config.get_active_project()
        if not active_project_path:
            raise ConfigurationError("No active project found. Please specify a project or set an active one using 'project set'")
        project = active_project_path

    # Get configurations
    files_config = config.get_files_config(project)

    provider = validate_and_get_provider(config)

    # Use project configuration
    active_organization_id = config.get("active_organization_id")
    project_id = config.get_project_id(project)

    # Get files to sync using patterns from files configuration
    local_files = get_local_files(config, config.get_project_root(), files_config)

    # Set as active project
    config.set_active_project(project, project_id)

    # Sync files
    remote_files = provider.list_files(active_organization_id, project_id)
    sync_manager = SyncManager(provider, config, project_id, config.get_project_root())
    sync_manager.sync(local_files, remote_files)

    click.echo(f"Project '{project}' synced successfully")
    click.echo(f"Remote URL: https://claude.ai/project/{project_id}")


cli.add_command(auth)
cli.add_command(organization)
cli.add_command(project)
cli.add_command(config)
cli.add_command(chat)
cli.add_command(simulate_push)
cli.add_command(file)
cli.add_command(zip)
cli.add_command(tokens)
cli.add_command(export)

if __name__ == "__main__":
    cli()
