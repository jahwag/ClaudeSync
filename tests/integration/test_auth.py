import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from claudesync.cli.main import cli
from claudesync.configmanager import FileConfigManager

class TestAuthIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        # Create a temporary directory for the test
        self.test_dir = tempfile.mkdtemp()
        self.old_home = os.environ.get('HOME')
        # Set HOME to our test directory so .claudesync is created there
        os.environ['HOME'] = self.test_dir

        # Delete any existing .claudesync folder in current directory
        claudesync_dir = Path(os.getcwd()) / '.claudesync'
        if claudesync_dir.exists():
            shutil.rmtree(claudesync_dir)

        # Create a CLI runner
        self.runner = CliRunner()

        # Ensure we have the required environment variable
        self.session_key = os.environ.get('CLAUDE_SESSION_KEY')
        if not self.session_key:
            raise ValueError("CLAUDE_SESSION_KEY environment variable must be set")

    @patch('claudesync.session_key_manager.SessionKeyManager._find_ssh_key')
    def tearDown(self, mock_find_ssh_key):
        """Clean up after each test"""
        mock_find_ssh_key.return_value = "/Users/thomasbuechner/.ssh/id_ed25519"

        archive_result = self.runner.invoke(cli, ['project', 'archive'])
        if archive_result.exit_code != 0:
            print(f"Failed to archive active project: {archive_result.output}")

        # Restore the original HOME
        if self.old_home:
            os.environ['HOME'] = self.old_home
        else:
            del os.environ['HOME']

        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    @patch('claudesync.session_key_manager.SessionKeyManager._find_ssh_key')
    def test_01_login_with_session_key(self, mock_find_ssh_key):
        """Test logging in with a session key provided via command line"""
        mock_find_ssh_key.return_value = "/Users/thomasbuechner/.ssh/id_ed25519"

        # Run the login command with the session key
        result = self.runner.invoke(
            cli,
            ['auth', 'login', '--session-key', self.session_key, '--auto-approve']
        )

        if result.exception:
            import traceback
            print(f"Exception during login: {result.exception}")
            print("Full traceback:")
            print(''.join(traceback.format_tb(result.exc_info[2])))
        if result.output:
            print(f"Command output: {result.output}")

        # Check command succeeded
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Successfully authenticated with Claude AI", result.output)

        # Verify config file was created
        config_dir = Path(self.test_dir) / '.claudesync'
        self.assertTrue(config_dir.exists())

        # assert that there is a file called config.json in the config_dir
        config_file = config_dir / 'config.json'
        self.assertTrue(config_file.exists())

        # Verify session key was stored
        config = FileConfigManager()
        stored_key, expiry = config.get_session_key()
        self.assertIsNotNone(stored_key)
        self.assertIsNotNone(expiry)

        # Verify we can use the stored credentials
        result = self.runner.invoke(cli, ['organization', 'ls'])
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("No organizations", result.output)

    @patch('claudesync.session_key_manager.SessionKeyManager._find_ssh_key')
    def test_02_project_create(self, mock_find_ssh_key):
        """Test creating a new project after successful login"""
        mock_find_ssh_key.return_value = "/Users/thomasbuechner/.ssh/id_ed25519"

        # First ensure we're logged in
        login_result = self.runner.invoke(
            cli,
            ['auth', 'login', '--session-key', self.session_key, '--auto-approve']
        )
        self.assertEqual(login_result.exit_code, 0)

        # Create a new project
        project_result = self.runner.invoke(
            cli,
            ['project', 'create', '--name', 'Test Project', '--internal-name', 'test-project',
             '--description', 'Test project created by integration test', '--no-git-check'],
            input='y\n'  # Automatically confirm any prompts
        )

        if project_result.exception:
            import traceback
            print(f"Exception during project creation: {project_result.exception}")
            print("Full traceback:")
            print(''.join(traceback.format_tb(project_result.exc_info[2])))
        if project_result.output:
            print(f"Command output: {project_result.output}")

        # Check command succeeded
        self.assertEqual(project_result.exit_code, 0)
        self.assertIn("Project", project_result.output)
        self.assertIn("has been created successfully", project_result.output)

        # Verify project files were created
        claudesync_dir = Path(os.getcwd()) / '.claudesync'
        project_config = claudesync_dir / 'test-project.project.json'
        project_id_config = claudesync_dir / 'test-project.project_id.json'
        active_project = claudesync_dir / 'active_project.json'

        self.assertTrue(project_config.exists())
        self.assertTrue(project_id_config.exists())
        self.assertTrue(active_project.exists())

        # Verify project configurations
        with open(project_config) as f:
            config_data = json.load(f)
            self.assertEqual(config_data['project_name'], 'Test Project')
            self.assertEqual(config_data['project_description'], 'Test project created by integration test')
            self.assertIn('includes', config_data)
            self.assertIn('excludes', config_data)

        # Verify project ID was stored
        with open(project_id_config) as f:
            id_data = json.load(f)
            self.assertIn('project_id', id_data)
            self.assertTrue(id_data['project_id'].strip())

        # Verify active project was set
        with open(active_project) as f:
            active_data = json.load(f)
            self.assertEqual(active_data['project_path'], 'test-project')
            self.assertEqual(active_data['project_id'], id_data['project_id'])

    @patch('claudesync.session_key_manager.SessionKeyManager._find_ssh_key')
    def test_03_project_push(self, mock_find_ssh_key):
        """Test pushing files to the project created in test_02_project_create"""
        mock_find_ssh_key.return_value = "/Users/thomasbuechner/.ssh/id_ed25519"

        # First ensure we're logged in
        login_result = self.runner.invoke(
            cli,
            ['auth', 'login', '--session-key', self.session_key, '--auto-approve']
        )
        self.assertEqual(login_result.exit_code, 0)

        # Create a test project first (reusing test_02_project_create logic)
        project_result = self.runner.invoke(
            cli,
            ['project', 'create', '--name', 'Test Project', '--internal-name', 'test-project',
             '--description', 'Test project created for push test', '--no-git-check'],
            input='y\n'
        )
        self.assertEqual(project_result.exit_code, 0)

        # Create some test files
        test_files_dir = Path(os.getcwd()) / 'test_files'
        test_files_dir.mkdir(exist_ok=True)

        # Create a Python file
        python_file = test_files_dir / 'test.py'
        python_file.write_text('''
    def hello():
        print("Hello, World!")
    
    if __name__ == "__main__":
        hello()
    ''')

        # Create a text file
        text_file = test_files_dir / 'readme.txt'
        text_file.write_text('This is a test file for claudesync push.')

        # Update project configuration to include these files
        claudesync_dir = Path(os.getcwd()) / '.claudesync'
        project_config = claudesync_dir / 'test-project.project.json'

        with open(project_config, 'r+') as f:
            config = json.load(f)
            config['includes'] = ['test_files/*.py', 'test_files/*.txt']
            f.seek(0)
            json.dump(config, f, indent=2)
            f.truncate()

        # Push files to the project
        push_result = self.runner.invoke(cli, ['push', 'test-project'])

        if push_result.exception:
            import traceback
            print(f"Exception during push: {push_result.exception}")
            print("Full traceback:")
            print(''.join(traceback.format_tb(push_result.exc_info[2])))
        if push_result.output:
            print(f"Command output: {push_result.output}")

        # Check command succeeded
        self.assertEqual(push_result.exit_code, 0)
        self.assertIn("Project 'test-project' synced successfully", push_result.output)

        # Verify files were pushed by listing them
        list_result = self.runner.invoke(cli, ['file', 'ls', 'test-project'])
        self.assertEqual(list_result.exit_code, 0)
        self.assertIn('test.py', list_result.output)
        self.assertIn('readme.txt', list_result.output)

        # Clean up test files
        shutil.rmtree(test_files_dir)

if __name__ == '__main__':
    unittest.main()