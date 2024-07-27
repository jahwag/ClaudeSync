from unittest.mock import patch
import pytest
from claudesync.provider_factory import get_provider
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.providers.claude_ai_curl import ClaudeAICurlProvider


class TestProviderFactory:

    @pytest.mark.parametrize("provider_name", ["claude.ai", "claude.ai-curl"])
    def test_get_provider_list(self, provider_name):
        # Test that get_provider returns a list of available providers when called without arguments
        providers = get_provider()
        assert isinstance(providers, list)
        assert provider_name in providers

    @pytest.mark.parametrize(
        "provider_name, expected_class",
        [("claude.ai", ClaudeAIProvider), ("claude.ai-curl", ClaudeAICurlProvider)],
    )
    def test_get_provider_instance(self, provider_name, expected_class):
        # Test that get_provider returns the correct provider instance
        provider = get_provider(provider_name)
        assert isinstance(provider, expected_class)

    @pytest.mark.parametrize(
        "provider_name, expected_class",
        [("claude.ai", ClaudeAIProvider), ("claude.ai-curl", ClaudeAICurlProvider)],
    )
    def test_get_provider_with_session_key(self, provider_name, expected_class):
        # Test that get_provider returns a provider instance with a session key
        session_key = "test_session_key"
        provider = get_provider(provider_name, session_key)
        assert isinstance(provider, expected_class)
        assert provider.session_key == session_key

    def test_get_provider_unknown(self):
        # Test that get_provider raises a ValueError for an unknown provider
        with pytest.raises(ValueError):
            get_provider("unknown_provider")

    @pytest.mark.parametrize(
        "provider_name, expected_class",
        [("claude.ai", ClaudeAIProvider), ("claude.ai-curl", ClaudeAICurlProvider)],
    )
    @patch("claudesync.provider_factory.ClaudeAIProvider")
    @patch("claudesync.provider_factory.ClaudeAICurlProvider")
    def test_get_provider_calls_constructor(
        self,
        mock_claude_ai_curl_provider,
        mock_claude_ai_provider,
        provider_name,
        expected_class,
    ):
        # Test that get_provider calls the provider's constructor
        session_key = "test_session_key"
        get_provider(provider_name, session_key)

        if provider_name == "claude.ai":
            mock_claude_ai_provider.assert_called_once_with(session_key)
        else:
            mock_claude_ai_curl_provider.assert_called_once_with(session_key)


if __name__ == "__main__":
    pytest.main()
