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


@cli.command()
@click.pass_context
def upgrade(config):
    """Upgrade ClaudeSync to the latest version and reset configuration, preserving sessionKey."""
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

    config_path = os.path.expanduser("~/.claudesync/config.json")
    session_key = None
    session_key_expiry = None

    # Read existing configuration
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            old_config = json.load(f)
            session_key = old_config.get("session_key")
            session_key_expiry = old_config.get("session_key_expiry")

        # Backup existing configuration
        backup_path = f"{config_path}.v{current_version}.bak"
        os.rename(config_path, backup_path)
        click.echo(f"Existing configuration backed up to: {backup_path}")

    # Upgrade ClaudeSync
    click.echo(f"Upgrading ClaudeSync from v{current_version} to v{latest_version}...")
    try:
        subprocess.run(["pip", "install", "--upgrade", "claudesync"], check=True)
        click.echo("ClaudeSync has been successfully upgraded.")
    except subprocess.CalledProcessError:
        click.echo(
            "Failed to upgrade ClaudeSync. Please try manually: pip install --upgrade claudesync"
        )

    # Create new configuration with preserved sessionKey
    if session_key and session_key_expiry:
        new_config = {
            "session_key": session_key,
            "session_key_expiry": session_key_expiry,
        }
        with open(config_path, "w") as f:
            json.dump(new_config, f, indent=2)
        click.echo("New configuration created with preserved sessionKey.")
    else:
        click.echo("No sessionKey found in the old configuration.")

    # Inform user about the upgrade process
    click.echo("\nUpgrade process completed:")
    click.echo(
        f"1. Your previous configuration (v{current_version}) has been backed up."
    )
    click.echo(
        f"2. ClaudeSync has been upgraded from v{current_version} to v{latest_version}."
    )
    click.echo(
        "3. A new configuration has been created, preserving your sessionKey if it existed."
    )
    click.echo(
        "\nPlease run 'claudesync api login' to complete your configuration setup."
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
