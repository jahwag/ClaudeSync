import click
import logging
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
import http.server
import socketserver
import threading

from ..utils import handle_errors, validate_and_get_provider

logger = logging.getLogger(__name__)

ANGULAR_APP_PATH = os.path.join(os.path.dirname(__file__), '..', 'web', 'dist', 'claudesync-simulate')

@click.command()
@click.option('--port', default=4200, help='Port to run the server on')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
@click.pass_obj
@handle_errors
def simulate(config, port, no_browser):
    """Launch a visualization of files to be synchronized."""
    # Validate configuration and provider
    provider = validate_and_get_provider(config, require_project=True)

    # Check if the Angular app is built
    if not os.path.exists(ANGULAR_APP_PATH):
        click.echo("Angular application not found. Please ensure the application is built.")
        sys.exit(1)

    # Set up the HTTP server
    handler = http.server.SimpleHTTPRequestHandler
    web_dir = os.path.join(os.path.dirname(__file__), ANGULAR_APP_PATH)
    os.chdir(web_dir)

    # Create and start the server
    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}"
        click.echo(f"Server started at {url}")

        # Start the server in a separate thread
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # Open the browser unless --no-browser is specified
        if not no_browser:
            webbrowser.open(url)

        click.echo("Press Ctrl+C to stop the server...")
        try:
            server_thread.join()
        except KeyboardInterrupt:
            click.echo("\nShutting down server...")
            httpd.shutdown()
            httpd.server_close()