from abc import ABC, abstractmethod
import copy


class BaseConfigManager(ABC):
    """
    Abstract base class for managing configuration settings.

    This class defines the interface for configuration management and includes
    common functionality that can be shared across different implementations,
    such as file-based and in-memory configurations.
    """

    def __init__(self):
        """
        Initializes the configuration manager with empty global and local configurations.

        - `global_config`: A dictionary to store global configuration settings that apply
          universally across all environments.
        - `local_config`: A dictionary to store local configuration settings specific to
          the current environment or project.
        """
        self.global_config = {}
        self.local_config = {}

    @abstractmethod
    def get_projects(self):
        """
        Get all configured projects.

        Returns:
            dict: A dictionary mapping project paths to their IDs.
                 Example: {
                    'datamodel/typeconstraints': 'project-uuid-1',
                    'myproject': 'project-uuid-2'
                 }

        Raises:
            ConfigurationError: If no project configuration is found
        """
        pass

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
            "prune_remote_files": True,
            "claude_api_url": "https://api.claude.ai/api",
            "compression_algorithm": "none"
        }

    @abstractmethod
    def get_active_project(self):
        """
        Get the currently active project.

        Returns:
            tuple: (project_path, project_id) if an active project exists, (None, None) otherwise
        """
        pass

    @abstractmethod
    def set_active_project(self, project_path, project_id):
        """
        Set the active project.

        Args:
            project_path (str): Path to the project like 'datamodel/typeconstraints'
            project_id (str): UUID of the project

        Raises:
            ConfigurationError: If the configuration directory is not found or there are
                              issues writing the active project configuration
        """
        pass

    @abstractmethod
    def get_project_id(self, project_path):
        """
        Get project id for the specified project path.

        Args:
            project_path (str): Project path like 'datamodel/typeconstraints'

        Returns:
            str: Project id
        """
        pass

    @abstractmethod
    def get_files_config(self, project_path):
        """
        Get files configuration for the specified project path.

        Args:
            project_path (str): Project path like 'datamodel/typeconstraints'

        Returns:
            dict: Files configuration with patterns and categories
        """
        pass

    @abstractmethod
    def _load_global_config(self):
        """
        Loads the global configuration settings.

        This method should be implemented by subclasses to load the global configuration
        from the appropriate source (e.g., a file or an in-memory structure).
        """
        pass

    @abstractmethod
    def _save_global_config(self):
        """
        Saves the global configuration settings.

        This method should be implemented by subclasses to save the global configuration
        to the appropriate destination (e.g., a file or an in-memory structure).
        """
        pass

    @abstractmethod
    def _save_local_config(self):
        """
        Saves the local configuration settings.

        This method should be implemented by subclasses to save the local configuration
        to the appropriate destination (e.g., a file or an in-memory structure).
        """
        pass

    @abstractmethod
    def set(self, key, value, local=False):
        """
        Sets a configuration value.

        Args:
            key (str): The key of the configuration setting to set.
            value: The value to associate with the given key.
            local (bool): Whether to set the configuration in the local context.
                          If False, the setting is stored in the global context.
                          Default is False.

        This method should be implemented by subclasses to handle the setting of
        configuration values, either globally or locally.
        """
        pass

    @abstractmethod
    def get(self, key, default=None):
        """
        Retrieves a configuration value.

        Args:
            key (str): The key of the configuration setting to retrieve.
            default: The default value to return if the key is not found.
                     Default is None.

        Returns:
            The value associated with the given key, or the default value if the key
            does not exist.

        This method should be implemented by subclasses to retrieve configuration
        values, checking the local context first, then the global context.
        """
        pass

    # Common methods that are shared between implementations
    def get_default_category(self):
        """
        Retrieves the default synchronization category.

        Returns:
            str: The default synchronization category, as specified in the configuration.
        """
        return self.get("default_sync_category")

    def set_default_category(self, category):
        """
        Sets the default synchronization category.

        Args:
            category (str): The category to set as the default for synchronization.
        """
        self.set("default_sync_category", category, local=True)

    def copy(self):
        """
        Creates a deep copy of the configuration manager.

        Returns:
            BaseConfigManager: A new instance of the configuration manager with
                               a deep copy of the global and local configurations.

        This method is useful when you need to duplicate the current state of the
        configuration manager, preserving the settings in a new instance.
        """
        new_instance = self.__class__()
        new_instance.global_config = copy.deepcopy(self.global_config)
        new_instance.local_config = copy.deepcopy(self.local_config)
        return new_instance
