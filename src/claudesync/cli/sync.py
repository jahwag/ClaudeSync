import os
import shutil
import sys
import click
from crontab import CronTab

from ..utils import handle_errors, validate_and_get_provider


@click.command()
@click.argument("project", required=False)
@click.pass_obj
@handle_errors
def ls(config, project):
    """List files in the active remote project."""
    provider = validate_and_get_provider(config, require_project=True)
    active_organization_id = config.get("active_organization_id")
    files_config = config.get_files_config(project)
    project_id = config.get_project_id(project)
    files = provider.list_files(active_organization_id, project_id)
    if not files:
        click.echo("No files found in the active project.")
    else:
        click.echo(
            f"Files in project '{files_config.get('project_name')}' (ID: {project_id}):"
        )
        for file in files:
            click.echo(
                f"  - {file['file_name']} (ID: {file['uuid']}, Created: {file['created_at']})"
            )


def validate_local_path(local_path):
    if not local_path:
        click.echo(
            "No local path set. Please select or create a project to set the local path."
        )
        sys.exit(1)
    if not os.path.exists(local_path):
        click.echo(f"The configured local path does not exist: {local_path}")
        click.echo("Please update the local path by selecting or creating a project.")
        sys.exit(1)
