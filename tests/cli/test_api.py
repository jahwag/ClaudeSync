import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from claudesync.cli.main import cli
from claudesync.exceptions import ProviderError


class TestAPICLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.mock_config = MagicMock()
        self.mock_provider = MagicMock()

    @patch("claudesync.cli.api.get_provider")
    @patch("claudesync.cli.main.ConfigManager")
    def test_login_success(self, mock_config_manager, mock_get_provider):
        mock_config_manager.return_value = self.mock_config
        mock_get_provider.return_value = self.mock_provider
        mock_get_provider.side_effect = lambda x=None: (
            ["claude.ai"] if x is None else self.mock_provider
        )
        self.mock_provider.login.return_value = "test_session_key"

        result = self.runner.invoke(cli, ["api", "login", "claude.ai"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Logged in successfully.", result.output)
        self.mock_config.set.assert_any_call("session_key", "test_session_key")
        self.mock_config.set.assert_any_call("active_provider", "claude.ai")

    @patch("claudesync.cli.api.get_provider")
    @patch("claudesync.cli.main.ConfigManager")
    def test_login_provider_error(self, mock_config_manager, mock_get_provider):
        mock_config_manager.return_value = self.mock_config
        mock_get_provider.return_value = self.mock_provider
        mock_get_provider.side_effect = lambda x=None: (
            ["claude.ai"] if x is None else self.mock_provider
        )
        self.mock_provider.login.side_effect = ProviderError("Login failed")

        result = self.runner.invoke(cli, ["api", "login", "claude.ai"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Error: Login failed", result.output)

    @patch("claudesync.cli.main.ConfigManager")
    def test_logout(self, mock_config_manager):
        mock_config_manager.return_value = self.mock_config

        result = self.runner.invoke(cli, ["api", "logout"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Logged out successfully.", result.output)
        self.mock_config.set.assert_any_call("session_key", None)
        self.mock_config.set.assert_any_call("active_provider", None)
        self.mock_config.set.assert_any_call("active_organization_id", None)

    @patch("claudesync.cli.main.ConfigManager")
    def test_ratelimit_set(self, mock_config_manager):
        mock_config_manager.return_value = self.mock_config

        result = self.runner.invoke(cli, ["api", "ratelimit", "--delay", "1.5"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Upload delay set to 1.5 seconds.", result.output)
        self.mock_config.set.assert_called_once_with("upload_delay", 1.5)

    @patch("claudesync.cli.main.ConfigManager")
    def test_ratelimit_negative_value(self, mock_config_manager):
        mock_config_manager.return_value = self.mock_config

        result = self.runner.invoke(cli, ["api", "ratelimit", "--delay", "-1"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn(
            "Error: Upload delay must be a non-negative number.", result.output
        )
        self.mock_config.set.assert_not_called()

    @patch("claudesync.cli.main.ConfigManager")
    def test_max_filesize_set(self, mock_config_manager):
        mock_config_manager.return_value = self.mock_config

        result = self.runner.invoke(cli, ["api", "max-filesize", "--size", "1048576"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Maximum file size set to 1048576 bytes.", result.output)
        self.mock_config.set.assert_called_once_with("max_file_size", 1048576)

    @patch("claudesync.cli.main.ConfigManager")
    def test_max_filesize_negative_value(self, mock_config_manager):
        mock_config_manager.return_value = self.mock_config

        result = self.runner.invoke(cli, ["api", "max-filesize", "--size", "-1"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn(
            "Error: Maximum file size must be a non-negative number.", result.output
        )
        self.mock_config.set.assert_not_called()


if __name__ == "__main__":
    unittest.main()
