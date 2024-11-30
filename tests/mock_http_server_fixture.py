# tests/conftest.py
import pytest
import threading
import time
from http.server import HTTPServer
from mock_http_server import MockClaudeAIHandler


class MockServer:
    def __init__(self, port=8000):
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        if self.server is not None:
            return

        self.server = HTTPServer(("", self.port), MockClaudeAIHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        time.sleep(0.1)  # Brief pause to let server start

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=1)
            self.server = None
            self.thread = None


@pytest.fixture(scope="session")
def mock_server():
    server = MockServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture(autouse=True)
def use_mock_server(mock_server):
    """Automatically use the mock server for all tests."""
    pass
