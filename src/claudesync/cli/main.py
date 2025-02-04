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
from claudesync.utils import handle_errors
from .auth import auth
from .organization import organization
from .project import project
from .simulate import simulate_push
from .config import config
from .zip import zip
from .tokens import tokens
from .sync_logic import push_files
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
    push_files(config, project)


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