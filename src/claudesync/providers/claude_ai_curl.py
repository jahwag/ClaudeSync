import io
import json
import subprocess
import tempfile
import os
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError
from ..config_manager import ConfigManager


class ClaudeAICurlProvider(BaseClaudeAIProvider):
    def __init__(self, session_key=None, session_key_expiry=None):
        super().__init__(session_key, session_key_expiry)
        self.config = ConfigManager()
        self.use_file_input = self.config.get("curl_use_file_input", False)

    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._prepare_headers()

        command = self._build_curl_command(method, url, headers, data)

        self.logger.debug(f"Executing command: {' '.join(command)}")

        try:
            result = subprocess.run(
                command, capture_output=True, text=True, check=True, encoding="utf-8"
            )

            if self.use_file_input and data:
                os.unlink(command[-1][1:])  # Remove the temporary file

            return self._process_result(result, headers)
        except subprocess.CalledProcessError as e:
            if self.use_file_input and data:
                os.unlink(command[-1][1:])  # Remove the temporary file
            self._handle_called_process_error(e, headers)
        except UnicodeDecodeError as e:
            if self.use_file_input and data:
                os.unlink(command[-1][1:])  # Remove the temporary file
            self._handle_unicode_decode_error(e, headers)

    def _prepare_headers(self):
        return [
            "-H",
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "-H",
            f"Cookie: sessionKey={self.session_key}",
            "-H",
            "Content-Type: application/json",
        ]

    def _write_data_to_temp_file(self, data):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            json.dump(data, temp_file)
            return temp_file.name

    def _build_curl_command(self, method, url, headers, data):
        command = ["curl", url, "--compressed", "-s", "-S", "-w", "%{http_code}"]
        command.extend(headers)

        if method != "GET":
            command.extend(["-X", method])

        if data:
            if self.use_file_input:
                temp_file_name = self._write_data_to_temp_file(data)
                command.extend(["--data", f"@{temp_file_name}"])
            else:
                json_data = json.dumps(data)
                command.extend(["-d", json_data])

        return command

    def _process_result(self, result, headers):
        if not result.stdout:
            raise ProviderError(
                f"Empty response from the server. Request headers: {headers}"
            )

        http_status_code = result.stdout[-3:]
        response_body = result.stdout[:-3].strip()
        self.logger.debug(f"Got HTTP {http_status_code}")

        if http_status_code.startswith("2"):
            if http_status_code == "204":
                # HTTP 204 No Content
                return None
            if not response_body:
                self.logger.warn(f"Got HTTP {http_status_code} but empty response")
                return None

            try:
                return json.loads(response_body)
            except json.JSONDecodeError as e:
                error_message = (
                    f"Failed to parse JSON response: {response_body}. Reason: {e}. Response content: {response_body}. Request "
                    f"headers: {headers}"
                )
                self.logger.error(error_message)
                raise ProviderError(error_message)
        else:
            error_message = (
                f"HTTP request failed with status code {http_status_code}. "
                f"Response content: {response_body}. Request headers: {headers}"
            )
            self.logger.error(error_message)
            raise ProviderError(error_message)

    def _handle_called_process_error(self, e, headers):
        if e.returncode == 1:
            error_message = (
                f"cURL command failed due to an unsupported protocol or a failed initialization. "
                f"Request headers: {headers}"
            )
        else:
            error_message = (
                f"cURL command failed with return code {e.returncode}. stdout: {e.stdout}, "
                f"stderr: {e.stderr}. Request headers: {headers}"
            )
        self.logger.error(error_message)
        raise ProviderError(error_message)

    def _handle_unicode_decode_error(self, e, headers):
        error_message = (
            f"Failed to decode cURL output: {e}. This might be due to non-UTF-8 characters in the "
            f"response. Request headers: {headers}"
        )
        self.logger.error(error_message)
        raise ProviderError(error_message)

    def _make_request_stream(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = [
            "-H",
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "-H",
            f"Cookie: sessionKey={self.session_key}",
            "-H",
            "Content-Type: application/json",
            "-H",
            "Accept: text/event-stream",
        ]

        command = ["curl", "-N", "-s", url, "-X", method] + headers
        if data:
            command.extend(["-d", json.dumps(data)])

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return io.TextIOWrapper(process.stdout)
