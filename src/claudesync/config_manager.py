import json
from pathlib import Path
from datetime import datetime


class ConfigManager:
    """
    Manages the configuration for ClaudeSync, handling both global and local (project-specific) settings.

    This class provides methods to load, save, and access configuration settings from both
    a global configuration file (~/.claudesync/config.json) and a local configuration file
    (.claudesync/config.local.json) in the project directory.
    """

    def __init__(self):
        """
        Initialize the ConfigManager.

        Sets up paths for global and local configuration files and loads both configurations.
        """
        self.global_config_dir = Path.home() / ".claudesync"
        self.global_config_file = self.global_config_dir / "config.json"
        self.global_config = self._load_global_config()
        self.local_config = {}
        self.local_config_dir = None
        self._load_local_config()

    def _get_default_config(self):
        """
        Returns the default configuration dictionary.

        This method centralizes the default configuration settings, making it easier to manage and update defaults.

        Returns:
            dict: The default configuration settings.
        """
        return {
            "log_level": "INFO",
            "upload_delay": 0.5,
            "max_file_size": 32 * 1024,
            "two_way_sync": False,
            "curl_use_file_input": False,
            "prune_remote_files": False,
            "file_categories": {
                "all_files": {
                    "description": "All files not ignored",
                    "patterns": ["*"],
                },
                "all_source_code": {
                    "description": "All source code files",
                    "patterns": [
                        "*.java",
                        "*.py",
                        "*.js",
                        "*.ts",
                        "*.c",
                        "*.cpp",
                        "*.h",
                        "*.hpp",
                        "*.go",
                        "*.rs",
                    ],
                },
                "production_code": {
                    "description": "Production source code",
                    "patterns": [
                        "src/**/*.java",
                        "src/**/*.py",
                        "src/**/*.js",
                        "src/**/*.ts",
                    ],
                },
                "test_code": {
                    "description": "Test source code",
                    "patterns": [
                        "test/**/*.java",
                        "tests/**/*.py",
                        "**/test_*.py",
                        "**/*Test.java",
                    ],
                },
                "build_config": {
                    "description": "Build configuration files",
                    "patterns": [
                        "pom.xml",
                        "build.gradle",
                        "package.json",
                        "setup.py",
                        "Cargo.toml",
                        "go.mod",
                    ],
                },
            },
        }

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
        or reaches the root directory.

        Returns:
            Path: The path containing the .claudesync folder, or None if not found.
        """
        current_dir = Path.cwd()
        root_dir = Path(current_dir.root)
        depth = 0  # Initialize depth counter

        while current_dir != root_dir:
            if (current_dir / ".claudesync").is_dir():
                return current_dir

            current_dir = current_dir.parent
            depth += 1  # Increment depth counter

            # Sanity check: stop if max_depth is reached
            if depth > max_depth:
                return None

        return None

    def _load_local_config(self):
        """
        Loads the local configuration from the nearest .claudesync/config.local.json file.

        Sets the local_config_dir and populates the local_config dictionary.
        """
        self.local_config_dir = self._find_local_config_dir()
        if self.local_config_dir:
            local_config_file = (
                self.local_config_dir / ".claudesync" / "config.local.json"
            )
            if local_config_file.exists():
                with open(local_config_file, "r") as f:
                    self.local_config = json.load(f)

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
            if not self.local_config_dir:
                self.local_config_dir = Path.cwd()
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

        Creates the .claudesync directory if it doesn't exist.
        """
        if self.local_config_dir:
            local_config_file = (
                self.local_config_dir / ".claudesync" / "config.local.json"
            )
            with open(local_config_file, "w") as f:
                json.dump(self.local_config, f, indent=2)

    def set_session_key(self, session_key, expiry):
        """
        Sets the session key and its expiry in the global configuration.

        Args:
            session_key (str): The session key to set.
            expiry (datetime): The expiry datetime for the session key.
        """
        self.global_config["session_key"] = session_key
        self.global_config["session_key_expiry"] = expiry.isoformat()
        self._save_global_config()

    def get_session_key(self):
        """
        Retrieves the session key if it's still valid.

        Returns:
            str: The session key if it's valid, None otherwise.
        """
        session_key = self.global_config.get("session_key")
        expiry_str = self.global_config.get("session_key_expiry")

        if not session_key or not expiry_str:
            return None

        expiry = datetime.fromisoformat(expiry_str)
        if datetime.now() > expiry:
            return None

        return session_key

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

    def set_default_category(self, category):
        """
        Sets the default category for synchronization in the local configuration.

        Args:
            category (str): The name of the category to set as default.
        """
        self.set("default_sync_category", category, local=True)

    def get_default_category(self):
        """
        Retrieves the default category for synchronization from the local configuration.

        Returns:
            str or None: The default category if set, otherwise None.
        """
        return self.get("default_sync_category")
