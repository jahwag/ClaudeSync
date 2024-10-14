import unittest
import threading
import time
from io import BytesIO
from unittest.mock import patch, mock_open
from datetime import datetime

from claudesync.configmanager import InMemoryConfigManager
from claudesync.providers.claude_ai import ClaudeAIProvider
from claudesync.exceptions import ProviderError
from mock_http_server import run_mock_server


class TestClaudeAIProvider(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_server_thread = threading.Thread(target=run_mock_server)
        cls.mock_server_thread.daemon = True
        cls.mock_server_thread.start()
        time.sleep(1)

    def setUp(self):
        self.config = InMemoryConfigManager()
        self.config.set("claude_api_url", "http://127.0.0.1:8000/api")
        self.provider = ClaudeAIProvider(self.config)

    def test_get_organizations(self):
        organizations = self.provider.get_organizations()
        self.assertEqual(len(organizations), 1)
        self.assertEqual(organizations[0]["id"], "org1")
        self.assertEqual(organizations[0]["name"], "Test Org 1")

    def test_get_projects(self):
        projects = self.provider.get_projects("org1")
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["id"], "proj1")
        self.assertEqual(projects[0]["name"], "Test Project 1")

    def test_create_project(self):
        new_project = self.provider.create_project(
            "org1", "New Project", "Test description"
        )
        self.assertEqual(new_project["uuid"], "new_proj")
        self.assertEqual(new_project["name"], "New Project")

    def test_login(self):
        expiry_str = "Thu, 26 Sep 2099 17:07:53 UTC"

        with patch("click.prompt", side_effect=["sk-ant-test123", expiry_str]):
            with patch.object(
                self.provider,
                "get_organizations",
                return_value=[{"id": "org1", "name": "Test Org"}],
            ):
                session_key, returned_expiry = self.provider.login()

        self.assertEqual("sk-ant-test123", session_key)
        self.assertIsInstance(returned_expiry, datetime)

    def test_list_files(self):
        with patch.object(
            self.provider,
            "_make_request",
            return_value=[
                {
                    "uuid": "file1",
                    "file_name": "test.txt",
                    "content": "Hello",
                    "created_at": "2023-01-01T00:00:00Z",
                }
            ],
        ):
            files = self.provider.list_files("org1", "proj1")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["uuid"], "file1")
        self.assertEqual(files[0]["file_name"], "test.txt")

    def test_upload_file(self):
        with patch.object(
            self.provider, "_make_request", return_value={"uuid": "file1"}
        ):
            result = self.provider.upload_file("org1", "proj1", "test.txt", "Hello")
        self.assertEqual(result["uuid"], "file1")

    def test_delete_file(self):
        with patch.object(self.provider, "_make_request", return_value=None):
            result = self.provider.delete_file("org1", "proj1", "file1")
        self.assertIsNone(result)

    def test_archive_project(self):
        with patch.object(
            self.provider, "_make_request", return_value={"is_archived": True}
        ):
            result = self.provider.archive_project("org1", "proj1")
        self.assertTrue(result["is_archived"])

    def test_get_published_artifacts(self):
        with patch.object(
            self.provider,
            "_make_request",
            return_value=[{"id": "artifact1", "name": "Test Artifact"}],
        ):
            artifacts = self.provider.get_published_artifacts("org1")
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0]["id"], "artifact1")

    def test_get_artifact_content(self):
        with patch.object(
            self.provider,
            "_make_request",
            return_value=[
                {
                    "published_artifact_uuid": "artifact1",
                    "artifact_content": "Test content",
                }
            ],
        ):
            content = self.provider.get_artifact_content("org1", "artifact1")
        self.assertEqual(content, "Test content")

    def test_delete_chat(self):
        with patch.object(
            self.provider, "_make_request", return_value={"deleted": ["chat1"]}
        ):
            result = self.provider.delete_chat("org1", ["chat1"])
        self.assertEqual(result["deleted"], ["chat1"])

    def test_create_chat(self):
        with patch.object(
            self.provider,
            "_make_request",
            return_value={"uuid": "chat1", "name": "New Chat"},
        ):
            chat = self.provider.create_chat("org1", "New Chat", "proj1")
        self.assertEqual(chat["uuid"], "chat1")
        self.assertEqual(chat["name"], "New Chat")

    def test_get_chat_conversations(self):
        chats = self.provider.get_chat_conversations("org1")
        self.assertEqual(len(chats), 2)
        self.assertEqual(chats[0]["uuid"], "chat1")
        self.assertEqual(chats[0]["name"], "Test Chat 1")

    def test_get_chat_conversation(self):
        chat = self.provider.get_chat_conversation("org1", "chat1")
        self.assertEqual(chat["uuid"], "chat1")
        self.assertEqual(len(chat["messages"]), 2)

    def test_send_message(self):
        messages = list(self.provider.send_message("org1", "chat1", "Hello"))
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["completion"], "Hello")
        self.assertEqual(messages[1]["completion"], " there. ")

    def test_handle_http_error_403(self):
        # This test still needs to use a mock as we can't easily trigger a 403 from our mock server
        mock_error = unittest.mock.MagicMock(code=403, headers={})
        mock_error.read.return_value = b'{"error": "Forbidden"}'
        with self.assertRaises(ProviderError) as context:
            self.provider.handle_http_error(mock_error)
        self.assertIn("403 Forbidden error", str(context.exception))


    def test_upload_image(self):
        mock_file_content = b'fake image data'
        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            with patch('mimetypes.guess_type', return_value=('image/jpeg', None)):
                result = self.provider.upload_image('org1', 'test.jpg')
        self.assertEqual(result['file_id'], 'uploaded_image_1')

    def test_send_message_with_image(self):
        mock_response = BytesIO(
            b'data: {"completion": "Analyzing image..."}\n\n'
            b'data: {"completion": "The image shows a cat."}\n\n'
            b'event: done\n\n'
        )
        with patch.object(self.provider, '_make_request_stream', return_value=mock_response):
            messages = list(self.provider.send_message('org1', 'chat1', 'Describe this image', files=[{'file_id': 'image1'}]))
        
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]['completion'], 'Analyzing image...')
        self.assertEqual(messages[1]['completion'], 'The image shows a cat.')


if __name__ == "__main__":
    unittest.main()
