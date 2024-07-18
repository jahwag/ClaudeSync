import os

import click
from functools import wraps
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

@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = ConfigManager()

@cli.command()
@click.argument('provider', required=False)
@click.pass_obj
@handle_errors
def login(config, provider):
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
    for key in ['session_key', 'active_provider', 'active_organization_id']:
        config.set(key, None)
    click.echo("Logged out successfully.")

@cli.group()
def organization():
    pass

@organization.command()
@click.pass_obj
@handle_errors
def list(config):
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
    pass

@project.command()
@click.pass_obj
@handle_errors
def archive(config):
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
    else:
        click.echo("Invalid selection. Please try again.")

@project.command()
@click.option('-a', '--all', 'show_all', is_flag=True, help="Show all projects, including archived ones")
@click.pass_obj
@handle_errors
def ls(config, show_all):
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
    click.echo("ClaudeSync status:")
    for key in ['active_provider', 'active_organization_id']:
        value = config.get(key)
        click.echo(f"{key.replace('_', ' ').capitalize()}: {value or 'Not set'}")
    projects = config.get('projects', {})
    if projects:
        click.echo("Synced projects:")
        for project_id, local_path in projects.items():
            click.echo(f"  - {project_id}: {local_path}")
    else:
        click.echo("No projects are currently being synced.")

@cli.group()
def remote():
    pass

@remote.command()
@click.pass_obj
@handle_errors
def ls(config):
    provider = validate_and_get_provider(config)
    active_organization_id = config.get('active_organization_id')
    active_project_id = config.get('active_project_id')
    files = provider.list_files(active_organization_id, active_project_id)
    if not files:
        click.echo("No files found in the active project.")
    else:
        click.echo(f"Files in project '{config.get('active_project_name')}' (ID: {active_project_id}):")
        for file in files:
            click.echo(f"  - {file['file_name']} (ID: {file['id']}, Created: {file['created_at']})")

@remote.command()
@click.pass_obj
@handle_errors
def sync(config):
    provider = validate_and_get_provider(config)
    active_organization_id = config.get('active_organization_id')
    active_project_id = config.get('active_project_id')
    local_path = config.get('local_path')
    if not local_path:
        raise ConfigurationError("No local path set. Use 'claudesync config set local_path <path>' to set it.")

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

if __name__ == '__main__':
    cli()