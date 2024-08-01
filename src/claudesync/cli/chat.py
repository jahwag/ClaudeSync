import click
import logging
import json
from tqdm import tqdm
from ..exceptions import ProviderError
from ..utils import handle_errors, validate_and_get_provider
from ..chat_sync import sync_chats

logger = logging.getLogger(__name__)


@click.group()
def chat():
    """Manage and synchronize chats."""
    pass


@chat.command()
@click.pass_obj
@handle_errors
def sync(config):
    """Synchronize chats and their artifacts from the remote source."""
    provider = validate_and_get_provider(config)
    sync_chats(provider, config)


@chat.command()
@click.pass_obj
@handle_errors
def list(config):
    """List all chats."""
    provider = validate_and_get_provider(config)
    organization_id = config.get("active_organization_id")
    chats = provider.get_chat_conversations(organization_id)
    for chat in chats:
        project_name = chat.get("project", {}).get("name", "N/A")
        click.echo(
            f"UUID: {chat.get('uuid', 'Unknown')}, "
            f"Name: {chat.get('name', 'Unnamed')}, "
            f"Project: {project_name}, "
            f"Updated: {chat.get('updated_at', 'Unknown')}"
        )


@chat.command()
@click.option("-a", "--all", "delete_all", is_flag=True, help="Delete all chats")
@click.pass_obj
@handle_errors
def delete(config, delete_all):
    """Delete chats. Use -a to delete all chats, or select a chat to delete."""
    provider = validate_and_get_provider(config)
    organization_id = config.get("active_organization_id")

    def delete_chats(uuids):
        try:
            result = provider.delete_chat(organization_id, uuids)
            return len(result)
        except ProviderError as e:
            logger.error(f"Error deleting chats: {str(e)}")
            click.echo(f"Error occurred while deleting chats: {str(e)}")
            return 0, len(uuids)

    if delete_all:
        if click.confirm("Are you sure you want to delete all chats?"):
            total_deleted = 0
            with click.progressbar(length=100, label="Deleting chats") as bar:
                while True:
                    chats = provider.get_chat_conversations(organization_id)
                    if not chats:
                        break
                    uuids_to_delete = [chat["uuid"] for chat in chats[:50]]
                    deleted = delete_chats(uuids_to_delete)
                    total_deleted += deleted
                    bar.update(len(uuids_to_delete))
            click.echo(f"Chat deletion complete. Total chats deleted: {total_deleted}")
    else:
        chats = provider.get_chat_conversations(organization_id)
        if not chats:
            click.echo("No chats found.")
            return

        click.echo("Available chats:")
        for idx, chat in enumerate(chats, 1):
            project_name = chat.get("project", {}).get("name", "N/A")
            click.echo(
                f"{idx}. Name: {chat.get('name', 'Unnamed')}, Project: {project_name}, Updated: {chat.get('updated_at', 'Unknown')}"
            )

        while True:
            selection = click.prompt(
                "Enter the number of the chat to delete (or 'q' to quit)", type=str
            )
            if selection.lower() == "q":
                return

            try:
                selection = int(selection)
                if 1 <= selection <= len(chats):
                    selected_chat = chats[selection - 1]
                    if click.confirm(
                        f"Are you sure you want to delete the chat '{selected_chat.get('name', 'Unnamed')}'?"
                    ):
                        deleted, failed = delete_chats([selected_chat["uuid"]])
                        if deleted:
                            click.echo(
                                f"Successfully deleted chat: {selected_chat.get('name', 'Unnamed')}"
                            )
                        else:
                            click.echo(
                                f"Failed to delete chat: {selected_chat.get('name', 'Unnamed')}"
                            )
                    break
                else:
                    click.echo("Invalid selection. Please try again.")
            except ValueError:
                click.echo("Invalid input. Please enter a number or 'q' to quit.")
