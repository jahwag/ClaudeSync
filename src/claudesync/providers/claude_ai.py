import requests
import json
import click
import logging
from ..exceptions import ProviderError
from ..config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ClaudeAIProvider:
    BASE_URL = "https://claude.ai/api"

    def __init__(self, session_key=None):
        self.session_key = session_key
        self.config = ConfigManager()
        self._configure_logging()

    def _configure_logging(self):
        log_level = self.config.get("log_level", "INFO")
        logging.basicConfig(level=getattr(logging, log_level))
        logger.setLevel(getattr(logging, log_level))

    def login(self):
        click.echo("To obtain your session key, please follow these steps:")
        click.echo("1. Open your web browser and go to https://claude.ai")
        click.echo("2. Log in to your Claude account if you haven't already")
        click.echo("3. Once logged in, open your browser's developer tools:")
        click.echo("   - Chrome/Edge: Press F12 or Ctrl+Shift+I (Cmd+Option+I on Mac)")
        click.echo("   - Firefox: Press F12 or Ctrl+Shift+I (Cmd+Option+I on Mac)")
        click.echo(
            "   - Safari: Enable developer tools in Preferences > Advanced, then press Cmd+Option+I"
        )
        click.echo(
            "4. In the developer tools, go to the 'Application' tab (Chrome/Edge) or 'Storage' tab (Firefox)"
        )
        click.echo(
            "5. In the left sidebar, expand 'Cookies' and select 'https://claude.ai'"
        )
        click.echo("6. Find the cookie named 'sessionKey' and copy its value")

        self.session_key = click.prompt("Please enter your sessionKey", type=str)
        return self.session_key

    def get_organizations(self):
        account_info = self._make_request("GET", "/bootstrap")
        if (
            "account" not in account_info
            or "memberships" not in account_info["account"]
        ):
            raise ProviderError("Unable to retrieve organization information")

        return [
            {
                "id": membership["organization"]["uuid"],
                "name": membership["organization"]["name"],
            }
            for membership in account_info["account"]["memberships"]
        ]

    def get_projects(self, organization_id, include_archived=False):
        projects = self._make_request(
            "GET", f"/organizations/{organization_id}/projects"
        )
        filtered_projects = [
            {
                "id": project["uuid"],
                "name": project["name"],
                "archived_at": project.get("archived_at"),
            }
            for project in projects
            if include_archived or project.get("archived_at") is None
        ]
        return filtered_projects

    def list_files(self, organization_id, project_id):
        files = self._make_request(
            "GET", f"/organizations/{organization_id}/projects/{project_id}/docs"
        )
        return [
            {
                "uuid": file["uuid"],
                "file_name": file["file_name"],
                "content": file["content"],
                "created_at": file["created_at"],
            }
            for file in files
        ]

    def upload_file(self, organization_id, project_id, file_name, content):
        return self._make_request(
            "POST",
            f"/organizations/{organization_id}/projects/{project_id}/docs",
            json={"file_name": file_name, "content": content},
        )

    def delete_file(self, organization_id, project_id, file_uuid):
        return self._make_request(
            "DELETE",
            f"/organizations/{organization_id}/projects/{project_id}/docs/{file_uuid}",
        )

    def _make_request(self, method, endpoint, **kwargs):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://claude.ai/",
            "Origin": "https://claude.ai",
            "Connection": "keep-alive",
        }
        cookies = {"sessionKey": self.session_key}

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            logger.debug(f"Making {method} request to {url}")
            logger.debug(f"Headers: {headers}")
            logger.debug(f"Cookies: {cookies}")
            if "data" in kwargs:
                logger.debug(f"Request data: {kwargs['data']}")

            response = requests.request(
                method, url, headers=headers, cookies=cookies, **kwargs
            )

            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            logger.debug(
                f"Response content: {response.text[:1000]}..."
            )  # Log first 1000 characters of response

            response.raise_for_status()

            if not response.content:
                return None

            try:
                return response.json()
            except json.JSONDecodeError as json_err:
                logger.error(f"Failed to parse JSON response: {str(json_err)}")
                logger.error(f"Response content: {response.text}")
                raise ProviderError(f"Invalid JSON response from API: {str(json_err)}")

        except requests.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response headers: {e.response.headers}")
                logger.error(f"Response content: {e.response.text}")
            raise ProviderError(f"API request failed: {str(e)}")

    def archive_project(self, organization_id, project_id):
        return self._make_request(
            "PUT",
            f"/organizations/{organization_id}/projects/{project_id}",
            json={"is_archived": True},
        )

    def create_project(self, organization_id, name, description=""):
        data = {"name": name, "description": description, "is_private": True}
        return self._make_request(
            "POST", f"/organizations/{organization_id}/projects", json=data
        )
