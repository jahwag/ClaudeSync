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

from ..exceptions import ConfigurationError
from ..utils import get_local_files, load_gitignore, load_claudeignore
from ..configmanager import FileConfigManager
from typing import Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)  # Ensure debug level is set

class TreeNode(TypedDict):
    name: str
    size: Optional[int]
    path: str
    children: Optional[List['TreeNode']]
    included: Optional[bool]

def build_file_tree(base_path: str, files_to_sync: Dict[str, str], config) -> dict:
    """
    Build a hierarchical tree structure from the list of files.

    Args:
        base_path: The root directory path
        files_to_sync: Dictionary of relative file paths and their hashes
        config: Configuration manager instance

    Returns:
        dict: Root node of the tree structure
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Building file tree from base directory with {len(files_to_sync)} sync-eligible files")

    root = {
        'name': os.path.basename(base_path) or 'root',
        'children': []
    }

    # Get sync filters
    gitignore = load_gitignore(base_path)
    claudeignore = load_claudeignore(base_path)

    # Create a set of files that will be synced for quick lookup
    sync_files = set(files_to_sync.keys())

    # Process all files in directory
    for root_dir, _, files in os.walk(base_path):
        rel_root = os.path.relpath(root_dir, base_path)
        rel_root = '' if rel_root == '.' else rel_root

        # Skip ignored directories
        if (gitignore and gitignore.match_file(rel_root)) or \
                (claudeignore and claudeignore.match_file(rel_root)):
            continue

        for filename in files:
            rel_path = os.path.join(rel_root, filename)
            full_path = os.path.join(root_dir, filename)

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
            current = root
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

    return root

def calculate_directory_metadata(node: TreeNode) -> tuple[int, bool]:
    """
    Recursively calculate the total size and inclusion status of directories.

    Args:
        node: Current tree node

    Returns:
        tuple[int, bool]: Total size and whether any children are included
    """
    if not node['children']:  # Leaf node (file)
        return node['size'] or 0, node.get('included', False)

    total_size = 0
    has_included_files = False

    for child in node['children']:
        child_size, child_included = calculate_directory_metadata(child)
        total_size += child_size
        has_included_files = has_included_files or child_included

    node['size'] = total_size
    node['included'] = has_included_files
    return total_size, has_included_files

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

def calculate_sync_stats(config):
    """Calculate statistics about files that would be synced."""
    local_path = config.get_local_path()
    logger.debug(f"Calculating sync stats for local path: {local_path}")

    if not local_path:
        logger.warning("No local path found in config")
        return {
            "totalFiles": 0,
            "filesToSync": 0,
            "totalSize": "0 B"
        }

    # Get the default category name
    default_category = config.get("default_sync_category")
    logger.debug(f"Using default sync category: {default_category}")

    # Get list of files that would be synced
    files_to_sync = get_local_files(config, local_path, default_category)
    logger.debug(f"Found {len(files_to_sync)} files to sync")

    # Calculate total size of files to sync
    total_size = 0
    total_files = 0

    for file_path in files_to_sync.keys():
        full_path = os.path.join(local_path, file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            total_size += size
            total_files += 1

    # Convert size to human-readable format
    size_str = format_size(total_size)

    # Count all files in project directory for comparison
    all_files = sum(1 for _ in Path(local_path).rglob('*') if _.is_file())
    logger.debug(f"Total files in directory: {all_files}")
    logger.debug(f"Files to sync: {total_files}")
    logger.debug(f"Total size to sync: {size_str}")

    return {
        "totalFiles": all_files,
        "filesToSync": total_files,
        "totalSize": size_str
    }

def format_size(size):
    """Convert size in bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

class SyncDataHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, config=None, **kwargs):
        self.config = config
        super().__init__(*args, **kwargs)

    def get_current_config(self):
        """Get a fresh config instance for each request"""
        return FileConfigManager()  # Always create new instance with fresh data

    def do_GET(self):
        parsed_path = urlparse(self.path)
        logger.debug(f"Handling GET request for path: {parsed_path.path}")

        def send_cors_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')

        if parsed_path.path.startswith('/api/file-content'):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            send_cors_headers(self)
            self.end_headers()

            # Get the file path from query parameters
            query_params = parse_qs(parsed_path.query)
            file_path = query_params.get('path', [''])[0]

            if not file_path:
                self.wfile.write(json.dumps({'error': 'No file path provided'}).encode())
                return

            config = self.get_current_config()
            local_path = config.get_local_path()

            if not local_path:
                self.wfile.write(json.dumps({'error': 'No local path configured'}).encode())
                return

            try:
                if not is_safe_path(local_path, file_path):
                    self.send_error(403, 'Access denied')
                    return

                full_path = os.path.join(local_path, file_path)
                # Basic security check to ensure the path is within the project directory
                if not os.path.abspath(full_path).startswith(os.path.abspath(local_path)):
                    self.wfile.write(json.dumps({'error': 'Invalid file path'}).encode())
                    return

                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.wfile.write(json.dumps({'content': content}).encode())
            except Exception as e:
                logger.error(f"Error reading file content: {str(e)}")
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        if parsed_path.path == '/api/treemap':
            logger.debug("Processing /api/treemap request")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            send_cors_headers(self)
            self.end_headers()

            config = self.get_current_config()
            local_path = config.get_local_path()

            # Get the default category name and then use it to get the active category
            default_category = config.get("default_sync_category")
            categories = config.get("file_categories", {})
            active_category = categories.get(default_category) if default_category else None

            if not local_path:
                self.wfile.write(json.dumps({'error': 'No local path configured'}).encode())
                return

            try:
                files_to_sync = get_local_files(config, local_path, default_category)
                tree = build_file_tree(local_path, files_to_sync, config)
                self.wfile.write(json.dumps(tree).encode())
            except Exception as e:
                logger.error(f"Error generating treemap data: {str(e)}")
                self.wfile.write(json.dumps({'error': str(e)}).encode())
                traceback.print_exc()
            return

        elif parsed_path.path == '/api/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            send_cors_headers(self)
            self.end_headers()

            config = self.get_current_config()

            # Get the default category name and then the active category
            default_category = config.get("default_sync_category")
            categories = config.get("file_categories", {})
            active_category = {
                default_category: categories.get(default_category)
            } if default_category and default_category in categories else {}

            response_data = {
                'fileCategories': active_category,
                'claudeignore': load_claudeignore_as_string()
            }
            self.wfile.write(json.dumps(response_data).encode())
            return

        elif parsed_path.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            send_cors_headers(self)
            self.end_headers()

            config = self.get_current_config()
            stats = calculate_sync_stats(config)
            self.wfile.write(json.dumps(stats).encode())
            return

        # For all other paths, serve static files
        return super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

@click.command()
@click.option('--port', default=4201, help='Port to run the server on')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
@click.option('--project', help='Project to simulate (defaults to active project)')
@click.pass_obj
def simulate_push(config, port, no_browser, project):
    """Launch a visualization of files to be synchronized."""
    logger.debug("Starting simulate command")
    logger.debug(f"Project: {project}")
    logger.debug(f"Configuration object type: {type(config)}")
    logger.debug(f"Configuration local path: {config.get_local_path()}")

    if not project:
        active_project, _ = config.get_active_project()
        if not active_project:
            raise ConfigurationError("No active project found. Please specify a project or set an active one using 'project set'")
        project = active_project

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
            # Explicitly bind to localhost
            self.socket.bind(('127.0.0.1', self.server_address[1]))

    handler = lambda *args: SyncDataHandler(*args, config=config)

    try:
        with LocalhostTCPServer(("127.0.0.1", port), handler) as httpd:
            url = f"http://localhost:{port}"
            click.echo(f"Server started at {url}")
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