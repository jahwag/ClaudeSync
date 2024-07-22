import click

from claudesync.provider_factory import get_provider
from ..utils import handle_errors


@click.group()
def api():
    """
    Defines a command group for API-related operations.

    This function serves as a decorator to create a new Click command group. Commands that are part of this group
    are related to managing API interactions, such as logging in or out from an AI provider. It acts as a namespace
    for API commands, allowing them to be organized under the 'api' command in the CLI tool.
    """
    pass


@api.command()
@click.argument("provider", required=False)
@click.pass_obj
@handle_errors
def login(config, provider):
    """
    Authenticate with an AI provider.

    This command allows the user to log in to a specified AI provider. If no provider is specified,
    it lists all available providers. Upon specifying a valid provider, it attempts to authenticate
    with that provider using its login mechanism. Successful authentication stores the session key
    and active provider name in the configuration.

    Args:
        config (ConfigManager): The configuration manager instance, passed automatically by Click.
        provider (str, optional): The name of the AI provider to authenticate with. If not provided,
                                  the command lists all available providers.

    Note:
        This function is decorated with `@handle_errors` to catch and handle exceptions raised during
        the authentication process, providing user-friendly error messages.
    """
    providers = get_provider()
    if not provider:
        click.echo("Available providers:\n" + "\n".join(f"  - {p}" for p in providers))
        return
    if provider not in providers:
        click.echo(
            f"Error: Unknown provider '{provider}'. Available: {', '.join(providers)}"
        )
        return
    provider_instance = get_provider(provider)
    session_key = provider_instance.login()
    config.set("session_key", session_key)
    config.set("active_provider", provider)
    click.echo("Logged in successfully.")


@api.command()
@click.pass_obj
def logout(config):
    """
    Log out from the current AI provider.

    This command clears the session key, active provider, and active organization ID from the configuration,
    effectively logging the user out. It is a part of the API command group and can be executed from the CLI
    to reset the user's session and provider information.

    Args:
        config (ConfigManager): The configuration manager instance, passed automatically by Click.
    """
    for key in ["session_key", "active_provider", "active_organization_id"]:
        config.set(key, None)
    click.echo("Logged out successfully.")


@click.command()
@click.option("--delay", type=float, required=True, help="Upload delay in seconds")
@click.pass_obj
@handle_errors
def ratelimit(config, delay):
    """
    Set the delay between file uploads during synchronization.

    This command configures the delay (in seconds) to wait between each file upload operation during the synchronization process.
    It ensures that the rate of upload does not exceed the limit specified by the user or the default system limit. This can be
    particularly useful in avoiding rate limits or bans from APIs or services that have a cap on how frequently they can be accessed.

    Args:
        config (ConfigManager): The configuration manager instance, passed automatically by Click.
        delay (float): The delay, in seconds, between file uploads. Must be a non-negative number.

    Raises:
        ValueError: If the provided delay is negative, indicating an invalid configuration.

    Note:
        This function is decorated with `@handle_errors` to catch and handle exceptions raised during the execution,
        providing user-friendly error messages.
    """
    if delay < 0:
        click.echo("Error: Upload delay must be a non-negative number.")
        return
    config.set("upload_delay", delay)
    click.echo(f"Upload delay set to {delay} seconds.")


@click.command()
@click.option("--size", type=int, required=True, help="Maximum file size in bytes")
@click.pass_obj
@handle_errors
def max_filesize(config, size):
    """
    Set the maximum file size for file synchronization.

    This command allows the user to specify a maximum file size limit for files to be synchronized. Files larger than
    this limit will not be synchronized. This can be useful for avoiding the synchronization of very large files that
    might be unnecessary or could consume excessive bandwidth.

    Args:
        config (ConfigManager): The configuration manager instance, passed automatically by Click.
        size (int): The maximum file size in bytes. Must be a non-negative number.

    Raises:
        ValueError: If the provided size is negative, indicating an invalid configuration.

    Note:
        This function is decorated with `@handle_errors` to catch and handle exceptions raised during the execution,
        providing user-friendly error messages.
    """
    if size < 0:
        click.echo("Error: Maximum file size must be a non-negative number.")
        return
    config.set("max_file_size", size)
    click.echo(f"Maximum file size set to {size} bytes.")
