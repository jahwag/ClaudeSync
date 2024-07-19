import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from claudesync.cli.main import cli
from claudesync.exceptions import ProviderError

class TestProjectCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    @patch('claudesync.cli.project.validate_and_get_provider')
    @patch('claudesync.cli.project.click.prompt')
    @patch('claudesync.cli.project.validate_and_store_local_path')
    def test_project_create(self, mock_validate_path, mock_prompt, mock_validate_and_get_provider):
        mock_provider = MagicMock()
        mock_provider.create_project.return_value = {
            'uuid': 'proj1',
            'name': 'New Project'
        }
        mock_validate_and_get_provider.return_value = mock_provider

        mock_prompt.side_effect = ['New Project', 'Project Description']

        result = self.runner.invoke(cli, ['project', 'create'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Project 'New Project' (uuid: proj1) has been created successfully.", result.output)
        self.assertIn("Active project set to: New Project (uuid: proj1)", result.output)
        mock_validate_path.assert_called_once()
        mock_provider.create_project.assert_called_once_with('org1', 'New Project', 'Project Description')

    @patch('claudesync.cli.project.validate_and_get_provider')
    @patch('claudesync.cli.project.click.prompt')
    @patch('claudesync.cli.project.click.confirm')
    def test_project_archive(self, mock_confirm, mock_prompt, mock_validate_and_get_provider):
        mock_provider = MagicMock()
        mock_provider.get_projects.return_value = [
            {'id': 'proj1', 'name': 'Project 1'},
            {'id': 'proj2', 'name': 'Project 2'}
        ]
        mock_validate_and_get_provider.return_value = mock_provider

        mock_prompt.return_value = 1
        mock_confirm.return_value = True

        result = self.runner.invoke(cli, ['project', 'archive'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Project 'Project 1' has been archived.", result.output)
        mock_provider.archive_project.assert_called_once_with('org1', 'proj1')

    @patch('claudesync.cli.project.validate_and_get_provider')
    @patch('claudesync.cli.project.click.prompt')
    @patch('claudesync.cli.project.validate_and_store_local_path')
    def test_project_select(self, mock_validate_path, mock_prompt, mock_validate_and_get_provider):
        mock_provider = MagicMock()
        mock_provider.get_projects.return_value = [
            {'id': 'proj1', 'name': 'Project 1'},
            {'id': 'proj2', 'name': 'Project 2'}
        ]
        mock_validate_and_get_provider.return_value = mock_provider

        mock_prompt.return_value = 1

        result = self.runner.invoke(cli, ['project', 'select'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Selected project: Project 1 (ID: proj1)", result.output)
        mock_validate_path.assert_called_once()

    @patch('claudesync.cli.project.validate_and_get_provider')
    def test_project_list(self, mock_validate_and_get_provider):
        mock_provider = MagicMock()
        mock_provider.get_projects.return_value = [
            {'id': 'proj1', 'name': 'Project 1', 'archived_at': None},
            {'id': 'proj2', 'name': 'Project 2', 'archived_at': '2023-01-01'}
        ]
        mock_validate_and_get_provider.return_value = mock_provider

        result = self.runner.invoke(cli, ['project', 'ls', '--all'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Project 1 (ID: proj1)", result.output)
        self.assertIn("Project 2 (ID: proj2) (Archived)", result.output)

    @patch('claudesync.cli.project.validate_and_get_provider')
    def test_project_list_no_projects(self, mock_validate_and_get_provider):
        mock_provider = MagicMock()
        mock_provider.get_projects.return_value = []
        mock_validate_and_get_provider.return_value = mock_provider

        result = self.runner.invoke(cli, ['project', 'ls'])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("No projects found.", result.output)

    @patch('claudesync.cli.project.validate_and_get_provider')
    def test_project_create_error(self, mock_validate_and_get_provider):
        mock_provider = MagicMock()
        mock_provider.create_project.side_effect = ProviderError("Failed to create project")
        mock_validate_and_get_provider.return_value = mock_provider

        result = self.runner.invoke(cli, ['project', 'create'], input='New Project\nProject Description\n')

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Failed to create project: Failed to create project", result.output)

if __name__ == '__main__':
    unittest.main()