import json
import requests
from .base_claude_ai import BaseClaudeAIProvider
from ..exceptions import ProviderError


class ClaudeAIProvider(BaseClaudeAIProvider):
    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Origin": "https://claude.ai",
            "Referer": "https://claude.ai/projects",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "anthropic-client-sha": "unknown",
            "anthropic-client-version": "unknown",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        cookies = {
            "sessionKey": self.session_key,
            "CH-prefers-color-scheme": "dark",
            "anthropic-consent-preferences": '{"analytics":true,"marketing":true}',
        }

        try:
            self.logger.debug(f"Making {method} request to {url}")
            self.logger.debug(f"Headers: {headers}")
            self.logger.debug(f"Cookies: {cookies}")
            if data:
                self.logger.debug(f"Request data: {data}")

            response = requests.request(
                method, url, headers=headers, cookies=cookies, json=data
            )

            self.logger.debug(f"Response status code: {response.status_code}")
            self.logger.debug(f"Response headers: {response.headers}")
            self.logger.debug(f"Response content: {response.text[:1000]}...")

            if response.status_code == 403:
                error_msg = (
                    "Received a 403 Forbidden error. Your session key might be invalid. "
                    "Please try logging out and logging in again. If the issue persists, "
                    "you can try using the claude.ai-curl provider as a workaround:\n"
                    "claudesync api logout\n"
                    "claudesync api login claude.ai-curl"
                )
                self.logger.error(error_msg)
                raise ProviderError(error_msg)

            response.raise_for_status()

            if not response.content:
                return None

            return response.json()

        except requests.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                self.logger.error(f"Response status code: {e.response.status_code}")
                self.logger.error(f"Response headers: {e.response.headers}")
                self.logger.error(f"Response content: {e.response.text}")
            raise ProviderError(f"API request failed: {str(e)}")
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Failed to parse JSON response: {str(json_err)}")
            self.logger.error(f"Response content: {response.text}")
            raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")
