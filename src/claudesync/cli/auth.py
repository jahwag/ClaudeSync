import click

from claudesync.provider_factory import get_provider
from ..exceptions import ProviderError
from ..utils import handle_errors


@click.group()
def auth():
    """Manage authentication."""
    pass


@auth.command()
@click.option(
    "--session-key",
    help="Directly provide the Claude.ai session key",
    envvar="CLAUDE_SESSION_KEY",
)
@click.option(
    "--auto-approve",
    is_flag=True,
    help="Automatically approve the suggested expiry time",
)
@click.pass_context
@handle_errors
def login(ctx, session_key, auto_approve):
    """Authenticate with Claude AI."""
    config = ctx.obj
    provider_instance = get_provider(config)

    try:
        if session_key:
            # If session key is provided, bypass the interactive prompt
            if not session_key.startswith("sk-ant"):
                raise ProviderError(
                    "Invalid sessionKey format. Must start with 'sk-ant'"
                )
            # Set auto_approve to True when session key is provided
            provider_instance._auto_approve_expiry = auto_approve
            provider_instance._provided_session_key = session_key

        session_key, expiry = provider_instance.login()
        config.set_session_key(session_key, expiry)

        organizations = provider_instance.get_organizations()
        organization_instance = organizations[0] if organizations else None
        organization_id = organization_instance["id"]
        config.set("active_organization_id", organization_id, local=False)

        config._save_global_config()
        click.echo(
            f"Successfully authenticated with Claude AI. Session key stored globally."
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
def ls(config):
    """List all authenticated providers."""
    authenticated_providers = config.get_providers_with_session_keys()
    if authenticated_providers:
        click.echo("Authenticated providers:")
        for provider in authenticated_providers:
            click.echo(f"  - {provider}")
    else:
        click.echo("No authenticated providers found.")
