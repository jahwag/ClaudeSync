import os

import click
import logging
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
def pull(config):
    """Synchronize chats and their artifacts from the remote source."""
    provider = validate_and_get_provider(config, require_project=True)
    sync_chats(provider, config)


@chat.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List all chats."""
    provider = validate_and_get_provider(config)
    organization_id = config.get("active_organization_id")
    chats = provider.get_chat_conversations(organization_id)

    for chat in chats:
        project = chat.get("project")
        project_name = project.get("name") if project else ""
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
def rm(config, delete_all):
    """Delete chat conversations. Use -a to delete all chats, or run without -a to select specific chats to delete."""
    provider = validate_and_get_provider(config)
    organization_id = config.get("active_organization_id")

    if delete_all:
        delete_all_chats(provider, organization_id)
    else:
        delete_single_chat(provider, organization_id)


def delete_chats(provider, organization_id, uuids):
    """Delete a list of chats by their UUIDs."""
    try:
        result = provider.delete_chat(organization_id, uuids)
        return len(result), 0
    except ProviderError as e:
        logger.error(f"Error deleting chats: {str(e)}")
        click.echo(f"Error occurred while deleting chats: {str(e)}")
        return 0, len(uuids)


def delete_all_chats(provider, organization_id):
    """Delete all chats for the given organization."""
    if click.confirm("Are you sure you want to delete all chats?"):
        total_deleted = 0
        with click.progressbar(length=100, label="Deleting chats") as bar:
            while True:
                chats = provider.get_chat_conversations(organization_id)
                if not chats:
                    break
                uuids_to_delete = [chat["uuid"] for chat in chats[:50]]
                deleted, _ = delete_chats(provider, organization_id, uuids_to_delete)
                total_deleted += deleted
                bar.update(len(uuids_to_delete))
        click.echo(f"Chat deletion complete. Total chats deleted: {total_deleted}")


def delete_single_chat(provider, organization_id):
    """Delete a single chat selected by the user."""
    chats = provider.get_chat_conversations(organization_id)
    if not chats:
        click.echo("No chats found.")
        return

    display_chat_list(chats)
    selected_chat = get_chat_selection(chats)
    if selected_chat:
        confirm_and_delete_chat(provider, organization_id, selected_chat)


def display_chat_list(chats):
    """Display a list of chats to the user."""
    click.echo("Available chats:")
    for idx, chat in enumerate(chats, 1):
        project = chat.get("project")
        project_name = project.get("name") if project else ""
        click.echo(
            f"{idx}. Name: {chat.get('name', 'Unnamed')}, "
            f"Project: {project_name}, Updated: {chat.get('updated_at', 'Unknown')}"
        )


def get_chat_selection(chats):
    """Get a valid chat selection from the user."""
    while True:
        selection = click.prompt(
            "Enter the number of the chat to delete (or 'q' to quit)", type=str
        )
        if selection.lower() == "q":
            return None
        try:
            selection = int(selection)
            if 1 <= selection <= len(chats):
                return chats[selection - 1]
            click.echo("Invalid selection. Please try again.")
        except ValueError:
            click.echo("Invalid input. Please enter a number or 'q' to quit.")


def confirm_and_delete_chat(provider, organization_id, chat):
    """Confirm deletion with the user and delete the selected chat."""
    if click.confirm(
        f"Are you sure you want to delete the chat '{chat.get('name', 'Unnamed')}'?"
    ):
        deleted, _ = delete_chats(provider, organization_id, [chat["uuid"]])
        if deleted:
            click.echo(f"Successfully deleted chat: {chat.get('name', 'Unnamed')}")
        else:
            click.echo(f"Failed to delete chat: {chat.get('name', 'Unnamed')}")


@chat.command()
@click.option("--name", default="", help="Name of the chat conversation")
@click.option("--project", help="UUID of the project to associate the chat with")
@click.pass_obj
@handle_errors
def init(config, name, project):
    """Initializes a new chat conversation on the active provider."""
    provider = validate_and_get_provider(config)
    organization_id = config.get("active_organization_id")
    active_project_id = config.get("active_project_id")
    active_project_name = config.get("active_project_name")
    local_path = config.get("local_path")

    if not organization_id:
        click.echo("No active organization set.")
        return

    if not project:
        project = select_project(
            active_project_id,
            active_project_name,
            local_path,
            organization_id,
            provider,
        )
        if project is None:
            return

    try:
        new_chat = provider.create_chat(
            organization_id, chat_name=name, project_uuid=project
        )
        click.echo(f"Created new chat conversation: {new_chat['uuid']}")
        if name:
            click.echo(f"Chat name: {name}")
        click.echo(f"Associated project: {project}")
    except Exception as e:
        click.echo(f"Failed to create chat conversation: {str(e)}")


@chat.command()
@click.argument("message", nargs=-1, required=True)
@click.option("--chat", help="UUID of the chat to send the message to")
@click.option("--timezone", default="UTC", help="Timezone for the message")
@click.option(
    "--model",
    help="Model to use for the conversation. Available options:\n"
    + "- claude-3-5-haiku-20241022\n"
    + "- claude-3-opus-20240229\n"
    + "Or any custom model string. If not specified, uses the default model.",
)
@click.pass_obj
@handle_errors
def message(config, message, chat, timezone, model):
    """Send a message to a specified chat or create a new chat and send the message."""
    provider = validate_and_get_provider(config, require_project=True)
    active_organization_id = config.get("active_organization_id")
    active_project_id = config.get("active_project_id")
    active_project_name = config.get("active_project_name")

    message = " ".join(message)  # Join all message parts into a single string

    try:
        chat = create_chat(
            config,
            active_project_id,
            active_project_name,
            chat,
            active_organization_id,
            provider,
            model,
        )
        if chat is None:
            return

        # Send message and process the streaming response
        for event in provider.send_message(
            active_organization_id, chat, message, timezone, model
        ):
            if "completion" in event:
                click.echo(event["completion"], nl=False)
            elif "content" in event:
                click.echo(event["content"], nl=False)
            elif "error" in event:
                click.echo(f"\nError: {event['error']}")
            elif "message_limit" in event:
                click.echo(
                    f"\nRemaining messages: {event['message_limit']['remaining']}"
                )

        click.echo()  # Print a newline at the end of the response

    except Exception as e:
        click.echo(f"Failed to send message: {str(e)}")


def create_chat(
    config,
    active_project_id,
    active_project_name,
    chat,
    active_organization_id,
    provider,
    model,
):
    if not chat:
        if not active_project_name:
            active_project_id = select_project(
                config,
                active_project_id,
                active_project_name,
                active_organization_id,
                provider,
            )
        if active_project_id is None:
            return None

        # Create a new chat with the selected project
        new_chat = provider.create_chat(
            active_organization_id, project_uuid=active_project_id, model=model
        )
        chat = new_chat["uuid"]
        click.echo(f"New chat created with ID: {chat}")
    return chat


def select_project(
    config, active_project_id, active_project_name, active_organization_id, provider
):
    all_projects = provider.get_projects(active_organization_id)
    if not all_projects:
        click.echo("No projects found in the active organization.")
        return None

    # Filter projects to include only the active project and its submodules
    filtered_projects = [
        p
        for p in all_projects
        if p["id"] == active_project_id
        or (
            p["name"].startswith(f"{active_project_name}-SubModule-")
            and not p.get("archived_at")
        )
    ]

    if not filtered_projects:
        click.echo("No active project or related submodules found.")
        return None

    # Determine the current working directory
    current_dir = os.path.abspath(os.getcwd())

    default_project = get_default_project(
        config, active_project_id, active_project_name, current_dir, filtered_projects
    )

    click.echo("Available projects:")
    for idx, proj in enumerate(filtered_projects, 1):
        project_type = (
            "Active Project" if proj["id"] == active_project_id else "Submodule"
        )
        default_marker = " (default)" if idx - 1 == default_project else ""
        click.echo(
            f"{idx}. {proj['name']} (ID: {proj['id']}) - {project_type}{default_marker}"
        )

    while True:
        prompt = "Enter the number of the project to associate with the chat"
        if default_project is not None:
            default_project_name = filtered_projects[default_project]["name"]
            prompt += f" (default: {default_project + 1} - {default_project_name})"
        selection = click.prompt(
            prompt,
            type=int,
            default=default_project + 1 if default_project is not None else None,
        )
        if 1 <= selection <= len(filtered_projects):
            project = filtered_projects[selection - 1]["id"]
            break
        click.echo("Invalid selection. Please try again.")
    return project


def get_default_project(
    config, active_project_id, active_project_name, current_dir, filtered_projects
):
    local_path = config.get("local_path")
    if not local_path:
        return None

    # Find the project that matches the current directory
    default_project = None
    for idx, proj in enumerate(filtered_projects):
        if proj["id"] == active_project_id:
            project_path = os.path.abspath(local_path)
        else:
            submodule_name = proj["name"].replace(
                f"{active_project_name}-SubModule-", ""
            )
            project_path = os.path.abspath(
                os.path.join(local_path, "services", submodule_name)
            )
        if current_dir.startswith(project_path):
            default_project = idx
            break
    return default_project
