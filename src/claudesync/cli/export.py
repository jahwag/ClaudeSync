import click
from datetime import datetime
import logging
import os
from pathlib import Path

from ..exceptions import ConfigurationError
from ..utils import get_local_files, handle_errors

logger = logging.getLogger(__name__)

def generate_default_filename(config):
    """Generate default export filename with flattened project name."""
    active_project_path = config.get_active_project()[0]
    if not active_project_path:
        raise ConfigurationError("No active project found")

    # Replace forward slashes with underscores for flat filename
    safe_project_name = active_project_path.replace('/', '_')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"claudesync_export_{safe_project_name}_{timestamp}.txt"

def write_single_file(output_file, file_path, base_path):
    """Write a single file's content with markers."""
    full_path = os.path.join(base_path, file_path)
    output_file.write(f"--- BEGIN FILE: {file_path} ---\n")
    
    try:
        # Check if file is binary by looking for null bytes
        with open(full_path, 'rb') as f:
            is_binary = b'\x00' in f.read(8192)
            f.seek(0)
            
            if is_binary:
                output_file.write("[BINARY FILE - NOT INCLUDED IN EXPORT]\n")
            else:
                with open(full_path, 'r', encoding='utf-8') as text_file:
                    content = text_file.read()
                    output_file.write(content)
                    if not content.endswith('\n'):
                        output_file.write('\n')
    except (UnicodeDecodeError, PermissionError, FileNotFoundError) as e:
        logger.warning(f"Error processing file {file_path}: {str(e)}")
        output_file.write(f"[ERROR READING FILE: {str(e)}]\n")
    
    output_file.write(f"--- END FILE: {file_path} ---\n\n")

def write_export_file(files, output_path, base_path):
    """Write files to export file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header with metadata
        f.write("# ClaudeSync Export\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write(f"# Total files: {len(files)}\n\n")
        
        # Write each file's content
        for file_path in sorted(files.keys()):
            write_single_file(f, file_path, base_path)

@click.command()
@click.argument("project", required=False)
@click.option(
    "--output",
    "-o",
    help="Output path for the export file. Defaults to claudesync_PROJECTNAME_TIMESTAMP.txt",
)
@click.pass_obj
@handle_errors
def export(config, project, output):
    """Export all files that would be synchronized into a single file.
    
    If no project is specified, uses the active project.
    """
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
        click.echo("No files found to export.")
        return

    # Generate default output filename if not provided
    if not output:
        output = generate_default_filename(config)

    # Ensure the output path is absolute
    if not os.path.isabs(output):
        output = os.path.join(os.getcwd(), output)

    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(output), exist_ok=True)

    # Write the export file
    write_export_file(local_files, output, project_root)

    click.echo(f"\nExport completed:")
    click.echo(f"  - Output file: {output}")
    click.echo(f"  - Total files: {len(local_files)}")
