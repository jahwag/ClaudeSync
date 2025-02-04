import click
import logging
from pathlib import Path
from typing import Tuple, Dict

from claudesync.configmanager import FileConfigManager
from claudesync.exceptions import ConfigurationError, ProviderError
from claudesync.utils import validate_and_get_provider, get_local_files
from claudesync.syncmanager import SyncManager

logger = logging.getLogger(__name__)

def push_files(
        config: FileConfigManager,
        project: str = None,
        simulate: bool = False
) -> Tuple[Dict[str, str], Dict[str, str], str]:
    """
    Push files to Claude.ai based on configuration.

    Args:
        config: Configuration manager instance
        project: Project name to push. If None, uses active project
        simulate: If True, only returns what would be pushed without executing

    Returns:
        Tuple containing:
        - Dictionary of files that would be pushed
        - Dictionary mapping project paths to their IDs
        - Project ID
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

    provider = validate_and_get_provider(config)

    # Use project configuration
    active_organization_id = config.get("active_organization_id")
    project_id = config.get_project_id(project)

    # Get files to sync using patterns from files configuration
    local_files = get_local_files(config, project_root, files_config)

    # Set as active project
    config.set_active_project(project, project_id)

    if not simulate:
        # Sync files
        remote_files = provider.list_files(active_organization_id, project_id)
        sync_manager = SyncManager(provider, config, project_id, project_root)
        sync_manager.sync(local_files, remote_files)
        click.echo(f"Project '{project}' synced successfully")
        click.echo(f"Remote URL: https://claude.ai/project/{project_id}")

    return local_files, files_config, project_id