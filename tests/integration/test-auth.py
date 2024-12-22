import os
import shutil
import tempfile
import unittest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch

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

    def test_login_with_session_key(self):
        """Test logging in with a session key provided via command line"""
        # Run the login command with the session key
        result = self.runner.invoke(
            cli,
            ['auth', 'login', '--session-key', self.session_key, '--auto-approve']
        )

        if result.exception:
            print(f"Exception during login: {result.exception}")
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
        
        # Verify we can use the stored credentials to make an API call
        result = self.runner.invoke(cli, ['organization', 'ls'])
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("No organizations", result.output)

    def test_login_with_invalid_session_key(self):
        """Test logging in with an invalid session key"""
        result = self.runner.invoke(
            cli,
            ['auth', 'login', '--session-key', 'sk-ant-invalid-key', '--auto-approve']
        )
        
        # Check command failed
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Authentication failed", result.output)

    def test_login_logout_flow(self):
        """Test the full login-logout flow"""
        # First login
        result = self.runner.invoke(
            cli,
            ['auth', 'login', '--session-key', self.session_key, '--auto-approve']
        )
        self.assertEqual(result.exit_code, 0)
        
        # Verify we're logged in
        result = self.runner.invoke(cli, ['auth', 'ls'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("claude.ai", result.output)
        
        # Logout
        result = self.runner.invoke(cli, ['auth', 'logout'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Logged out", result.output)
        
        # Verify we're logged out
        result = self.runner.invoke(cli, ['auth', 'ls'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No authenticated providers found", result.output)

    def test_session_key_format_validation(self):
        """Test validation of session key format"""
        # Test with key that doesn't start with sk-ant
        result = self.runner.invoke(
            cli,
            ['auth', 'login', '--session-key', 'invalid-prefix-key', '--auto-approve']
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid sessionKey format", result.output)

    def test_config_file_permissions(self):
        """Test that config files are created with correct permissions"""
        # Login first
        result = self.runner.invoke(
            cli,
            ['auth', 'login', '--session-key', self.session_key, '--auto-approve']
        )

        if result.exception:
            print(f"Exception during login: {result.exception}")
        if result.output:
            print(f"Command output: {result.output}")

        self.assertEqual(result.exit_code, 0)
        
        # Check .claudesync directory permissions
        config_dir = Path(self.test_dir) / '.claudesync'
        stat = config_dir.stat()
        
        # Directory should be readable and writeable by owner only
        expected_mode = 0o700  # rwx------ 
        self.assertEqual(stat.st_mode & 0o777, expected_mode)
        
        # Check key file permissions
        key_file = config_dir / 'claude.ai.key'
        stat = key_file.stat()
        
        # File should be readable and writeable by owner only
        expected_mode = 0o600  # rw-------
        self.assertEqual(stat.st_mode & 0o777, expected_mode)

    def test_multiple_logins(self):
        """Test logging in multiple times with the same credentials"""
        # First login
        result1 = self.runner.invoke(
            cli,
            ['auth', 'login', '--session-key', self.session_key, '--auto-approve']
        )
        self.assertEqual(result1.exit_code, 0)
        
        # Get first session key
        config = FileConfigManager()
        first_key, _ = config.get_session_key()
        
        # Second login
        result2 = self.runner.invoke(
            cli,
            ['auth', 'login', '--session-key', self.session_key, '--auto-approve']
        )
        self.assertEqual(result2.exit_code, 0)
        
        # Get second session key
        second_key, _ = config.get_session_key()
        
        # Keys should be the same since we used the same session key
        self.assertEqual(first_key, second_key)
        
        # Verify we can still make API calls
        result = self.runner.invoke(cli, ['organization', 'ls'])
        self.assertEqual(result.exit_code, 0)


if __name__ == '__main__':
    unittest.main()
