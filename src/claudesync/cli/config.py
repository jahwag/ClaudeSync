import json

import click

from .category import category
from ..exceptions import ConfigurationError
from ..utils import handle_errors


@click.group()
def config():
    """Manage claudesync configuration."""
    pass


@config.command()
@click.argument("key")
@click.argument("value")
@click.pass_obj
@handle_errors
def set(config, key, value):
    """Set a configuration value."""
    # Check if the key exists in the configuration
    if key not in config.global_config and key not in config.local_config:
        raise ConfigurationError(f"Configuration property '{key}' does not exist.")

    # Convert string 'true' and 'false' to boolean
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    # Try to convert to int or float if possible
    else:
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass  # Keep as string if not a number

    config.set(key, value)
    click.echo(f"Configuration {key} set to {value}")


@config.command()
@click.argument("key")
@click.pass_obj
@handle_errors
def get(config, key):
    """Get a configuration value."""
    value = config.get(key)
    if value is None:
        click.echo(f"Configuration {key} is not set")
    else:
        click.echo(f"{key}: {value}")


@config.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List all configuration values."""
    # Combine global and local configurations
    combined_config = config.global_config.copy()
    combined_config.update(config.local_config)

    # Print the combined configuration as JSON
    click.echo(json.dumps(combined_config, indent=2, sort_keys=True))


config.add_command(category)
