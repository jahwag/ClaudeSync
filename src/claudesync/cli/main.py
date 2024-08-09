import click
import click_completion
import click_completion.core

from claudesync.cli.chat import chat
from claudesync.config_manager import ConfigManager
from .api import api
from .organization import organization
from .project import project
from .sync import ls, sync, schedule
from .config import config
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

click_completion.init()


@click.group()
@click.pass_context
def cli(ctx):
    """ClaudeSync: Synchronize local files with ai projects."""
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
        "local_path",
        "log_level",
    ]:
        value = config.get(key)
        click.echo(f"{key.replace('_', ' ').capitalize()}: {value or 'Not set'}")

@cli.group()
def path():
    """Manage local paths for synchronization."""
    pass

@path.command(name="add")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True))
@click.pass_obj
def add_path(config, path):
    """Add a local path for synchronization."""
    config.add_local_path(path)
    click.echo(f"Added local path: {path}")

@path.command(name="remove")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True))
@click.pass_obj
def remove_path(config, path):
    """Remove a local path from synchronization."""
    config.remove_local_path(path)
    click.echo(f"Removed local path: {path}")

@path.command(name="list")
@click.pass_obj
def list_paths(config):
    """List all local paths for synchronization."""
    paths = config.get_local_paths()
    if paths:
        click.echo("Local paths for synchronization:")
        for path in paths:
            click.echo(f"  - {path}")
    else:
        click.echo("No local paths configured for synchronization.")

# Add the new path command group to the main CLI
cli.add_command(path)

cli.add_command(api)
cli.add_command(organization)
cli.add_command(project)
cli.add_command(ls)
cli.add_command(sync)
cli.add_command(schedule)
cli.add_command(config)
cli.add_command(chat)

if __name__ == "__main__":
    cli()
