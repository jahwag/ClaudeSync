import click
from datetime import datetime
from ..utils import handle_errors, validate_and_get_provider
from ..exceptions import ProviderError


@click.group()
def session():
    """Manage Claude Code web sessions."""
    pass


@session.group()
def environment():
    """Manage Claude Code environments."""
    pass


@session.group()
def branch():
    """Manage Claude Code repository branches."""
    pass


@branch.command(name="ls")
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output in JSON format",
)
@click.option(
    "-s",
    "--search",
    help="Filter repositories by name",
)
@click.pass_obj
@handle_errors
def branch_ls(config, json_output, search):
    """List available repositories for Claude Code sessions."""
    import json as json_module

    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")

    try:
        repos_data = provider.get_code_repos(active_organization_id)

        if not repos_data or not repos_data.get("repos"):
            click.echo("No repositories found.")
            return

        repos = repos_data["repos"]

        # Filter by search term if provided
        if search:
            repos = [
                r
                for r in repos
                if search.lower() in r.get("repo", {}).get("name", "").lower()
            ]

        if not repos:
            click.echo(f"No repositories found matching '{search}'.")
            return

        if json_output:
            click.echo(json_module.dumps(repos, indent=2))
            return

        # Display repositories in a formatted way
        click.echo(f"Found {len(repos)} repository(ies):")

        for idx, repo_data in enumerate(repos, 1):
            repo = repo_data.get("repo", {})
            name = repo.get("name", "Unknown")
            owner = repo.get("owner", {}).get("login", "Unknown")
            default_branch = repo.get("default_branch", "N/A")

            click.echo(f"\n{idx}. {owner}/{name}")
            click.echo(f"  Default branch: {default_branch}")

    except ProviderError as e:
        click.echo(f"Failed to list repositories: {str(e)}")


@environment.command(name="ls")
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output in JSON format",
)
@click.pass_obj
@handle_errors
def environment_ls(config, json_output):
    """List all Claude Code environments."""
    import json as json_module

    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")

    try:
        environments_data = provider.get_environments(active_organization_id)

        if not environments_data or not environments_data.get("environments"):
            click.echo("No environments found.")
            return

        environments = environments_data["environments"]

        if json_output:
            click.echo(json_module.dumps(environments, indent=2))
            return

        # Display environments in a formatted way
        click.echo(f"Found {len(environments)} environment(s):")

        for idx, env in enumerate(environments, 1):
            env_id = env.get("environment_id", "N/A")
            name = env.get("name", "Unnamed Environment")
            kind = env.get("kind", "N/A")
            state = env.get("state", "unknown")

            click.echo(f"\n{idx}. {name}")
            click.echo(f"  ID: {env_id}")
            click.echo(f"  Kind: {kind}")
            click.echo(f"  State: {state}")

    except ProviderError as e:
        click.echo(f"Failed to list environments: {str(e)}")


