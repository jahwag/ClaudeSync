import threading
import time
import unittest
from click.testing import CliRunner
from unittest.mock import patch
from claudesync.cli.main import cli
from claudesync.configmanager import InMemoryConfigManager
from mock_http_server import run_mock_server


class TestClaudeSyncHappyPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mock_server_thread = threading.Thread(target=run_mock_server)
        cls.mock_server_thread.daemon = True
        cls.mock_server_thread.start()
        time.sleep(1)  # Wait for the mock server to start

    def setUp(self):
        self.runner = CliRunner()
        self.config = InMemoryConfigManager()
        self.config.set(
            "claude_api_url", "http://127.0.0.1:8000/api"
        )  # Set BASE_URL for the mock server

    @patch("claudesync.utils.get_local_files")
    def test_happy_path(self, mock_get_local_files):
        # Mock the API calls
        mock_get_local_files.return_value = {"test.txt": "content_hash"}

        # Login
        result = self.runner.invoke(
            cli,
            ["auth", "login", "--provider", "claude.ai"],
            input="sk-ant-1234\nThu, 26 Sep 2099 17:07:53 UTC\n",
            obj=self.config,
        )
        self.assertEqual(0, result.exit_code)
        self.assertIn("Successfully authenticated with claude.ai", result.output)

        # Create project using init --new
        result = self.runner.invoke(
            cli,
            [
                "project",
                "init",
                "--new",
                "--name",
                "New Project",
                "--description",
                "Test description",
                "--local-path",
                "./",
                "--provider",
                "claude.ai",
            ],
            obj=self.config,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn(
            "Project 'New Project' (uuid: new_proj) has been created successfully",
            result.output,
        )
        self.assertIn("Project created:", result.output)
        self.assertIn("Project location:", result.output)
        self.assertIn("Project config location:", result.output)
        self.assertIn("Remote URL: https://claude.ai/project/new_proj", result.output)

        # Push project
        result = self.runner.invoke(cli, ["push"], obj=self.config)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Main project 'New Project' synced successfully", result.output)


if __name__ == "__main__":
    unittest.main()
