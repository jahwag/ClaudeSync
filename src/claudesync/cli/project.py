import click

from claudesync.exceptions import ProviderError
from ..utils import (
    handle_errors,
    validate_and_get_provider,
    validate_and_store_local_path,
)


@click.group()
def project():
    """Manage ai projects within the active organization."""
    pass


@project.command()
@click.pass_obj
@handle_errors
def create(config):
    """Create a new project in the active organization."""
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
    """Archive an existing project."""
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
    """Set the active project for syncing."""
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
    "-a",
    "--all",
    "show_all",
    is_flag=True,
    help="Include archived projects in the list",
)
@click.pass_obj
@handle_errors
def ls(config, show_all):
    """List all projects in the active organization."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    projects = provider.get_projects(active_organization_id, include_archived=show_all)
    if not projects:
        click.echo("No projects found.")
    else:
        click.echo("Remote projects:")
        for project in projects:
            status = " (Archived)" if project.get("archived_at") else ""
            click.echo(f"  - {project['name']} (ID: {project['id']}){status}")
