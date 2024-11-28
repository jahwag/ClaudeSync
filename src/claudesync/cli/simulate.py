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

class SyncDataHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            config = {
                "fileCategories": {
                    "main": {
                        "description": "Active Category",
                        "patterns": [
                            "app.py",
                            "src/index.html",
                            "src/main.ts",
                            "src/styles.css"
                        ]
                    },
                    "docs": {
                        "description": "Documentation",
                        "patterns": [
                            "docs/*.md",
                            "README.md"
                        ]
                    }
                },
                "claudeignore": load_claudeignore()
            }

            self.wfile.write(json.dumps(config).encode())
            return

        elif parsed_path.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            stats = {
                "totalFiles": 127,
                "filesToSync": 43,
                "totalSize": "2.4 MB"
            }

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

    handler = SyncDataHandler
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