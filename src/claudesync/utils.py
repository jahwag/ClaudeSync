import hashlib
import logging
import mimetypes
import os
from functools import wraps

import click
import pathspec

from claudesync.exceptions import ConfigurationError, ProviderError
from claudesync.provider_factory import get_provider

logger = logging.getLogger(__name__)


def calculate_checksum(content):
    """
    Calculate the MD5 checksum of the given content after normalizing line endings.

    This function normalizes the line endings of the input content to Unix-style (\n),
    strips leading and trailing whitespace, and then calculates the MD5 checksum of the
    normalized content. This is useful for ensuring consistent checksums across different
    operating systems and environments.

    Args:
        content (str): The content for which to calculate the checksum.

    Returns:
        str: The hexadecimal MD5 checksum of the normalized content.
    """
    normalized_content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.md5(normalized_content.encode("utf-8")).hexdigest()


def load_gitignore(base_path):
    """
    Load and parse .gitignore patterns from a given base path.

    This function traverses up the directory tree starting from the given base path,
    looking for .gitignore files. It aggregates all patterns found in these files.
    The search stops when it reaches the root of the Git repository (identified by the
    presence of a .git directory) or the filesystem root.

    Args:
        base_path (str): The base path from which to start searching for .gitignore files.

    Returns:
        pathspec.PathSpec: A PathSpec object containing all aggregated .gitignore patterns.
                            Returns None if no patterns are found.
    """
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
    """
    Determine if a file should be ignored based on various criteria.

    This function checks if a file should be ignored based on its MIME type, presence in a .git directory,
    being a temporary editor file, its size, or if it matches patterns in a .gitignore file.

    Args:
        gitignore (pathspec.PathSpec): A PathSpec object containing .gitignore patterns.
        local_path (str): The path to the file being checked.

    Returns:
        bool: True if the file should be ignored, False otherwise.
    """
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
    if os.path.getsize(local_path) > 200 * 1024:
        return True
    # Check .gitignore
    return gitignore.match_file(local_path) if gitignore else False


def get_local_files(local_path):
    """
    Retrieve a dictionary of local files not ignored by .gitignore, mapped to their checksums.

    This function walks through the directory tree starting from `local_path`, checking each file
    against .gitignore rules to determine if it should be included. For each file not ignored,
    it calculates the file's checksum and stores it in a dictionary with the file's relative path as the key.

    Args:
        local_path (str): The root directory path to start searching for files.

    Returns:
        dict: A dictionary where keys are relative file paths from `local_path` and values are their MD5 checksums.
              Files ignored by .gitignore are not included.
    """
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
    """
    A decorator to handle exceptions raised by the decorated function.

    This decorator wraps a function and catches specific exceptions (ConfigurationError, ProviderError).
    If an exception is caught, it prints the error message to the console using click.echo.
    This is useful for CLI applications where a friendly error message is preferred over a full traceback.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapper function that includes exception handling.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ConfigurationError, ProviderError) as e:
            click.echo(f"Error: {str(e)}")

    return wrapper


def validate_and_get_provider(config, require_org=True):
    """
    Validate the configuration and retrieve the active provider based on the configuration.

    This function checks if the configuration contains an active provider and a session key.
    If either is missing, it raises a ConfigurationError indicating that the user needs to log in first.
    Additionally, if the `require_org` flag is set to True, it also checks for an active organization ID
    in the configuration. If no active organization is set, it raises a ConfigurationError asking the user
    to select an organization. If all validations pass, it retrieves and returns the active provider using
    the provider's name and session key.

    Args:
        config (dict): The configuration dictionary containing provider, session key, and optionally an organization ID.
        require_org (bool, optional): A flag indicating whether an active organization ID is required. Defaults to True.

    Returns:
        object: The active provider object retrieved based on the configuration.

    Raises:
        ConfigurationError: If no active provider or session key is found, or if `require_org` is True and no active
                             organization ID is set.
    """
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
    """
    Prompt the user for the absolute path to their local project directory and store it in the configuration.

    This function repeatedly prompts the user to enter the absolute path to their local project directory until
    a valid absolute path is provided. The path is then stored in the provided configuration object. It uses the
    current working directory as the default path.

    Args:
        config: The configuration object where the local path should be stored. This object must have a set method.

    """

    def get_default_path():
        """
        Retrieve the current working directory as the default local project path.

        Returns:
            str: The absolute path of the current working directory.
        """
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
