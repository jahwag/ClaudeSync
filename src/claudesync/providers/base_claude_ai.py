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

    def get_sessions(self, organization_id):
        """Get all web sessions from the v1 API endpoint."""
        # The sessions endpoint is at /v1/sessions, not under /api
        # Requires x-organization-uuid header
        return self._make_request_v1(
            "GET", "/v1/sessions", organization_id=organization_id
        )

    def get_environments(self, organization_id):
        """Get all environments from the v1 API endpoint."""
        # Get environments for the organization
        endpoint = f"/v1/environment_providers/private/organizations/{organization_id}/environments"
        return self._make_request_v1("GET", endpoint, organization_id=organization_id)

    def get_code_repos(self, organization_id, skip_status=True):
        """Get all code repositories available for Claude Code sessions.

        Args:
            organization_id: The organization UUID
            skip_status: Whether to skip fetching repository status (default: True)

        Returns:
            dict: Contains 'repos' array with repository information
        """
        endpoint = f"/organizations/{organization_id}/code/repos"
        params = "?skip_status=true" if skip_status else ""
        return self._make_request("GET", f"{endpoint}{params}")

    def archive_session(self, organization_id, session_id):
        """Archive a session by its ID."""
        # Requires x-organization-uuid header
        return self._make_request_v1(
            "POST",
            f"/v1/sessions/{session_id}/archive",
            organization_id=organization_id,
        )

    def create_session(
        self,
        organization_id,
        title,
        environment_id,
        git_repo_url=None,
        git_repo_owner=None,
        git_repo_name=None,
        branch_name=None,
        model="claude-sonnet-4-5-20250929",
    ):
        """Create a new Claude Code web session.

        Args:
            organization_id: The organization UUID
            title: Session title
            environment_id: Environment UUID (e.g., env_011CUPDTyMiRVMf18tfu2VUa)
            git_repo_url: Optional git repository URL
            git_repo_owner: Optional git repository owner (e.g., "Bytelope")
            git_repo_name: Optional git repository name (e.g., "uppdragsradarn3")
            branch_name: Optional branch name to create
            model: Model to use (default: claude-sonnet-4-5-20250929)

        Returns:
            dict: Created session with id, title, session_context, etc.
        """
        endpoint = "/v1/sessions"

        data = {
            "title": title,
            "environment_id": environment_id,
            "session_context": {"model": model},
        }

        # Add git repository source if URL provided
        if git_repo_url:
            data["session_context"]["sources"] = [
                {"type": "git_repository", "url": git_repo_url}
            ]

        # Add git repository outcome if repo details provided
        if git_repo_owner and git_repo_name:
            # If no branch name specified, generate a simple one
            # The API will append the session ID automatically
            if not branch_name:
                # Generate from title: lowercase, replace spaces/special chars with hyphens
                import re

                safe_title = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
                # Limit to reasonable length
                safe_title = safe_title[:50]
                branch_name = f"claude/{safe_title}"

            git_info = {
                "type": "github",
                "repo": f"{git_repo_owner}/{git_repo_name}",
                "branches": [branch_name],
            }

            data["session_context"]["outcomes"] = [
                {"type": "git_repository", "git_info": git_info}
            ]

        return self._make_request_v1(
            "POST", endpoint, data=data, organization_id=organization_id
        )

    def _make_request_v1(self, method, endpoint, data=None, organization_id=None):
        """Make a request to the v1 API (not under /api prefix).

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Optional request data
            organization_id: Optional organization UUID for x-organization-uuid header
        """
        # This method should be implemented by subclasses to handle v1 API requests
        # that are not under the /api prefix
        raise NotImplementedError("This method should be implemented by subclasses")

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

    def _make_request_stream_v1(self, method, endpoint, organization_id=None):
        """Make a streaming request to the v1 API."""
        # This method should be implemented by subclasses
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

    def _parse_sse_event(self, event):
        """Parse a single SSE event and return the data."""
        if not event.data or event.data.strip() == "":
            return None
        try:
            return json.loads(event.data)
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse event data: {event.data}")
            return {"error": "Failed to parse JSON", "raw_data": event.data}

    def stream_session_events(self, organization_id, session_id):
        """Stream events from a Claude Code session.

        Args:
            organization_id: The organization UUID
            session_id: The session ID to stream events from

        Yields:
            dict: Event data from the session stream
        """
        import signal

        endpoint = f"/v1/sessions/{session_id}/events"
        self.logger.debug(f"Opening SSE stream to {endpoint}")

        def timeout_handler(signum, frame):
            raise TimeoutError("No events received within timeout period")

        response = self._make_request_stream_v1("GET", endpoint, organization_id)
        client = sseclient.SSEClient(response)

        # Set timeout for first event
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)

        try:
            for event_num, event in enumerate(client.events()):
                if event_num == 0:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)

                parsed_data = self._parse_sse_event(event)
                if parsed_data:
                    yield parsed_data

                if event.event in ("error", "done"):
                    if event.event == "error":
                        yield {"error": event.data}
                    break
        except TimeoutError:
            yield {
                "error": "timeout",
                "message": "No events received from session within 30 seconds",
            }
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def send_session_input(self, organization_id, session_id, prompt):
        """Send input/prompt to a Claude Code session.

        This is used to send an initial prompt or user input to a session.
        The session will process the input and emit events through the event stream.

        Args:
            organization_id: The organization UUID
            session_id: The session ID
            prompt: The text prompt to send to Claude

        Returns:
            dict: Response from the API (typically session state or acknowledgment)
        """
        # Try different possible endpoints - the actual endpoint is not documented
        possible_endpoints = [
            (f"/v1/sessions/{session_id}/prompt", {"prompt": prompt}),
            (f"/v1/sessions/{session_id}/message", {"message": prompt}),
            (f"/v1/sessions/{session_id}/messages", {"content": prompt}),
            (f"/v1/sessions/{session_id}/input", {"input": prompt}),
        ]

        last_error = None
        for endpoint, data in possible_endpoints:
            try:
                return self._make_request_v1("POST", endpoint, data, organization_id)
            except Exception as e:
                last_error = e
                # Try next endpoint
                continue

        # If all endpoints failed, raise the last error
        if last_error:
            raise last_error
