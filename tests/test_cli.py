import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import unittest
from unittest.mock import patch, MagicMock, mock_open
from click.testing import CliRunner
from claudesync.cli import cli

class TestCLI(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch('claudesync.cli.ConfigManager')
    @patch('claudesync.cli.get_provider')
    def test_organization_list(self, mock_get_provider, mock_config_manager):
        mock_provider = MagicMock()
        mock_provider.get_organizations.return_value = [
            {'id': 'org1', 'name': 'Organization 1'},
            {'id': 'org2', 'name': 'Organization 2'}
        ]
        mock_get_provider.return_value = mock_provider

        result = self.runner.invoke(cli, ['organization', 'list'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Organization 1', result.output)
        self.assertIn('Organization 2', result.output)

    @patch('claudesync.cli.ConfigManager')
    @patch('claudesync.cli.get_provider')
    @patch('claudesync.cli.os.path.isabs', return_value=True)
    @patch('claudesync.cli.os.path.exists', return_value=True)
    def test_project_create(self, mock_exists, mock_isabs, mock_get_provider, mock_config_manager):
        mock_provider = MagicMock()
        mock_provider.create_project.return_value = {
            'uuid': 'proj1',
            'name': 'New Project'
        }
        mock_get_provider.return_value = mock_provider

        mock_config = MagicMock()
        mock_config.get.return_value = 'org1'
        mock_config_manager.return_value = mock_config

        result = self.runner.invoke(cli, ['project', 'create'], input='New Project\nProject Description\n/path/to/local/dir\n')
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Project \'New Project\' (uuid: proj1) has been created successfully', result.output)

        # Verify that the project details were stored
        mock_config.set.assert_any_call('active_project_id', 'proj1')
        mock_config.set.assert_any_call('active_project_name', 'New Project')
        mock_config.set.assert_any_call('local_path', '/path/to/local/dir')

    @patch('claudesync.cli.ConfigManager')
    @patch('claudesync.cli.get_provider')
    @patch('claudesync.cli.get_local_files')
    @patch('claudesync.cli.os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data="File content")
    def test_sync(self, mock_file, mock_exists, mock_get_local_files, mock_get_provider, mock_config_manager):
        # Mock configuration
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            'active_provider': 'claude.ai',
            'session_key': 'test_session_key',
            'active_organization_id': 'org1',
            'active_project_id': 'proj1',
            'local_path': '/path/to/local/dir'
        }.get(key)
        mock_config_manager.return_value = mock_config

        # Mock provider
        mock_provider = MagicMock()
        mock_provider.list_files.return_value = [
            {'file_name': 'existing_file.txt', 'uuid': 'file1', 'content': 'Existing content', 'created_at': '2023-01-01'},
            {'file_name': 'modified_file.txt', 'uuid': 'file2', 'content': 'Old content', 'created_at': '2023-01-01'}
        ]
        mock_get_provider.return_value = mock_provider

        # Mock local files
        mock_get_local_files.return_value = {
            'existing_file.txt': 'new_checksum',
            'modified_file.txt': 'modified_checksum',
            'new_file.txt': 'new_checksum'
        }

        # Run sync command
        result = self.runner.invoke(cli, ['sync'])

        # Print debug information
        print(f"Exit code: {result.exit_code}")
        print(f"Output: {result.output}")
        if result.exception:
            print(f"Exception: {result.exception}")

        # Assertions
        self.assertEqual(result.exit_code, 0, f"Sync command failed with exit code {result.exit_code}")
        self.assertIn('Updating existing_file.txt on remote...', result.output)
        self.assertIn('Updating modified_file.txt on remote...', result.output)
        self.assertIn('Uploading new file new_file.txt to remote...', result.output)
        self.assertIn('Sync completed successfully.', result.output)

        # Verify provider method calls
        self.assertEqual(mock_provider.delete_file.call_count, 2)  # For existing_file.txt and modified_file.txt
        self.assertEqual(mock_provider.upload_file.call_count, 3)  # For all three files

if __name__ == '__main__':
    unittest.main()