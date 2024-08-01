import os
import json
import logging
from tqdm import tqdm
from .config_manager import ConfigManager
from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def sync_chats(provider, config):
    """
    Synchronize chats and their artifacts from the remote source.

    This function fetches all chats for the active organization, saves their metadata,
    messages, and extracts any artifacts found in the assistant's messages.

    Args:
        provider: The API provider instance.
        config: The configuration manager instance.

    Raises:
        ConfigurationError: If required configuration settings are missing.
    """
    # Get the configured destinations for chats and artifacts
    chat_destination = config.get("chat_destination")
    artifact_destination = config.get("artifact_destination")
    if not chat_destination or not artifact_destination:
        raise ConfigurationError(
            "Chat or artifact destination not set. Use 'claudesync config set chat_destination <path>' and "
            "'claudesync config set artifact_destination <path>' to set them."
        )

    # Get the active organization ID
    organization_id = config.get("active_organization_id")
    if not organization_id:
        raise ConfigurationError(
            "No active organization set. Please select an organization."
        )

    # Fetch all chats for the organization
    logger.info(f"Fetching chats for organization {organization_id}")
    chats = provider.get_chat_conversations(organization_id)
    logger.info(f"Found {len(chats)} chats")

    # Process each chat
    for chat in tqdm(chats, desc="Syncing chats"):
        logger.info(f"Processing chat {chat['uuid']}")
        chat_folder = os.path.join(chat_destination, chat["uuid"])
        os.makedirs(chat_folder, exist_ok=True)

        # Save chat metadata
        with open(os.path.join(chat_folder, "metadata.json"), "w") as f:
            json.dump(chat, f, indent=2)

        # Fetch full chat conversation
        logger.info(f"Fetching full conversation for chat {chat['uuid']}")
        full_chat = provider.get_chat_conversation(organization_id, chat["uuid"])

        # Process each message in the chat
        for message in full_chat["chat_messages"]:
            # Save the message
            message_file = os.path.join(chat_folder, f"{message['uuid']}.json")
            with open(message_file, "w") as f:
                json.dump(message, f, indent=2)

            # Handle artifacts in assistant messages
            if message["sender"] == "assistant":
                artifacts = extract_artifacts(message["text"])
                if artifacts:
                    logger.info(
                        f"Found {len(artifacts)} artifacts in message {message['uuid']}"
                    )
                    for artifact in artifacts:
                        # Save each artifact
                        artifact_file = os.path.join(
                            artifact_destination,
                            f"{artifact['identifier']}.{get_file_extension(artifact['type'])}",
                        )
                        os.makedirs(os.path.dirname(artifact_file), exist_ok=True)
                        with open(artifact_file, "w") as f:
                            f.write(artifact["content"])

    logger.info(f"Chats synchronized to {chat_destination}")
    logger.info(f"Artifacts synchronized to {artifact_destination}")


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
    start_tag = '<antArtifact undefined isClosed="true" />'

    while start_tag in text:
        start = text.index(start_tag)
        end = text.index(end_tag, start) + len(end_tag)

        artifact_text = text[start:end]
        identifier = extract_attribute(artifact_text, "identifier")
        artifact_type = extract_attribute(artifact_text, "type")
        content = artifact_text[
            artifact_text.index(">") + 1 : artifact_text.rindex("<")
        ]

        artifacts.append(
            {"identifier": identifier, "type": artifact_type, "content": content}
        )

        text = text[end:]

    return artifacts


def extract_attribute(text, attribute):
    """
    Extract the value of a specific attribute from an XML-like tag.

    Args:
        text (str): The XML-like tag text.
        attribute (str): The name of the attribute to extract.

    Returns:
        str: The value of the specified attribute.
    """
    start = text.index(f'{attribute}="') + len(f'{attribute}="')
    end = text.index('"', start)
    return text[start:end]
