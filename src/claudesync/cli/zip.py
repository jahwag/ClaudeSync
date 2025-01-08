# src/claudesync/cli/zip.py

import os
import zipfile
from datetime import datetime
import click
from pathlib import Path

from ..exceptions import ConfigurationError
from ..utils import get_local_files, handle_errors

@click.command()
@click.argument("project", required=False)
@click.option(
    "--output",
    "-o",
    help="Output path for the zip file. Defaults to claudesync_PROJECTNAME_TIMESTAMP.zip",
)
@click.pass_obj
@handle_errors
def zip(config, project, output):
    """Create a ZIP file containing all files that would be synchronized."""
    if not project:
        # Use the active project if no project specified
        active_project_path, active_project_id = config.get_active_project()
        if not active_project_path:
            raise ConfigurationError(
                "No active project found. Please specify a project or set an active one using 'project set'"
            )
        project = active_project_path

    # Get configurations
    files_config = config.get_files_config(project)
    project_root = config.get_project_root()

    # Get files to include using patterns from files configuration
    local_files = get_local_files(config, project_root, files_config)

    if not local_files:
        click.echo("No files found to include in the ZIP file.")
        return

    # Generate default output filename if not provided
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Replace slashes with underscores in project name
        safe_project_name = project.replace('/', '_')
        output = f"claudesync_{safe_project_name}_{timestamp}.zip"

    # Ensure the output path is absolute and in current directory if no path specified
    if os.path.dirname(output) == '':
        output = os.path.join(os.getcwd(), output)
    else:
        output = os.path.abspath(output)

    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(output), exist_ok=True)

    # Create the ZIP file
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
        with click.progressbar(
            local_files.items(),
            label=f"Creating ZIP file",
            length=len(local_files),
        ) as progress_bar:
            for rel_path, _ in progress_bar:
                full_path = os.path.join(project_root, rel_path)
                if os.path.exists(full_path):
                    zipf.write(full_path, rel_path)

    total_size = os.path.getsize(output)
    size_str = _format_size(total_size)

    click.echo(f"\nCreated ZIP file: {output}")
    click.echo(f"Total files: {len(local_files)}")
    click.echo(f"Total size: {size_str}")

def _format_size(size):
    """Convert size in bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
