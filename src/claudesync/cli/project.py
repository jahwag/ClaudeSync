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

def get_default_internal_name():
    """
    Determine default internal name based on existing projects.
    Returns 'all' if no projects exist, None otherwise.
    """
    from claudesync.configmanager import FileConfigManager

    config = FileConfigManager()
    try:
        projects = config.get_projects()
        return 'all' if not projects else None
    except ConfigurationError:
        return 'all'  # Return 'all' if no .claudesync directory exists yet

def ensure_gitignore_entries(claudesync_dir, internal_name=None):
    """
    Ensure project_id.json patterns are in .gitignore

    Args:
        claudesync_dir (Path): Path to .claudesync directory
        internal_name (str, optional): If provided, also add specific pattern

    Returns:
        bool: True if .gitignore was updated, False otherwise
    """
    gitignore_path = claudesync_dir.parent / '.gitignore'
    entries_to_add = [
        '.claudesync/*.project_id.json',
        '.claudesync/active_project.json',
        '.venv',
        '.github'
    ]

    # If specific internal_name provided, add more specific pattern
    if internal_name and '/' in internal_name:
        # For nested project paths like 'subdir/project'
        path_parts = internal_name.split('/')
        nested_path = '/'.join(path_parts[:-1])
        entries_to_add.append(f'.claudesync/{nested_path}/*.project_id.json')

    # Create .gitignore if it doesn't exist
    if not gitignore_path.exists():
        with open(gitignore_path, 'w') as f:
            f.write('\n'.join(entries_to_add) + '\n')
        return True

    # Check if entries already exist
    with open(gitignore_path, 'r') as f:
        content = f.read()
        lines = content.splitlines()

    # Find entries to add (those not already in .gitignore)
    new_entries = [entry for entry in entries_to_add
                   if entry not in lines]

    # Add new entries if needed
    if new_entries:
        with open(gitignore_path, 'a') as f:
            # Add a newline if file doesn't end with one
            if content and not content.endswith('\n'):
                f.write('\n')

            f.write('\n#claudesync\n')
            f.write('\n'.join(new_entries) + '\n')
        return True

    return False  # No changes made

@project.command()
@click.option(
    "--template",
    help="Name of an existing project to use as a template (e.g. 'myproject' will use .claudesync/myproject.project.json)",
)
@click.option(
    "--name",
    help="The name of the project",
    required=False,
)
@click.option(
    "--internal-name",
    help="The internal name used for configuration files",
    required=False,
)
@click.option(
    "--description",
    help="The project description",
    required=False,
)
@click.option(
    "--organization",
    help="The organization ID to use for this project",
    required=False,
)
@click.option(
    "--no-git-check",
    is_flag=True,
    help="Skip git repository check",
)
@click.pass_context
@handle_errors
def create(ctx, template, name, internal_name, description, organization, no_git_check):
    """Creates a new project for the selected provider.

    There are two ways to create a project:

    1. Interactive mode (default):
       claudesync project create

    2. Using an existing project as template:
       claudesync project create --template existing-project
    """
    config = ctx.obj
    provider_instance = get_provider(config)

    # Handle configuration from template if provided
    if template:
        try:
            # Look for template in .claudesync directory
            claudesync_dir = Path.cwd() / ".claudesync"
            template_file = claudesync_dir / f"{template}.project.json"

            if not template_file.exists():
                raise ConfigurationError(f"Template project configuration not found: {template_file}")

            with open(template_file, 'r') as f:
                template_config = json.load(f)

            # Extract project name from template if not provided via CLI
            name = name or template_config.get('project_name')
            if not name:
                raise ConfigurationError("Template must contain 'project_name' field")

            # For internal_name: use CLI argument, or generate from template name if not provided
            if not internal_name:
                # If not provided via CLI, try to generate a safe internal name from the template path
                template_base = os.path.basename(template)  # Get last part of path
                internal_name = template_base.replace('.project.json', '')

            # Description is optional, default to standard description if not provided
            description = description or template_config.get('project_description', "Project created with ClaudeSync")

            if not all([name, internal_name]):
                raise ConfigurationError("Template must contain 'project_name' and 'internal_name' fields")

        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in template file: {str(e)}")
        except IOError as e:
            raise ConfigurationError(f"Error reading template file: {str(e)}")
    else:
        # Interactive mode - prompt for required values if not provided
        if not name:
            name = click.prompt("Enter a title for your new project", default=Path.cwd().name)

        if not internal_name:
            default_internal = get_default_internal_name()
            internal_name = click.prompt("Enter the internal name for your project (used for config files)",
                                         default=default_internal)

        if not description:
            description = click.prompt("Enter the project description",
                                       default="Project created with ClaudeSync")

    # Get organization from available organizations
    organizations = provider_instance.get_organizations()
    organization_instance = organizations[0] if organizations else None
    organization_id = organization or organization_instance["id"]

    # Get the current directory
    current_dir = Path.cwd()

    # Create .claudesync directory if it doesn't exist
    claudesync_dir = current_dir / ".claudesync"
    os.makedirs(claudesync_dir, exist_ok=True)

    # Check if project config already exists
    project_config_path = claudesync_dir / f"{internal_name}.project.json"
    project_config_exists = project_config_path.exists()

    if project_config_exists:
        click.echo(f"Found existing project configuration: {project_config_path}")
        click.echo("Existing configuration will be preserved.")

    try:
        # Create the project remotely
        new_project = provider_instance.create_project(organization_id, name, description)
        click.echo(
            f"Project '{new_project['name']}' (uuid: {new_project['uuid']}) has been created successfully."
        )

        # Create project ID configuration file
        project_id_config = {
            "project_id": new_project["uuid"],
        }

        # Only create project configuration file if it doesn't exist
        if not project_config_exists:
            if template:
                # Use configuration from template
                project_config = {
                    "project_name": new_project["name"],
                    "project_description": description,
                    "includes": template_config.get('includes', []),
                    "excludes": template_config.get('excludes', []),
                    "use_ignore_files": template_config.get('use_ignore_files', True),
                    "push_roots": template_config.get('push_roots', [])
                }
            else:
                # Use default configuration
                project_config = {
                    "project_name": new_project["name"],
                    "project_description": description,
                    "includes": [],
                    "excludes": [],
                    "use_ignore_files": True,
                    "push_roots": []
                }

            # Save files configuration
            project_config_path = claudesync_dir / f"{internal_name}.project.json"
            with open(project_config_path, 'w') as f:
                json.dump(project_config, f, indent=2)

        # Determine if internal_name contains a path
        config_path = Path(internal_name)
        if len(config_path.parts) > 1:
            # Create subdirectories if needed
            os.makedirs(claudesync_dir / config_path.parent, exist_ok=True)

        # Save project configuration
        project_id_config_path = claudesync_dir / f"{internal_name}.project_id.json"
        with open(project_id_config_path, 'w') as f:
            json.dump(project_id_config, f, indent=2)

        # Set as active project
        config.set_active_project(internal_name, new_project["uuid"])

        # Ensure .gitignore has entries to exclude ID files
        gitignore_updated = ensure_gitignore_entries(claudesync_dir, internal_name)

        click.echo("\nProject created and set as active:")
        click.echo(f"  - Project location: {current_dir}")
        click.echo(f"  - Project ID config: {project_id_config_path}")
        click.echo(f"  - Project config: {project_config_path} ({'preserved' if project_config_exists else 'created'})")
        click.echo(f"  - Remote URL: https://claude.ai/project/{new_project['uuid']}")

        if gitignore_updated:
            click.echo(f"  - Added entries to .gitignore to prevent sharing project IDs")

    except (ProviderError, ConfigurationError) as e:
        click.echo(f"Failed to create project: {str(e)}")

