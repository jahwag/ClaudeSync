import click

from ..exceptions import ConfigurationError
from ..utils import handle_errors, validate_and_get_provider


@click.group()
def file():
    """Manage remote project files."""
    pass


@file.command()
@click.argument("project", required=False)
@click.pass_obj
@handle_errors
def ls(config, project):
    """List files in the active remote project."""
    if not project:
        active_project_path, active_project_id = config.get_active_project()
        if not active_project_path:
            raise ConfigurationError("No active project found. Please specify a project or set an active one using 'project set'")
        project = active_project_path

    provider = validate_and_get_provider(config, require_project=True)
    active_organization_id = config.get("active_organization_id")
    project_id = config.get_project_id(project)
    files = provider.list_files(active_organization_id, project_id)
    if not files:
        click.echo("No files found in the active project.")
    else:
        click.echo(
            f"Files in project '{config.get('project_name')}' (ID: {project_id}):"
        )
        for file in files:
            click.echo(
                f"  - {file['file_name']} (ID: {file['uuid']}, Created: {file['created_at']})"
            )
