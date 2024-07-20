import os
import hashlib
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
    gitignore_path = os.path.join(base_path, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return None


def is_text_file(file_path, sample_size=8192):
    try:
        with open(file_path, "rb") as file:
            return b"\x00" not in file.read(sample_size)
    except IOError:
        return False


def calculate_checksum(content):
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def get_local_files(local_path):
    gitignore = load_gitignore(local_path)
    files = {}

    # List of directories to exclude
    exclude_dirs = {".git", ".svn", ".hg", ".bzr", "_darcs", "CVS"}

    for root, dirs, filenames in os.walk(local_path):
        # Remove excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        rel_root = os.path.relpath(root, local_path)
        if rel_root == ".":
            rel_root = ""

        for filename in filenames:
            rel_path = os.path.join(rel_root, filename)
            full_path = os.path.join(root, filename)

            # Skip files larger than 200KB
            max_file_size = config_manager.get("max_file_size", 32 * 1024)
            if os.path.getsize(full_path) > max_file_size:
                continue

            # Skip temporary editor files
            if filename.endswith("~"):
                continue

            # Use gitignore rules if available
            if gitignore and gitignore.match_file(rel_path):
                continue

            # Check if it's a text file
            if not is_text_file(full_path):
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as file:
                    content = file.read()
                    files[rel_path] = calculate_checksum(content)
            except UnicodeDecodeError:
                # If UTF-8 decoding fails, it's likely not a text file we can handle
                logger.debug(f"Unable to read {full_path} as UTF-8 text. Skipping.")
                continue
            except Exception as e:
                logger.error(f"Error reading file {full_path}: {str(e)}")

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
