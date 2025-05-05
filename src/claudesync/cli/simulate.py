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
from .sync_logic import push_files
from claudesync.utils import load_gitignore, load_claudeignore



logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class TreeNode(TypedDict):
    name: str
    size: Optional[int]
    path: str
    children: Optional[List['TreeNode']]
    included: Optional[bool]

def build_file_tree(base_path: str, files_to_sync: Dict[str, str], config, files_config) -> dict:
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

    use_ignore_files = files_config.get("use_ignore_files", True)

    # Get sync filters
    gitignore = load_gitignore(base_path) if use_ignore_files else None
    claudeignore = load_claudeignore(base_path) if use_ignore_files else None

    # Create root node
    root = {
        'name': 'root',
        'children': []
    }

    # Get push_roots from project config
    project_config = config.get_files_config(config.get_active_project()[0])
    push_roots = project_config.get('push_roots', [])

    # Create a set of files that will be synced for quick lookup
    sync_files = set(files_to_sync.keys())

    if not push_roots:
        # Original behavior - use base_path as single root
        process_root(base_path, '', root, sync_files, gitignore, claudeignore)
    else:
        # Process each specified root directory
        for root_dir in push_roots:
            full_root_path = os.path.join(base_path, root_dir)
            if not os.path.exists(full_root_path):
                logger.warning(f"Specified root path does not exist: {full_root_path}")
                continue

            # Process files under this root
            process_root(full_root_path, root_dir, root, sync_files, gitignore, claudeignore)

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

def get_project_root():
    """Get the project root directory."""
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    logger.debug(f"Project root directory: {project_root}")
    return project_root