@project.command()
@click.argument("project-path", required=True)
@click.pass_obj
@handle_errors
def set(config, project_path):
    """Set the active project.

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

@project.command()
@click.pass_obj
@handle_errors
def archive(config):
    """Archive the active project."""
    try:
        # Get active project
        active_project_path, active_project_id = config.get_active_project()
        if not active_project_path:
            raise ConfigurationError("No active project found. Please set an active project using 'project set'")

        # Get project details
        files_config = config.get_files_config(active_project_path)
        project_name = files_config.get('project_name', 'Unknown Project')

        # Get provider and archive the project
        provider = validate_and_get_provider(config)
        active_organization_id = config.get("active_organization_id")
        provider.archive_project(active_organization_id, active_project_id)

        click.echo(f"Successfully archived project '{project_name}'")
        click.echo(f"  - Project path: {active_project_path}")
        click.echo(f"  - Project ID: {active_project_id}")

    except ConfigurationError as e:
        click.echo(f"Error: {str(e)}")
        click.echo("Make sure you have an active project set.")

@project.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List all configured projects."""
    try:
        # Get all projects from config
        projects = config.get_projects()
        if not projects:
            click.echo("No projects found.")
            return

        # Get active project for comparison
        active_project_path, active_project_id = config.get_active_project()

        click.echo("\nConfigured projects:")
        for project_path, project_id in projects.items():
            # Get project details from project configuration
            try:
                files_config = config.get_files_config(project_path)
                project_name = files_config.get('project_name', 'Unknown Project')

                # Mark active project with an asterisk
                active_marker = "*" if project_path == active_project_path else " "

                click.echo(f"{active_marker} {project_name}")
                click.echo(f"  - Path: {project_path}")
                click.echo(f"  - ID: {project_id}")
                click.echo(f"  - URL: https://claude.ai/project/{project_id}")
                click.echo()

            except ConfigurationError:
                # Skip projects with missing or invalid configuration
                continue

        if active_project_path:
            click.echo("Note: Projects marked with * are currently active")

    except ConfigurationError as e:
        click.echo(f"Error: {str(e)}")

project.add_command(file)

__all__ = ["project"]