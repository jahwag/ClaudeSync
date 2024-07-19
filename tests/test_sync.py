import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from claudesync.cli.main import cli
from claudesync.exceptions import ConfigurationError, ProviderError
import os

class TestSyncCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    @patch('claudesync.cli.sync.validate_and_get_provider')
    def test_ls_command(self, mock_validate_and_get_provider):
        mock_provider = MagicMock()
        mock_provider.list_files.return_value = [
            {'file_name': 'file1.txt', 'uuid': 'uuid1', 'created_at': '2023-01-01'},
            {'file_name': 'file2.py', 'uuid': 'uuid2', 'created_at': '2023-01-02'}
        ]
        mock_validate_and_get_provider.return_value = mock_provider

        result = self.runner.invoke(cli, ['ls'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn('file1.txt', result.output)
        self.assertIn('file2.py', result.output)
        mock_provider.list_files.assert_called_once()

    @patch('claudesync.cli.sync.validate_and_get_provider')
    def test_ls_command_no_files(self, mock_validate_and_get_provider):
        mock_provider = MagicMock()
        mock_provider.list_files.return_value = []
        mock_validate_and_get_provider.return_value = mock_provider

        result = self.runner.invoke(cli, ['ls'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn('No files found in the active project.', result.output)

    @patch('claudesync.cli.sync.validate_and_get_provider')
    @patch('claudesync.cli.sync.get_local_files')
    @patch('claudesync.cli.sync.os.path.exists')
    @patch('claudesync.cli.sync.open', new_callable=unittest.mock.mock_open, read_data="file content")
    @patch('claudesync.config_manager.ConfigManager')
    def test_sync_command(self, mock_config_manager, mock_open, mock_path_exists, mock_get_local_files, mock_validate_and_get_provider):
        # Mock the ConfigManager
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            'active_organization_id': 'org1',
            'active_project_id': 'proj1',
            'local_path': '/mock/local/path'
        }.get(key, default)
        mock_config_manager.return_value = mock_config

        mock_provider = MagicMock()
        mock_provider.list_files.return_value = [
            {'file_name': 'existing.txt', 'uuid': 'uuid1', 'content': 'old content'}
        ]
        mock_validate_and_get_provider.return_value = mock_provider

        mock_get_local_files.return_value = {
            'existing.txt': 'new_checksum',
            'new_file.txt': 'new_file_checksum'
        }

        mock_path_exists.return_value = True

        with patch('claudesync.cli.main.ConfigManager', return_value=mock_config):
            result = self.runner.invoke(cli, ['sync'])

        self.assertEqual(result.exit_code, 0, f"Command failed with output: {result.output}")
        self.assertIn('Updating existing.txt on remote...', result.output)
        self.assertIn('Uploading new file new_file.txt to remote...', result.output)
        self.assertIn('Sync completed successfully.', result.output)

        mock_provider.delete_file.assert_called_once_with('org1', 'proj1', 'uuid1')
        self.assertEqual(mock_provider.upload_file.call_count, 2)

    @patch('claudesync.cli.sync.validate_and_get_provider')
    @patch('claudesync.cli.sync.os.path.exists')
    def test_sync_command_no_local_path(self, mock_path_exists, mock_validate_and_get_provider):
        mock_provider = MagicMock()
        mock_validate_and_get_provider.return_value = mock_provider
        mock_path_exists.return_value = False

        result = self.runner.invoke(cli, ['sync'])

        self.assertEqual(result.exit_code, 1)
        self.assertIn('No local path set. Please select or create a project to set the local path.', result.output)

    @patch('claudesync.cli.sync.shutil.which')
    @patch('claudesync.cli.sync.sys.platform', 'linux')
    @patch('claudesync.cli.sync.CronTab')
    def test_schedule_command_unix(self, mock_crontab, mock_which):
        mock_which.return_value = '/usr/local/bin/claudesync'
        mock_cron = MagicMock()
        mock_crontab.return_value = mock_cron

        result = self.runner.invoke(cli, ['schedule'], input='10\n')

        self.assertEqual(result.exit_code, 0)
        self.assertIn('Cron job created successfully!', result.output)
        mock_cron.new.assert_called_once_with(command='/usr/local/bin/claudesync sync')
        mock_cron.write.assert_called_once()

    @patch('claudesync.cli.sync.shutil.which')
    @patch('claudesync.cli.sync.sys.platform', 'win32')
    def test_schedule_command_windows(self, mock_which):
        mock_which.return_value = 'C:\\Program Files\\claudesync\\claudesync.exe'

        result = self.runner.invoke(cli, ['schedule'], input='10\n')

        self.assertEqual(result.exit_code, 0)
        self.assertIn('Windows Task Scheduler setup:', result.output)
        self.assertIn('schtasks /create /tn "ClaudeSync" /tr "C:\\Program Files\\claudesync\\claudesync.exe sync" /sc minute /mo 10', result.output)

    @patch('claudesync.cli.sync.shutil.which')
    def test_schedule_command_claudesync_not_found(self, mock_which):
        mock_which.return_value = None

        result = self.runner.invoke(cli, ['schedule'], input='10\n')

        self.assertEqual(result.exit_code, 1)
        self.assertIn('Error: claudesync not found in PATH.', result.output)

if __name__ == '__main__':
    unittest.main()