import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from datetime import datetime, timedelta

from claudesync.cli.main import cli
from claudesync.configmanager import InMemoryConfigManager
from claudesync.providers.claude_ai import ClaudeAIProvider


class TestClaudeSyncHappyPath(unittest.TestCase):
    def setUp(self):
        self.config = InMemoryConfigManager()
        self.file_config_patcher = patch("claudesync.cli.main.FileConfigManager")
        self.mock_file_config = self.file_config_patcher.start()
        self.mock_file_config.return_value = self.config

        self.provider_patcher = patch("claudesync.providers.claude_ai.ClaudeAIProvider")
        self.mock_provider_class = self.provider_patcher.start()
        self.mock_provider = self.mock_provider_class.return_value

        self.runner = CliRunner()

    def tearDown(self):
        self.file_config_patcher.stop()
        self.provider_patcher.stop()

    @patch("click.prompt")
    @patch("claudesync.providers.base_claude_ai._get_session_key_expiry")
    def test_happy_path(self, mock_get_expiry, mock_prompt):
        # Mock session key expiry
        expiry_date = datetime.now() + timedelta(days=30)
        mock_get_expiry.return_value = expiry_date

        mock_prompt.side_effect = [
            "sk-ant-test123",  # Session key
            "1",  # Select organization
            "Test Project",  # Project name
            "Test description",  # Project description
            "/path/to/project",  # Local path
        ]

        # Mock the login method
        self.mock_provider.login.return_value = ("sk-ant-test123", expiry_date)
        self.mock_provider.get_organizations.return_value = [
            {"id": "org1", "name": "Test Org 1"}
        ]

        # Login
        result = self.runner.invoke(
            cli, ["auth", "login", "claude.ai"], obj=self.config
        )
        self.assertIn("Successfully authenticated with claude.ai", result.output)
        self.assertEqual(result.exit_code, 0)

        # Set organization
        result = self.runner.invoke(cli, ["organization", "set"], obj=self.config)
        self.assertIn("Selected organization: Test Org 1", result.output)
        self.assertEqual(result.exit_code, 0)

        # Create project
        self.mock_provider.create_project.return_value = {
            "uuid": "new_proj",
            "name": "New Project",
        }
        result = self.runner.invoke(cli, ["project", "create"], obj=self.config)
        self.assertIn(
            "Project 'New Project' (uuid: new_proj) has been created successfully",
            result.output,
        )
        self.assertEqual(result.exit_code, 0)

        # Push project
        with patch(
            "claudesync.utils.get_local_files",
            return_value={"test.txt": "content_hash"},
        ):
            result = self.runner.invoke(cli, ["push"], obj=self.config)
        self.assertIn("Main project 'New Project' synced successfully", result.output)
        self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
