from .providers.claude_ai import ClaudeAIProvider

# Import other providers here as they are added


def get_provider(provider_name=None, session_key=None):
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
