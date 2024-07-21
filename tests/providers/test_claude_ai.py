import unittest
from unittest.mock import patch, MagicMock
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError


class TestClaudeAIProvider(unittest.TestCase):

    def setUp(self):
        self.provider = ClaudeAIProvider()

    @patch("claudesync.providers.claude_ai.click.prompt")
    def test_login(self, mock_prompt):
        mock_prompt.return_value = "test_session_key"
        session_key = self.provider.login()
        self.assertEqual(session_key, "test_session_key")

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_get_organizations(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "uuid": "org1",
                "name": "Organization 1",
                "settings": {},
                "capabilities": [],
                "rate_limit_tier": "",
                "billing_type": "",
                "created_at": "",
                "updated_at": "",
            },
            {
                "uuid": "org2",
                "name": "Organization 2",
                "settings": {},
                "capabilities": [],
                "rate_limit_tier": "",
                "billing_type": "",
                "created_at": "",
                "updated_at": "",
            },
        ]
        mock_request.return_value = mock_response

        organizations = self.provider.get_organizations()
        self.assertEqual(len(organizations), 2)
        self.assertEqual(organizations[0]["id"], "org1")
        self.assertEqual(organizations[0]["name"], "Organization 1")
        self.assertEqual(organizations[1]["id"], "org2")
        self.assertEqual(organizations[1]["name"], "Organization 2")

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_get_projects(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"uuid": "proj1", "name": "Project 1", "archived_at": None},
            {"uuid": "proj2", "name": "Project 2", "archived_at": "2023-01-01"},
        ]
        mock_request.return_value = mock_response

        projects = self.provider.get_projects("org1", include_archived=True)
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0]["id"], "proj1")
        self.assertEqual(projects[0]["name"], "Project 1")
        self.assertIsNone(projects[0]["archived_at"])
        self.assertEqual(projects[1]["id"], "proj2")
        self.assertEqual(projects[1]["name"], "Project 2")
        self.assertEqual(projects[1]["archived_at"], "2023-01-01")

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_list_files(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "uuid": "file1",
                "file_name": "test1.txt",
                "content": "Hello",
                "created_at": "2023-01-01",
            },
            {
                "uuid": "file2",
                "file_name": "test2.txt",
                "content": "World",
                "created_at": "2023-01-02",
            },
        ]
        mock_request.return_value = mock_response

        files = self.provider.list_files("org1", "proj1")
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0]["uuid"], "file1")
        self.assertEqual(files[0]["file_name"], "test1.txt")
        self.assertEqual(files[0]["content"], "Hello")
        self.assertEqual(files[0]["created_at"], "2023-01-01")

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_upload_file(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"uuid": "new_file"}
        mock_request.return_value = mock_response

        result = self.provider.upload_file(
            "org1", "proj1", "new_file.txt", "New content"
        )
        self.assertEqual(result["uuid"], "new_file")

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_delete_file(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        result = self.provider.delete_file("org1", "proj1", "file1")
        mock_request.assert_called_once_with(
            "DELETE",
            f"{self.provider.BASE_URL}/organizations/org1/projects/proj1/docs/file1",
            headers=unittest.mock.ANY,
            cookies=unittest.mock.ANY,
        )

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_archive_project(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"is_archived": True}
        mock_request.return_value = mock_response

        result = self.provider.archive_project("org1", "proj1")
        self.assertTrue(result["is_archived"])

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_create_project(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"uuid": "new_proj", "name": "New Project"}
        mock_request.return_value = mock_response

        result = self.provider.create_project("org1", "New Project", "Description")
        self.assertEqual(result["uuid"], "new_proj")
        self.assertEqual(result["name"], "New Project")


if __name__ == "__main__":
    unittest.main()
