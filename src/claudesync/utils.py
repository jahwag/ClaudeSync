import os
import hashlib
import mimetypes
from functools import wraps

import click
import pathspec
import logging

from claudesync.exceptions import ConfigurationError, ProviderError
from claudesync.provider_factory import get_provider
from claudesync.config_manager import ConfigManager

logger = logging.getLogger(__name__)

config_manager = ConfigManager()

def calculate_checksum(content):
    normalized_content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.md5(normalized_content.encode("utf-8")).hexdigest()


def load_gitignore(base_path):
    patterns = []
    current_dir = base_path
    while True:
        gitignore_path = os.path.join(current_dir, ".gitignore")
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as f:
                patterns.extend(f.read().splitlines())

        if os.path.exists(os.path.join(current_dir, ".git")):
            break  # Stop if we've reached the root of the Git repository

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir or parent_dir == base_path:
            break  # Stop if we've reached the filesystem root or the base watched directory
        current_dir = parent_dir

    return pathspec.PathSpec.from_lines("gitwildmatch", patterns) if patterns else None

def should_ignore(gitignore, local_path):
    # Check file type
    mime_type, _ = mimetypes.guess_type(local_path)
    if mime_type and not mime_type.startswith("text/"):
        return True
    # Check if .git dir
    if ".git" in local_path.split(os.sep):
        return True
    # Check if temporary editor file
    if local_path.endswith("~"):
        return True
    # Check if too big
    max_file_size = config_manager.get("max_file_size", 32 * 1024)  # Default to 32 KB if not set
    if os.path.getsize(local_path) > max_file_size:
        return True
    # Check .gitignore
    return gitignore.match_file(local_path) if gitignore else False


def get_local_files(local_path):
    gitignore = load_gitignore(local_path)
    files = {}
    for root, _, filenames in os.walk(local_path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            if not should_ignore(gitignore, file_path):
                rel_path = os.path.relpath(file_path, local_path)
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                        files[rel_path] = calculate_checksum(content)
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
                    continue
    return files


def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ConfigurationError, ProviderError) as e:
            click.echo(f"Error: {str(e)}")

    return wrapper


def validate_and_get_provider(config, require_org=True):
    active_provider = config.get("active_provider")
    session_key = config.get("session_key")
    if not active_provider or not session_key:
        raise ConfigurationError(
            "No active provider or session key. Please login first."
        )
    if require_org and not config.get("active_organization_id"):
        raise ConfigurationError(
            "No active organization set. Please select an organization."
        )
    return get_provider(active_provider, session_key)


def validate_and_store_local_path(config):
    def get_default_path():
        return os.getcwd()

    while True:
        default_path = get_default_path()
        local_path = click.prompt(
            "Enter the absolute path to your local project directory",
            type=click.Path(
                exists=True, file_okay=False, dir_okay=True, resolve_path=True
            ),
            default=default_path,
            show_default=True,
        )

        if os.path.isabs(local_path):
            config.set("local_path", local_path)
            click.echo(f"Local path set to: {local_path}")
            break
        else:
            click.echo("Please enter an absolute path.")
