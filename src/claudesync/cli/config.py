import click
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
def list(config):
    """List all configuration values."""
    for key, value in config.config.items():
        click.echo(f"{key}: {value}")
