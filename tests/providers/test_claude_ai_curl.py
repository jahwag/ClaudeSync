import unittest
from unittest.mock import patch, MagicMock
import subprocess
from claudesync.providers.claude_ai_curl import ClaudeAICurlProvider
from claudesync.exceptions import ProviderError
import json


class TestClaudeAICurlProvider(unittest.TestCase):
    def setUp(self):
        self.provider = ClaudeAICurlProvider("test_session_key")

    @patch("subprocess.run")
    def test_make_request_success(self, mock_run):
        # Prepare mock response
        mock_response = MagicMock()
        mock_response.stdout = json.dumps({"key": "value"}) + "200"
        mock_response.returncode = 0
        mock_run.return_value = mock_response

        # Make the request
        result = self.provider._make_request("GET", "/test")

        # Assert the result
        self.assertEqual(result, {"key": "value"})

        # Assert that subprocess.run was called with the correct arguments
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertIn("curl", args[0])
        self.assertIn("https://claude.ai/api/test", args[0])
        self.assertIn("--compressed", args[0])
        self.assertIn("-s", args[0])
        self.assertIn("-S", args[0])
        self.assertIn("-w", args[0])
        self.assertIn("%{http_code}", args[0])
        self.assertIn("-H", args[0])
        self.assertIn(
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            args[0],
        )
        self.assertIn("Cookie: sessionKey=test_session_key", args[0])
        self.assertIn("Content-Type: application/json", args[0])

        # Assert that the correct kwargs were passed to subprocess.run
        self.assertTrue(kwargs.get("capture_output"))
        self.assertTrue(kwargs.get("text"))
        self.assertTrue(kwargs.get("check"))
        self.assertEqual(kwargs.get("encoding"), "utf-8")

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
