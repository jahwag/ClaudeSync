import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from claudesync.cli.main import cli
from claudesync.configmanager import InMemoryConfigManager


class TestProjectCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.config_mock = MagicMock(spec=InMemoryConfigManager)

    @patch("claudesync.cli.project.validate_and_get_provider")
    def test_project_sync_no_local_path(self, mock_validate_and_get_provider):
        # Mock the provider
        mock_provider = MagicMock()
        mock_validate_and_get_provider.return_value = mock_provider

        # Set up the config mock to return None for local_path
        self.config_mock.get.side_effect = lambda key, default=None: (
            None if key == "local_path" else default
        )

        result = self.runner.invoke(cli, ["project", "sync"], obj=self.config_mock)

        self.assertIn("No local path set for this project", result.output)
        self.assertEqual(result.exit_code, 0)

        # Verify that the provider's methods were not called
        mock_provider.list_files.assert_not_called()
        mock_provider.get_projects.assert_not_called()


if __name__ == "__main__":
    unittest.main()
