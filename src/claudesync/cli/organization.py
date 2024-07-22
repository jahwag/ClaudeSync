import click

from ..utils import handle_errors, validate_and_get_provider


@click.group()
def organization():
    """
    Defines a command group for organization-related operations.

    This function serves as a decorator to create a new Click command group. Commands that are part of this group
    are related to managing AI organizations, such as listing available organizations or setting the active organization.
    It acts as a namespace for organization commands, allowing them to be organized under the 'organization' command
    in the CLI tool.
    """
    pass


@organization.command()
@click.pass_obj
@handle_errors
def ls(config):
    """
    List all available organizations.

    This command retrieves and displays a list of all organizations accessible to the user. If no organizations are found,
    it outputs a message indicating that no organizations are available. Otherwise, it lists each organization with its
    name and ID.

    Args:
        config (ConfigManager): The configuration manager instance, passed automatically by Click. It is used to access
                                the current configuration settings, including the provider information.

    Note:
        This function is decorated with `@handle_errors` to catch and handle exceptions raised during the execution,
        providing user-friendly error messages.
    """
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
    """
    Set the active organization by allowing the user to choose from a list of available organizations.

    This command first retrieves a list of all organizations accessible to the user. If no organizations are found,
    it informs the user accordingly. Otherwise, it displays a list of available organizations, prompting the user to
    select one by entering the corresponding number. Upon a valid selection, it sets the chosen organization as the
    active organization in the configuration.

    Args:
        config (ConfigManager): The configuration manager instance, passed automatically by Click. It is used to
                                access and modify the current configuration settings, including setting the active
                                organization ID.

    Note:
        This function is decorated with `@handle_errors` to catch and handle exceptions raised during the execution,
        providing user-friendly error messages. It relies on `validate_and_get_provider` to ensure that a valid provider
        is available and uses it to fetch the list of organizations.
    """
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
