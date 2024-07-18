import click
import sys
import os
import shutil

from functools import wraps
from crontab import CronTab
from .config_manager import ConfigManager
from .provider_factory import get_provider
from .exceptions import ConfigurationError, ProviderError
from .utils import calculate_checksum, get_local_files

def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ConfigurationError, ProviderError) as e:
            click.echo(f"Error: {str(e)}")
    return wrapper

def validate_and_get_provider(config, require_org=True):
    active_provider = config.get('active_provider')
    session_key = config.get('session_key')
    if not active_provider or not session_key:
        raise ConfigurationError("No active provider or session key. Please login first.")
    if require_org and not config.get('active_organization_id'):
        raise ConfigurationError("No active organization set. Please select an organization.")
    return get_provider(active_provider, session_key)

def validate_and_store_local_path(config):
    while True:
        local_path = click.prompt("Enter the absolute path to your local project directory", type=str)
        if os.path.isabs(local_path):
            if os.path.exists(local_path):
                config.set('local_path', local_path)
                click.echo(f"Local path set to: {local_path}")
                break
            else:
                click.echo("The specified path does not exist. Please enter a valid path.")
        else:
            click.echo("Please enter an absolute path.")

@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = ConfigManager()

@cli.command()
@click.argument('provider', required=False)
@click.pass_obj
@handle_errors
def login(config, provider):
    """Login to an AI provider"""
    providers = get_provider()
    if not provider:
        click.echo("Available providers:\n" + "\n".join(f"  - {p}" for p in providers))
        return
    if provider not in providers:
        click.echo(f"Error: Unknown provider '{provider}'. Available: {', '.join(providers)}")
        return
    provider_instance = get_provider(provider)
    session_key = provider_instance.login()
    config.set('session_key', session_key)
    config.set('active_provider', provider)
    click.echo("Logged in successfully.")

@cli.command()
@click.pass_obj
def logout(config):
    """Logout from an AI provider"""
    for key in ['session_key', 'active_provider', 'active_organization_id']:
        config.set(key, None)
    click.echo("Logged out successfully.")

@cli.group()
def organization():
    """Organization management"""
    pass

@organization.command()
@click.pass_obj
@handle_errors
def list(config):
    """List available organizations"""
    provider = validate_and_get_provider(config, require_org=False)
    organizations = provider.get_organizations()
    if not organizations:
        click.echo("No organizations found.")
    else:
        click.echo("Available organizations:")
        for idx, org in enumerate(organizations, 1):
            click.echo(f"  {idx}. {org['name']} (ID: {org['id']})")

@organization.command()
@click.pass_obj
@handle_errors
def select(config):
    """Select active organization"""
    provider = validate_and_get_provider(config, require_org=False)
    organizations = provider.get_organizations()
    if not organizations:
        click.echo("No organizations found.")
        return
    click.echo("Available organizations:")
    for idx, org in enumerate(organizations, 1):
        click.echo(f"  {idx}. {org['name']} (ID: {org['id']})")
    selection = click.prompt("Enter the number of the organization to select", type=int)
    if 1 <= selection <= len(organizations):
        selected_org = organizations[selection - 1]
        config.set('active_organization_id', selected_org['id'])
        click.echo(f"Selected organization: {selected_org['name']} (ID: {selected_org['id']})")
    else:
        click.echo("Invalid selection. Please try again.")

@cli.group()
def project():
    """Project management"""
    pass

@project.command()
@click.pass_obj
@handle_errors
def create(config):
    """Create a project"""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get('active_organization_id')

    title = click.prompt("Enter the project title")
    description = click.prompt("Enter the project description (optional)", default="")

    try:
        new_project = provider.create_project(active_organization_id, title, description)
        click.echo(f"Project '{new_project['name']}' (uuid: {new_project['uuid']}) has been created successfully.")

        config.set('active_project_id', new_project['uuid'])
        config.set('active_project_name', new_project['name'])
        click.echo(f"Active project set to: {new_project['name']} (uuid: {new_project['uuid']})")

        validate_and_store_local_path(config)

    except ProviderError as e:
        click.echo(f"Failed to create project: {str(e)}")

@project.command()
@click.pass_obj
@handle_errors
def archive(config):
    """Archive a project"""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get('active_organization_id')
    projects = provider.get_projects(active_organization_id, include_archived=False)
    if not projects:
        click.echo("No active projects found.")
        return
    click.echo("Available projects to archive:")
    for idx, project in enumerate(projects, 1):
        click.echo(f"  {idx}. {project['name']} (ID: {project['id']})")
    selection = click.prompt("Enter the number of the project to archive", type=int)
    if 1 <= selection <= len(projects):
        selected_project = projects[selection - 1]
        if click.confirm(f"Are you sure you want to archive '{selected_project['name']}'?"):
            provider.archive_project(active_organization_id, selected_project['id'])
            click.echo(f"Project '{selected_project['name']}' has been archived.")
    else:
        click.echo("Invalid selection. Please try again.")

