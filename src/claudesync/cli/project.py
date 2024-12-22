import click
import os
import logging

from tqdm import tqdm
from ..provider_factory import get_provider
from ..utils import handle_errors, validate_and_get_provider
from ..exceptions import ProviderError, ConfigurationError
from .file import file
from .submodule import submodule
from ..syncmanager import retry_on_403

logger = logging.getLogger(__name__)


@click.group()
def project():
    """Manage AI projects within the active organization."""
    pass


@project.command()
@click.option(
    "--name",
    default=lambda: os.path.basename(os.getcwd()),
    prompt="Enter a title for your project",
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
    "--new",
    is_flag=True,
    help="Create a new remote project on Claude.ai",
)
@click.option(
    "--provider",
    type=click.Choice(["claude.ai"], case_sensitive=False),
    default="claude.ai",
    help="The provider to use for this project",
)
@click.pass_context
@handle_errors
def init(ctx, name, description, local_path, new, provider):
    """Initialize a new project configuration.

    If --new is specified, also creates a remote project on Claude.ai.
    Otherwise, only creates the local configuration. Use 'claudesync organization set'
    and 'claudesync project set' to link to an existing remote project."""

    config = ctx.obj

    # Create .claudesync directory and save initial config
    claudesync_dir = os.path.join(local_path, ".claudesync")
    os.makedirs(claudesync_dir, exist_ok=True)

    # Set basic configuration
    config.set("active_provider", provider, local=True)
    config.set("local_path", local_path, local=True)

    if new:
        # Create remote project if --new flag is specified
        provider_instance = get_provider(config, provider)

        # Get organization
        organizations = provider_instance.get_organizations()
        if not organizations:
            raise ConfigurationError(
                "No organizations with required capabilities found."
            )
        organization = organizations[0]["id"]

        try:
            new_project = provider_instance.create_project(
                organization, name, description
            )
            click.echo(
                f"Project '{new_project['name']}' (uuid: {new_project['uuid']}) has been created successfully."
            )

            # Update configuration with remote details
            config.set("active_organization_id", organization, local=True)
            config.set("active_project_id", new_project["uuid"], local=True)
            config.set("active_project_name", new_project["name"], local=True)

            click.echo("\nProject created:")
            click.echo(f"  - Project location: {local_path}")
            click.echo(
                f"  - Project config location: {os.path.join(claudesync_dir, 'config.local.json')}"
            )
            click.echo(
                f"  - Remote URL: https://claude.ai/project/{new_project['uuid']}"
            )

        except (ProviderError, ConfigurationError) as e:
            click.echo(f"Failed to create remote project: {str(e)}")
            raise click.Abort()
    else:
        config._save_local_config()
        click.echo("\nLocal project configuration created:")
        click.echo(f"  - Project location: {local_path}")
        click.echo(
            f"  - Project config location: {os.path.join(claudesync_dir, 'config.local.json')}"
        )
        click.echo("\nTo link to a remote project:")
        click.echo("1. Run 'claudesync organization set' to select an organization")
        click.echo("2. Run 'claudesync project set' to select an existing project")


@project.command()
@click.pass_context
def create(ctx, **kwargs):
    """Create a new project (alias for 'init --new')."""
    # Forward to init command with --new flag
    ctx.forward(init, new=True)


@project.command()
@click.option(
    "-a",
    "--all",
    "archive_all",
    is_flag=True,
    help="Archive all active projects",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_obj
@handle_errors
def archive(config, archive_all, yes):
    """Archive existing projects."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    projects = provider.get_projects(active_organization_id, include_archived=False)

    if not projects:
        click.echo("No active projects found.")
        return

    if archive_all:
        if not yes:
            click.echo("The following projects will be archived:")
            for project in projects:
                click.echo(f"  - {project['name']} (ID: {project['id']})")
            if not click.confirm("Are you sure you want to archive all projects?"):
                click.echo("Operation cancelled.")
                return

        with click.progressbar(
            projects,
            label="Archiving projects",
            item_show_func=lambda p: p["name"] if p else "",
        ) as bar:
            for project in bar:
                try:
                    provider.archive_project(active_organization_id, project["id"])
                except Exception as e:
                    click.echo(
                        f"\nFailed to archive project '{project['name']}': {str(e)}"
                    )

        click.echo("\nArchive operation completed.")
        return

    single_project_archival(projects, yes, provider, active_organization_id)


def single_project_archival(projects, yes, provider, active_organization_id):
    click.echo("Available projects to archive:")
    for idx, project in enumerate(projects, 1):
        click.echo(f"  {idx}. {project['name']} (ID: {project['id']})")

    selection = click.prompt("Enter the number of the project to archive", type=int)
    if 1 <= selection <= len(projects):
        selected_project = projects[selection - 1]
        if yes or click.confirm(
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
        claudesync_dir = os.path.abspath(".claudesync")
        config_file_path = os.path.join(claudesync_dir, "config.local.json")
        config._save_local_config()

        click.echo("\nProject created:")
        click.echo(f"  - Project location: {os.getcwd()}")
        click.echo(f"  - Project config location: {config_file_path}")
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
@click.option("--all", "truncate_all", is_flag=True, help="Truncate all projects")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_obj
@handle_errors
def truncate(config, include_archived, truncate_all, yes):
    """Truncate one or all projects."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")

    projects = provider.get_projects(
        active_organization_id, include_archived=include_archived
    )

    if not projects:
        click.echo("No projects found.")
        return

    if truncate_all:
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
        return

    click.echo("Available projects:")
    for idx, project in enumerate(projects, 1):
        status = " (Archived)" if project.get("archived_at") else ""
        click.echo(f"  {idx}. {project['name']} (ID: {project['id']}){status}")

    selection = click.prompt("Enter the number of the project to truncate", type=int)
    if 1 <= selection <= len(projects):
        selected_project = projects[selection - 1]
        if yes or click.confirm(
            f"Are you sure you want to delete ALL files from project '{selected_project['name']}'?"
        ):
            delete_files_from_project(
                provider,
                active_organization_id,
                selected_project["id"],
                selected_project["name"],
            )
            click.echo(
                f"All files have been deleted from project '{selected_project['name']}'."
            )
    else:
        click.echo("Invalid selection. Please try again.")


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
