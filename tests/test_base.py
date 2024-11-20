import unittest

from claudesync.configmanager.inmemory_config_manager import InMemoryConfigManager
from tests.mock_http_server import SharedMockServer


class BaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_server = SharedMockServer.get_instance()
        cls.mock_server.start()

    def setUp(self):
        self.config = InMemoryConfigManager()
        self.config.set("claude_api_url", "http://localhost:8000/api")
