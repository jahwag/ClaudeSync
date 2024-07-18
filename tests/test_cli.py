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

if __name__ == '__main__':
    unittest.main()