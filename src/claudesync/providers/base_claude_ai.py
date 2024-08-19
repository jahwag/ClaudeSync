import datetime
import logging
import urllib

import click
from .base_provider import BaseProvider
from ..config_manager import ConfigManager
from ..exceptions import ProviderError


def is_url_encoded(s):
    decoded_s = urllib.parse.unquote(s)
    return decoded_s != s


def _get_session_key_expiry():
    while True:
        date_format = "%a, %d %b %Y %H:%M:%S %Z"
        default_expires = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(days=30)
        formatted_expires = default_expires.strftime(date_format).strip()
        expires = click.prompt(
            "Please enter the expires time for the sessionKey (optional)",
            default=formatted_expires,
            type=str,
        ).strip()
        try:
            expires_on = datetime.datetime.strptime(expires, date_format)
            return expires_on
        except ValueError:
            print(
                "The entered date does not match the required format. Please try again."
            )


class BaseClaudeAIProvider(BaseProvider):
    BASE_URL = "https://api.claude.ai/api"

    def __init__(self, session_key=None, session_key_expiry=None):
        self.config = ConfigManager()
        self.session_key = session_key
        self.session_key_expiry = session_key_expiry
        self.logger = logging.getLogger(__name__)
        self._configure_logging()

    def _configure_logging(self):
        log_level = self.config.get("log_level", "INFO")
        logging.basicConfig(level=getattr(logging, log_level))
        self.logger.setLevel(getattr(logging, log_level))

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
        click.echo(
            "6. Locate the cookie named 'sessionKey' and copy its value. "
            "Ensure that the value is not URL-encoded."
        )

        while True:
            session_key = click.prompt(
                "Please enter your sessionKey", type=str, hide_input=True
            )
            if not session_key.startswith("sk-ant"):
                click.echo(
                    "Invalid sessionKey format. Please make sure it starts with 'sk-ant'."
                )
                continue
            if is_url_encoded(session_key):
                click.echo(
                    "The session key appears to be URL-encoded. Please provide the decoded version."
                )
                continue

            expires = _get_session_key_expiry()
            self.session_key = session_key
            self.session_key_expiry = expires
            try:
                organizations = self.get_organizations()
                if organizations:
                    break  # Exit the loop if get_organizations is successful
            except ProviderError as e:
                click.echo(e)
                click.echo(
                    "Failed to retrieve organizations. Please enter a valid sessionKey."
                )

        return self.session_key, self.session_key_expiry

    def get_organizations(self):
        response = self._make_request("GET", "/organizations")
        if not response:
            raise ProviderError("Unable to retrieve organization information")
        return [
            {"id": org["uuid"], "name": org["name"]}
            for org in response
            if (
                {"chat", "claude_pro"}.issubset(set(org.get("capabilities", [])))
                or {"chat", "raven"}.issubset(set(org.get("capabilities", [])))
            )
        ]

    def get_projects(self, organization_id, include_archived=False):
        response = self._make_request(
            "GET", f"/organizations/{organization_id}/projects"
        )
        projects = [
            {
                "id": project["uuid"],
                "name": project["name"],
                "archived_at": project.get("archived_at"),
            }
            for project in response
            if include_archived or project.get("archived_at") is None
        ]
        return projects

    def list_files(self, organization_id, project_id):
        response = self._make_request(
            "GET", f"/organizations/{organization_id}/projects/{project_id}/docs"
        )
        return [
            {
                "uuid": file["uuid"],
                "file_name": file["file_name"],
                "content": file["content"],
                "created_at": file["created_at"],
            }
            for file in response
        ]

    def upload_file(self, organization_id, project_id, file_name, content):
        data = {"file_name": file_name, "content": content}
        return self._make_request(
            "POST", f"/organizations/{organization_id}/projects/{project_id}/docs", data
        )

    def delete_file(self, organization_id, project_id, file_uuid):
        return self._make_request(
            "DELETE",
            f"/organizations/{organization_id}/projects/{project_id}/docs/{file_uuid}",
        )

    def archive_project(self, organization_id, project_id):
        data = {"is_archived": True}
        return self._make_request(
            "PUT", f"/organizations/{organization_id}/projects/{project_id}", data
        )

    def create_project(self, organization_id, name, description=""):
        data = {"name": name, "description": description, "is_private": True}
        return self._make_request(
            "POST", f"/organizations/{organization_id}/projects", data
        )

    def get_chat_conversations(self, organization_id):
        return self._make_request(
            "GET", f"/organizations/{organization_id}/chat_conversations"
        )

    def get_published_artifacts(self, organization_id):
        return self._make_request(
            "GET", f"/organizations/{organization_id}/published_artifacts"
        )

    def get_chat_conversation(self, organization_id, conversation_id):
        return self._make_request(
            "GET",
            f"/organizations/{organization_id}/chat_conversations/{conversation_id}?rendering_mode=raw",
        )

    def get_artifact_content(self, organization_id, artifact_uuid):
        artifacts = self._make_request(
            "GET", f"/organizations/{organization_id}/published_artifacts"
        )
        for artifact in artifacts:
            if artifact["published_artifact_uuid"] == artifact_uuid:
                return artifact.get("artifact_content", "")
        raise ProviderError(f"Artifact with UUID {artifact_uuid} not found")

    def delete_chat(self, organization_id, conversation_uuids):
        endpoint = f"/organizations/{organization_id}/chat_conversations/delete_many"
        data = {"conversation_uuids": conversation_uuids}
        return self._make_request("POST", endpoint, data)

    def _make_request(self, method, endpoint, data=None):
        raise NotImplementedError("This method should be implemented by subclasses")
