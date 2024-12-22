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

        # Create a CLI runner
        self.runner = CliRunner()

        # Ensure we have the required environment variable
        self.session_key = os.environ.get('CLAUDE_SESSION_KEY')
        if not self.session_key:
            raise ValueError("CLAUDE_SESSION_KEY environment variable must be set")

    def tearDown(self):
        """Clean up after each test"""
        # Restore the original HOME
        if self.old_home:
            os.environ['HOME'] = self.old_home
        else:
            del os.environ['HOME']

        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    @patch('claudesync.session_key_manager.SessionKeyManager._find_ssh_key')
    @patch('claudesync.session_key_manager.SessionKeyManager._get_key_type')
    @patch('claudesync.session_key_manager.SessionKeyManager._derive_key_from_ssh_key')
    @patch('claudesync.session_key_manager.SessionKeyManager._encrypt_symmetric')
    def test_login_with_session_key(self, mock_encrypt_symmetric, mock_derive_key_from_ssh_key,
                                    mock_get_key_type, mock_find_ssh_key):
        """Test logging in with a session key provided via command line"""

        mock_find_ssh_key.return_value = "/dummy/path/to/id_ed25519"
        mock_get_key_type.return_value = "ed25519"
        mock_derive_key_from_ssh_key.return_value = "derived_key"
        mock_encrypt_symmetric.return_value = ("encrypted_key", "symmetric")

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

        # Verify session key was stored
        config = FileConfigManager()
        stored_key, expiry = config.get_session_key()
        self.assertIsNotNone(stored_key)
        self.assertIsNotNone(expiry)

        # Verify we can use the stored credentials
        result = self.runner.invoke(cli, ['organization', 'ls'])
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("No organizations", result.output)

if __name__ == '__main__':
    unittest.main()