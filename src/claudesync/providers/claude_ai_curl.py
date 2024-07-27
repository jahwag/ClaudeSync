import json
import subprocess
import click
from .base_provider import BaseProvider
from ..exceptions import ProviderError


class ClaudeAICurlProvider(BaseProvider):
    """
    A provider class for interacting with the Claude AI API using cURL.

    This class encapsulates methods for performing API operations such as logging in, retrieving organizations,
    projects, and files, as well as uploading and deleting files. It uses cURL commands for HTTP requests and
    a session key for authentication.

    Attributes:
        BASE_URL (str): The base URL for the Claude AI API.
        session_key (str, optional): The session key used for authentication with the API.
    """

    BASE_URL = "https://claude.ai/api"

    def __init__(self, session_key=None):
        """
        Initializes the ClaudeAICurlProvider instance.

        Args:
            session_key (str, optional): The session key used for authentication. Defaults to None.
        """
        self.session_key = session_key

    def _execute_curl(self, method, endpoint, data=None):
        """
        Executes a cURL command to make an HTTP request to the Claude AI API.

        This method constructs and executes a cURL command based on the provided method, endpoint, and data.
        It handles the response and potential errors from the cURL execution.

        Args:
            method (str): The HTTP method for the request (e.g., "GET", "POST", "PUT", "DELETE").
            endpoint (str): The API endpoint to call, relative to the BASE_URL.
            data (dict, optional): The data to send with the request for POST or PUT methods. Defaults to None.

        Returns:
            dict: The JSON-decoded response from the API.

        Raises:
            ProviderError: If the cURL command fails, returns no output, or the response cannot be parsed as JSON.
        """
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
        ]  # Add -s for silent mode, -S to show errors
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

        This method sends a GET request to the '/organizations' endpoint to fetch account information,
        including memberships in organizations. It parses the response to extract and return
        organization IDs and names.

        Returns:
            list of dict: A list of dictionaries, each containing the 'id' and 'name' of an organization.

        Raises:
            ProviderError: If there's an issue with retrieving organization information.
        """
        response = self._execute_curl("GET", "/organizations")
        if not response:
            raise ProviderError("Unable to retrieve organization information")
        return [{"id": org["uuid"], "name": org["name"]} for org in response]

    def get_projects(self, organization_id, include_archived=False):
        """
        Retrieves a list of projects for a specified organization.

        This method sends a GET request to fetch all projects associated with a given organization ID.
        It then filters these projects based on the `include_archived` parameter.

        Args:
            organization_id (str): The unique identifier for the organization.
            include_archived (bool, optional): Flag to include archived projects in the result. Defaults to False.

        Returns:
            list of dict: A list of dictionaries, each representing a project with its ID, name, and archival status.
        """
        response = self._execute_curl(
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
        response = self._execute_curl(
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
        data = {"file_name": file_name, "content": content}
        return self._execute_curl(
            "POST", f"/organizations/{organization_id}/projects/{project_id}/docs", data
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
        return self._execute_curl(
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
        data = {"is_archived": True}
        return self._execute_curl(
            "PUT", f"/organizations/{organization_id}/projects/{project_id}", data
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
        return self._execute_curl(
            "POST", f"/organizations/{organization_id}/projects", data
        )
