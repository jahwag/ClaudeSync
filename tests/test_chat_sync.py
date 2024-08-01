import textwrap
import unittest
from unittest.mock import MagicMock

from claudesync.chat_sync import extract_artifacts, get_file_extension, sync_chats
from claudesync.exceptions import ConfigurationError


class TestExtractArtifacts(unittest.TestCase):

    def setUp(self):
        self.mock_provider = MagicMock()
        self.mock_config = MagicMock()
        self.mock_config.get.side_effect = lambda key, default=None: {
            "local_path": "/test/path",
            "active_organization_id": "org123",
            "active_project_id": "proj456",
        }.get(key, default)

    def test_extract_single_artifact(self):
        text = """
        Here is some introductory text.
        <antArtifact identifier="test-id" type="text/html" title="Test Title">
        <html>
        <head><title>Test</title></head>
        <body>Test Content</body>
        </html>
        </antArtifact>
        Some concluding text.
        """
        expected_result = [
            {
                "identifier": "test-id",
                "type": "text/html",
                "content": "<html>\n<head><title>Test</title></head>\n<body>Test Content</body>\n</html>",
            }
        ]
        self.assertEqual(extract_artifacts(textwrap.dedent(text)), expected_result)

    def test_extract_multiple_artifacts(self):
        text = """
        Here is some introductory text.
        <antArtifact identifier="first-id" type="text/plain" title="First Title">
        First artifact content.
        </antArtifact>
        Some middle text.
        <antArtifact identifier="second-id" type="text/xml" title="Second Title">
        <note>
        <to>User</to>
        <from>ChatGPT</from>
        <heading>Reminder</heading>
        <body>Don't forget to check your email!</body>
        </note>
        </antArtifact>
        Some concluding text.
        """
        expected_result = [
            {
                "identifier": "first-id",
                "type": "text/plain",
                "content": "First artifact content.",
            },
            {
                "identifier": "second-id",
                "type": "text/xml",
                "content": "<note>\n<to>User</to>\n<from>ChatGPT</from>"
                "\n<heading>Reminder</heading>\n<body>Don't forget to check your email!</body>\n</note>",
            },
        ]
        self.assertEqual(extract_artifacts(textwrap.dedent(text)), expected_result)

    def test_no_artifacts(self):
        text = """
        Here is some text without any artifacts.
        """
        expected_result = []
        self.assertEqual(extract_artifacts(text), expected_result)

    def test_sync_chats_no_local_path(self):
        self.mock_config.get.side_effect = lambda key, default=None: (
            None if key == "local_path" else "some_value"
        )
        with self.assertRaises(ConfigurationError):
            sync_chats(self.mock_provider, self.mock_config)

    def test_sync_chats_no_organization(self):
        self.mock_config.get.side_effect = lambda key, default=None: (
            None if key == "active_organization_id" else "some_value"
        )
        with self.assertRaises(ConfigurationError):
            sync_chats(self.mock_provider, self.mock_config)

    def test_get_file_extension(self):
        self.assertEqual(get_file_extension("text/html"), "html")
        self.assertEqual(get_file_extension("application/vnd.ant.code"), "txt")
        self.assertEqual(get_file_extension("image/svg+xml"), "svg")
        self.assertEqual(get_file_extension("application/vnd.ant.mermaid"), "mmd")
        self.assertEqual(get_file_extension("application/vnd.ant.react"), "jsx")
        self.assertEqual(get_file_extension("unknown/type"), "txt")
