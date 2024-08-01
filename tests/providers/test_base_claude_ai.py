import unittest
from unittest.mock import patch
from claudesync.providers.base_claude_ai import BaseClaudeAIProvider


class TestBaseClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = BaseClaudeAIProvider("test_session_key")

    @patch("click.prompt")
    def test_login(self, mock_prompt):
        mock_prompt.return_value = "new_session_key"
        result = self.provider.login()
        self.assertEqual(result, "new_session_key")
        self.assertEqual(self.provider.session_key, "new_session_key")

    @patch.object(BaseClaudeAIProvider, "_make_request")
    def test_get_organizations(self, mock_make_request):
        mock_make_request.return_value = [
            {"uuid": "org1", "name": "Org 1"},
            {"uuid": "org2", "name": "Org 2"},
        ]
        result = self.provider.get_organizations()
        expected = [{"id": "org1", "name": "Org 1"}, {"id": "org2", "name": "Org 2"}]
        self.assertEqual(result, expected)

    @patch.object(BaseClaudeAIProvider, "_make_request")
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

    @patch.object(BaseClaudeAIProvider, "_make_request")
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

    @patch.object(BaseClaudeAIProvider, "_make_request")
    def test_upload_file(self, mock_make_request):
        mock_make_request.return_value = {"uuid": "new_file", "file_name": "test.txt"}
        result = self.provider.upload_file("org1", "proj1", "test.txt", "content")
        self.assertEqual(result, {"uuid": "new_file", "file_name": "test.txt"})
        mock_make_request.assert_called_once_with(
            "POST",
            "/organizations/org1/projects/proj1/docs",
            {"file_name": "test.txt", "content": "content"},
        )

    @patch.object(BaseClaudeAIProvider, "_make_request")
    def test_delete_file(self, mock_make_request):
        mock_make_request.return_value = {"status": "deleted"}
        result = self.provider.delete_file("org1", "proj1", "file1")
        self.assertEqual(result, {"status": "deleted"})
        mock_make_request.assert_called_once_with(
            "DELETE", "/organizations/org1/projects/proj1/docs/file1"
        )

    def test_make_request_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.provider._make_request("GET", "/test")


if __name__ == "__main__":
    unittest.main()
