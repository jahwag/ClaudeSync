import json
import subprocess
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError


class ClaudeAICurlProvider(BaseClaudeAIProvider):
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = [
            "-H",
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "-H",
            f"Cookie: sessionKey={self.session_key};",
            "-H",
            "Content-Type: application/json",
        ]

        command = [
            "curl",
            url,
            "--compressed",
            "-s",
            "-S",
        ]
        command.extend(headers)

        if method != "GET":
            command.extend(["-X", method])

        if data:
            json_data = json.dumps(data)
            command.extend(["-d", json_data])

        try:
            result = subprocess.run(
                command, capture_output=True, text=True, check=True, encoding="utf-8"
            )

            if not result.stdout:
                return None

            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise ProviderError(
                    f"Failed to parse JSON response: {e}. Response content: {result.stdout}"
                )

        except subprocess.CalledProcessError as e:
            error_message = f"cURL command failed with return code {e.returncode}. "
            error_message += f"stdout: {e.stdout}, stderr: {e.stderr}"
            raise ProviderError(error_message)
        except UnicodeDecodeError as e:
            error_message = f"Failed to decode cURL output: {e}. "
            error_message += (
                "This might be due to non-UTF-8 characters in the response."
            )
            raise ProviderError(error_message)
