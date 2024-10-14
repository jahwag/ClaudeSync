import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class MockClaudeAIHandler(BaseHTTPRequestHandler):
    files = {}  # Store files in memory

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path.endswith("/chat_conversations"):
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
        elif "/chat_conversations/" in parsed_path.path:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = json.dumps(
                {
                    "uuid": "chat1",
                    "name": "Test Chat 1",
                    "messages": [
                        {"uuid": "msg1", "content": "Hello"},
                        {"uuid": "msg2", "content": "World"},
                    ],
                }
            )
            self.wfile.write(response.encode())
        else:
            print(f"Received GET request: {self.path}")
            # time.sleep(0.01)  # Add a small delay to simulate network latency
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
                        {
                            "uuid": "org2",
                            "name": "Test Org 2",
                            "capabilities": ["chat"],
                        },
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
                        {
                            "uuid": "proj1",
                            "name": "Test Project 1",
                            "archived_at": None,
                        },
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
            ) and parsed_path.path.endswith("/docs"):
                org_id, project_id = (
                    parsed_path.path.split("/")[-3],
                    parsed_path.path.split("/")[-2],
                )
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                files = self.files.get(f"{org_id}/{project_id}", [])
                response = json.dumps(files)
                self.wfile.write(response.encode())
            else:
                self.send_error(404, "Not Found")

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        parsed_path = urlparse(self.path)

        if parsed_path.path.endswith("/chat_conversations"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = json.dumps({"uuid": "new_chat", "name": "New Chat"})
            self.wfile.write(response.encode())
        elif parsed_path.path.endswith('/upload'):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = json.dumps({'file_id': 'uploaded_image_1'})
            self.wfile.write(response.encode())
        elif parsed_path.path.endswith("/completion"):
            self.send_response(200)
            self.send_header("Content-type", "text/event-stream")
            self.end_headers()
            self.wfile.write(b'data: {"completion": "Hello"}\n\n')
            self.wfile.write(b'data: {"completion": " there. "}\n\n')
            self.wfile.write(
                b'data: {"completion": "I apologize for the confusion. You\'re right."}\n\n'
            )
            self.wfile.write(b"event: done\n\n")
            if 'files' in data and data['files']:
                self.wfile.write(b'data: {"completion": "Analyzing image..."}\n\n')
                self.wfile.write(b'data: {"completion": "The image shows a cat."}\n\n')
        else:
            # time.sleep(0.01)  # Add a small delay to simulate network latency
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
            ) and parsed_path.path.endswith("/docs"):
                org_id, project_id = (
                    parsed_path.path.split("/")[-3],
                    parsed_path.path.split("/")[-2],
                )
                data = json.loads(post_data.decode("utf-8"))
                file_data = {
                    "uuid": f"file_{len(self.files.get(f'{org_id}/{project_id}', []))}",
                    "file_name": data["file_name"],
                    "content": data["content"],
                    "created_at": "2023-01-01T00:00:00Z",
                }
                if f"{org_id}/{project_id}" not in self.files:
                    self.files[f"{org_id}/{project_id}"] = []
                self.files[f"{org_id}/{project_id}"].append(file_data)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(file_data).encode())
            else:
                self.send_error(404, "Not Found")

    def do_DELETE(self):
        # time.sleep(0.01)  # Add a small delay to simulate network latency
        parsed_path = urlparse(self.path)
        if (
            parsed_path.path.startswith("/api/organizations/")
            and "/docs/" in parsed_path.path
        ):
            org_id, project_id, file_uuid = (
                parsed_path.path.split("/")[-4],
                parsed_path.path.split("/")[-3],
                parsed_path.path.split("/")[-1],
            )
            if f"{org_id}/{project_id}" in self.files:
                self.files[f"{org_id}/{project_id}"] = [
                    f
                    for f in self.files[f"{org_id}/{project_id}"]
                    if f["uuid"] != file_uuid
                ]
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404, "Not Found")


def run_mock_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, MockClaudeAIHandler)
    print(f"Mock server running on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_mock_server()
