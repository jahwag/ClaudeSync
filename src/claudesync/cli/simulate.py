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
from ..utils import get_local_files
from ..configmanager import FileConfigManager

logger = logging.getLogger(__name__)

def get_project_root():
    """Get the project root directory."""
    # Start from the directory containing this script
    current_dir = Path(__file__).resolve().parent
    # Go up two levels: from cli/ to project root
    return current_dir.parent.parent

def load_claudeignore():
    """Load .claudeignore content from project root directory."""
    project_root = get_project_root()
    claudeignore_path = project_root / '.claudeignore'

    try:
        with open(claudeignore_path, 'r') as f:
            return f.read().strip()
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

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get('file_categories', {})
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
    if not local_path:
        return {
            "totalFiles": 0,
            "filesToSync": 0,
            "totalSize": "0 B"
        }

    # Get the default category or use None to include all files
    category = config.get_default_category()

    # Get list of files that would be synced
    files_to_sync = get_local_files(config, local_path, category)

    # Calculate total size of files to sync
    total_size = 0
    total_files = 0

    for file_path in files_to_sync.keys():
        full_path = os.path.join(local_path, file_path)
        if os.path.exists(full_path):
            total_size += os.path.getsize(full_path)
            total_files += 1

    # Convert size to human-readable format
    size_str = format_size(total_size)

    # Count all files in project directory for comparison
    all_files = sum(1 for _ in Path(local_path).rglob('*') if _.is_file())

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

    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            config = {
                "fileCategories": load_config(),
                "claudeignore": load_claudeignore()
            }

            self.wfile.write(json.dumps(config).encode())
            return

        elif parsed_path.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            stats = calculate_sync_stats(self.config)
            self.wfile.write(json.dumps(stats).encode())
            return

        return super().do_GET()

@click.command()
@click.option('--port', default=4200, help='Port to run the server on')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
@click.pass_obj
def simulate(config, port, no_browser):
    """Launch a visualization of files to be synchronized."""
    web_dir = os.path.join(os.path.dirname(__file__), '../web/dist/claudesync-simulate/browser')
    os.chdir(web_dir)

    # Create handler class with config
    handler = lambda *args: SyncDataHandler(*args, config=config)

    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}"
        click.echo(f"Server started at {url}")

        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        if not no_browser:
            webbrowser.open(url)

        click.echo("Press Ctrl+C to stop the server...")
        try:
            server_thread.join()
        except KeyboardInterrupt:
            click.echo("\nShutting down server...")
            httpd.shutdown()
            httpd.server_close()