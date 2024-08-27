import click
from ..utils import handle_errors, validate_and_get_provider


@click.group()
def file():
    """Manage remote project files."""
    pass


@file.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List files in the active remote project."""
    provider = validate_and_get_provider(config, require_project=True)
    active_organization_id = config.get("active_organization_id")
    active_project_id = config.get("active_project_id")
    files = provider.list_files(active_organization_id, active_project_id)
    if not files:
        click.echo("No files found in the active project.")
    else:
        click.echo(
            f"Files in project '{config.get('active_project_name')}' (ID: {active_project_id}):"
        )
        for file in files:
            click.echo(
                f"  - {file['file_name']} (ID: {file['uuid']}, Created: {file['created_at']})"
            )
