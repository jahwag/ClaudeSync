import unittest
from unittest.mock import patch

from claudesync.exceptions import ProviderError
from claudesync.providers.base_claude_ai import BaseClaudeAIProvider


class TestBaseClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = BaseClaudeAIProvider("test_session_key")

    @patch("click.prompt")
    @patch.object(BaseClaudeAIProvider, "get_organizations")
    def test_login(self, mock_get_organizations, mock_prompt):
        # Test successful login on first attempt
        mock_prompt.return_value = "sk-ant-valid_session_key"
        mock_get_organizations.return_value = [{"id": "org1", "name": "Org 1"}]

        result = self.provider.login()

        self.assertEqual(result, "sk-ant-valid_session_key")
        self.assertEqual(self.provider.session_key, "sk-ant-valid_session_key")
        mock_prompt.assert_called_once()
        mock_get_organizations.assert_called_once()

        # Reset mocks for next test
        mock_prompt.reset_mock()
        mock_get_organizations.reset_mock()

        # Test invalid session key followed by valid session key
        mock_prompt.side_effect = ["invalid_key", "sk-ant-valid_session_key"]
        mock_get_organizations.side_effect = [
            ProviderError("Invalid session key"),
            [{"id": "org1", "name": "Org 1"}],
        ]

        result = self.provider.login()

        self.assertEqual(result, "sk-ant-valid_session_key")
        self.assertEqual(self.provider.session_key, "sk-ant-valid_session_key")
        self.assertEqual(mock_prompt.call_count, 2)
        self.assertEqual(mock_get_organizations.call_count, 2)

        # Reset mocks for next test
        mock_prompt.reset_mock()
        mock_get_organizations.reset_mock()

        # Test when get_organizations returns an empty list
        mock_prompt.return_value = "sk-ant-valid_session_key"
        mock_get_organizations.return_value = []

        result = self.provider.login()

        self.assertEqual(result, "sk-ant-valid_session_key")
        self.assertEqual(self.provider.session_key, "sk-ant-valid_session_key")
        mock_prompt.assert_called_once()
        mock_get_organizations.assert_called_once()

    @patch.object(BaseClaudeAIProvider, "_make_request")
    def test_get_organizations(self, mock_make_request):
        mock_make_request.return_value = [
            {"uuid": "org1", "name": "Org 1", "capabilities": ["chat", "claude_pro"]},
            {"uuid": "org2", "name": "Org 2", "capabilities": ["chat"]},
            {
                "uuid": "org3",
                "name": "Org 3",
                "capabilities": ["chat", "claude_pro", "other"],
            },
            {"uuid": "org4", "name": "Org 4", "capabilities": ["other"]},
        ]
        result = self.provider.get_organizations()
        expected = [{"id": "org1", "name": "Org 1"}, {"id": "org3", "name": "Org 3"}]
        self.assertEqual(result, expected)

    @patch.object(BaseClaudeAIProvider, "_make_request")
    def test_get_organizations_no_valid_orgs(self, mock_make_request):
        mock_make_request.return_value = [
            {"uuid": "org1", "name": "Org 1", "capabilities": ["api"]},
            {"uuid": "org2", "name": "Org 2", "capabilities": ["chat"]},
        ]
        result = self.provider.get_organizations()
        self.assertEqual(result, [])

    @patch.object(BaseClaudeAIProvider, "_make_request")
    def test_get_organizations_error(self, mock_make_request):
        mock_make_request.return_value = None
        with self.assertRaises(ProviderError):
            self.provider.get_organizations()

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
