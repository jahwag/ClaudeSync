import unittest
from unittest.mock import patch, MagicMock
import subprocess
from claudesync.providers.claude_ai_curl import ClaudeAICurlProvider
from claudesync.exceptions import ProviderError


class TestClaudeAICurlProvider(unittest.TestCase):

    def setUp(self):
        self.provider = ClaudeAICurlProvider("test_session_key")

    @patch("subprocess.run")
    def test_make_request_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = '{"key": "value"}'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.provider._make_request("GET", "/test")

        self.assertEqual(result, {"key": "value"})
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_make_request_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "curl", stderr="Test error"
        )

        with self.assertRaises(ProviderError):
            self.provider._make_request("GET", "/test")

    @patch("subprocess.run")
    def test_make_request_json_decode_error(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = "Invalid JSON"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with self.assertRaises(ProviderError):
            self.provider._make_request("GET", "/test")
