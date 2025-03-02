import urllib.request
import urllib.error
import urllib.parse
import json
import gzip
from datetime import datetime, timezone
import os
import sseclient
import mimetypes
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError


class ClaudeAIProvider(BaseClaudeAIProvider):
    def __init__(self, config=None):
        super().__init__(config)

    def _make_request(self, method, endpoint, data=None):
        url = f"{self.base_url}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }

        session_key, expiry = self.config.get_session_key("claude.ai")
        cookies = {
            "sessionKey": session_key,
        }

        try:
            self.logger.debug(f"Making {method} request to {url}")
            self.logger.debug(f"Headers: {headers}")
            self.logger.debug(f"Cookies: {cookies}")
            if data:
                self.logger.debug(f"Request data: {data}")

            # Prepare the request
            req = urllib.request.Request(url, method=method)
            for key, value in headers.items():
                req.add_header(key, value)

            # Add cookies
            cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            req.add_header("Cookie", cookie_string)

            # Add data if present
            if data:
                json_data = json.dumps(data).encode("utf-8")
                req.data = json_data

            # Make the request
            with urllib.request.urlopen(req) as response:
                self.logger.debug(f"Response status code: {response.status}")
                self.logger.debug(f"Response headers: {response.headers}")

                # Handle gzip encoding
                if response.headers.get("Content-Encoding") == "gzip":
                    content = gzip.decompress(response.read())
                else:
                    content = response.read()

                content_str = content.decode("utf-8")
                self.logger.debug(f"Response content: {content_str[:1000]}...")

                if not content:
                    return None

                return json.loads(content_str)

        except urllib.error.HTTPError as e:
            self.handle_http_error(e)
        except urllib.error.URLError as e:
            self.logger.error(f"URL Error: {str(e)}")
            raise ProviderError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
            self.logger.error(f"Response content: {content_str}")
            raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")

    def _make_multipart_request(self, url, file_data, file_name):
        """
        Make a multipart form-data request for file upload
        Args:
            url: URL to upload to
            file_data: Raw file data as bytes
            file_name: Name of the file being uploaded
        Returns:
            dict: Response from the server
        """
        # Initialize mimetypes if not already done
        if not mimetypes.inited:
            mimetypes.init()
            
        # Determine content type from file extension, default to application/octet-stream
        content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
        boundary = "----WebKitFormBoundaryuB2M6eYE1M5pTCkx"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "anthropic-client-platform": "web_claude_ai",
            "anthropic-client-sha": "unknown",
            "anthropic-client-version": "unknown"
        }

        session_key, _ = self.config.get_session_key("claude.ai")
        headers["Cookie"] = f"sessionKey={session_key}"

        # Prepare multipart form data
        body = bytearray()
        
        # Add file part headers
        body.extend(f"--{boundary}\r\n".encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'.encode('utf-8'))
        body.extend(f"Content-Type: {content_type}\r\n".encode('utf-8'))
        body.extend(b"\r\n")
        
        # Add raw file data
        body.extend(file_data)
        
        # Add closing boundary
        body.extend(f"\r\n--{boundary}--\r\n".encode('utf-8'))

        # Create request
        req = urllib.request.Request(url, method="POST")
        for key, value in headers.items():
            req.add_header(key, value)

        req.data = body

        try:
            with urllib.request.urlopen(req) as response:
                content = response.read()
                return json.loads(content.decode("utf-8"))
        except urllib.error.HTTPError as e:
            self.handle_http_error(e)
        except urllib.error.URLError as e:
            raise ProviderError(f"API request failed: {str(e)}")

    def upload_file(self, organization_id: str, project_id: str, file_name: str, content: str) -> dict:
        """Keep original upload_file method from base class"""
        return super().upload_file(organization_id, project_id, file_name, content)

    def upload_attachment(self, organization_id: str, file_path: str) -> dict:
        """
        Upload a file as an attachment to Claude.ai using multipart/form-data
        Args:
            organization_id: Organization ID to upload to
            file_path: Path to the file to upload
        Returns:
            dict: Response containing file_uuid and other metadata
        """
        url = f"{self.base_url}/{organization_id}/upload"
        
        # Read file in binary mode
        with open(file_path, 'rb') as f:
            file_data = f.read()

        file_name = os.path.basename(file_path)
        return self._make_multipart_request(url, file_data, file_name)

    def handle_http_error(self, e):
        self.logger.debug(f"Request failed: {str(e)}")
        self.logger.debug(f"Response status code: {e.code}")
        self.logger.debug(f"Response headers: {e.headers}")

        try:
            # Check if the content is gzip-encoded
            if e.headers.get("Content-Encoding") == "gzip":
                content = gzip.decompress(e.read())
            else:
                content = e.read()

            # Try to decode the content as UTF-8
            content_str = content.decode("utf-8")
        except UnicodeDecodeError:
            # If UTF-8 decoding fails, try to decode as ISO-8859-1
            content_str = content.decode("iso-8859-1")

        self.logger.debug(f"Response content: {content_str}")

        if e.code == 403:
            error_msg = "Received a 403 Forbidden error."
            raise ProviderError(error_msg)
        elif e.code == 429:
            try:
                error_data = json.loads(content_str)
                resets_at_unix = json.loads(error_data["error"]["message"])["resetsAt"]
                resets_at_local = datetime.fromtimestamp(
                    resets_at_unix, tz=timezone.utc
                ).astimezone()
                formatted_time = resets_at_local.strftime("%a %b %d %Y %H:%M:%S %Z%z")
                error_msg = f"Message limit exceeded. Try again after {formatted_time}"
            except (KeyError, json.JSONDecodeError) as parse_error:
                error_msg = f"HTTP 429: Too Many Requests. Failed to parse error response: {parse_error}"
            self.logger.error(error_msg)
            raise ProviderError(error_msg)
        else:
            error_msg = f"API request failed with status code {e.code}: {content_str}"
            self.logger.error(error_msg)
            raise ProviderError(error_msg)

    def send_message_with_attachment(
        self, organization_id: str, chat_id: str, prompt: str, file_path: str, timezone: str = "UTC"
    ):
        """
        Upload a file and send a message with the attachment
        Args:
            organization_id: Organization ID
            chat_id: Chat ID to send message to
            prompt: Message text
            file_path: Path to file to attach
            timezone: Optional timezone (default UTC)
        Returns:
            Generator yielding message events
        """
        # First upload the file
        attachment = self.upload_attachment(organization_id, file_path)
        
        # Get the file UUID
        file_uuid = attachment.get('file_uuid')
        if not file_uuid:
            raise ProviderError("Failed to get file UUID from upload response")

        # Send message with attachment
        endpoint = f"/organizations/{organization_id}/chat_conversations/{chat_id}/completion"
        data = {
            "prompt": prompt,
            "timezone": timezone,
            "attachments": [],
            "files": [file_uuid]
        }

        response = self._make_request_stream("POST", endpoint, data)
        client = sseclient.SSEClient(response)
        for event in client.events():
            if event.data:
                try:
                    yield json.loads(event.data)
                except json.JSONDecodeError:
                    yield {"error": "Failed to parse JSON"}
            if event.event == "error":
                yield {"error": event.data}
            if event.event == "done":
                break

    def _make_request_stream(self, method, endpoint, data=None):
        url = f"{self.base_url}{endpoint}"
        session_key, _ = self.config.get_session_key("claude.ai")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cookie": f"sessionKey={session_key}",
        }

        req = urllib.request.Request(url, method=method, headers=headers)
        if data:
            req.data = json.dumps(data).encode("utf-8")

        try:
            return urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            self.handle_http_error(e)
        except urllib.error.URLError as e:
            raise ProviderError(f"API request failed: {str(e)}")
