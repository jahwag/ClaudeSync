# src/claudesync/cli/tokens.py

import click
from tqdm import tqdm
from ..exceptions import ConfigurationError
from ..utils import handle_errors
from ..token_counter import count_project_tokens

def format_token_count(count: int) -> str:
    """Format token count with thousands separator and k/M suffix."""
    if count >= 1_000_000:
        return f"{count/1_000_000:.1f}M tokens"
    elif count >= 1_000:
        return f"{count/1_000:.1f}k tokens"
    return f"{count:,} tokens"

@click.command()
@click.argument("project", required=False)
@click.option("--verbose", "-v", is_flag=True, help="Show token counts for individual files")
@click.pass_obj
@handle_errors
def tokens(config, project, verbose):
    """Count tokens in files that would be synchronized.
    
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

    click.echo(f"\nCounting tokens for project '{project}'...")
    
    # Count tokens
    result = count_project_tokens(config, files_config, project_root)
    
    # Display results
    total_tokens = result['total']
    file_counts = result['files']
    failed_files = result['failed_files']
    
    click.echo(f"\nTotal: {format_token_count(total_tokens)}")
    click.echo(f"Files processed: {len(file_counts)}")
    
    if verbose and file_counts:
        click.echo("\nToken counts by file:")
        # Sort files by token count in descending order
        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        for file_path, count in sorted_files:
            click.echo(f"  {format_token_count(count).ljust(15)} {file_path}")
            
    if failed_files:
        click.echo(f"\nWarning: Failed to process {len(failed_files)} files:")
        for file_path in failed_files:
            click.echo(f"  {file_path}")
