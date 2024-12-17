import traceback

import click
import logging
import os
import json
import http.server
import socketserver
import webbrowser
import threading
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from pathspec import pathspec

from ..exceptions import ConfigurationError
from ..utils import get_local_files, load_gitignore, load_claudeignore
from ..configmanager import FileConfigManager
from typing import Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class TreeNode(TypedDict):
    name: str
    size: Optional[int]
    path: str
    children: Optional[List['TreeNode']]
    included: Optional[bool]

def build_file_tree(base_path: str, files_to_sync: Dict[str, str], config) -> dict:
    """
    Build a hierarchical tree structure from the list of files with support for multiple roots.

    Args:
        base_path: The root directory path
        files_to_sync: Dictionary of relative file paths and their hashes
        config: Configuration manager instance

    Returns:
        dict: Root node of the tree structure with support for multiple roots
    """
    logger = logging.getLogger(__name__)

    # Get sync filters
    gitignore = load_gitignore(base_path)
    claudeignore = load_claudeignore(base_path)

    # Create root node
    root = {
        'name': 'root',
        'children': []
    }

    # Get simulate_push_roots from project config
    project_config = config.get_files_config(config.get_active_project()[0])
    simulate_push_roots = project_config.get('simulate_push_roots', [])

    # Create a set of files that will be synced for quick lookup
    sync_files = set(files_to_sync.keys())

    if not simulate_push_roots:
        # Original behavior - use base_path as single root
        process_root(base_path, '', root, sync_files, gitignore, claudeignore)
    else:
        # Process each specified root directory
        for root_dir in simulate_push_roots:
            full_root_path = os.path.join(base_path, root_dir)
            if not os.path.exists(full_root_path):
                logger.warning(f"Specified root path does not exist: {full_root_path}")
                continue

            # Create node for this root directory
            root_node = {
                'name': root_dir,
                'children': []
            }
            root['children'].append(root_node)

            # Process files under this root
            process_root(full_root_path, root_dir, root_node, sync_files, gitignore, claudeignore)

    return root

def process_root(root_dir: str, rel_root_base: str, node: dict, sync_files: set,
                 gitignore: Optional[pathspec.PathSpec], claudeignore: Optional[pathspec.PathSpec]):
    """
    Process a single root directory and build its tree structure.

    Args:
        root_dir: The full path to the root directory
        rel_root_base: The relative path base for this root
        node: The node to populate with the tree structure
        sync_files: Set of files that will be synced
        gitignore: PathSpec object for gitignore patterns
        claudeignore: PathSpec object for claudeignore patterns
    """
    for current_dir, _, files in os.walk(root_dir):
        # Get path relative to the project root
        rel_root = os.path.relpath(current_dir, root_dir)
        rel_root = '' if rel_root == '.' else rel_root

        # Skip ignored directories
        full_rel_path = os.path.join(rel_root_base, rel_root) if rel_root_base else rel_root
        if (gitignore and gitignore.match_file(full_rel_path)) or \
                (claudeignore and claudeignore.match_file(full_rel_path)):
            continue

        for filename in files:
            rel_path = os.path.join(full_rel_path, filename)
            full_path = os.path.join(current_dir, filename)

            # Skip if file doesn't exist anymore or is ignored
            if not os.path.exists(full_path) or \
                    (claudeignore and claudeignore.match_file(rel_path)):
                continue

            # Get file size
            try:
                file_size = os.path.getsize(full_path)
            except OSError:
                continue

            # Build path in tree
            current = node
            path_parts = Path(rel_path).parts

            # Navigate/build the tree structure
            for i, part in enumerate(path_parts[:-1]):
                # Find or create directory node
                child = next((c for c in current['children'] if c['name'] == part), None)
                if child is None:
                    child = {
                        'name': part,
                        'children': []
                    }
                    current['children'].append(child)
                current = child

            # Add the file node
            current['children'].append({
                'name': path_parts[-1],
                'size': file_size,
                'included': rel_path in sync_files
            })

def convert_to_plotly_format(node: TreeNode) -> tuple[List[str], List[str], List[int], List[str], List[bool]]:
    """
    Convert the tree structure to Plotly treemap format.

    Args:
        node: Root node of the tree

    Returns:
        tuple: (labels, parents, values, ids, included) for Plotly treemap
    """
    labels: List[str] = []
    parents: List[str] = []
    values: List[int] = []
    ids: List[str] = []
    included: List[bool] = []

    def traverse(node: TreeNode, parent: str = ""):
        node_id = os.path.join(parent, node['name']) if parent else node['name']

        labels.append(node['name'])
        parents.append(parent)
        values.append(node['size'] or 0)
        ids.append(node_id)
        included.append(node.get('included', False))

        if node['children']:
            for child in node['children']:
                traverse(child, node_id)

    traverse(node)
    return labels, parents, values, ids, included

def get_project_root():
    """Get the project root directory."""
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    logger.debug(f"Project root directory: {project_root}")
    return project_root

def load_claudeignore_as_string():
    """Load .claudeignore content from local project directory."""
    config = FileConfigManager()
    local_path = config.get_local_path()
    logger.debug(f"Loading .claudeignore from local path: {local_path}")

    if not local_path:
        logger.warning("No local path found in config")
        return ""

    claudeignore_path = Path(local_path) / '.claudeignore'
    logger.debug(f"Attempting to load .claudeignore from: {claudeignore_path}")

    try:
        with open(claudeignore_path, 'r') as f:
            content = f.read().strip()
            logger.debug(f"Successfully loaded .claudeignore with content length: {len(content)}")
            return content
    except FileNotFoundError:
        logger.warning(f".claudeignore file not found at {claudeignore_path}")
        return ""
    except Exception as e:
        logger.error(f"Error reading .claudeignore at {claudeignore_path}: {e}")
        return ""

