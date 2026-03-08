from pathlib import Path
from unittest.mock import patch
from claudesync.session_key_manager import SessionKeyManager


class TestFindSshKey:
    """Tests for SessionKeyManager._find_ssh_key key discovery logic."""

    @patch("claudesync.session_key_manager.input", return_value="/fake/key")
    def test_configured_file_path(self, mock_input, tmp_path):
        """When ssh_key_path points to an existing file, use it directly."""
        key_file = tmp_path / "my_custom_key"
        key_file.write_text("fake-key-content")

        mgr = SessionKeyManager(ssh_key_path=str(key_file))
        assert mgr.ssh_key_path == str(key_file)
        mock_input.assert_not_called()

    @patch("claudesync.session_key_manager.input", return_value="/fake/key")
    def test_configured_directory(self, mock_input, tmp_path):
        """When ssh_key_path is a directory, search it for standard key names."""
        key_file = tmp_path / "id_ed25519"
        key_file.write_text("fake-key-content")

        mgr = SessionKeyManager(ssh_key_path=str(tmp_path))
        assert mgr.ssh_key_path == str(key_file)
        mock_input.assert_not_called()

    @patch("claudesync.session_key_manager.input", return_value="/fake/key")
    def test_default_fallback(self, mock_input, tmp_path):
        """When no config provided, search ~/.ssh for standard key names."""
        fake_ssh = tmp_path / ".ssh"
        fake_ssh.mkdir()
        key_file = fake_ssh / "id_ed25519"
        key_file.write_text("fake-key-content")

        with patch.object(Path, "home", return_value=tmp_path):
            mgr = SessionKeyManager()
            assert mgr.ssh_key_path == str(key_file)
            mock_input.assert_not_called()

    @patch("claudesync.session_key_manager.input", return_value="/user/entered/key")
    def test_no_key_found_prompts_user(self, mock_input, tmp_path):
        """When no key exists anywhere, prompt the user."""
        fake_ssh = tmp_path / ".ssh"
        fake_ssh.mkdir()
        # No key files created

        with patch.object(Path, "home", return_value=tmp_path):
            mgr = SessionKeyManager()
            assert mgr.ssh_key_path == "/user/entered/key"
            mock_input.assert_called_once()

    @patch("claudesync.session_key_manager.input", return_value="/fake/key")
    def test_nonexistent_configured_path_warns(self, mock_input, tmp_path):
        """When ssh_key_path doesn't exist, log warning and fall through."""
        fake_ssh = tmp_path / ".ssh"
        fake_ssh.mkdir()
        key_file = fake_ssh / "id_ed25519"
        key_file.write_text("fake-key-content")

        with patch.object(Path, "home", return_value=tmp_path):
            mgr = SessionKeyManager(ssh_key_path="/nonexistent/path")
            # Should fall through to default and find the key
            assert mgr.ssh_key_path == str(key_file)
            mock_input.assert_not_called()
