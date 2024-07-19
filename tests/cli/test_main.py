import unittest
from click.testing import CliRunner
from claudesync.cli.main import cli


class TestMainCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_cli_group(self):
        result = self.runner.invoke(cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn(
            "ClaudeSync: Synchronize local files with ai projects.", result.output
        )

    def test_install_completion(self):
        result = self.runner.invoke(cli, ["install-completion", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Install completion for the specified shell.", result.output)

    def test_status(self):
        result = self.runner.invoke(cli, ["status"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Active provider:", result.output)


if __name__ == "__main__":
    unittest.main()
