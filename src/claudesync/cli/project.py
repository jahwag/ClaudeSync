import json
import os
import click
from tqdm import tqdm

from claudesync.exceptions import ProviderError
from .file import file
from .submodule import submodule
from ..syncmanager import retry_on_403
from ..utils import (
    handle_errors,
    validate_and_get_provider,
)


@click.group()
def project():
    """Manage AI projects within the active organization."""
    pass


@project.command()
@click.pass_obj
@handle_errors
def create(config):
    """Initializes a new project in the active organization."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")

    if not active_organization_id:
        click.echo("No active organization set. Please select an organization first.")
        return

    default_name = os.path.basename(os.getcwd())
    title = click.prompt("Enter a title for your new project", default=default_name)
    description = click.prompt("Enter the project description (optional)", default="")

    try:
        new_project = provider.create_project(
            active_organization_id, title, description
        )
        click.echo(
            f"Project '{new_project['name']}' (uuid: {new_project['uuid']}) has been created successfully."
        )

        # Set the new project as the active project in the local configuration
        config.set("active_project_id", new_project["uuid"], local=True)
        config.set("active_project_name", new_project["name"], local=True)
        click.echo(
            f"Active project set to: {new_project['name']} (uuid: {new_project['uuid']})"
        )

        # Create .claudesync directory in the current working directory
        claudesync_dir = os.path.join(os.getcwd(), ".claudesync")
        os.makedirs(claudesync_dir, exist_ok=True)
        click.echo(f"Created .claudesync directory in {os.getcwd()}")

        # Create an empty config.local.json file
        local_config_file = os.path.join(claudesync_dir, "config.local.json")
        with open(local_config_file, "w") as f:
            json.dump({}, f)
        click.echo(f"Created empty config.local.json in {claudesync_dir}")

        click.echo(
            "Project setup complete. You can now start syncing files with this project."
        )

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
            f"Are you sure you want to archive the project '{selected_project['name']}'? "
            f"Archived projects cannot be modified but can still be viewed."
        ):
            provider.archive_project(active_organization_id, selected_project["id"])
            click.echo(f"Project '{selected_project['name']}' has been archived.")
    else:
        click.echo("Invalid selection. Please try again.")


@project.command()
@click.option(
    "-a",
    "--all",
    "show_all",
    is_flag=True,
    help="Include submodule projects in the selection",
)
@click.pass_context
@handle_errors
def set(ctx, show_all):
    """Set the active project for syncing."""
    config = ctx.obj
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    active_project_name = config.get("active_project_name")
    projects = provider.get_projects(active_organization_id, include_archived=False)

    if show_all:
        selectable_projects = projects
    else:
        # Filter out submodule projects
        selectable_projects = [p for p in projects if "-SubModule-" not in p["name"]]

    if not selectable_projects:
        click.echo("No active projects found.")
        return

    click.echo("Available projects:")
    for idx, project in enumerate(selectable_projects, 1):
        project_type = (
            "Main Project"
            if not project["name"].startswith(f"{active_project_name}-SubModule-")
            else "Submodule"
        )
        click.echo(f"  {idx}. {project['name']} (ID: {project['id']}) - {project_type}")

    selection = click.prompt(
        "Enter the number of the project to select", type=int, default=1
    )
    if 1 <= selection <= len(selectable_projects):
        selected_project = selectable_projects[selection - 1]
        config.set("active_project_id", selected_project["id"], local=True)
        config.set("active_project_name", selected_project["name"], local=True)
        click.echo(
            f"Selected project: {selected_project['name']} (ID: {selected_project['id']})"
        )

        # Create .claudesync directory in the current working directory if it doesn't exist
        os.makedirs(".claudesync", exist_ok=True)
        click.echo(f"Ensured .claudesync directory exists in {os.getcwd()}")
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


@project.command()
@click.option(
    "-a", "--include-archived", is_flag=True, help="Include archived projects"
)
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_obj
@handle_errors
def truncate(config, include_archived, yes):
    """Truncate all projects."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")

    projects = provider.get_projects(
        active_organization_id, include_archived=include_archived
    )

    if not projects:
        click.echo("No projects found.")
        return

    if not yes:
        click.echo("This will delete ALL files from the following projects:")
        for project in projects:
            status = " (Archived)" if project.get("archived_at") else ""
            click.echo(f"  - {project['name']} (ID: {project['id']}){status}")
        if not click.confirm(
            "Are you sure you want to continue? This may take some time."
        ):
            click.echo("Operation cancelled.")
            return

    with tqdm(total=len(projects), desc="Deleting files from projects") as pbar:
        for project in projects:
            delete_files_from_project(
                provider, active_organization_id, project["id"], project["name"]
            )
            pbar.update(1)

    click.echo("All files have been deleted from all projects.")


@retry_on_403()
def delete_files_from_project(provider, organization_id, project_id, project_name):
    try:
        files = provider.list_files(organization_id, project_id)
        with tqdm(
            total=len(files), desc=f"Deleting files from {project_name}", leave=False
        ) as file_pbar:
            for current_file in files:
                provider.delete_file(organization_id, project_id, current_file["uuid"])
                file_pbar.update(1)
    except ProviderError as e:
        click.echo(f"Error deleting files from project {project_name}: {str(e)}")


project.add_command(submodule)
project.add_command(file)

__all__ = ["project"]
