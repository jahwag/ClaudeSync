import click
from claudesync.provider_factory import get_provider
from ..utils import handle_errors

@click.command()
@click.argument('provider', required=False)
@click.pass_obj
@handle_errors
def login(config, provider):
    """Authenticate with an AI provider."""
    providers = get_provider()
    if not provider:
        click.echo("Available providers:\n" + "\n".join(f"  - {p}" for p in providers))
        return
    if provider not in providers:
        click.echo(f"Error: Unknown provider '{provider}'. Available: {', '.join(providers)}")
        return
    provider_instance = get_provider(provider)
    session_key = provider_instance.login()
    config.set('session_key', session_key)
    config.set('active_provider', provider)
    click.echo("Logged in successfully.")

@click.command()
@click.pass_obj
def logout(config):
    """Log out from the current AI provider."""
    for key in ['session_key', 'active_provider', 'active_organization_id']:
        config.set(key, None)
    click.echo("Logged out successfully.")