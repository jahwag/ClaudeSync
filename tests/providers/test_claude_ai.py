import unittest
from unittest.mock import patch, MagicMock
import requests
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError


class TestClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = ClaudeAIProvider("test_session_key")

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_make_request_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response

        result = self.provider._make_request("GET", "/test")

        self.assertEqual(result, {"key": "value"})
        mock_request.assert_called_once()

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_make_request_failure(self, mock_request):
        mock_request.side_effect = requests.RequestException("Test error")

        with self.assertRaises(ProviderError):
            self.provider._make_request("GET", "/test")

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_make_request_403_error(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_request.return_value = mock_response

        with self.assertRaises(ProviderError) as context:
            self.provider._make_request("GET", "/test")

        self.assertIn("403 Forbidden error", str(context.exception))
