import datetime
import json
import logging
import urllib
import sseclient

import click
from .base_provider import BaseProvider
from ..configmanager import FileConfigManager, InMemoryConfigManager
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
            click.echo(
                "The entered date does not match the required format. Please try again."
            )


class BaseClaudeAIProvider(BaseProvider):
    def __init__(self, config=None):
        self.config = config
        if self.config is None:
            self.config = InMemoryConfigManager()
            self.config.load_from_file_config(
                FileConfigManager()
            )  # a provider may not edit the config
        self.logger = logging.getLogger(__name__)
        self._configure_logging()

    @property
    def base_url(self):
        return self.config.get("claude_api_url", "https://claude.ai/api")

    def _configure_logging(self):
        log_level = self.config.get("log_level", "INFO")
        logging.basicConfig(level=getattr(logging, log_level))
        self.logger.setLevel(getattr(logging, log_level))

    def login(self):
        """
        Handle login with support for direct session key and auto-approve options.

        Returns:
            tuple: (session_key, expires) where session_key is the authenticated key
                   and expires is the datetime when the key expires

        Raises:
            ProviderError: If authentication fails or the session key is invalid
        """
        if hasattr(self, "_provided_session_key"):
            return self._handle_provided_session_key()
        return self._handle_interactive_login()

    def _handle_provided_session_key(self):
        """Handle login with a pre-provided session key."""
        session_key = self._provided_session_key

        if not session_key.startswith("sk-ant"):
            raise ProviderError("Invalid sessionKey format. Must start with 'sk-ant'")

        expires = self._get_session_expiry()

        # Validate the session key
        try:
            self.config.set_session_key("claude.ai", session_key, expires)
            organizations = self.get_organizations()
            if organizations:
                return session_key, expires
        except ProviderError as e:
            raise ProviderError(f"Invalid session key: {str(e)}")

    def _handle_interactive_login(self):
        """Handle interactive login flow with user prompts."""
        self._display_login_instructions()

        while True:
            session_key = self._get_valid_session_key()
            expires = self._get_session_expiry()

            try:
                self.config.set_session_key("claude.ai", session_key, expires)
                organizations = self.get_organizations()
                if organizations:
                    return session_key, expires
            except ProviderError as e:
                click.echo(e)
                click.echo(
                    "Failed to retrieve organizations. Please enter a valid sessionKey."
                )

    def _get_session_expiry(self):
        """Get session expiry time, either auto-approved or user-specified."""
        if hasattr(self, "_auto_approve_expiry") and self._auto_approve_expiry:
            return self._get_default_expiry()
        return _get_session_key_expiry()

    def _get_default_expiry(self):
        """Get default expiry time (30 days from now)."""
        expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            days=30
        )
        date_format = "%a, %d %b %Y %H:%M:%S %Z"
        expires = expires.strftime(date_format).strip()
        return datetime.datetime.strptime(expires, date_format)

    def _display_login_instructions(self):
        """Display instructions for obtaining a session key."""
        click.echo(
            f"A session key is required to call: {self.config.get('claude_api_url')}"
        )
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
            "6. Locate the cookie named 'sessionKey' and copy its value. Ensure that the value is not URL-encoded."
        )

    def _get_valid_session_key(self):
        """Get and validate a session key from user input."""
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

            return session_key

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
                or {"chat", "claude_max"}.issubset(set(org.get("capabilities", [])))
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

    def create_chat(self, organization_id, chat_name="", project_uuid=None, model=None):
        data = {
            "uuid": self._generate_uuid(),
            "name": chat_name,
            "project_uuid": project_uuid,
        }
        if model is not None:
            data["model"] = model

        return self._make_request(
            "POST", f"/organizations/{organization_id}/chat_conversations", data
        )

    def _generate_uuid(self):
        """Generate a UUID for the chat conversation."""
        import uuid

        return str(uuid.uuid4())

    def _make_request_stream(self, method, endpoint, data=None):
        # This method should be implemented by subclasses to return a response object
        # that can be used with sseclient
        raise NotImplementedError("This method should be implemented by subclasses")

    def send_message(
        self, organization_id, chat_id, prompt, timezone="UTC", model=None
    ):
        endpoint = (
            f"/organizations/{organization_id}/chat_conversations/{chat_id}/completion"
        )
        data = {
            "prompt": prompt,
            "timezone": timezone,
            "attachments": [],
            "files": [],
        }
        if model is not None:
            data["model"] = model

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
