# src/claudesync/provider_factory.py

from .providers.base_provider import BaseProvider
from .providers.claude_ai import ClaudeAIProvider


def get_provider(config=None):
    """
    Get an instance of the Claude AI provider.

    Args:
        config: Configuration manager instance

    Returns:
        ClaudeAIProvider: An instance of the Claude AI provider
    """
    return ClaudeAIProvider(config)
