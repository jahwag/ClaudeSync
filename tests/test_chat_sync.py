import textwrap
import unittest

from claudesync.chat_sync import extract_artifacts


class TestExtractArtifacts(unittest.TestCase):

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
