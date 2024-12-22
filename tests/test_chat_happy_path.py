import unittest
import threading
import time
from click.testing import CliRunner
from claudesync.cli.main import cli
from claudesync.configmanager import InMemoryConfigManager
from mock_http_server import run_mock_server


class TestChatHappyPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the mock server in a separate thread
        cls.mock_server_thread = threading.Thread(target=run_mock_server)
        cls.mock_server_thread.daemon = True
        cls.mock_server_thread.start()
        time.sleep(1)  # Give the server a moment to start

    def setUp(self):
        self.runner = CliRunner()
        self.config = InMemoryConfigManager()
        self.config.set("claude_api_url", "http://localhost:8000/api")

    def test_chat_happy_path(self):
        # Step 1: Login
        result = self.runner.invoke(
            cli,
            ["auth", "login", "--provider", "claude.ai"],
            input="sk-ant-1234\nThu, 26 Sep 2099 17:07:53 UTC\n",
            obj=self.config,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Successfully authenticated with claude.ai", result.output)

        # Step 2: Set organization
        result = self.runner.invoke(
            cli, ["organization", "set"], input="1\n", obj=self.config
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Selected organization: Test Org 1", result.output)

        # Step 3: Create project using init --new
        result = self.runner.invoke(
            cli,
            [
                "project",
                "init",
                "--new",
                "--name",
                "Test Project",
                "--description",
                "Test Description",
                "--local-path",
                ".",
            ],
            obj=self.config,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn(
            "Project 'New Project' (uuid: new_proj) has been created successfully",
            result.output,
        )

        # Step 4: Send message
        result = self.runner.invoke(
            cli, ["chat", "message", "Hello, Claude!"], input="1\n", obj=self.config
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Hello there.", result.output)
        self.assertIn("I apologize for the confusion. You're right.", result.output)


if __name__ == "__main__":
    unittest.main()
