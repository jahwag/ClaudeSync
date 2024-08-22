import click

from claudesync.provider_factory import get_provider
from ..utils import handle_errors
from ..cli.organization import select as org_select
from ..cli.project import select as proj_select
from ..cli.submodule import create as submodule_create
from ..cli.project import create as project_create


@click.group()
def api():
    """Manage api."""
    pass


@api.command()
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
            config.set("active_provider", provider)
            click.echo("Logged in successfully using existing session key.")
        else:
            session = provider_instance.login()
            config.set_session_key(session[0], session[1])
            config.set("active_provider", provider)
            click.echo("Logged in successfully with new session key.")
    else:
        session = provider_instance.login()
        config.set_session_key(session[0], session[1])
        config.set("active_provider", provider)
        click.echo("Logged in successfully.")

    # Automatically run organization select
    ctx.invoke(org_select)

    use_existing_project = click.confirm(
        "Would you like to select an existing project, or create a new one? (Selecting 'No' will prompt you to create "
        "a new project)",
        default=True,
    )
    if use_existing_project:
        ctx.invoke(proj_select)
    else:
        ctx.invoke(project_create)
        ctx.invoke(submodule_create)

    delete_remote_files = click.confirm(
        "Do you want ClaudeSync to automatically delete remote files that are not present in your local workspace? ("
        "You can change this setting later with claudesync config set prune_remote_files=True|False)",
        default=True,
    )
    config.set("prune_remote_files", delete_remote_files)


@api.command()
@click.pass_obj
def logout(config):
    """Log out from the current AI provider."""
    for key in [
        "session_key",
        "session_key_expiry",
        "active_provider",
        "active_organization_id",
        "active_project_id",
        "active_project_name",
        "local_path",
    ]:
        config.set(key, None)
    click.echo("Logged out successfully.")


@api.command()
@click.option("--delay", type=float, required=True, help="Upload delay in seconds")
@click.pass_obj
@handle_errors
def ratelimit(config, delay):
    """Set the delay between file uploads during sync."""
    if delay < 0:
        click.echo("Error: Upload delay must be a non-negative number.")
        return
    config.set("upload_delay", delay)
    click.echo(f"Upload delay set to {delay} seconds.")


@api.command()
@click.option("--size", type=int, required=True, help="Maximum file size in bytes")
@click.pass_obj
@handle_errors
def max_filesize(config, size):
    """Set the maximum file size for syncing."""
    if size < 0:
        click.echo("Error: Maximum file size must be a non-negative number.")
        return
    config.set("max_file_size", size)
    click.echo(f"Maximum file size set to {size} bytes.")