def load_claudeignore_as_string(config):
    """Load .claudeignore content from local project directory."""
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
    def __init__(self, *args, config=None, **kwargs):
        self.config = config
        super().__init__(*args, **kwargs)

    def get_active_project(self):
        """Get the currently active project path"""
        active_project_path, active_project_id = self.config.get_active_project()
        if not active_project_path:
            raise ConfigurationError("No active project found")
        return active_project_path

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        logger.debug(f"Handling POST request for path: {parsed_path.path}")

        if parsed_path.path == '/api/set-active-project':
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length)

            try:
                data = json.loads(request_body)
                project_path = data.get('path')

                if not project_path:
                    raise ValueError("Project path is required")

                # Verify the project exists
                project_id = self.config.get_project_id(project_path)
                if not project_id:
                    raise ValueError(f"Project not found: {project_path}")

                # Set the active project
                self.config.set_active_project(project_path, project_id)
                self.project = project_path  # Update handler's project reference

                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': f'Active project set to: {project_path}'
                }).encode())

                logger.debug(f"Successfully set active project to: {project_path}")

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in request body: {e}")
                self._send_error_response(400, "Invalid JSON in request body")
            except ValueError as e:
                logger.error(f"Invalid request: {str(e)}")
                self._send_error_response(400, str(e))
            except Exception as e:
                logger.error(f"Error setting active project: {str(e)}\n{traceback.format_exc()}")
                self._send_error_response(500, f"Internal server error: {str(e)}")

            return

        if parsed_path.path == '/api/update-config-incrementally':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    return self._send_error_response(400, "Request body is required")

                request_body = self.rfile.read(content_length)
                try:
                    data = json.loads(request_body)
                except json.JSONDecodeError as e:
                    return self._send_error_response(400, f"Invalid JSON in request body: {str(e)}")

                return self._handle_incremental_config_update(data)
            except Exception as e:
                logger.error(f"Error processing update config request: {str(e)}\n{traceback.format_exc()}")
                return self._send_error_response(500, f"Internal server error: {str(e)}")

        if parsed_path.path == '/api/replace-project-config':
            return self._handle_full_config_replacement()

        if parsed_path.path == '/api/save-claudeignore':
            return self._handle_save_claudeignore()

        if parsed_path.path == '/api/push':
            return self._handle_push()

        if parsed_path.path == '/api/resolve-dropped-files':
            return self._handle_resolve_dropped_files()

        # Handle other POST requests (if any)
        self._send_error_response(404, "Not Found")

    def _handle_incremental_config_update(self, data):
        """
        Perform surgical, incremental updates to the project configuration.

        This method allows targeted modifications to specific configuration lists
        (like includes/excludes) without replacing the entire configuration. It's
        designed for quick, precise adjustments to the project's synchronization settings.

        Update actions include:
        - Adding or removing a pattern to includes
        - Adding or removing a pattern from excludes
        - Dynamically modifying configuration in a granular manner

        Args:
            data (dict): A dictionary containing:
                - 'action': The type of update (e.g., 'addInclude', 'removeExclude')
                - 'pattern': The specific pattern to add or remove

        Returns:
            dict: A response indicating the result of the configuration update

        Raises:
            ValueError: If the update action is invalid or cannot be performed
        """
        try:
            # Validate request data
            if not isinstance(data, dict):
                return self._send_error_response(400, "Invalid request format")

            # Get required fields
            action = data.get('action')
            pattern = data.get('pattern')

            # Validate fields
            if not action:
                return self._send_error_response(400, "No action specified")
            if not pattern:
                return self._send_error_response(400, "No pattern provided")
            if not isinstance(pattern, str):
                return self._send_error_response(400, "Pattern must be a string")
            if len(pattern.strip()) == 0:
                return self._send_error_response(400, "Pattern cannot be empty")

            # Get active project and configuration
            active_project = self.config.get_active_project()[0]
            if not active_project:
                return self._send_error_response(400, "No active project found")

            try:
                files_config = self.config.get_files_config(active_project)
            except ConfigurationError as e:
                logger.error(f"Failed to load project configuration: {str(e)}")
                return self._send_error_response(500, f"Failed to load project configuration: {str(e)}")

            # Initialize includes/excludes if they don't exist
            if 'includes' not in files_config:
                files_config['includes'] = []
            if 'excludes' not in files_config:
                files_config['excludes'] = []

            # Validate lists
            if not isinstance(files_config['includes'], list):
                return self._send_error_response(500, "Invalid project configuration: 'includes' must be a list")
            if not isinstance(files_config['excludes'], list):
                return self._send_error_response(500, "Invalid project configuration: 'excludes' must be a list")

            # Handle different actions
            if action == 'addInclude':
                if pattern in files_config['includes']:
                    return self._send_error_response(409, f"Pattern '{pattern}' already exists in includes")
                files_config['includes'].append(pattern)
                message = f"Added pattern to includes: {pattern}"

            elif action == 'removeInclude':
                if pattern not in files_config['includes']:
                    return self._send_error_response(404, f"Pattern '{pattern}' not found in includes")
                files_config['includes'].remove(pattern)
                message = f"Removed pattern from includes: {pattern}"

            elif action == 'addExclude':
                if pattern in files_config['excludes']:
                    return self._send_error_response(409, f"Pattern '{pattern}' already exists in excludes")
                files_config['excludes'].append(pattern)
                message = f"Added pattern to excludes: {pattern}"

            elif action == 'removeExclude':
                if pattern not in files_config['excludes']:
                    return self._send_error_response(404, f"Pattern '{pattern}' not found in excludes")
                files_config['excludes'].remove(pattern)
                message = f"Removed pattern from excludes: {pattern}"

            else:
                return self._send_error_response(400, f"Unknown action: {action}")

            # Save updated config
            try:
                project_config_path = self.config.config_dir / f"{active_project}.project.json"
                with open(project_config_path, 'w') as f:
                    json.dump(files_config, f, indent=2)
            except IOError as e:
                logger.error(f"Failed to save project configuration: {str(e)}")
                return self._send_error_response(500, f"Failed to save configuration: {str(e)}")

            # Send success response with updated config
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'message': message,
                'config': files_config
            }).encode())

        except Exception as e:
            logger.error(f"Error updating config: {str(e)}\n{traceback.format_exc()}")
            return self._send_error_response(500, f"Internal server error: {str(e)}")

    def _handle_full_config_replacement(self):
        """
        Handle replacing the entire project configuration with a new one.
        """
        try:
            # Read the request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return self._send_error_response(400, "Request body is required")

            request_body = self.rfile.read(content_length)
            try:
                data = json.loads(request_body)
                content = data.get('content')

                if not content:
                    return self._send_error_response(400, "No configuration content provided")

                # Validate JSON
                try:
                    json_config = json.loads(content)

                    # Additional validation - check for required fields
                    required_fields = ['project_name', 'includes', 'excludes']
                    for field in required_fields:
                        if field not in json_config:
                            return self._send_error_response(400, f"Missing required field: {field}")

                except json.JSONDecodeError as e:
                    return self._send_error_response(400, f"Invalid JSON configuration: {str(e)}")

                # Get active project
                active_project_path, _ = self.config.get_active_project()
                if not active_project_path:
                    return self._send_error_response(400, "No active project found")

                # Determine the project config file path
                project_config_path = self.config.config_dir / f"{active_project_path}.project.json"

                # Write the updated configuration
                with open(project_config_path, 'w') as f:
                    f.write(content)

                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': 'Project configuration updated successfully'
                }).encode())

                logger.debug(f"Updated project configuration for {active_project_path}")

            except json.JSONDecodeError as e:
                return self._send_error_response(400, f"Invalid request body: {str(e)}")

        except Exception as e:
            logger.error(f"Error saving project configuration: {str(e)}\n{traceback.format_exc()}")
            return self._send_error_response(500, f"Internal server error: {str(e)}")


    def _handle_save_claudeignore(self):
        """
        Handle saving updated .claudeignore content.
        """
        try:
            # Read the request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return self._send_error_response(400, "Request body is required")

            request_body = self.rfile.read(content_length)
            try:
                data = json.loads(request_body)
                content = data.get('content')

                if content is None:
                    return self._send_error_response(400, "No .claudeignore content provided")

                # Get project root
                project_root = self.config.get_project_root()
                if not project_root:
                    return self._send_error_response(500, "Could not determine project root")

                claudeignore_path = Path(project_root) / '.claudeignore'

                # Write the updated .claudeignore
                with open(claudeignore_path, 'w') as f:
                    f.write(content)

                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'message': '.claudeignore updated successfully'
                }).encode())

                logger.debug(f"Updated .claudeignore at {claudeignore_path}")

            except json.JSONDecodeError as e:
                return self._send_error_response(400, f"Invalid request body: {str(e)}")

        except Exception as e:
            logger.error(f"Error saving .claudeignore: {str(e)}\n{traceback.format_exc()}")
            return self._send_error_response(500, f"Internal server error: {str(e)}")

    def _send_error_response(self, status_code: int, message: str):
        """Helper method to send error responses"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({
            'success': False,
            'error': message
        }).encode())

    def do_GET(self):
        parsed_path = urlparse(self.path)
        logger.debug(f"Handling GET request for path: {parsed_path.path}")

        if parsed_path.path.startswith('/api/file-content'):
            try:
                # Parse the file path from query parameters
                query_params = parse_qs(parsed_path.query)
                file_path = query_params.get('path', [''])[0]

                if not file_path:
                    self._send_error_response(400, "Missing file path parameter")
                    return

                # Get current config and project root
                project_root = self.config.get_project_root()

                # Validate the requested path is within project root for security
                full_path = os.path.join(project_root, file_path)
                if not is_safe_path(project_root, file_path):
                    self._send_error_response(403, "Access denied - path is outside project root")
                    return

                # Check if file exists
                if not os.path.exists(full_path) or not os.path.isfile(full_path):
                    self._send_error_response(404, "File not found")
                    return

                # Read and return file content
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'content': content,
                        'path': file_path
                    }).encode())

                except UnicodeDecodeError:
                    self._send_error_response(400, "File is not valid UTF-8 text")
                except IOError as e:
                    self._send_error_response(500, f"Error reading file: {str(e)}")

            except Exception as e:
                logger.error(f"Error processing file content request: {str(e)}\n{traceback.format_exc()}")
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        if parsed_path.path == '/api/sync-data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()

            try:
                local_path = self.config.get_project_root()
                active_project = self.get_active_project()
                files_config = self.config.get_files_config(active_project)

                # Get files that would be synced based on project configuration
                files_to_sync = get_local_files(self.config, local_path, files_config)

                # Build response data
                response_data = {
                    'claudeignore': load_claudeignore_as_string(self.config),
                    'project': files_config,
                    'stats': self._get_stats(local_path, files_to_sync),
                    'treemap': self._get_treemap(local_path, files_to_sync, self.config, files_config)
                }

                self.wfile.write(json.dumps(response_data).encode())
            except Exception as e:
                logger.error(f"Error processing sync data request: {str(e)}\n{traceback.format_exc()}")
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        if parsed_path.path == '/api/projects':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()

            try:
                # Get all projects, including unlinked ones
                projects = self.config.get_projects(include_unlinked=True)
                active_project_path, active_project_id = self.config.get_active_project()

                response = {
                    'projects': [
                        {
                            'id': project_id if project_id else '',  # Empty string for unlinked projects
                            'path': project_path,
                            'linked': bool(project_id)  # True if project has an ID
                        }
                        for project_path, project_id in projects.items()
                    ],
                    'activeProject': active_project_path
                }

                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                logger.error(f"Error getting projects: {str(e)}\n{traceback.format_exc()}")
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

    def _get_treemap(self, local_path, files_to_sync, config, files_config):
        """Generate treemap data"""
        tree = build_file_tree(local_path, files_to_sync, config, files_config)
        return tree

    def _handle_push(self):
        try:
            push_files(self.config)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'message': 'Files successfully pushed to Claude.ai'
            }).encode())
        except Exception as e:
            self._send_error_response(500, str(e))

    def _handle_resolve_dropped_files(self):
        """
        Handle resolving dropped files to their project paths.

        This endpoint accepts file content and scans the project
        directory to find matches, returning the relative paths.
        """
        try:
            # Read the request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return self._send_error_response(400, "Request body is required")

            request_body = self.rfile.read(content_length)
            try:
                data = json.loads(request_body)
                files = data.get('files', [])

                if not files or not isinstance(files, list):
                    return self._send_error_response(400, "Invalid or empty files array")

                # Get project root
                project_root = self.config.get_project_root()
                if not project_root:
                    return self._send_error_response(500, "Could not determine project root")

                # Process files and find matches
                results = self._find_file_matches(project_root, files)

                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'results': results
                }).encode())

            except json.JSONDecodeError as e:
                return self._send_error_response(400, f"Invalid JSON in request body: {str(e)}")

        except Exception as e:
            logger.error(f"Error resolving dropped files: {str(e)}\n{traceback.format_exc()}")
            return self._send_error_response(500, f"Internal server error: {str(e)}")


    def _find_file_matches(self, project_root, files):
        """
        Find file matches in the project directory based on filename only.
        Also considers patterns from .gitignore and .claudeignore.

        Args:
            project_root (str): Path to the project root directory
            files (list): List of dictionaries with file info

        Returns:
            list: List of match results with original names and resolved paths
        """
        results = []

        # Load .gitignore and .claudeignore patterns
        gitignore = load_gitignore(project_root)
        claudeignore = load_claudeignore(project_root)

        for file_info in files:
            name = file_info.get('name', '')

            if not name:
                results.append({
                    'originalName': name,
                    'resolved': False,
                    'error': 'Missing filename'
                })
                continue

            # Find all files with matching name
            name_matches = []
            for root, _, filenames in os.walk(project_root):
                for filename in filenames:
                    if filename == name:
                        full_path = os.path.join(root, filename)
                        # Get relative path and ensure forward slashes
                        rel_path = os.path.relpath(full_path, project_root)
                        rel_path = rel_path.replace('\\', '/')

                        # Skip files matching .gitignore or .claudeignore patterns
                        if gitignore and gitignore.match_file(rel_path):
                            continue
                        if claudeignore and claudeignore.match_file(rel_path):
                            continue

                        name_matches.append(rel_path)

            if name_matches:
                results.append({
                    'originalName': name,
                    'resolved': True,
                    'paths': name_matches
                })
            else:
                results.append({
                    'originalName': name,
                    'resolved': False,
                    'error': 'No matching file found in project'
                })

        return results

@click.command()
@click.option('--port', default=4201, help='Port to run the server on')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
@click.pass_obj
def simulate_push(config, port, no_browser):
    """Launch a visualization of files to be synchronized."""
    logger.debug("Starting simulate command")

    # Import the ensure_gitignore_entries function
    from claudesync.cli.project import ensure_gitignore_entries

    # Ensure .gitignore entries are set
    try:
        # Get the .claudesync directory path
        claudesync_dir = config.config_dir
        if claudesync_dir:
            # Get the active project for more specific pattern
            active_project_path, _ = config.get_active_project()
            ensure_gitignore_entries(claudesync_dir, active_project_path)
    except Exception as e:
        logger.warning(f"Could not ensure .gitignore entries: {str(e)}")

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

    handler = lambda *args: SyncDataHandler(*args, config=config)

    try:
        with LocalhostTCPServer(("127.0.0.1", port), handler) as httpd:
            url = f"http://localhost:{port}"
            click.echo(f"Server started at {url}")

            # Get active project for initial message
            try:
                active_project = config.get_active_project()[0]
                click.echo(f"Simulating sync for active project: {active_project}")
            except ConfigurationError:
                click.echo("Warning: No active project set")

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

