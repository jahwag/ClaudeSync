import json
from pathlib import Path

import click
import os
import logging

from tqdm import tqdm
from ..provider_factory import get_provider
from ..utils import handle_errors, validate_and_get_provider
from ..exceptions import ProviderError, ConfigurationError
from .file import file
from ..syncmanager import retry_on_403

logger = logging.getLogger(__name__)


@click.group()
def project():
    """Manage AI projects within the active organization."""
    pass


@project.command()
@click.option(
    "--name",
    prompt="Enter a title for your new project",
    help="The name of the project",
)
@click.option(
    "--internal-name",
    prompt="Enter the internal name for your project (used for config files)",
    help="The internal name used for configuration files",
)
@click.option(
    "--description",
    default="Project created with ClaudeSync",
    prompt="Enter the project description",
    help="The project description",
    show_default=True,
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
@click.option(
    "--no-git-check",
    is_flag=True,
    help="Skip git repository check",
)
@click.pass_context
@handle_errors
def create(ctx, name, internal_name, description, provider, organization, no_git_check):
    """Creates a new project for the selected provider."""
    config = ctx.obj
    provider_instance = get_provider(config, provider)

    if organization is None:
        organizations = provider_instance.get_organizations()
        organization_instance = organizations[0] if organizations else None
        organization = organization_instance["id"]

    # Get the current directory
    current_dir = Path.cwd()

    # Create .claudesync directory if it doesn't exist
    claudesync_dir = current_dir / ".claudesync"
    os.makedirs(claudesync_dir, exist_ok=True)

    try:
        # Create the project remotely
        new_project = provider_instance.create_project(organization, name, description)
        click.echo(
            f"Project '{new_project['name']}' (uuid: {new_project['uuid']}) has been created successfully."
        )

        # Create project ID configuration file
        project_id_config = {
            "project_id": new_project["uuid"],
        }

        # Create project configuration file
        project_config = {
            "project_name": new_project["name"],
            "project_description": description,
            "includes": [],
            "excludes": []
        }

        # Determine if internal_name contains a path
        config_path = Path(internal_name)
        if len(config_path.parts) > 1:
            # Create subdirectories if needed
            os.makedirs(claudesync_dir / config_path.parent, exist_ok=True)

        # Save project configuration
        project_id_config_path = claudesync_dir / f"{internal_name}.project_id.json"
        with open(project_id_config_path, 'w') as f:
            json.dump(project_id_config, f, indent=2)

        # Save files configuration
        project_config_path = claudesync_dir / f"{internal_name}.project.json"
        with open(project_config_path, 'w') as f:
            json.dump(project_config, f, indent=2)

        # Set as active project
        config.set_active_project(internal_name, new_project["uuid"])

        click.echo("\nProject created and set as active:")
        click.echo(f"  - Project location: {current_dir}")
        click.echo(f"  - Project ID config: {project_id_config_path}")
        click.echo(f"  - Project config: {project_config_path}")
        click.echo(f"  - Remote URL: https://claude.ai/project/{new_project['uuid']}")

    except (ProviderError, ConfigurationError) as e:
        click.echo(f"Failed to create project: {str(e)}")

# Add this to src/claudesync/cli/project.py, right after the @project.command() create function

@project.command()
@click.argument("project-path", required=True)
@click.pass_obj
@handle_errors
def set(config, project_path):
    """Set the active project for the current directory.

    PROJECT_PATH: The project path like 'datamodel/typeconstraints' or 'myproject'"""
    try:
        # Get project ID from config
        project_id = config.get_project_id(project_path)

        # Set as active project
        config.set_active_project(project_path, project_id)

        # Get project details
        files_config = config.get_files_config(project_path)
        project_name = files_config.get('project_name', 'Unknown Project')

        click.echo(f"Set active project to '{project_name}'")
        click.echo(f"  - Project path: {project_path}")
        click.echo(f"  - Project ID: {project_id}")
        click.echo(f"  - Project location: {config.get_project_root()}")
        click.echo(f"  - Remote URL: https://claude.ai/project/{project_id}")

    except ConfigurationError as e:
        click.echo(f"Error: {str(e)}")
        click.echo("Make sure the project exists and has been properly configured.")
        click.echo("You may need to create the project first using 'claudesync project create'")

project.add_command(file)

__all__ = ["project"]
