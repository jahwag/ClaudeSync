import unittest
from unittest.mock import patch, MagicMock
import requests
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError
from claudesync.config_manager import ConfigManager


class TestClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = ClaudeAIProvider("test_session_key")
        # Mock ConfigManager
        self.mock_config = MagicMock(spec=ConfigManager)
        self.mock_config.get_headers.return_value = {}
        self.mock_config.get.return_value = {}
        self.provider.config = self.mock_config

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_make_request_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response

        result = self.provider._make_request("GET", "/test")

        self.assertEqual(result, {"key": "value"})
        mock_request.assert_called_once()

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_make_request_failure(self, mock_request):
        mock_request.side_effect = requests.RequestException("Test error")

        with self.assertRaises(ProviderError):
            self.provider._make_request("GET", "/test")

    @patch("claudesync.providers.claude_ai.click.prompt")
    def test_login(self, mock_prompt):
        mock_prompt.return_value = "new_session_key"

        result = self.provider.login()

        self.assertEqual(result, "new_session_key")
        self.assertEqual(self.provider.session_key, "new_session_key")

    @patch("claudesync.providers.claude_ai.ClaudeAIProvider._make_request")
    def test_get_organizations(self, mock_make_request):
        mock_make_request.return_value = [
            {"uuid": "org1", "name": "Org 1"},
            {"uuid": "org2", "name": "Org 2"},
        ]

        result = self.provider.get_organizations()

        expected = [{"id": "org1", "name": "Org 1"}, {"id": "org2", "name": "Org 2"}]
        self.assertEqual(result, expected)

    @patch("claudesync.providers.claude_ai.ClaudeAIProvider._make_request")
    def test_get_projects(self, mock_make_request):
        mock_make_request.return_value = [
            {"uuid": "proj1", "name": "Project 1", "archived_at": None},
            {"uuid": "proj2", "name": "Project 2", "archived_at": "2023-01-01"},
        ]

        result = self.provider.get_projects("org1", include_archived=True)

        expected = [
            {"id": "proj1", "name": "Project 1", "archived_at": None},
            {"id": "proj2", "name": "Project 2", "archived_at": "2023-01-01"},
        ]
        self.assertEqual(result, expected)

    @patch("claudesync.providers.claude_ai.ClaudeAIProvider._make_request")
    def test_list_files(self, mock_make_request):
        mock_make_request.return_value = [
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

    @patch("claudesync.providers.claude_ai.ClaudeAIProvider._make_request")
    def test_upload_file(self, mock_make_request):
        mock_make_request.return_value = {"uuid": "new_file", "file_name": "test.txt"}

        result = self.provider.upload_file("org1", "proj1", "test.txt", "content")

        self.assertEqual(result, {"uuid": "new_file", "file_name": "test.txt"})
        mock_make_request.assert_called_once_with(
            "POST",
            "/organizations/org1/projects/proj1/docs",
            json={"file_name": "test.txt", "content": "content"},
        )

    @patch("claudesync.providers.claude_ai.ClaudeAIProvider._make_request")
    def test_delete_file(self, mock_make_request):
        mock_make_request.return_value = {"status": "deleted"}

        result = self.provider.delete_file("org1", "proj1", "file1")

        self.assertEqual(result, {"status": "deleted"})
        mock_make_request.assert_called_once_with(
            "DELETE", "/organizations/org1/projects/proj1/docs/file1"
        )

    @patch("claudesync.providers.claude_ai.ClaudeAIProvider._make_request")
    def test_archive_project(self, mock_make_request):
        mock_make_request.return_value = {"uuid": "proj1", "is_archived": True}

        result = self.provider.archive_project("org1", "proj1")

        self.assertEqual(result, {"uuid": "proj1", "is_archived": True})
        mock_make_request.assert_called_once_with(
            "PUT", "/organizations/org1/projects/proj1", json={"is_archived": True}
        )

    @patch("claudesync.providers.claude_ai.ClaudeAIProvider._make_request")
    def test_create_project(self, mock_make_request):
        mock_make_request.return_value = {"uuid": "new_proj", "name": "New Project"}

        result = self.provider.create_project("org1", "New Project", "Description")

        self.assertEqual(result, {"uuid": "new_proj", "name": "New Project"})
        mock_make_request.assert_called_once_with(
            "POST",
            "/organizations/org1/projects",
            json={
                "name": "New Project",
                "description": "Description",
                "is_private": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