@session.command()
@click.option(
    "-a",
    "--all",
    "archive_all",
    is_flag=True,
    help="Archive all active sessions",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_obj
@handle_errors
def archive(config, archive_all, yes):
    """Archive existing sessions."""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    sessions_data = provider.get_sessions(active_organization_id)

    if not sessions_data or not sessions_data.get("data"):
        click.echo("No sessions found.")
        return

    # Filter for active sessions (not archived)
    sessions = [
        s
        for s in sessions_data["data"]
        if s.get("session_status") in ["running", "idle"]
    ]

    if not sessions:
        click.echo("No active sessions found.")
        return

    if archive_all:
        if not yes:
            click.echo("The following sessions will be archived:")
            for sess in sessions:
                title = sess.get("title", "Untitled")
                sess_id = sess.get("id", "N/A")
                click.echo(f"  - {title} (ID: {sess_id})")
            if not click.confirm("Are you sure you want to archive all sessions?"):
                click.echo("Operation cancelled.")
                return

        success_count = 0
        failure_count = 0
        with click.progressbar(
            sessions,
            label="Archiving sessions",
            item_show_func=lambda s: s.get("title", "Untitled") if s else "",
        ) as bar:
            for sess in bar:
                try:
                    provider.archive_session(active_organization_id, sess.get("id"))
                    success_count += 1
                except ProviderError as e:
                    failure_count += 1
                    title = sess.get("title", "Untitled")
                    click.echo(f"\nFailed to archive session '{title}': {str(e)}")

        click.echo(
            f"\nArchive operation completed. "
            f"Successfully archived: {success_count}, Failed: {failure_count}"
        )
        return

    single_session_archival(sessions, yes, provider, active_organization_id)


def single_session_archival(sessions, yes, provider, organization_id):
    """Archive a single session selected by the user."""
    click.echo("Available sessions to archive:")
    for idx, sess in enumerate(sessions, 1):
        title = sess.get("title", "Untitled")
        sess_id = sess.get("id", "N/A")
        click.echo(f"  {idx}. {title} (ID: {sess_id})")

    selection = click.prompt("Enter the number of the session to archive", type=int)
    if 1 <= selection <= len(sessions):
        selected_session = sessions[selection - 1]
        title = selected_session.get("title", "Untitled")
        if yes or click.confirm(
            f"Are you sure you want to archive the session '{title}'? "
            f"Archived sessions cannot be modified but can still be viewed."
        ):
            try:
                provider.archive_session(organization_id, selected_session.get("id"))
                click.echo(f"Session '{title}' has been archived.")
            except ProviderError as e:
                click.echo(f"Failed to archive session '{title}': {str(e)}")
    else:
        click.echo("Invalid selection. Please try again.")


@session.command()
@click.argument("title", required=False)
@click.option(
    "-e",
    "--environment-id",
    help="Environment ID (if not provided, will try to use active environment)",
)
@click.option(
    "-m",
    "--model",
    default="claude-sonnet-4-5-20250929",
    help="Model to use (default: claude-sonnet-4-5-20250929)",
)
@click.option(
    "-b",
    "--branch",
    help="Branch name to create (auto-generated if not provided)",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output in JSON format",
)
@click.pass_obj
@handle_errors
def create(config, title, environment_id, model, branch, json_output):  # noqa: C901
    """Create a new Claude Code web session.

    Provide a title for the session. If no title is provided, you will be prompted.
    If the current directory is a git repository, it will be automatically linked to the session.
    """
    import json as json_module
    import subprocess
    import re

    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")

    # Get the title from user if not provided
    if not title:
        title = click.prompt("Enter the session title")

    if not title.strip():
        click.echo("Error: Title cannot be empty.")
        return

    # Get environment_id from config or parameter
    if not environment_id:
        environment_id = config.get("active_environment_id")
        if not environment_id:
            # Try to get environments and let user select
            try:
                environments_data = provider.get_environments(active_organization_id)
                environments = environments_data.get("environments", [])

                if not environments:
                    click.echo("Error: No environments found.")
                    click.echo(
                        "Please create an environment first or use -e flag to specify one."
                    )
                    return

                # Show available environments
                click.echo("Available environments:")
                for idx, env in enumerate(environments, 1):
                    env_id = env.get("environment_id", "N/A")
                    name = env.get("name", "Unnamed")
                    state = env.get("state", "unknown")
                    click.echo(f"  {idx}. {name} ({state}) - {env_id}")

                # Prompt user to select
                selection = click.prompt(
                    "Select an environment number", type=int, default=1
                )

                if 1 <= selection <= len(environments):
                    environment_id = environments[selection - 1].get("environment_id")
                    if not json_output:
                        click.echo(
                            f"Using environment: {environments[selection - 1].get('name')}"
                        )
                else:
                    click.echo("Invalid selection.")
                    return

            except ProviderError as e:
                click.echo(f"Error: Could not retrieve environments: {str(e)}")
                click.echo("Please use -e flag to specify an environment ID.")
                return

    # Try to detect git repository context and verify it's available
    git_repo_url = None
    git_repo_owner = None
    git_repo_name = None
    local_repo_detected = False
    local_owner = None
    local_name = None

    try:
        # Get git remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        git_remote = result.stdout.strip()

        # Parse GitHub URL (supports both SSH and HTTPS)
        # SSH: git@github.com:owner/repo.git
        # HTTPS: https://github.com/owner/repo.git
        github_ssh_pattern = r"git@github\.com:([^/]+)/(.+?)(?:\.git)?$"
        github_https_pattern = r"https://github\.com/([^/]+)/(.+?)(?:\.git)?$"

        match = re.match(github_ssh_pattern, git_remote) or re.match(
            github_https_pattern, git_remote
        )
        if match:
            local_owner = match.group(1)
            local_name = match.group(2)
            local_repo_detected = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not in a git repository or git not available
        local_repo_detected = False

    # Get available repos to verify local repo is connected
    repo_available = False
    if local_repo_detected:
        try:
            repos_data = provider.get_code_repos(active_organization_id)
            repos = repos_data.get("repos", [])

            # Check if local repo is in available repos
            for repo_data in repos:
                repo = repo_data.get("repo", {})
                owner = repo.get("owner", {}).get("login")
                name = repo.get("name")
                if owner == local_owner and name == local_name:
                    git_repo_owner = local_owner
                    git_repo_name = local_name
                    git_repo_url = (
                        f"https://github.com/{git_repo_owner}/{git_repo_name}"
                    )
                    repo_available = True
                    if not json_output:
                        click.echo(
                            f"Using detected repository: {git_repo_owner}/{git_repo_name}"
                        )
                    break

            if not repo_available and not json_output:
                click.echo(
                    f"\nDetected local repository {local_owner}/{local_name}, but it's not connected to Claude Code."
                )
                click.echo(
                    "You need to connect this repository via GitHub OAuth first."
                )
                click.echo("Available repositories:")
        except ProviderError:
            repos = []

    # If no valid repo, prompt user to select one
    if not repo_available and not json_output:
        try:
            # If we haven't fetched repos yet, fetch them now
            if not local_repo_detected or not repos:
                repos_data = provider.get_code_repos(active_organization_id)
                repos = repos_data.get("repos", [])

            if repos:
                for idx, repo_data in enumerate(repos, 1):
                    repo = repo_data.get("repo", {})
                    name = repo.get("name", "Unknown")
                    owner = repo.get("owner", {}).get("login", "Unknown")
                    click.echo(f"  {idx}. {owner}/{name}")
                click.echo(
                    f"  {len(repos) + 1}. Skip (create session without repository)"
                )

                selection = click.prompt(
                    "Select a repository number", type=int, default=len(repos) + 1
                )

                if 1 <= selection <= len(repos):
                    selected_repo = repos[selection - 1].get("repo", {})
                    git_repo_owner = selected_repo.get("owner", {}).get("login")
                    git_repo_name = selected_repo.get("name")
                    if git_repo_owner and git_repo_name:
                        git_repo_url = (
                            f"https://github.com/{git_repo_owner}/{git_repo_name}"
                        )
                        click.echo(
                            f"Using repository: {git_repo_owner}/{git_repo_name}"
                        )
                elif selection == len(repos) + 1:
                    click.echo("Creating session without git repository context")
                else:
                    click.echo(
                        "Invalid selection. Creating session without repository."
                    )

        except ProviderError:
            # If we can't get repos, just continue without repo context
            if not json_output:
                click.echo("Creating session without git repository context")

    try:
        result = provider.create_session(
            organization_id=active_organization_id,
            title=title,
            environment_id=environment_id,
            git_repo_url=git_repo_url,
            git_repo_owner=git_repo_owner,
            git_repo_name=git_repo_name,
            branch_name=branch,
            model=model,
        )

        session_id = result.get("id", "N/A")
        session_title = result.get("title", "N/A")
        session_status = result.get("session_status", "N/A")

        # Extract branch name from outcomes
        branch_info = "N/A"
        try:
            outcomes = result.get("session_context", {}).get("outcomes", [])
            for outcome in outcomes:
                if outcome.get("type") == "git_repository":
                    branches = outcome.get("git_info", {}).get("branches", [])
                    if branches:
                        branch_info = branches[0]
        except (AttributeError, TypeError, KeyError):
            pass

        if json_output:
            click.echo(json_module.dumps(result, indent=2))
        else:
            click.echo("Session created successfully!")
            click.echo(f"ID: {session_id}")
            click.echo(f"Title: {session_title}")
            click.echo(f"Status: {session_status}")
            if branch_info != "N/A":
                click.echo(f"Branch: {branch_info}")

            click.echo(f"\nView session at: https://claude.ai/code/{session_id}")
            click.echo(
                "\nNote: Session starts idle. Send a message through the web UI to begin."
            )
            click.echo("\n--- Streaming session events (Ctrl+C to stop) ---\n")
            click.echo("Connecting to event stream...")

            # Stream session events
            try:
                event_count = 0
                for event in provider.stream_session_events(
                    active_organization_id, session_id
                ):
                    event_count += 1

                    # Debug: show raw events for now
                    click.echo(f"[Event {event_count}] {json_module.dumps(event)}")

                    if "error" in event:
                        click.echo(f"Error: {event['error']}")
                        break

                    # Handle different event types
                    event_type = event.get("type")
                    if event_type == "message":
                        content = event.get("content", "")
                        if content:
                            click.echo(f"Claude: {content}")
                    elif event_type == "session_status":
                        status = event.get("status", "")
                        if status:
                            click.echo(f"Status: {status}")

                if event_count == 0:
                    click.echo("\nNo events received from session.")
                    click.echo("The session may still be initializing.")
            except KeyboardInterrupt:
                click.echo("\n\nSession streaming stopped by user.")
                click.echo(f"Session {session_id} continues running in the background.")
                click.echo(
                    "You can view it at: https://claude.ai/code/session_{session_id}"
                )
            except Exception as e:
                click.echo(f"\nError streaming events: {str(e)}")
                click.echo(
                    f"Session {session_id} is still running. View at: https://claude.ai/code/{session_id}"
                )

    except ProviderError as e:
        click.echo(f"Failed to create session: {str(e)}")


@session.command()
@click.option(
    "-a",
    "--all",
    "show_all",
    is_flag=True,
    help="Show all sessions including archived (default shows only running and idle)",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output in JSON format",
)
@click.pass_obj
@handle_errors
def ls(config, show_all, json_output):  # noqa: C901
    """List all web sessions."""
    import json as json_module

    provider = validate_and_get_provider(config)
    active_organization_id = config.get("active_organization_id")
    sessions_data = provider.get_sessions(active_organization_id)

    if not sessions_data or not sessions_data.get("data"):
        click.echo("No sessions found.")
        return

    sessions = sessions_data["data"]

    # Filter sessions if not showing all
    if not show_all:
        sessions = [
            s for s in sessions if s.get("session_status") in ["running", "idle"]
        ]

    if not sessions:
        click.echo("No active sessions found. Use --all to show archived sessions.")
        return

    if json_output:
        click.echo(json_module.dumps(sessions, indent=2))
        return

    # Display sessions in a formatted way
    click.echo(f"Found {len(sessions)} session(s):")

    for idx, sess in enumerate(sessions, 1):
        session_id = sess.get("id", "N/A")
        title = sess.get("title", "Untitled")
        status = sess.get("session_status", "unknown")
        created_at = sess.get("created_at", "N/A")
        updated_at = sess.get("updated_at", "N/A")

        # Parse and format timestamps
        try:
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            created_str = created_dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            created_str = created_at

        try:
            updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            updated_str = updated_dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            updated_str = updated_at

        # Get repository info if available
        repo_info = ""
        try:
            context = sess.get("session_context", {})
            outcomes = context.get("outcomes", [])
            for outcome in outcomes:
                if outcome.get("type") == "git_repository":
                    git_info = outcome.get("git_info", {})
                    repo = git_info.get("repo", "")
                    branches = git_info.get("branches", [])
                    if repo:
                        repo_info = f"\n  Repository: {repo}"
                        if branches:
                            repo_info += f"\n  Branch: {branches[0]}"
        except (AttributeError, TypeError, KeyError):
            # Skip repo info if structure is unexpected
            pass

        # Status text
        status_text = status.capitalize()

        click.echo(f"\n{idx}. {title}")
        click.echo(f"  ID: {session_id}")
        click.echo(f"  Status: {status_text}")
        click.echo(f"  Created: {created_str}")
        click.echo(f"  Updated: {updated_str}")
        if repo_info:
            click.echo(repo_info)


__all__ = ["session"]
