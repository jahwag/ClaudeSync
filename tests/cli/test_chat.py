import unittest
from unittest.mock import patch, MagicMock, ANY
from click.testing import CliRunner
from claudesync.cli.main import cli


class TestChatCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    @patch("claudesync.cli.chat.validate_and_get_provider")
    @patch("claudesync.cli.chat.sync_chats")
    def test_sync_command(self, mock_sync_chats, mock_validate_and_get_provider):
        mock_provider = MagicMock()
        mock_validate_and_get_provider.return_value = mock_provider

        result = self.runner.invoke(cli, ["chat", "sync"])

        self.assertEqual(result.exit_code, 0)
        mock_validate_and_get_provider.assert_called_once_with(
            ANY, require_project=True
        )
        mock_sync_chats.assert_called_once_with(mock_provider, ANY)

    @patch("claudesync.cli.chat.validate_and_get_provider")
    def test_ls_command(self, mock_validate_and_get_provider):
        mock_provider = MagicMock()
        mock_provider.get_chat_conversations.return_value = [
            {
                "uuid": "chat1",
                "name": "Chat 1",
                "updated_at": "2023-01-01",
                "project": {"name": "Project 1"},
            },
            {
                "uuid": "chat2",
                "name": "Chat 2",
                "updated_at": "2023-01-02",
                "project": {"name": "Project 2"},
            },
        ]
        mock_validate_and_get_provider.return_value = mock_provider

        result = self.runner.invoke(cli, ["chat", "ls"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Chat 1", result.output)
        self.assertIn("Chat 2", result.output)
