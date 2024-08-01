# src/claudesync/providers/base_provider.py

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    @abstractmethod
    def login(self):
        """Authenticate with the provider and return a session key."""
        pass

    @abstractmethod
    def get_organizations(self):
        """Retrieve a list of organizations the user is a member of."""
        pass

    @abstractmethod
    def get_projects(self, organization_id, include_archived=False):
        """Retrieve a list of projects for a specified organization."""
        pass

    @abstractmethod
    def list_files(self, organization_id, project_id):
        """List all files within a specified project and organization."""
        pass

    @abstractmethod
    def upload_file(self, organization_id, project_id, file_name, content):
        """Upload a file to a specified project within an organization."""
        pass

    @abstractmethod
    def delete_file(self, organization_id, project_id, file_uuid):
        """Delete a file from a specified project within an organization."""
        pass

    @abstractmethod
    def archive_project(self, organization_id, project_id):
        """Archive a specified project within an organization."""
        pass

    @abstractmethod
    def create_project(self, organization_id, name, description=""):
        """Create a new project within a specified organization."""
        pass

    @abstractmethod
    def get_chat_conversations(self, organization_id):
        """Retrieve a list of chat conversations for a specified organization."""
        pass

    @abstractmethod
    def get_published_artifacts(self, organization_id):
        """Retrieve a list of published artifacts for a specified organization."""
        pass

    @abstractmethod
    def get_chat_conversation(self, organization_id, conversation_id):
        """Retrieve the full content of a specific chat conversation."""
        pass

    @abstractmethod
    def get_artifact_content(self, organization_id, artifact_uuid):
        """Retrieve the full content of a specific published artifact."""
        pass

    @abstractmethod
    def delete_chat(self, organization_id, conversation_uuids):
        """Delete specified chats for a given organization."""
        pass
