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
@click.option("--org-id", help="ID of the organization to set as active")
@click.option(
    "--provider",
    type=click.Choice(["claude.ai"]),  # Add more providers as they become available
    default="claude.ai",
    help="Specify the provider for repositories without .claudesync",
)
@click.pass_context
@handle_errors
def set(ctx, org_id, provider):
    """Set the active organization."""
    config = ctx.obj

    # If provider is not specified, try to get it from the config
    if not provider:
        provider = config.get("active_provider")

    # If provider is still not available, prompt the user
    if not provider:
        provider = click.prompt(
            "Please specify the provider",
            type=click.Choice(
                ["claude.ai"]
            ),  # Add more providers as they become available
        )

    # Update the config with the provider
    config.set("active_provider", provider, local=True)

    # Now we can get the provider instance
    provider_instance = validate_and_get_provider(config, require_org=False)
    organizations = provider_instance.get_organizations()

    if not organizations:
        click.echo("No organizations with required capabilities found.")
        return

    if org_id:
        selected_org = next((org for org in organizations if org["id"] == org_id), None)
        if selected_org:
            config.set("active_organization_id", selected_org["id"], local=True)
            click.echo(
                f"Selected organization: {selected_org['name']} (ID: {selected_org['id']})"
            )
        else:
            click.echo(f"Organization with ID {org_id} not found.")
    else:
        click.echo("Available organizations:")
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
        else:
            click.echo("Invalid selection. Please try again.")

    # Clear project-related settings when changing organization
    config.set("active_project_id", None, local=True)
    config.set("active_project_name", None, local=True)
    click.echo(
        "Project settings cleared. Please select or create a new project for this organization."
    )
