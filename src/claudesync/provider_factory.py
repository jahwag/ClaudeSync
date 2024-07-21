from .providers.claude_ai import ClaudeAIProvider


# Import other providers here as they are added


def get_provider(provider_name=None, session_key=None):
    """
    Retrieve an instance of a provider class based on the provider name and session key.

    This function serves as a factory to instantiate provider classes. It maintains a registry of available
    providers. If a provider name is not specified, it returns a list of available provider names. If a provider
    name is specified but not found in the registry, it raises a ValueError. If a session key is provided, it
    is passed to the provider class constructor.

    Args: provider_name (str, optional): The name of the provider to retrieve. If None, returns a list of available
    provider names. session_key (str, optional): The session key to be used by the provider for authentication.
    Defaults to None.

    Returns:
        object: An instance of the requested provider class if both provider_name and session_key are provided.
        list: A list of available provider names if provider_name is None.

    Raises:
        ValueError: If the specified provider_name is not found in the registry of providers.
    """
    providers = {
        "claude.ai": ClaudeAIProvider,
        # Add other providers here as they are implemented
    }

    if provider_name is None:
        return list(providers.keys())

    provider_class = providers.get(provider_name)
    if provider_class is None:
        raise ValueError(f"Unsupported provider: {provider_name}")

    return provider_class(session_key) if session_key else provider_class()
