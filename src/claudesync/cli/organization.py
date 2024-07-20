import click

from ..utils import handle_errors, validate_and_get_provider


@click.group()
def organization():
    """Manage ai organizations."""
    pass


@organization.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List all available organizations."""
    provider = validate_and_get_provider(config, require_org=False)
    organizations = provider.get_organizations()
    if not organizations:
        click.echo("No organizations found.")
    else:
        click.echo("Available organizations:")
        for idx, org in enumerate(organizations, 1):
            click.echo(f"  {idx}. {org['name']} (ID: {org['id']})")


@organization.command()
@click.pass_obj
@handle_errors
def select(config):
    """Set the active organization."""
    provider = validate_and_get_provider(config, require_org=False)
    organizations = provider.get_organizations()
    if not organizations:
        click.echo("No organizations found.")
        return
    click.echo("Available organizations:")
    for idx, org in enumerate(organizations, 1):
        click.echo(f"  {idx}. {org['name']} (ID: {org['id']})")
    selection = click.prompt("Enter the number of the organization to select", type=int)
    if 1 <= selection <= len(organizations):
        selected_org = organizations[selection - 1]
        config.set("active_organization_id", selected_org["id"])
        click.echo(
            f"Selected organization: {selected_org['name']} (ID: {selected_org['id']})"
        )
    else:
        click.echo("Invalid selection. Please try again.")
