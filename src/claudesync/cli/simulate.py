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
from ..utils import get_local_files, load_gitignore, should_process_file, load_claudeignore
from ..configmanager import FileConfigManager
from typing import Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Ensure debug level is set

class TreeNode(TypedDict):
    name: str
    size: Optional[int]
    path: str
    children: Optional[List['TreeNode']]

def build_file_tree(base_path: str, files_to_sync: Dict[str, str], config) -> TreeNode:
    """
    Build a hierarchical tree structure from the list of files.

    Args:
        base_path: The root directory path
        files_to_sync: Dictionary of relative file paths and their hashes
        config: Configuration manager instance

    Returns:
        TreeNode: Root node of the tree structure
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Building file tree from base directory with {len(files_to_sync)} sync-eligible files")

    root: TreeNode = {
        'name': os.path.basename(base_path) or 'root',
        'path': '',
        'size': None,
        'children': []
    }

    # Get sync filters
    gitignore = load_gitignore(base_path)
    claudeignore = load_claudeignore(base_path)

    # Process all files in directory
    for root_dir, _, files in os.walk(base_path):
        rel_root = os.path.relpath(root_dir, base_path)
        rel_root = '' if rel_root == '.' else rel_root

        for filename in files:
            rel_path = os.path.join(rel_root, filename)
            full_path = os.path.join(root_dir, filename)

            # Skip if file doesn't exist anymore
            if not os.path.exists(full_path):
                continue

            # Check if file would be included in sync
            would_process = should_process_file(
                config,
                full_path,
                filename,
                gitignore,
                base_path,
                claudeignore
            )

            # Get file size
            try:
                file_size = os.path.getsize(full_path)
            except OSError:
                continue

            # Build path in tree
            current = root
            path_parts = Path(rel_path).parts

            current_path = ''
            for i, part in enumerate(path_parts):
                current_path = os.path.join(current_path, part) if current_path else part

                # Check if this node already exists in children
                child = next((c for c in current['children'] if c['name'] == part), None)

                if child is None:
                    # Create new node
                    is_file = (i == len(path_parts) - 1)
                    new_node: TreeNode = {
                        'name': part,
                        'path': current_path,
                        'size': file_size if is_file else None,
                        'children': [] if not is_file else None,
                        'included': would_process if is_file else None
                    }
                    current['children'].append(new_node)
                    current = new_node
                else:
                    current = child

    # Calculate directory sizes and inclusion status
    calculate_directory_metadata(root)
    logger.debug("Completed building file tree")
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
    """Load .claudeignore content from project root directory."""
    project_root = get_project_root()
    claudeignore_path = project_root / '.claudeignore'
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

    category = config.get_default_category()
    logger.debug(f"Using category: {category}")

    # Get list of files that would be synced
    files_to_sync = get_local_files(config, local_path, category)
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
        logger.debug("Loading fresh config instance")
        if self.config:
            return self.config
        return FileConfigManager()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        logger.debug(f"Handling GET request for path: {parsed_path.path}")

        # Add CORS headers for all responses
        def send_cors_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')

        if parsed_path.path == '/api/treemap':
            logger.debug("Processing /api/treemap request")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            send_cors_headers(self)
            self.end_headers()

            config = self.get_current_config()
            local_path = config.get_local_path()
            category = config.get("default_category")

            if not local_path:
                self.wfile.write(json.dumps({'error': 'No local path configured'}).encode())
                return

            try:
                files_to_sync = get_local_files(config, local_path, category)
                tree = build_file_tree(local_path, files_to_sync, config)
                labels, parents, values, ids, included = convert_to_plotly_format(tree)

                response_data = {
                    'labels': labels,
                    'parents': parents,
                    'values': values,
                    'ids': ids,
                    'included': included
                }
                self.wfile.write(json.dumps(response_data).encode())
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
            response_data = {
                'fileCategories': config.get('file_categories', {}),
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
@click.pass_obj
def simulate(config, port, no_browser):
    """Launch a visualization of files to be synchronized."""
    logger.debug("Starting simulate command")
    logger.debug(f"Configuration object type: {type(config)}")
    logger.debug(f"Configuration local path: {config.get_local_path()}")
    logger.debug(f"Configuration default category: {config.get_default_category()}")

    web_dir = os.path.join(os.path.dirname(__file__), '../web/dist/claudesync-simulate/browser')
    logger.debug(f"Web directory path: {web_dir}")

    if not os.path.exists(web_dir):
        logger.error(f"Web directory does not exist: {web_dir}")
        click.echo(f"Error: Web directory not found at {web_dir}")
        return

    os.chdir(web_dir)

    handler = lambda *args: SyncDataHandler(*args, config=config)

    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}"
        click.echo(f"Server started at {url}")
        logger.debug(f"Server started on port {port}")

        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        if not no_browser:
            webbrowser.open(url)

        click.echo("Press Ctrl+C to stop the server...")
        try:
            server_thread.join()
        except KeyboardInterrupt:
            logger.debug("Received KeyboardInterrupt, shutting down server")
            click.echo("\nShutting down server...")
            httpd.shutdown()
            httpd.server_close()