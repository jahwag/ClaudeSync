import unittest
from unittest.mock import patch
from claudesync.provider_factory import get_provider
from claudesync.providers.claude_ai import ClaudeAIProvider


class TestProviderFactory(unittest.TestCase):

    def test_get_provider_list(self):
        # Test that get_provider returns a list of available providers when called without arguments
        providers = get_provider()
        self.assertIsInstance(providers, list)
        self.assertIn("claude.ai", providers)

    def test_get_provider_claude_ai(self):
        # Test that get_provider returns a ClaudeAIProvider instance for "claude.ai"
        provider = get_provider("claude.ai")
        self.assertIsInstance(provider, ClaudeAIProvider)

    def test_get_provider_with_session_key(self):
        # Test that get_provider returns a provider instance with a session key
        session_key = "test_session_key"
        provider = get_provider("claude.ai", session_key)
        self.assertIsInstance(provider, ClaudeAIProvider)
        self.assertEqual(provider.session_key, session_key)

    def test_get_provider_unknown(self):
        # Test that get_provider raises a ValueError for an unknown provider
        with self.assertRaises(ValueError):
            get_provider("unknown_provider")

    @patch("claudesync.provider_factory.ClaudeAIProvider")
    def test_get_provider_calls_constructor(self, mock_claude_ai_provider):
        # Test that get_provider calls the provider's constructor
        session_key = "test_session_key"
        get_provider("claude.ai", session_key)
        mock_claude_ai_provider.assert_called_once_with(session_key)


if __name__ == "__main__":
    unittest.main()
