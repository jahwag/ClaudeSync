import click

from claudesync.provider_factory import get_provider
from ..exceptions import ProviderError
from ..utils import handle_errors


@click.group()
def auth():
    """Manage authentication."""
    pass


@auth.command()
@click.argument("provider", required=False)
@click.pass_context
@handle_errors
def login(ctx, provider):
    """Authenticate with an AI provider."""
    config = ctx.obj
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

    try:
        session_key, expiry = provider_instance.login()
        config.set_session_key(provider, session_key, expiry)
        click.echo(
            f"Successfully authenticated with {provider}. Session key stored globally."
        )
    except ProviderError as e:
        click.echo(f"Authentication failed: {str(e)}")


@auth.command()
@click.pass_obj
def logout(config):
    """Log out from all AI providers."""
    config.clear_all_session_keys()
    click.echo("Logged out from all providers successfully.")


@auth.command()
@click.pass_obj
def list(config):
    """List all authenticated providers."""
    authenticated_providers = config.get_providers_with_session_keys()
    if authenticated_providers:
        click.echo("Authenticated providers:")
        for provider in authenticated_providers:
            click.echo(f"  - {provider}")
    else:
        click.echo("No authenticated providers found.")
