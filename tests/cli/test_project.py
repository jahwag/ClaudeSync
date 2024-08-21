import unittest
from unittest.mock import patch, MagicMock, ANY
from click.testing import CliRunner
from claudesync.cli.main import cli


class TestProjectCLI(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch("claudesync.cli.project.validate_and_get_provider")
    @patch("claudesync.cli.project.SyncManager")
    @patch("claudesync.cli.project.get_local_files")
    @patch("claudesync.cli.project.detect_submodules")
    def test_project_sync(
        self,
        mock_detect_submodules,
        mock_get_local_files,
        mock_sync_manager,
        mock_validate_and_get_provider,
    ):
        # Mock the provider and its methods
        mock_provider = MagicMock()
        mock_validate_and_get_provider.return_value = mock_provider
        mock_provider.get_projects.return_value = [
            {"id": "main_project_id", "name": "Main Project"},
            {"id": "submodule_id", "name": "Main Project-SubModule-submodule1"},
        ]
        mock_provider.list_files.side_effect = [
            [{"file_name": "main_file.txt"}],  # Main project files
            [{"file_name": "submodule_file.txt"}],  # Submodule files
        ]

        # Mock the configuration
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "active_organization_id": "org_id",
            "active_project_id": "main_project_id",
            "active_project_name": "Main Project",
            "local_path": "/path/to/project",
            "submodule_detect_filenames": ["pom.xml"],
        }.get(key, default)

        # Mock submodule detection
        mock_detect_submodules.return_value = [("submodule1", "pom.xml")]

        # Mock local file retrieval
        mock_get_local_files.side_effect = [
            {"main_file.txt": "hash1"},  # Main project files
            {"submodule_file.txt": "hash2"},  # Submodule files
        ]

        # Mock SyncManager
        mock_sync_manager_instance = MagicMock()
        mock_sync_manager.return_value = mock_sync_manager_instance

        # Run the command
        result = self.runner.invoke(cli, ["project", "sync"], obj=mock_config)

        # Assertions
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Main project 'Main Project' synced successfully.", result.output)
        self.assertIn("Syncing submodule 'submodule1'...", result.output)
        self.assertIn("Submodule 'submodule1' synced successfully.", result.output)
        self.assertIn(
            "Project sync completed successfully, including available submodules.",
            result.output,
        )

        # Verify method calls
        mock_validate_and_get_provider.assert_called_once_with(
            ANY, require_project=True
        )
        mock_provider.get_projects.assert_called_once_with(
            "org_id", include_archived=False
        )
        mock_provider.list_files.assert_any_call("org_id", "main_project_id")
        mock_provider.list_files.assert_any_call("org_id", "submodule_id")
        mock_get_local_files.assert_any_call("/path/to/project", None)
        mock_get_local_files.assert_any_call("/path/to/project/submodule1", None)
        mock_sync_manager_instance.sync.assert_called()
        self.assertEqual(
            mock_sync_manager_instance.sync.call_count, 2
        )  # Once for main project, once for submodule


if __name__ == "__main__":
    unittest.main()