def is_safe_path(base_dir: str, requested_path: str) -> bool:
    """
    Safely verify that the requested path is within the base directory.
    """
    try:
        # Resolve any symlinks and normalize path
        base_dir = os.path.realpath(base_dir)
        requested_path = os.path.realpath(os.path.join(base_dir, requested_path))

        # Check if the resolved path starts with the base directory
        common_prefix = os.path.commonpath([requested_path, base_dir])
        return common_prefix == base_dir
    except (ValueError, OSError):
        # Handle any path manipulation errors
        return False

def load_config():
    """Load configuration from .claudesync/config.local.json."""
    project_root = get_project_root()
    config_path = project_root / '.claudesync' / 'config.local.json'
    logger.debug(f"Attempting to load config from: {config_path}")

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            categories = config.get('file_categories', {})
            logger.debug(f"Successfully loaded config with {len(categories)} categories: {list(categories.keys())}")
            return categories
    except FileNotFoundError:
        logger.warning(f"Config file not found at {config_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file at {config_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error reading config file at {config_path}: {e}")
        return {}

def format_size(size):
    """Convert size in bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

class SyncDataHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, config=None, project=None, **kwargs):
        self.config = config
        self.project = project
        super().__init__(*args, **kwargs)

    def get_current_config(self):
        """Get a fresh config instance for each request"""
        return FileConfigManager()  # Always create new instance with fresh data

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_GET(self):
        parsed_path = urlparse(self.path)
        logger.debug(f"Handling GET request for path: {parsed_path.path}")

        if parsed_path.path == '/api/sync-data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()

            try:
                config = self.get_current_config()
                local_path = config.get_project_root()
                files_config = config.get_files_config(self.project)

                # Get files that would be synced based on project configuration
                files_to_sync = get_local_files(config, local_path, files_config)

                # Build response data
                response_data = {
                    'config': {
                        'fileCategories': files_config,
                        'claudeignore': load_claudeignore_as_string(),
                        'project': self.project
                    },
                    'stats': self._get_stats(local_path, files_to_sync),
                    'treemap': self._get_treemap(local_path, files_to_sync, config)
                }

                self.wfile.write(json.dumps(response_data).encode())
            except Exception as e:
                logger.error(f"Error processing sync data request: {str(e)}\n{traceback.format_exc()}")
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        # For all other paths, serve static files
        return super().do_GET()

    def _get_stats(self, local_path, files_to_sync):
        """Calculate sync statistics"""
        total_size = 0
        total_files = 0

        for file_path in files_to_sync:
            full_path = os.path.join(local_path, file_path)
            if os.path.exists(full_path):
                size = os.path.getsize(full_path)
                total_size += size
                total_files += 1

        return {
            "filesToSync": total_files,
            "totalSize": format_size(total_size)
        }

    def _get_treemap(self, local_path, files_to_sync, config):
        """Generate treemap data"""
        tree = build_file_tree(local_path, files_to_sync, config)
        return tree

@click.command()
@click.argument("project", required=False)
@click.option('--port', default=4201, help='Port to run the server on')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
@click.pass_obj
def simulate_push(config, project, port, no_browser):
    """Launch a visualization of files to be synchronized."""
    logger.debug("Starting simulate command")
    logger.debug(f"Project: {project}")

    if not project:
        active_project_path, active_project_id = config.get_active_project()
        if not active_project_path:
            raise ConfigurationError("No active project found. Please specify a project or set an active one using 'project set'")
        project = active_project_path

    # Verify the project exists and get its configuration
    try:
        project_id = config.get_project_id(project)
        files_config = config.get_files_config(project)
        logger.debug(f"Using project: {project} (ID: {project_id})")
    except ConfigurationError as e:
        logger.error(f"Project configuration error: {e}")
        click.echo(f"Error: {str(e)}")
        return

    web_dir = os.path.join(os.path.dirname(__file__), '../web/dist/claudesync-simulate')
    logger.debug(f"Web directory path: {web_dir}")

    if not os.path.exists(web_dir):
        logger.error(f"Web directory does not exist: {web_dir}")
        click.echo(f"Error: Web directory not found at {web_dir}")
        return

    os.chdir(web_dir)

    class LocalhostTCPServer(socketserver.TCPServer):
        def server_bind(self):
            self.socket.setsockopt(socketserver.socket.SOL_SOCKET, socketserver.socket.SO_REUSEADDR, 1)
            self.socket.bind(('127.0.0.1', self.server_address[1]))

    handler = lambda *args: SyncDataHandler(*args, config=config, project=project)

    try:
        with LocalhostTCPServer(("127.0.0.1", port), handler) as httpd:
            url = f"http://localhost:{port}"
            click.echo(f"Server started at {url}")
            click.echo(f"Simulating sync for project: {project}")
            logger.debug(f"Server started on port {port}, bound to localhost only")

            if not no_browser:
                webbrowser.open(url)

            click.echo("Press Ctrl+C to stop the server...")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                logger.debug("Received KeyboardInterrupt, shutting down server")
                click.echo("\nShutting down server...")
                httpd.shutdown()
                httpd.server_close()
    except OSError as e:
        if e.errno == 98:  # Address already in use
            logger.error(f"Port {port} is already in use")
            click.echo(f"Error: Port {port} is already in use. Try a different port with --port option.")
        else:
            logger.error(f"Failed to start server: {e}")
            click.echo(f"Error: Failed to start server: {e}")