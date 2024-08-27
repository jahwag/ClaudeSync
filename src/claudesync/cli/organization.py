import click
from ..utils import handle_errors, validate_and_get_provider


@click.group()
def organization():
    """Manage AI organizations."""
    pass


@organization.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List all available organizations with required capabilities."""
    provider = validate_and_get_provider(config, require_org=False)
    organizations = provider.get_organizations()
    if not organizations:
        click.echo(
            "No organizations with required capabilities (chat and claude_pro) found."
        )
    else:
        click.echo("Available organizations with required capabilities:")
        for idx, org in enumerate(organizations, 1):
            click.echo(f"  {idx}. {org['name']} (ID: {org['id']})")


@organization.command()
@click.pass_context
@handle_errors
def set(ctx):
    """Set the active organization."""
    config = ctx.obj
    provider = validate_and_get_provider(config, require_org=False)
    organizations = provider.get_organizations()
    if not organizations:
        click.echo(
            "No organizations with required capabilities (chat and claude_pro) found."
        )
        return
    click.echo("Available organizations with required capabilities:")
    for idx, org in enumerate(organizations, 1):
        click.echo(f"  {idx}. {org['name']} (ID: {org['id']})")
    selection = click.prompt(
        "Enter the number of the organization you want to work with",
        type=int,
        default=1,
    )
    if 1 <= selection <= len(organizations):
        selected_org = organizations[selection - 1]
        config.set("active_organization_id", selected_org["id"], local=True)
        click.echo(
            f"Selected organization: {selected_org['name']} (ID: {selected_org['id']})"
        )

        # Clear project-related settings when changing organization
        config.set("active_project_id", None, local=True)
        config.set("active_project_name", None, local=True)
        click.echo(
            "Project settings cleared. Please select or create a new project for this organization."
        )
    else:
        click.echo("Invalid selection. Please try again.")
