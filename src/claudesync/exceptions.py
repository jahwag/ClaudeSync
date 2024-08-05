class ConfigurationError(Exception):
    """
    Exception raised when there's an issue with the application's configuration.

    This exception should be raised to indicate problems such as missing required configuration options,
    invalid values, or issues loading configuration files. It helps in distinguishing configuration-related
    errors from other types of exceptions.
    """

    pass


class ProviderError(Exception):
    """
    Exception raised when there's an issue with a provider operation.

    This exception is used to signal failures in operations related to external service providers,
    such as authentication failures, data retrieval errors, or actions that cannot be completed as requested.
    It allows for more granular error handling that is specific to provider interactions.
    """

    pass
