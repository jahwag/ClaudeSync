import json
from pathlib import Path


class ConfigManager:
    """
    A class to manage configuration settings for the application.

    This class handles loading, saving, and accessing configuration settings from a JSON file.
    It ensures that default values are set for certain keys if they are not present in the configuration file.

    Attributes:
        config_dir (Path): The directory where the configuration file is stored.
        config_file (Path): The path to the configuration file.
        config (dict): The current configuration loaded into memory.
    """

    def __init__(self):
        """
        Initializes the ConfigManager instance by setting up the configuration directory and file paths,
        and loading the current configuration from the file, applying default values as necessary.
        """
        self.config_dir = Path.home() / ".claudesync"
        self.config_file = self.config_dir / "config.json"
        self.config = self._load_config()

    def _load_config(self):
        """
        Loads the configuration from the JSON file, applying default values for missing keys.

        If the configuration file does not exist, it creates the directory (if necessary) and returns a dictionary
        with default values.

        Returns:
            dict: The loaded configuration with default values for missing keys.
        """
        if not self.config_file.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            return {
                "log_level": "INFO",
                "upload_delay": 0.5,
                "max_file_size": 32 * 1024,  # Default 32 KB
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
                    "Origin": "https://claude.ai",
                },
                "two_way_sync": False,  # Default to False
            }
        with open(self.config_file, "r") as f:
            config = json.load(f)
            # Ensure all default values are present
            defaults = {
                "log_level": "INFO",
                "upload_delay": 0.5,
                "max_file_size": 32 * 1024,
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
                    "Origin": "https://claude.ai",
                },
                "two_way_sync": False,
            }
            for key, value in defaults.items():
                if key not in config:
                    config[key] = value
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

        This method updates the configuration with the provided key-value pair and then saves the configuration
        to the file.
        """
        self.config[key] = value
        self._save_config()

    def update_headers(self, new_headers):
        """
        Updates the headers configuration with new values.

        Args:
            new_headers (dict): A dictionary containing the new header key-value pairs to update or add.

        This method updates the existing headers with the new values provided, adds any new headers,
        and then saves the updated configuration to the file.
        """
        self.config.setdefault("headers", {}).update(new_headers)
        self._save_config()

    def get_headers(self):
        """
        Retrieves the current headers configuration.

        Returns:
            dict: The current headers configuration.
        """
        return self.config.get("headers", {})

    def update_cookies(self, new_cookies):
        """
        Updates the cookies configuration with new values.

        Args:
            new_cookies (dict): A dictionary containing the new cookie key-value pairs to update or add.

        This method updates the existing cookies with the new values provided, adds any new cookies,
        and then saves the updated configuration to the file.
        """
        self.config.setdefault("cookies", {}).update(new_cookies)
        self._save_config()
