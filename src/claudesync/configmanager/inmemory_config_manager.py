from datetime import datetime

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
        self.session_keys = {}

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

    def set_session_key(self, provider, session_key, expiry):
        self.session_keys[provider] = {"session_key": session_key, "expiry": expiry}

    def get_session_key(self, provider):
        if provider in self.session_keys:
            data = self.session_keys[provider]
            if datetime.now() < data["expiry"]:
                return data["session_key"], data["expiry"]
        return None, None

    def load_from_file_config(self, file_config_manager):
        self.global_config = file_config_manager.global_config.copy()
        self.local_config = file_config_manager.local_config.copy()

        # Copy session keys
        if hasattr(file_config_manager, "session_keys"):
            self.session_keys = file_config_manager.session_keys.copy()
        else:
            # If FileConfigManager doesn't have session_keys attribute,
            # we need to manually copy the session keys
            for provider in file_config_manager.get_providers_with_session_keys():
                session_key, expiry = file_config_manager.get_session_key(provider)
                if session_key and expiry:
                    self.set_session_key(provider, session_key, expiry)

    def get_active_provider(self):
        """
        Retrieves the active provider from the local configuration.

        Returns:
            str: The name of the active provider, or None if not set.
        """
        return self.local_config.get("active_provider")

    def get_local_path(self):
        return "."
