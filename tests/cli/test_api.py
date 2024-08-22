import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from click.testing import CliRunner
from claudesync.cli.main import cli
from claudesync.config_manager import ConfigManager


class TestAPICLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.config_mock = MagicMock(spec=ConfigManager)

    @patch("claudesync.cli.api.get_provider")
    def test_login_provider_error(self, mock_get_provider):
        mock_get_provider.return_value = ["claude.ai", "claude.ai-curl"]
        result = self.runner.invoke(
            cli, ["api", "login", "invalid_provider"], obj=self.config_mock
        )
        self.assertIn("Error: Unknown provider 'invalid_provider'", result.output)
        self.assertEqual(result.exit_code, 0)

    @patch("claudesync.cli.api.get_provider")
    @patch("claudesync.cli.api.click.confirm")
    @patch("claudesync.cli.api.org_select")
    @patch("claudesync.cli.api.proj_select")
    @patch("claudesync.cli.api.project_create")
    @patch("claudesync.cli.api.submodule_create")
    def test_login_success(
        self,
        mock_submodule_create,
        mock_project_create,
        mock_proj_select,
        mock_org_select,
        mock_confirm,
        mock_get_provider,
    ):
        # Mock provider instance
        mock_provider = MagicMock()
        mock_provider.login.return_value = (
            "mock_session_key",
            datetime.now() + timedelta(days=30),
        )
        mock_provider.get_organizations.return_value = [
            {"id": "org1", "name": "Test Org"}
        ]
        mock_provider.get_projects.return_value = [
            {"id": "proj1", "name": "Test Project"}
        ]

        # Mock get_provider to return the list of providers and then the mock provider instance
        mock_get_provider.side_effect = [["claude.ai", "claude.ai-curl"], mock_provider]

        # Mock user confirmations
        mock_confirm.side_effect = [
            False,  # Don't use existing session
            True,  # Select existing project
            True,  # Delete remote files
        ]

        # Mock config operations
        self.config_mock.get_session_key.return_value = None
        self.config_mock.get.return_value = None

        # Mock organization and project selection
        mock_org_select.return_value = None
        mock_proj_select.return_value = None

        runner = CliRunner()
        result = runner.invoke(cli, ["api", "login", "claude.ai"], obj=self.config_mock)

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Logged in successfully", result.output)

        # Verify that organization select was invoked
        mock_org_select.assert_called_once()


if __name__ == "__main__":
    unittest.main()
