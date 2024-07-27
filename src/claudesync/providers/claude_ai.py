# src/claudesync/providers/claude_ai.py

import json
import logging

import click
import requests

from .base_provider import BaseProvider
from ..config_manager import ConfigManager
from ..exceptions import ProviderError

logger = logging.getLogger(__name__)


class ClaudeAIProvider(BaseProvider):
    """
    A provider class for interacting with the Claude AI API.

    This class encapsulates methods for performing API operations such as logging in, retrieving organizations,
    projects, and files, as well as uploading and deleting files. It uses a session key for authentication,
    which can be obtained through the login method.

    Attributes:
        BASE_URL (str): The base URL for the Claude AI API.
        session_key (str, optional): The session key used for authentication with the API.
        config (ConfigManager): An instance of ConfigManager to manage application configuration.
    """

    BASE_URL = "https://claude.ai/api"

    def __init__(self, session_key=None):
        """
        Initializes the ClaudeAIProvider instance.

        Sets up the session key if provided, initializes the configuration manager, and configures logging
        based on the configuration.

        Args:
            session_key (str, optional): The session key used for authentication. Defaults to None.
        """
        self.session_key = session_key
        self.config = ConfigManager()
        self._configure_logging()

    def _configure_logging(self):
        """
        Configures the logging level for the application based on the configuration.
        This method sets the global logging configuration to the level specified in the application's configuration.
        If the log level is not specified in the configuration, it defaults to "INFO".
        It ensures that all log messages across the application are handled at the configured log level.
        """

        log_level = self.config.get(
            "log_level", "INFO"
        )  # Retrieve log level from config, default to "INFO"
        logging.basicConfig(
            level=getattr(logging, log_level)
        )  # Set global logging configuration
        logger.setLevel(
            getattr(logging, log_level)
        )  # Set logger instance to the specified log level

    def _make_request(self, method, endpoint, **kwargs):
        url = f"{self.BASE_URL}{endpoint}"
        headers = self.config.get_headers()
        cookies = self.config.get("cookies", {})

        # Update headers
        headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
                "Origin": "https://claude.ai",
                "Referer": "https://claude.ai/projects",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "en-US,en;q=0.5",
                "anthropic-client-sha": "unknown",
                "anthropic-client-version": "unknown",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            }
        )

        # Merge cookies
        cookies.update(
            {
                "sessionKey": self.session_key,
                "CH-prefers-color-scheme": "dark",
                "anthropic-consent-preferences": '{"analytics":true,"marketing":true}',
            }
        )

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

            # Update cookies with any new values from the response
            self.config.update_cookies(response.cookies.get_dict())

            if response.status_code == 403:
                error_msg = (
                    "Received a 403 Forbidden error. Your session key might be invalid. "
                    "Please try logging out and logging in again. If the issue persists, "
                    "you can try using the claude.ai-curl provider as a workaround:\n"
                    "claudesync api logout\n"
                    "claudesync api login claude.ai-curl"
                )
                logger.error(error_msg)
                raise ProviderError(error_msg)

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

    def login(self):
        """
        Guides the user through obtaining a session key from the Claude AI website.

        This method provides step-by-step instructions for the user to log in to the Claude AI website,
        access the developer tools of their browser, navigate to the cookies section, and retrieve the
        'sessionKey' cookie value. It then prompts the user to enter this session key, which is stored
        in the instance for future requests.

        Returns:
            str: The session key entered by the user.
        """
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
        """
        Retrieves a list of organizations the user is a member of.

        This method sends a GET request to the '/bootstrap' endpoint to fetch account information,
        including memberships in organizations. It parses the response to extract and return
        organization IDs and names.

        Raises:
            ProviderError: If the account information does not contain 'account' or 'memberships' keys,
                            indicating an issue with retrieving organization information.

        Returns:
            list of dict: A list of dictionaries, each containing the 'id' and 'name' of an organization.
        """
        organizations = self._make_request("GET", "/organizations")
        if not organizations:
            raise ProviderError("Unable to retrieve organization information")

        return [
            {
                "id": org["uuid"],
                "name": org["name"],
            }
            for org in organizations
        ]

    def get_projects(self, organization_id, include_archived=False):
        """
        Retrieves a list of projects for a specified organization.

        This method sends a GET request to fetch all projects associated with a given organization ID.
        It then filters these projects based on the `include_archived` parameter. If `include_archived`
        is False (default), only active projects are returned. If True, both active and archived projects
        are returned.

        Args:
            organization_id (str): The unique identifier for the organization.
            include_archived (bool, optional): Flag to include archived projects in the result. Defaults to False.

        Returns:
            list of dict: A list of dictionaries, each representing a project with its ID, name, and archival status.
        """
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
        """
        Lists all files within a specified project and organization.

        This method sends a GET request to the Claude AI API to retrieve all documents associated with a given project
        within an organization. It then formats the response into a list of dictionaries, each representing a file with
        its unique identifier, file name, content, and creation date.

        Args:
            organization_id (str): The unique identifier for the organization.
            project_id (str): The unique identifier for the project within the organization.

        Returns:
            list of dict: A list of dictionaries, each containing details of a file such as its UUID, file name,
                          content, and the date it was created.
        """
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
        """
        Uploads a file to a specified project within an organization.

        This method sends a POST request to the Claude AI API to upload a file with the given name and content
        to a specified project within an organization. The file's metadata, including its name and content,
        is sent as JSON in the request body.

        Args:
            organization_id (str): The unique identifier for the organization.
            project_id (str): The unique identifier for the project within the organization.
            file_name (str): The name of the file to be uploaded.
            content (str): The content of the file to be uploaded.

        Returns:
            dict: The response from the server after the file upload operation, typically including details
                  about the uploaded file such as its ID, name, and a confirmation of the upload status.
        """
        return self._make_request(
            "POST",
            f"/organizations/{organization_id}/projects/{project_id}/docs",
            json={"file_name": file_name, "content": content},
        )

    def delete_file(self, organization_id, project_id, file_uuid):
        """
        Deletes a file from a specified project within an organization.

        This method sends a DELETE request to the Claude AI API to remove a file, identified by its UUID,
        from a specified project within an organization. The organization and project are identified by their
        respective unique identifiers.

        Args:
            organization_id (str): The unique identifier for the organization.
            project_id (str): The unique identifier for the project within the organization.
            file_uuid (str): The unique identifier (UUID) of the file to be deleted.

        Returns:
            dict: The response from the server after the file deletion operation, typically confirming the deletion.
        """
        return self._make_request(
            "DELETE",
            f"/organizations/{organization_id}/projects/{project_id}/docs/{file_uuid}",
        )

    def archive_project(self, organization_id, project_id):
        """
        Archives a specified project within an organization.

        This method sends a PUT request to the Claude AI API to change the archival status of a specified project
        to archive. The project and organization are identified by their respective unique identifiers.

        Args:
            organization_id (str): The unique identifier for the organization.
            project_id (str): The unique identifier for the project within the organization.

        Returns:
            dict: The response from the server after the archival operation, typically confirming the archival status.
        """
        return self._make_request(
            "PUT",
            f"/organizations/{organization_id}/projects/{project_id}",
            json={"is_archived": True},
        )

    def create_project(self, organization_id, name, description=""):
        """
        Creates a new project within a specified organization.

        This method sends a POST request to the Claude AI API to create a new project with the given name,
        description, and sets it as private within the specified organization. The project's name, description,
        and privacy status are sent as JSON in the request body.

        Args:
            organization_id (str): The unique identifier for the organization.
            name (str): The name of the project to be created.
            description (str, optional): A description of the project. Defaults to an empty string.

        Returns:
            dict: The response from the server after the project creation operation, typically including details
                  about the created project such as its ID, name, and a confirmation of the creation status.
        """
        data = {"name": name, "description": description, "is_private": True}
        return self._make_request(
            "POST", f"/organizations/{organization_id}/projects", json=data
        )
