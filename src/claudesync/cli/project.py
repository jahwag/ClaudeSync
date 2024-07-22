import click

from claudesync.exceptions import ProviderError
from ..utils import (
    handle_errors,
    validate_and_get_provider,
    validate_and_store_local_path,
)


@click.group()
def project():
    """
    Manage AI projects within the active organization.

    This command group serves as a namespace for project-related operations such as creating, archiving, selecting,
    and listing projects. It allows users to perform various actions on projects within the context of the currently
    active organization. Each sub-command under this group is designed to handle a specific aspect of project management
    in a CLI environment.

    Usage:
        Use this command followed by a sub-command to perform the desired project management operation. For example,
        `project create` to create a new project, or `project list` to list all projects.

    Note:
        This command group must be used in conjunction with a sub-command to perform any meaningful action.
    """
    pass


@project.command()
@click.pass_obj
@handle_errors
def create(config):
    """
    Create a new project within the active organization.

    This command prompts the user for a project title and an optional description, then attempts to create a new project
    with these details in the currently active organization. Upon successful creation, the new project is set as the
    active project for subsequent operations.

    Args:
        config (ConfigManager): The configuration manager instance, passed automatically by Click. It contains
                                settings and methods to interact with the application's configuration, such as
                                the active organization ID.

    Raises:
        ProviderError: If the project creation fails due to an error from the provider side.

    Note:
        This function is decorated with `@handle_errors` to catch and handle exceptions raised during the execution,
        providing user-friendly error messages. It also uses `validate_and_store_local_path` to ensure the local
        project path is valid and stored in the configuration.
    """
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")

    title = click.prompt("Enter the project title")
    description = click.prompt("Enter the project description (optional)", default="")

    try:
        new_project = provider.create_project(
            active_organization_id, title, description
        )
        click.echo(
            f"Project '{new_project['name']}' (uuid: {new_project['uuid']}) has been created successfully."
        )

        config.set("active_project_id", new_project["uuid"])
        config.set("active_project_name", new_project["name"])
        click.echo(
            f"Active project set to: {new_project['name']} (uuid: {new_project['uuid']})"
        )

        validate_and_store_local_path(config)

    except ProviderError as e:
        click.echo(f"Failed to create project: {str(e)}")


@project.command()
@click.pass_obj
@handle_errors
def archive(config):
    """
    Archive an existing project within the active organization.

    This command lists all active projects and allows the user to select one for archiving. Once a project is selected,
    the user is prompted to confirm the archiving action. If confirmed, the selected project is archived, making it
    inaccessible for regular operations unless specifically requested.

    Args:
        config (ConfigManager): The configuration manager instance, passed automatically by Click. It contains
                                settings and methods to interact with the application's configuration, such as
                                the active organization ID.

    Raises:
        ProviderError: If the archiving process fails due to an error from the provider side.

    Note:
        This function is decorated with `@handle_errors` to catch and handle exceptions raised during the execution,
        providing user-friendly error messages. It relies on `validate_and_get_provider` to ensure that a valid provider
        is available and uses it to fetch the list of active (non-archived) projects.
    """
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    projects = provider.get_projects(active_organization_id, include_archived=False)
    if not projects:
        click.echo("No active projects found.")
        return
    click.echo("Available projects to archive:")
    for idx, project in enumerate(projects, 1):
        click.echo(f"  {idx}. {project['name']} (ID: {project['id']})")
    selection = click.prompt("Enter the number of the project to archive", type=int)
    if 1 <= selection <= len(projects):
        selected_project = projects[selection - 1]
        if click.confirm(
                f"Are you sure you want to archive '{selected_project['name']}'?"
        ):
            provider.archive_project(active_organization_id, selected_project["id"])
            click.echo(f"Project '{selected_project['name']}' has been archived.")
    else:
        click.echo("Invalid selection. Please try again.")


@project.command()
@click.pass_obj
@handle_errors
def select(config):
    """
    Set the active project for syncing.

    This command allows the user to select an active project from a list of available projects within the active organization.
    It first fetches the list of projects that are not archived. If no projects are found, it notifies the user. Otherwise,
    it displays the list and prompts the user to select a project by entering its corresponding number. Upon a valid selection,
    the chosen project's ID and name are set as the active project in the configuration, facilitating operations like syncing
    to be performed on this project.

    Args:
        config (ConfigManager): The configuration manager instance, passed automatically by Click. It is used to access
                                and modify the current configuration settings, including setting the active project ID and name.

    Note:
        This function is decorated with `@handle_errors` to catch and handle exceptions raised during the execution,
        providing user-friendly error messages. It relies on `validate_and_get_provider` to ensure that a valid provider
        is available and uses it to fetch the list of non-archived projects. It also uses `validate_and_store_local_path`
        to ensure the local project path is valid and stored in the configuration.
    """
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    projects = provider.get_projects(active_organization_id, include_archived=False)
    if not projects:
        click.echo("No active projects found.")
        return
    click.echo("Available projects:")
    for idx, project in enumerate(projects, 1):
        click.echo(f"  {idx}. {project['name']} (ID: {project['id']})")
    selection = click.prompt("Enter the number of the project to select", type=int)
    if 1 <= selection <= len(projects):
        selected_project = projects[selection - 1]
        config.set("active_project_id", selected_project["id"])
        config.set("active_project_name", selected_project["name"])
        click.echo(
            f"Selected project: {selected_project['name']} (ID: {selected_project['id']})"
        )

        validate_and_store_local_path(config)
    else:
        click.echo("Invalid selection. Please try again.")


@project.command()
@click.option(
    "-a", "--all", "show_all", is_flag=True, help="Include archived projects in the list",
)
# Adds an option to the `ls` command to include archived projects in the output.
# This option can be enabled by passing `-a` or `--all` when calling the command.
#
# Args:
#     show_all (bool): A flag that, when set to True, includes archived projects in the list.
#                      This is controlled by the `-a` or `--all` command-line option.
@click.pass_obj
@handle_errors
def ls(config, show_all):
    """
    List all projects in the active organization, optionally including archived projects.

    This command fetches and displays a list of all projects within the active organization. It can be configured to
    include archived projects in the list through the use of a command-line option.

    Args:
        config (ConfigManager): The configuration manager instance, passed automatically by Click. It contains
                                settings and methods to interact with the application's configuration, such as
                                the active organization ID.
        show_all (bool): A flag indicating whether to include archived projects in the list. This is controlled
                         by the `-a` or `--all` command-line option.

    Note:
        This function is decorated with `@handle_errors` to catch and handle exceptions raised during the execution,
        providing user-friendly error messages. It relies on `validate_and_get_provider` to ensure that a valid provider
        is available for fetching the list of projects.
    """
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    projects = provider.get_projects(active_organization_id, include_archived=show_all)
    if not projects:
        click.echo("No projects found.")
    else:
        click.echo("Remote projects:")
        for p in projects:
            status = " (Archived)" if p.get("archived_at") else ""
            click.echo(f"  - {p['name']} (ID: {p['id']}){status}")