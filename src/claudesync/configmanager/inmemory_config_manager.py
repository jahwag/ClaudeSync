import copy

from claudesync.configmanager import BaseConfigManager


class InMemoryConfigManager(BaseConfigManager):
    """
    A configuration manager that stores configuration settings entirely in memory.

    This class provides an in-memory implementation of the BaseConfigManager, meaning that
    all configuration data is stored in Python dictionaries and does not persist between
    program runs.
    """

    def __init__(self):
        """
        Initializes the in-memory configuration manager with default settings.
        """
        super().__init__()
        self.global_config = self._get_default_config()
        self.local_config = {}

    def _load_global_config(self):
        """
        Loads the global configuration settings.

        Since this is an in-memory implementation, this method doesn't load from any external source.
        Instead, it relies on the initial in-memory defaults or previous modifications made during runtime.
        """
        # No action needed for in-memory implementation
        pass

    def _load_local_config(self):
        """
        Loads the local configuration settings.

        Since this is an in-memory implementation, this method doesn't load from any external source.
        """
        # No action needed for in-memory implementation
        pass

    def _save_global_config(self):
        """
        Saves the global configuration settings.

        Since this is an in-memory implementation, this method doesn't save to any external destination.
        """
        # No action needed for in-memory implementation
        pass

    def _save_local_config(self):
        """
        Saves the local configuration settings.

        Since this is an in-memory implementation, this method doesn't save to any external destination.
        """
        # No action needed for in-memory implementation
        pass

    def set(self, key, value, local=False):
        """
        Sets a configuration value in the in-memory store.

        Args:
            key (str): The key of the configuration setting to set.
            value: The value to associate with the given key.
            local (bool): Whether to set the configuration in the local context.
                          If False, the setting is stored in the global context.
                          Default is False.
        """
        if local:
            self.local_config[key] = value
        else:
            self.global_config[key] = value

    def get(self, key, default=None):
        """
        Retrieves a configuration value from the in-memory store.

        Args:
            key (str): The key of the configuration setting to retrieve.
            default: The default value to return if the key is not found.
                     Default is None.

        Returns:
            The value associated with the given key, or the default value if the key
            does not exist.
        """
        return self.local_config.get(key, self.global_config.get(key, default))

    def _find_local_config_dir(self):
        """
        Finds the local configuration directory.

        Returns:
            None: Since this is an in-memory implementation, there is no local configuration directory.
        """
        return None

    def load_from_file_config(self, file_config_manager):
        """
        Loads configuration settings from a FileConfigManager instance into the in-memory store.

        Args:
            file_config_manager (FileConfigManager): An instance of FileConfigManager
                                                     from which to load settings.
        """
        # Load the global and local configurations from the file-based manager
        self.global_config = copy.deepcopy(file_config_manager.global_config)
        self.local_config = copy.deepcopy(file_config_manager.local_config)
