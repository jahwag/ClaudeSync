import urllib.request
import urllib.error
import urllib.parse
import json
import gzip
from datetime import datetime, timezone
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError


class ClaudeAIProvider(BaseClaudeAIProvider):
    def __init__(self, config=None):
        super().__init__(config)

    def _make_request_internal(  # noqa: C901
        self, method, endpoint, data, base_url, extra_headers=None
    ):
        """Internal method to make HTTP requests with specified base URL."""
        url = f"{base_url}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }

        if extra_headers:
            headers.update(extra_headers)

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

    def _make_request(self, method, endpoint, data=None):
        return self._make_request_internal(method, endpoint, data, self.base_url)

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

    def _make_request_v1(self, method, endpoint, data=None, organization_id=None):
        """Make a request to the v1 API (not under /api prefix)."""
        # For v1 endpoints, we use the root URL without the /api prefix
        base_url = self.base_url.replace("/api", "")

        # Add required Anthropic headers for v1 API
        extra_headers = {
            "anthropic-version": "2023-06-01",
        }

        # Add organization header if provided
        if organization_id:
            extra_headers["x-organization-uuid"] = organization_id

        return self._make_request_internal(
            method, endpoint, data, base_url, extra_headers
        )

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

    def _make_request_stream_v1(self, method, endpoint, organization_id=None):
        """Make a streaming request to the v1 API."""
        # For v1 endpoints, use root URL without /api prefix
        base_url = self.base_url.replace("/api", "")
        url = f"{base_url}{endpoint}"

        session_key, _ = self.config.get_session_key("claude.ai")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "Accept": "text/event-stream",
            "anthropic-version": "2023-06-01",
            "Cookie": f"sessionKey={session_key}",
        }

        # Add organization header if provided
        if organization_id:
            headers["x-organization-uuid"] = organization_id

        req = urllib.request.Request(url, method=method, headers=headers)

        try:
            return urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            self.handle_http_error(e)
        except urllib.error.URLError as e:
            raise ProviderError(f"API request failed: {str(e)}")
