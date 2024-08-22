import datetime
import json
from pathlib import Path


class ConfigManager:
    """
    A class to manage configuration settings for the ClaudeSync application.

    This class handles loading, saving, and accessing configuration settings from a JSON file.
    It ensures that default values are set for certain keys if they are not present in the configuration file,
    and handles the expansion of user home directory paths.

    Attributes:
        config_dir (Path): The directory where the configuration file is stored.
        config_file (Path): The path to the configuration file.
        config (dict): The current configuration loaded into memory.
    """

    def __init__(self):
        """
        Initializes the ConfigManager instance.

        Sets up the configuration directory and file paths, and loads the current configuration from the file.
        """
        self.config_dir = Path.home() / ".claudesync"
        self.config_file = self.config_dir / "config.json"
        self.config = self._load_config()

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
            "submodule_detect_filenames": [
                "pom.xml",
                "build.gradle",
                "package.json",
                "setup.py",
                "Cargo.toml",
                "go.mod",
            ],
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

    def _load_config(self):
        """
        Loads the configuration from the JSON file, applying default values for missing keys.

        If the configuration file does not exist,
        it creates the directory (if necessary) and returns the default configuration.
        For existing configurations, it ensures all default values are present and expands user home directory paths.

        Returns:
            dict: The loaded configuration with default values for missing keys and expanded paths.
        """
        if not self.config_file.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            return self._get_default_config()

        with open(self.config_file, "r") as f:
            config = json.load(f)
            defaults = self._get_default_config()
            for key, value in defaults.items():
                if key not in config:
                    config[key] = value
                elif key == "file_categories":
                    # Merge default categories with user-defined categories
                    for category, category_data in value.items():
                        if category not in config[key]:
                            config[key][category] = category_data
            return config

    def _save_config(self):
        """
        Saves the current configuration to the JSON file.

        This method writes the current state of the `config` attribute to the configuration file,
        pretty-printing the JSON for readability.
        """
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)

    def get(self, key, default=None):
        """
        Retrieves a configuration value.

        Args:
            key (str): The key for the configuration setting to retrieve.
            default (any, optional): The default value to return if the key is not found. Defaults to None.

        Returns:
            The value of the configuration setting if found, otherwise the default value.
        """
        return self.config.get(key, default)

    def set(self, key, value):
        """
        Sets a configuration value and saves the configuration.

        Args:
            key (str): The key for the configuration setting to set.
            value (any): The value to set for the given key.

        This method updates the configuration with the provided key-value pair and then saves the configuration to the file.
        """
        self.config[key] = value
        self._save_config()

    def set_session_key(self, session_key, expiry: datetime):
        self.config["session_key"] = session_key
        self.config["session_key_expiry"] = expiry.isoformat()
        self._save_config()

    def get_session_key(self):
        session_key = self.config.get("session_key")
        expiry_str = self.config.get("session_key_expiry")

        if not session_key or not expiry_str:
            return None

        expiry = datetime.datetime.fromisoformat(expiry_str)
        if datetime.datetime.now() > expiry:
            return None

        return session_key

    def add_file_category(self, category_name, description, patterns):
        if "file_categories" not in self.config:
            self.config["file_categories"] = {}
        self.config["file_categories"][category_name] = {
            "description": description,
            "patterns": patterns,
        }
        self._save_config()

    def remove_file_category(self, category_name):
        if (
            "file_categories" in self.config
            and category_name in self.config["file_categories"]
        ):
            del self.config["file_categories"][category_name]
            self._save_config()

    def update_file_category(self, category_name, description=None, patterns=None):
        if (
            "file_categories" in self.config
            and category_name in self.config["file_categories"]
        ):
            if description is not None:
                self.config["file_categories"][category_name][
                    "description"
                ] = description
            if patterns is not None:
                self.config["file_categories"][category_name]["patterns"] = patterns
            self._save_config()
