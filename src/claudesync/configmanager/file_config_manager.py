import json
import os
from datetime import datetime
from pathlib import Path
import logging

from claudesync.configmanager.base_config_manager import BaseConfigManager
from claudesync.exceptions import ConfigurationError
from claudesync.session_key_manager import SessionKeyManager


class FileConfigManager(BaseConfigManager):
    """
    Manages the configuration for ClaudeSync, handling both global and local (project-specific) settings.

    This class provides methods to load, save, and access configuration settings from both
    a global configuration file (~/.claudesync/config.json) and a local configuration file
    (.claudesync/config.local.json) in the project directory. Session keys are stored separately
    in provider-specific files.
    """

    def __init__(self):
        """
        Initialize the ConfigManager.

        Sets up paths for global and local configuration files and loads both configurations.
        """
        super().__init__()
        self.global_config_dir = Path.home() / ".claudesync"
        self.global_config_file = self.global_config_dir / "config.json"
        self.global_config = self._load_global_config()
        self.config_dir = self._find_config_dir()

    def get_projects(self):
        """
        Get all projects configured in the .claudesync directory.

        Returns:
            dict: A dictionary mapping project paths to their IDs
            Example: {
                'datamodel/typeconstraints': 'project-uuid-1',
                'myproject': 'project-uuid-2'
            }

        Raises:
            ConfigurationError: If no .claudesync directory is found
        """
        if not self.config_dir:
            raise ConfigurationError("No .claudesync directory found")

        projects = {}

        # Walk through the .claudesync directory
        for root, _, files in os.walk(self.config_dir):
            for file in files:
                if file.endswith('.project_id.json'):
                    # Extract project path from filename
                    project_path = file[:-len('.project_id.json')]

                    # Handle nested projects by getting relative path from .claudesync dir
                    rel_root = os.path.relpath(root, self.config_dir)
                    if rel_root != '.':
                        project_path = os.path.join(rel_root, project_path)

                    try:
                        # Load project ID from file
                        with open(os.path.join(root, file)) as f:
                            project_data = json.load(f)
                            project_id = project_data.get('project_id')
                            if project_id:
                                projects[project_path] = project_id
                    except (json.JSONDecodeError, IOError) as e:
                        logging.warning(f"Failed to load project file {file}: {str(e)}")
                        continue

        return projects

    def get_active_project(self):
        """
        Get the currently active project.

        Returns:
            tuple: (project_path, project_id) if an active project exists, (None, None) otherwise
        """
        if not self.config_dir:
            return None, None

        active_project_file = self.config_dir / "active_project.json"
        if not active_project_file.exists():
            return None, None

        try:
            with open(active_project_file) as f:
                data = json.load(f)
                return data.get("project_path"), data.get("project_id")
        except (json.JSONDecodeError, IOError):
            return None, None

    def set_active_project(self, project_path, project_id):
        """
        Set the active project.

        Args:
            project_path (str): Path to the project like 'datamodel/typeconstraints'
            project_id (str): UUID of the project
        """
        if not self.config_dir:
            raise ConfigurationError("No .claudesync directory found")

        active_project_file = self.config_dir / "active_project.json"

        data = {
            "project_path": project_path,
            "project_id": project_id
        }

        with open(active_project_file, "w") as f:
            json.dump(data, f, indent=2)

    def _find_config_dir(self):
        current_dir = Path.cwd()
        root_dir = Path(current_dir.root)

        if current_dir != root_dir:
            config_dir = current_dir / ".claudesync"

            # Create the directory if it doesn't exist
            config_dir.mkdir(exist_ok=True)

            if config_dir.is_dir():
                return config_dir


        return None

    def get_project_id(self, project_path):
        if not self.config_dir:
            raise ConfigurationError("No .claudesync directory found")

        project_file = self.config_dir / f"{project_path}.project_id.json"
        if not project_file.exists():
            # Try with subdirectories
            parts = project_path.split('/')
            project_file = self.config_dir / '/'.join(parts[:-1]) / f"{parts[-1]}.project_id.json"

        if not project_file.exists():
            raise ConfigurationError(f"Project configuration not found for {project_path}")

        with open(project_file) as f:
            return json.load(f)['project_id']

    def get_files_config(self, project_path):
        """Get files configuration from files-specific JSON file."""
        if not self.config_dir:
            raise ConfigurationError("No .claudesync directory found")

        files_file = self.config_dir / f"{project_path}.project.json"
        if not files_file.exists():
            # Try with subdirectories
            parts = project_path.split('/')
            files_file = self.config_dir / '/'.join(parts[:-1]) / f"{parts[-1]}.project.json"

        if not files_file.exists():
            raise ConfigurationError(f"Files configuration not found for {project_path}")

        with open(files_file) as f:
            return json.load(f)

    def get_project_root(self):
        """Get the root directory containing .claudesync."""
        return self.config_dir.parent if self.config_dir else None


    def _load_global_config(self):
        """
        Loads the global configuration from the JSON file.

        If the configuration file doesn't exist, it creates the directory (if necessary)
        and returns the default configuration.

        Returns:
            dict: The loaded global configuration with default values for missing keys.
        """
        if not self.global_config_file.exists():
            self.global_config_dir.mkdir(parents=True, exist_ok=True)
            return self._get_default_config()

        with open(self.global_config_file, "r") as f:
            config = json.load(f)
            defaults = self._get_default_config()
            for key, value in defaults.items():
                if key not in config:
                    config[key] = value
            return config

    def _find_local_config_dir(self, max_depth=100):
        """
        Finds the nearest directory containing a .claudesync folder.

        Searches from the current working directory upwards until it finds a .claudesync folder
        or reaches the root directory. Excludes the ~/.claudesync directory.

        Returns:
            Path: The path containing the .claudesync folder, or None if not found.
        """
        current_dir = Path.cwd()
        root_dir = Path(current_dir.root)
        home_dir = Path.home()
        depth = 0

        while current_dir != root_dir:
            claudesync_dir = current_dir / ".claudesync"
            if claudesync_dir.is_dir() and claudesync_dir != home_dir / ".claudesync":
                return current_dir

            current_dir = current_dir.parent
            depth += 1

            if depth > max_depth:
                return None

        return None

    def get_local_path(self):
        """
        Retrieves the path of the directory containing the .claudesync folder.

        Returns:
            str: The path of the directory containing the .claudesync folder, or None if not found.
        """
        if not self.config_dir:
            return None
        # Return the parent directory of .claudesync folder which is the project root
        return str(self.config_dir.parent)

    def get(self, key, default=None):
        """
        Retrieves a configuration value.

        Checks the local configuration first, then falls back to the global configuration.

        Args:
            key (str): The key for the configuration setting to retrieve.
            default (any, optional): The default value to return if the key is not found. Defaults to None.

        Returns:
            The value of the configuration setting if found, otherwise the default value.
        """
        return self.local_config.get(key) or self.global_config.get(key, default)

    def set(self, key, value, local=False):
        """
        Sets a configuration value and saves the configuration.

        Args:
            key (str): The key for the configuration setting to set.
            value (any): The value to set for the given key.
            local (bool): If True, sets the value in the local configuration. Otherwise, sets it in the global configuration.
        """
        if local:
            # Update local_config_dir when setting local_path
            if key == "local_path":
                self.local_config_dir = Path(value)
                # Create .claudesync directory in the specified path
                (self.local_config_dir / ".claudesync").mkdir(exist_ok=True)

            self.local_config[key] = value
            self._save_local_config()
        else:
            self.global_config[key] = value
            self._save_global_config()

    def _save_global_config(self):
        """
        Saves the current global configuration to the JSON file.

        This method writes the current state of the `global_config` attribute to the configuration file,
        pretty-printing the JSON for readability.
        """
        with open(self.global_config_file, "w") as f:
            json.dump(self.global_config, f, indent=2)

    def _save_local_config(self):
        """
        Saves the current local configuration to the .claudesync/config.local.json file.
        """
        if self.local_config_dir:
            local_config_file = (
                self.local_config_dir / ".claudesync" / "config.local.json"
            )
            local_config_file.parent.mkdir(exist_ok=True)
            with open(local_config_file, "w") as f:
                json.dump(self.local_config, f, indent=2)

    def set_session_key(self, session_key, expiry):
        """
        Sets the session key and its expiry for a specific provider.

        Args:
            session_key (str): The session key to set.
            expiry (datetime): The expiry datetime for the session key.
        """
        try:
            session_key_manager = SessionKeyManager()
            encrypted_session_key, encryption_method = (
                session_key_manager.encrypt_session_key(session_key)
            )

            self.global_config_dir.mkdir(parents=True, exist_ok=True)
            provider_key_file = self.global_config_dir / f"claude.ai.key"
            with open(provider_key_file, "w") as f:
                json.dump(
                    {
                        "session_key": encrypted_session_key,
                        "session_key_encryption_method": encryption_method,
                        "session_key_expiry": expiry.isoformat(),
                    },
                    f,
                )
        except RuntimeError as e:
            logging.error(f"Failed to encrypt session key: {str(e)}")
            raise

    def get_session_key(self):
        """
        Retrieves the session key if it's still valid.

        Returns:
            tuple: A tuple containing the session key and expiry if valid, (None, None) otherwise.
        """
        provider_key_file = self.global_config_dir / f"claude.ai.key"
        if not provider_key_file.exists():
            return None, None

        with open(provider_key_file, "r") as f:
            data = json.load(f)

        encrypted_key = data.get("session_key")
        encryption_method = data.get("session_key_encryption_method")
        expiry_str = data.get("session_key_expiry")

        if not encrypted_key or not expiry_str:
            return None, None

        expiry = datetime.fromisoformat(expiry_str)
        if datetime.now() > expiry:
            return None, None

        try:
            session_key_manager = SessionKeyManager()
            session_key = session_key_manager.decrypt_session_key(
                encryption_method, encrypted_key
            )
            return session_key, expiry
        except RuntimeError as e:
            logging.error(f"Failed to decrypt session key: {str(e)}")
            return None, None

    def clear_all_session_keys(self):
        """
        Removes all stored session keys.
        """
        for file in self.global_config_dir.glob("*.key"):
            os.remove(file)

    def get_providers_with_session_keys(self):
        """
        Retrieves a list of providers that have valid session keys.

        Returns:
            list: A list of provider names with valid session keys.
        """
        providers = []
        for file in self.global_config_dir.glob("claude.ai.key"):
            provider = file.stem
            session_key, expiry = self.get_session_key()
            if session_key and expiry > datetime.now():
                providers.append(provider)
        return providers
