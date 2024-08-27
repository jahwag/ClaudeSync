import click

from claudesync.provider_factory import get_provider
from ..utils import handle_errors
from ..cli.organization import set as org_select
from ..cli.project import set as proj_select
from ..cli.submodule import add as submodule_add
from ..cli.project import create as project_create


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

    # Check for existing valid session key
    existing_session_key = config.get_session_key()
    existing_session_key_expiry = config.get("session_key_expiry")

    if existing_session_key and existing_session_key_expiry:
        use_existing = click.confirm(
            "An existing session key was found. Would you like to use it?", default=True
        )
        if use_existing:
            config.set("active_provider", provider, local=True)
            click.echo("Logged in successfully using existing session key.")
        else:
            session = provider_instance.login()
            config.set_session_key(session[0], session[1])
            config.set("active_provider", provider, local=True)
            click.echo("Logged in successfully with new session key.")
    else:
        session = provider_instance.login()
        config.set_session_key(session[0], session[1])
        config.set("active_provider", provider, local=True)
        click.echo("Logged in successfully.")

    # Automatically run organization select
    ctx.invoke(org_select)

    use_existing_project = click.confirm(
        "Would you like to select an existing project, or create a new one? "
        "(Selecting 'No' will prompt you to create a new project)",
        default=True,
    )
    if use_existing_project:
        ctx.invoke(proj_select)
    else:
        ctx.invoke(project_create)
        ctx.invoke(submodule_add)

    delete_remote_files = click.confirm(
        "Do you want ClaudeSync to automatically delete remote files that are not present in your local workspace? "
        "(You can change this setting later with claudesync config set prune_remote_files=True|False)",
        default=True,
    )
    config.set("prune_remote_files", delete_remote_files)


@auth.command()
@click.pass_obj
def logout(config):
    """Log out from the current AI provider."""
    keys_to_clear = [
        "session_key",
        "session_key_expiry",
        "active_provider",
        "active_organization_id",
        "active_project_id",
        "active_project_name",
    ]
    for key in keys_to_clear:
        config.set(key, None, local=True)
    click.echo("Logged out successfully.")
