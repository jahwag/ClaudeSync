import unittest
from unittest.mock import patch, MagicMock
from claudesync.providers.claude_ai import ClaudeAIProvider


class TestClaudeAIProvider(unittest.TestCase):
    def setUp(self):
        self.provider = ClaudeAIProvider("test_session_key")

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
                "file_name": "file1.txt",
                "content": "content1",
                "created_at": "2023-01-01",
            },
            {
                "uuid": "file2",
                "file_name": "file2.py",
                "content": "content2",
                "created_at": "2023-01-02",
            },
        ]
        mock_request.return_value = mock_response

        files = self.provider.list_files("org1", "proj1")

        self.assertEqual(len(files), 2)
        self.assertEqual(files[0]["uuid"], "file1")
        self.assertEqual(files[0]["file_name"], "file1.txt")
        self.assertEqual(files[0]["content"], "content1")
        self.assertEqual(files[0]["created_at"], "2023-01-01")
        self.assertEqual(files[1]["uuid"], "file2")
        self.assertEqual(files[1]["file_name"], "file2.py")
        self.assertEqual(files[1]["content"], "content2")
        self.assertEqual(files[1]["created_at"], "2023-01-02")

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_upload_file(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "uuid": "new_file",
            "file_name": "new_file.txt",
        }
        mock_request.return_value = mock_response

        result = self.provider.upload_file(
            "org1", "proj1", "new_file.txt", "file content"
        )

        self.assertEqual(result["uuid"], "new_file")
        self.assertEqual(result["file_name"], "new_file.txt")
        mock_request.assert_called_once_with(
            "POST",
            "https://claude.ai/api/organizations/org1/projects/proj1/docs",
            headers=unittest.mock.ANY,
            cookies={"sessionKey": "test_session_key"},
            json={"file_name": "new_file.txt", "content": "file content"},
        )

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_delete_file(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = None
        mock_request.return_value = mock_response

        self.provider.delete_file("org1", "proj1", "file1")

        mock_request.assert_called_once_with(
            "DELETE",
            "https://claude.ai/api/organizations/org1/projects/proj1/docs/file1",
            headers=unittest.mock.ANY,
            cookies={"sessionKey": "test_session_key"},
        )

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_create_project(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"uuid": "new_proj", "name": "New Project"}
        mock_request.return_value = mock_response

        result = self.provider.create_project(
            "org1", "New Project", "Project Description"
        )

        self.assertEqual(result["uuid"], "new_proj")
        self.assertEqual(result["name"], "New Project")
        mock_request.assert_called_once_with(
            "POST",
            "https://claude.ai/api/organizations/org1/projects",
            headers=unittest.mock.ANY,
            cookies={"sessionKey": "test_session_key"},
            json={
                "name": "New Project",
                "description": "Project Description",
                "is_private": True,
            },
        )

    @patch("claudesync.providers.claude_ai.requests.request")
    def test_archive_project(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "uuid": "proj1",
            "name": "Project 1",
            "is_archived": True,
        }
        mock_request.return_value = mock_response

        result = self.provider.archive_project("org1", "proj1")

        self.assertTrue(result["is_archived"])
        mock_request.assert_called_once_with(
            "PUT",
            "https://claude.ai/api/organizations/org1/projects/proj1",
            headers=unittest.mock.ANY,
            cookies={"sessionKey": "test_session_key"},
            json={"is_archived": True},
        )


if __name__ == "__main__":
    unittest.main()
