import click
import os

from ..provider_factory import get_provider
from ..utils import handle_errors, validate_and_get_provider
from ..exceptions import ProviderError, ConfigurationError
from tqdm import tqdm
from .file import file
from .submodule import submodule
from ..syncmanager import retry_on_403


@click.group()
def project():
    """Manage AI projects within the active organization."""
    pass


@project.command()
@click.option(
    "--name",
    default=lambda: os.path.basename(os.getcwd()),
    prompt="Enter a title for your new project",
    help="The name of the project (defaults to current directory name)",
    show_default="current directory name",
)
@click.option(
    "--description",
    default="Project created with ClaudeSync",
    prompt="Enter the project description",
    help="The project description",
    show_default=True,
)
@click.option(
    "--local-path",
    default=lambda: os.getcwd(),
    prompt="Enter the absolute path to your local project directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    help="The local path for the project (defaults to current working directory)",
    show_default="current working directory",
)
@click.option(
    "--provider",
    prompt="Pick the provider to use for this project",
    type=click.Choice(["claude.ai"], case_sensitive=False),
    default="claude.ai",
    help="The provider to use for this project",
)
@click.option(
    "--organization",
    default=None,
    help="The organization ID to use for this project",
)
@click.pass_context
@handle_errors
def create(ctx, name, description, local_path, provider, organization):
    """Creates a new project for the selected provider."""
    config = ctx.obj
    provider_instance = get_provider(config, provider)

    if organization is None:
        organizations = provider_instance.get_organizations()
        organization_instance = organizations[0] if organizations else None
        organization = organization_instance["id"]

    try:
        new_project = provider_instance.create_project(organization, name, description)
        click.echo(
            f"Project '{new_project['name']}' (uuid: {new_project['uuid']}) has been created successfully."
        )

        config.set("active_provider", provider, local=True)
        config.set("active_organization_id", organization, local=True)
        config.set("active_project_id", new_project["uuid"], local=True)
        config.set("active_project_name", new_project["name"], local=True)
        config.set("local_path", local_path, local=True)

        claudesync_dir = os.path.join(local_path, ".claudesync")
        os.makedirs(claudesync_dir, exist_ok=True)
        config._save_local_config()

        click.echo(
            f"\nProject setup complete. You can now start syncing files with this project. "
            f"URL: https://claude.ai/project/{new_project['uuid']}"
        )

    except (ProviderError, ConfigurationError) as e:
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
@click.option(
    "--provider",
    type=click.Choice(["claude.ai"]),  # Add more providers as they become available
    default="claude.ai",
    help="Specify the provider for repositories without .claudesync",
)
@click.pass_context
@handle_errors
def set(ctx, show_all, provider):
    """Set the active project for syncing."""
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
    provider_instance = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    active_project_name = config.get("active_project_name")
    projects = provider_instance.get_projects(
        active_organization_id, include_archived=False
    )

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
