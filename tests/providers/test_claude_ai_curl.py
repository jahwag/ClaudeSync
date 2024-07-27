import unittest
from unittest.mock import patch, MagicMock
import subprocess
from claudesync.providers.claude_ai_curl import ClaudeAICurlProvider
from claudesync.exceptions import ProviderError


class TestClaudeAICurlProvider(unittest.TestCase):

    def setUp(self):
        self.provider = ClaudeAICurlProvider("test_session_key")

    @patch("subprocess.run")
    def test_execute_curl_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = '{"key": "value"}'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.provider._execute_curl("GET", "/test")

        self.assertEqual(result, {"key": "value"})
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_execute_curl_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "curl", stderr="Test error"
        )

        with self.assertRaises(ProviderError):
            self.provider._execute_curl("GET", "/test")

    @patch("claudesync.providers.claude_ai_curl.click.prompt")
    def test_login(self, mock_prompt):
        mock_prompt.return_value = "new_session_key"

        result = self.provider.login()

        self.assertEqual(result, "new_session_key")
        self.assertEqual(self.provider.session_key, "new_session_key")

    @patch("claudesync.providers.claude_ai_curl.ClaudeAICurlProvider._execute_curl")
    def test_get_organizations(self, mock_execute_curl):
        mock_execute_curl.return_value = [
            {"uuid": "org1", "name": "Org 1"},
            {"uuid": "org2", "name": "Org 2"},
        ]

        result = self.provider.get_organizations()

        expected = [{"id": "org1", "name": "Org 1"}, {"id": "org2", "name": "Org 2"}]
        self.assertEqual(result, expected)

    @patch("claudesync.providers.claude_ai_curl.ClaudeAICurlProvider._execute_curl")
    def test_get_projects(self, mock_execute_curl):
        mock_execute_curl.return_value = [
            {"uuid": "proj1", "name": "Project 1", "archived_at": None},
            {"uuid": "proj2", "name": "Project 2", "archived_at": "2023-01-01"},
        ]

        result = self.provider.get_projects("org1", include_archived=True)

        expected = [
            {"id": "proj1", "name": "Project 1", "archived_at": None},
            {"id": "proj2", "name": "Project 2", "archived_at": "2023-01-01"},
        ]
        self.assertEqual(result, expected)

    @patch("claudesync.providers.claude_ai_curl.ClaudeAICurlProvider._execute_curl")
    def test_list_files(self, mock_execute_curl):
        mock_execute_curl.return_value = [
            {
                "uuid": "file1",
                "file_name": "test1.txt",
                "content": "content1",
                "created_at": "2023-01-01",
            },
            {
                "uuid": "file2",
                "file_name": "test2.txt",
                "content": "content2",
                "created_at": "2023-01-02",
            },
        ]

        result = self.provider.list_files("org1", "proj1")

        expected = [
            {
                "uuid": "file1",
                "file_name": "test1.txt",
                "content": "content1",
                "created_at": "2023-01-01",
            },
            {
                "uuid": "file2",
                "file_name": "test2.txt",
                "content": "content2",
                "created_at": "2023-01-02",
            },
        ]
        self.assertEqual(result, expected)

    @patch("claudesync.providers.claude_ai_curl.ClaudeAICurlProvider._execute_curl")
    def test_upload_file(self, mock_execute_curl):
        mock_execute_curl.return_value = {"uuid": "new_file", "file_name": "test.txt"}

        result = self.provider.upload_file("org1", "proj1", "test.txt", "content")

        self.assertEqual(result, {"uuid": "new_file", "file_name": "test.txt"})
        mock_execute_curl.assert_called_once_with(
            "POST",
            "/organizations/org1/projects/proj1/docs",
            {"file_name": "test.txt", "content": "content"},
        )

    @patch("claudesync.providers.claude_ai_curl.ClaudeAICurlProvider._execute_curl")
    def test_delete_file(self, mock_execute_curl):
        mock_execute_curl.return_value = {"status": "deleted"}

        result = self.provider.delete_file("org1", "proj1", "file1")

        self.assertEqual(result, {"status": "deleted"})
        mock_execute_curl.assert_called_once_with(
            "DELETE", "/organizations/org1/projects/proj1/docs/file1"
        )

    @patch("claudesync.providers.claude_ai_curl.ClaudeAICurlProvider._execute_curl")
    def test_archive_project(self, mock_execute_curl):
        mock_execute_curl.return_value = {"uuid": "proj1", "is_archived": True}

        result = self.provider.archive_project("org1", "proj1")

        self.assertEqual(result, {"uuid": "proj1", "is_archived": True})
        mock_execute_curl.assert_called_once_with(
            "PUT", "/organizations/org1/projects/proj1", {"is_archived": True}
        )

    @patch("claudesync.providers.claude_ai_curl.ClaudeAICurlProvider._execute_curl")
    def test_create_project(self, mock_execute_curl):
        mock_execute_curl.return_value = {"uuid": "new_proj", "name": "New Project"}

        result = self.provider.create_project("org1", "New Project", "Description")

        self.assertEqual(result, {"uuid": "new_proj", "name": "New Project"})
        mock_execute_curl.assert_called_once_with(
            "POST",
            "/organizations/org1/projects",
            {
                "name": "New Project",
                "description": "Description",
                "is_private": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
