import json
import os
from datetime import datetime
from pathlib import Path
import logging

from claudesync.configmanager.base_config_manager import BaseConfigManager
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
        self.local_config = {}
        self.local_config_dir = None
        self._load_local_config()

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

    def _load_local_config(self):
        """
        Loads the local configuration from the nearest .claudesync/config.local.json file.
        Automatically normalizes any Windows-style paths.
        """
        self.local_config_dir = self._find_local_config_dir()
        if self.local_config_dir:
            local_config_file = (
                self.local_config_dir / ".claudesync" / "config.local.json"
            )
            if local_config_file.exists():
                with open(local_config_file, "r") as f:
                    self.local_config = json.load(f)

                # Check and fix Windows-style paths in submodules
                if "submodules" in self.local_config:
                    needs_save = False
                    for submodule in self.local_config["submodules"]:
                        if "\\" in submodule["relative_path"]:
                            submodule["relative_path"] = submodule[
                                "relative_path"
                            ].replace("\\", "/")
                            needs_save = True

                    if needs_save:
                        self._save_local_config()

    def get_local_path(self):
        """
        Retrieves the path of the directory containing the .claudesync folder.

        Returns:
            str: The path of the directory containing the .claudesync folder, or None if not found.
        """
        return str(self.local_config_dir) if self.local_config_dir else None

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

    def set_session_key(self, provider, session_key, expiry):
        """
        Sets the session key and its expiry for a specific provider.

        Args:
            provider (str): The name of the provider.
            session_key (str): The session key to set.
            expiry (datetime): The expiry datetime for the session key.
        """
        try:
            session_key_manager = SessionKeyManager()
            encrypted_session_key, encryption_method = (
                session_key_manager.encrypt_session_key(provider, session_key)
            )

            self.global_config_dir.mkdir(parents=True, exist_ok=True)
            provider_key_file = self.global_config_dir / f"{provider}.key"
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

    def get_session_key(self, provider):
        """
        Retrieves the session key for the specified provider if it's still valid.

        Args:
            provider (str): The name of the provider.

        Returns:
            tuple: A tuple containing the session key and expiry if valid, (None, None) otherwise.
        """
        provider_key_file = self.global_config_dir / f"{provider}.key"
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
                provider, encryption_method, encrypted_key
            )
            return session_key, expiry
        except RuntimeError as e:
            logging.error(f"Failed to decrypt session key: {str(e)}")
            return None, None

    def add_file_category(self, category_name, description, patterns):
        """
        Adds a new file category to the global configuration.

        Args:
            category_name (str): The name of the category to add.
            description (str): A description of the category.
            patterns (list): A list of file patterns for the category.
        """
        if "file_categories" not in self.global_config:
            self.global_config["file_categories"] = {}
        self.global_config["file_categories"][category_name] = {
            "description": description,
            "patterns": patterns,
        }
        self._save_global_config()

    def remove_file_category(self, category_name):
        """
        Removes a file category from the global configuration.

        Args:
            category_name (str): The name of the category to remove.
        """
        if (
            "file_categories" in self.global_config
            and category_name in self.global_config["file_categories"]
        ):
            del self.global_config["file_categories"][category_name]
            self._save_global_config()

    def update_file_category(self, category_name, description=None, patterns=None):
        """
        Updates an existing file category in the global configuration.

        Args:
            category_name (str): The name of the category to update.
            description (str, optional): The new description for the category. If None, the description is not updated.
            patterns (list, optional): The new list of file patterns for the category. If None, the patterns are not updated.
        """
        if (
            "file_categories" in self.global_config
            and category_name in self.global_config["file_categories"]
        ):
            if description is not None:
                self.global_config["file_categories"][category_name][
                    "description"
                ] = description
            if patterns is not None:
                self.global_config["file_categories"][category_name][
                    "patterns"
                ] = patterns
            self._save_global_config()

    def clear_all_session_keys(self):
        """
        Removes all stored session keys.
        """
        for file in self.global_config_dir.glob("*.key"):
            os.remove(file)

    def get_active_provider(self):
        """
        Retrieves the active provider from the local configuration.

        Returns:
            str: The name of the active provider, or None if not set.
        """
        return self.local_config.get("active_provider")

    def get_providers_with_session_keys(self):
        """
        Retrieves a list of providers that have valid session keys.

        Returns:
            list: A list of provider names with valid session keys.
        """
        providers = []
        for file in self.global_config_dir.glob("*.key"):
            provider = file.stem
            session_key, expiry = self.get_session_key(provider)
            if session_key and expiry > datetime.now():
                providers.append(provider)
        return providers
