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
            return {"log_level": "INFO", "upload_delay": 0.5}  # Default values
        with open(self.config_file, "r") as f:
            config = json.load(f)
            if "log_level" not in config:
                config["log_level"] = "INFO"
            if "upload_delay" not in config:
                config["upload_delay"] = 0.5
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
