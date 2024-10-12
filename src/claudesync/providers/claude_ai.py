import urllib.request
import urllib.error
import urllib.parse
import json
import gzip
import os
import mimetypes
import random
import string
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
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
            

    def generate_boundary(self):
        prefix = 'WebKitFormBoundary'
        random_sequence = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        return prefix + random_sequence

    def upload_image(self, organization_id, file_path):

        self.logger.debug(f"Uploading image: {file_path}")
        url = f"{self.base_url}/{organization_id}/upload"
        
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        file_name = os.path.basename(file_path)
        content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        
        boundary = self.generate_boundary()
        data = self._encode_multipart_formdata(file_data, file_name, content_type, boundary)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en;q=0.9',
            'anthropic-client-sha': 'unknown',
            'anthropic-client-version': 'unknown',
            'origin': 'https://claude.ai',
            'referer': 'https://claude.ai/',
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Cookie': f'sessionKey={self.config.get_session_key("claude.ai")[0]}'
        }

        try:
            req = Request(url, data=data, headers=headers, method='POST')
            response = urlopen(req)

            content = response.read()
            content_str = content.decode("utf-8")

            if not content:
                return None
            return json.loads(content_str)
        except urllib.error.HTTPError as e:
            self.handle_http_error(e)
        except urllib.error.URLError as e:
            self.logger.error(f"URL Error: {str(e)}")
            raise ProviderError(f"API request failed: {str(e)}")

    def _encode_multipart_formdata(self, file_data, file_name, content_type, boundary):
        lines = [
            f'--{boundary}',
            f'Content-Disposition: form-data; name="file"; filename="{file_name}"',
            f'Content-Type: {content_type}',
            '',
            file_data,
            f'--{boundary}--',
            ''
        ]
        body = b'\r\n'.join(line.encode() if isinstance(line, str) else line for line in lines)
        return body


        



