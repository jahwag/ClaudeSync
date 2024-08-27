# src/claudesync/provider_factory.py

from .providers.base_provider import BaseProvider
from .providers.claude_ai import ClaudeAIProvider


def get_provider(config=None, provider_name=None) -> BaseProvider:
    """
    Retrieve an instance of a provider class based on the provider name.

    This function serves as a factory to instantiate provider classes. It maintains a registry of available
    providers. If a provider name is not specified, it returns a list of available provider names. If a provider
    name is specified but not found in the registry, it raises a ValueError.

    Args:
        config: for testing
        provider_name (str, optional): The name of the provider to retrieve. If None, returns a list of available
                                       provider names.

    Returns:
        BaseProvider: An instance of the requested provider class.

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

    return provider_class(config)
