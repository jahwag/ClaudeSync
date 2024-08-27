import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import time


class MockClaudeAIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/api/organizations":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = json.dumps(
                [
                    {
                        "uuid": "org1",
                        "name": "Test Org 1",
                        "capabilities": ["chat", "claude_pro"],
                    },
                    {"uuid": "org2", "name": "Test Org 2", "capabilities": ["chat"]},
                ]
            )
            self.wfile.write(response.encode())
        elif parsed_path.path.startswith(
            "/api/organizations/"
        ) and parsed_path.path.endswith("/projects"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = json.dumps(
                [
                    {"uuid": "proj1", "name": "Test Project 1", "archived_at": None},
                    {
                        "uuid": "proj2",
                        "name": "Test Project 2",
                        "archived_at": "2023-01-01",
                    },
                ]
            )
            self.wfile.write(response.encode())
        elif parsed_path.path.startswith(
            "/api/organizations/"
        ) and parsed_path.path.endswith("/chat_conversations"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = json.dumps(
                [
                    {"uuid": "chat1", "name": "Test Chat 1"},
                    {"uuid": "chat2", "name": "Test Chat 2"},
                ]
            )
            self.wfile.write(response.encode())
        elif (
            parsed_path.path.startswith("/api/organizations/")
            and "/chat_conversations/" in parsed_path.path
        ):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = json.dumps(
                {
                    "uuid": "chat1",
                    "name": "Test Chat 1",
                    "messages": [
                        {"uuid": "msg1", "content": "Hello"},
                        {"uuid": "msg2", "content": "Hi there"},
                    ],
                }
            )
            self.wfile.write(response.encode())
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        parsed_path = urlparse(self.path)

        if parsed_path.path.startswith(
            "/api/organizations/"
        ) and parsed_path.path.endswith("/projects"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = json.dumps({"uuid": "new_proj", "name": "New Project"})
            self.wfile.write(response.encode())
        elif parsed_path.path.startswith(
            "/api/organizations/"
        ) and parsed_path.path.endswith("/completion"):
            self.send_response(200)
            self.send_header("Content-type", "text/event-stream")
            self.end_headers()

            # Simulate SSE response
            self.wfile.write(b'data: {"completion": "Hello"}\n\n')
            self.wfile.flush()
            time.sleep(0.1)
            self.wfile.write(b'data: {"completion": " there"}\n\n')
            self.wfile.flush()
            time.sleep(0.1)
            self.wfile.write(b"event: done\ndata: {}\n\n")
            self.wfile.flush()
        else:
            self.send_error(404, "Not Found")


def run_mock_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, MockClaudeAIHandler)
    print(f"Mock server running on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_mock_server()
