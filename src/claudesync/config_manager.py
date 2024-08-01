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
            "max_file_size": 32 * 1024,  # Default 32 KB
            "two_way_sync": False,  # Default to False
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
                elif key == "chat_destination":
                    # Expand user home directory for path-based settings
                    config[key] = str(Path(config[key]).expanduser())
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

        For path-based settings (chat_destination), this method expands the user's home directory.

        Args:
            key (str): The key for the configuration setting to set.
            value (any): The value to set for the given key.

        This method updates the configuration with the provided key-value pair and then saves the configuration to the file.
        """
        if key == "chat_destination":
            # Expand user home directory for path-based settings
            value = str(Path(value).expanduser())
        self.config[key] = value
        self._save_config()