@project.command()
@click.pass_obj
@handle_errors
def select(config):
    """Select active project"""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get('active_organization_id')
    projects = provider.get_projects(active_organization_id, include_archived=False)
    if not projects:
        click.echo("No active projects found.")
        return
    click.echo("Available projects:")
    for idx, project in enumerate(projects, 1):
        click.echo(f"  {idx}. {project['name']} (ID: {project['id']})")
    selection = click.prompt("Enter the number of the project to select", type=int)
    if 1 <= selection <= len(projects):
        selected_project = projects[selection - 1]
        config.set('active_project_id', selected_project['id'])
        config.set('active_project_name', selected_project['name'])
        click.echo(f"Selected project: {selected_project['name']} (ID: {selected_project['id']})")

        validate_and_store_local_path(config)
    else:
        click.echo("Invalid selection. Please try again.")

@project.command()
@click.option('-a', '--all', 'show_all', is_flag=True, help="Show all projects, including archived ones")
@click.pass_obj
@handle_errors
def ls(config, show_all):
    """List projects"""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get('active_organization_id')
    projects = provider.get_projects(active_organization_id, include_archived=show_all)
    if not projects:
        click.echo("No projects found.")
    else:
        click.echo("Remote projects:")
        for project in projects:
            status = " (Archived)" if project.get('archived_at') else ""
            click.echo(f"  - {project['name']} (ID: {project['id']}){status}")

@cli.command()
@click.pass_obj
def status(config):
    """Show status"""
    for key in ['active_provider', 'active_organization_id', 'active_project_id', 'active_project_name', 'local_path', 'log_level']:
        value = config.get(key)
        click.echo(f"{key.replace('_', ' ').capitalize()}: {value or 'Not set'}")

@cli.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List remote files"""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get('active_organization_id')
    active_project_id = config.get('active_project_id')
    files = provider.list_files(active_organization_id, active_project_id)
    if not files:
        click.echo("No files found in the active project.")
    else:
        click.echo(f"Files in project '{config.get('active_project_name')}' (ID: {active_project_id}):")
        for file in files:
            click.echo(f"  - {file['file_name']} (ID: {file['uuid']}, Created: {file['created_at']})")

@cli.command()
@click.pass_obj
@handle_errors
def sync(config):
    """Sync remote files"""
    provider = validate_and_get_provider(config)
    active_organization_id = config.get('active_organization_id')
    active_project_id = config.get('active_project_id')
    local_path = config.get('local_path')

    if not local_path:
        click.echo("No local path set. Please select or create a project to set the local path.")
        sys.exit(1)

    if not os.path.exists(local_path):
        click.echo(f"The configured local path does not exist: {local_path}")
        click.echo("Please update the local path by selecting or creating a project.")
        sys.exit(1)

    remote_files = provider.list_files(active_organization_id, active_project_id)
    local_files = get_local_files(local_path)

    for local_file, local_checksum in local_files.items():
        remote_file = next((rf for rf in remote_files if rf['file_name'] == local_file), None)
        if remote_file:
            remote_checksum = calculate_checksum(remote_file['content'])
            if local_checksum != remote_checksum:
                click.echo(f"Updating {local_file} on remote...")
                for rf in remote_files:
                    if rf['file_name'] == local_file:
                        provider.delete_file(active_organization_id, active_project_id, rf['uuid'])
                with open(os.path.join(local_path, local_file), 'r', encoding='utf-8') as file:
                    content = file.read()
                provider.upload_file(active_organization_id, active_project_id, local_file, content)
        else:
            click.echo(f"Uploading new file {local_file} to remote...")
            with open(os.path.join(local_path, local_file), 'r', encoding='utf-8') as file:
                content = file.read()
            provider.upload_file(active_organization_id, active_project_id, local_file, content)

    click.echo("Sync completed successfully.")

@cli.command()
@click.pass_obj
@click.option('--interval', type=int, default=5, prompt='Enter sync interval in minutes')
@handle_errors
def schedule(config, interval):
    """Set up a cron job to run claudesync remote sync at regular intervals"""
    claudesync_path = shutil.which('claudesync')
    if not claudesync_path:
        click.echo("Error: claudesync not found in PATH. Please ensure it's installed correctly.")
        sys.exit(1)

    if sys.platform.startswith('win'):
        click.echo("Windows Task Scheduler setup:")
        command = f'schtasks /create /tn "ClaudeSync" /tr "{claudesync_path} sync" /sc minute /mo {interval}'
        click.echo(f"Run this command to create the task:\n{command}")
        click.echo("\nTo remove the task, run: schtasks /delete /tn \"ClaudeSync\" /f")
    else:
        # Unix-like systems (Linux, macOS)
        cron = CronTab(user=True)
        job = cron.new(command=f'{claudesync_path} sync')
        job.minute.every(interval)

        cron.write()
        click.echo(f"Cron job created successfully! It will run every {interval} minutes.")
        click.echo("\nTo remove the cron job, run: crontab -e and remove the line for ClaudeSync")

if __name__ == '__main__':
    cli()