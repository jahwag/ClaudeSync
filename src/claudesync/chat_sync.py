import json
import logging
import os
import re

from tqdm import tqdm

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def sync_chats(provider, config, sync_all=False):
    """
    Synchronize chats and their artifacts from the remote source.

    This function fetches all chats for the active organization, saves their metadata,
    messages, and extracts any artifacts found in the assistant's messages.

    Args:
        provider: The API provider instance.
        config: The configuration manager instance.
        sync_all (bool): If True, sync all chats regardless of project. If False, only sync chats for the active project.

    Raises:
        ConfigurationError: If required configuration settings are missing.
    """
    # Get the local_path for chats
    local_path = config.get("local_path")
    if not local_path:
        raise ConfigurationError(
            "Local path not set. Use 'claudesync project set' or 'claudesync project create' to set it."
        )

    # Create chats directory within local_path
    chat_destination = os.path.join(local_path, "claude_chats")
    os.makedirs(chat_destination, exist_ok=True)

    # Get the active organization ID
    organization_id = config.get("active_organization_id")
    if not organization_id:
        raise ConfigurationError(
            "No active organization set. Please set an organization."
        )

    # Get the active project ID
    active_project_id = config.get("active_project_id")
    if not active_project_id and not sync_all:
        raise ConfigurationError(
            "No active project set. Please set a project or use the -a flag to sync all chats."
        )

    # Fetch all chats for the organization
    logger.debug(f"Fetching chats for organization {organization_id}")
    chats = provider.get_chat_conversations(organization_id)
    logger.debug(f"Found {len(chats)} chats")

    # Process each chat
    for chat in tqdm(chats, desc="Chats"):
        sync_chat(
            active_project_id,
            chat,
            chat_destination,
            organization_id,
            provider,
            sync_all,
        )

    logger.debug(f"Chats and artifacts synchronized to {chat_destination}")


def sync_chat(
    active_project_id, chat, chat_destination, organization_id, provider, sync_all
):
    # Check if the chat belongs to the active project or if we're syncing all chats
    if sync_all or (
        chat.get("project") and chat["project"].get("uuid") == active_project_id
    ):
        logger.debug(f"Processing chat {chat['uuid']}")
        chat_folder = os.path.join(chat_destination, chat["uuid"])
        os.makedirs(chat_folder, exist_ok=True)

        # Save chat metadata
        metadata_file = os.path.join(chat_folder, "metadata.json")
        if not os.path.exists(metadata_file):
            with open(metadata_file, "w") as f:
                json.dump(chat, f, indent=2)

        # Fetch full chat conversation
        logger.debug(f"Fetching full conversation for chat {chat['uuid']}")
        full_chat = provider.get_chat_conversation(organization_id, chat["uuid"])

        # Process each message in the chat
        for message in full_chat["chat_messages"]:
            message_file = os.path.join(chat_folder, f"{message['uuid']}.json")

            # Skip processing if the message file already exists
            if os.path.exists(message_file):
                logger.debug(f"Skipping existing message {message['uuid']}")
                continue

            # Save the message
            with open(message_file, "w") as f:
                json.dump(message, f, indent=2)

            # Handle artifacts in assistant messages
            if message["sender"] == "assistant":
                artifacts = extract_artifacts(message["text"])
                if artifacts:
                    save_artifacts(artifacts, chat_folder, message)
    else:
        logger.debug(
            f"Skipping chat {chat['uuid']} as it doesn't belong to the active project"
        )


def save_artifacts(artifacts, chat_folder, message):
    logger.info(f"Found {len(artifacts)} artifacts in message {message['uuid']}")
    artifact_folder = os.path.join(chat_folder, "artifacts")
    os.makedirs(artifact_folder, exist_ok=True)
    for artifact in artifacts:
        # Save each artifact
        artifact_file = os.path.join(
            artifact_folder,
            f"{artifact['identifier']}.{get_file_extension(artifact['type'])}",
        )
        if not os.path.exists(artifact_file):
            with open(artifact_file, "w") as f:
                f.write(artifact["content"])


def get_file_extension(artifact_type):
    """
    Get the appropriate file extension for a given artifact type.

    Args:
        artifact_type (str): The MIME type of the artifact.

    Returns:
        str: The corresponding file extension.
    """
    type_to_extension = {
        "text/html": "html",
        "application/vnd.ant.code": "txt",
        "image/svg+xml": "svg",
        "application/vnd.ant.mermaid": "mmd",
        "application/vnd.ant.react": "jsx",
    }
    return type_to_extension.get(artifact_type, "txt")


def extract_artifacts(text):
    """
    Extract artifacts from the given text.

    This function searches for antArtifact tags in the text and extracts
    the artifact information, including identifier, type, and content.

    Args:
        text (str): The text to search for artifacts.

    Returns:
        list: A list of dictionaries containing artifact information.
    """
    artifacts = []

    # Regular expression to match the <antArtifact> tags and extract their attributes and content
    pattern = re.compile(
        r'<antArtifact\s+identifier="([^"]+)"\s+type="([^"]+)"\s+title="([^"]+)">([\s\S]*?)</antArtifact>',
        re.MULTILINE,
    )

    # Find all matches in the text
    matches = pattern.findall(text)

    for match in matches:
        identifier, artifact_type, title, content = match
        artifacts.append(
            {
                "identifier": identifier,
                "type": artifact_type,
                "content": content.strip(),
            }
        )

    return artifacts
