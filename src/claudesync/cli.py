
import click
from .config_manager import ConfigManager
from .provider_factory import get_provider
from .exceptions import ConfigurationError, ProviderError

def validate_and_get_provider(config, require_org=True):
    """
    Validate configuration and return an initialized provider.
    Raises ConfigurationError if any required config is missing.
    """
    active_provider = config.get('active_provider')
    if not active_provider:
        raise ConfigurationError("No active provider set. Please login first.")

    session_key = config.get('session_key')
    if not session_key:
        raise ConfigurationError("No session key found. Please login first.")

    if require_org:
        active_organization_id = config.get('active_organization_id')
        if not active_organization_id:
            raise ConfigurationError("No active organization set. Please use 'claudesync organization select' to choose an organization.")

    try:
        return get_provider(active_provider, session_key)
    except ValueError as e:
        raise ConfigurationError(str(e))

@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = ConfigManager()

@cli.command()
@click.argument('provider', required=False)
@click.pass_obj
def login(config, provider):
    providers = get_provider()

    if not provider:
        click.echo("Available providers:")
        for p in providers:
            click.echo(f"  - {p}")
        return

    if provider not in providers:
        click.echo(f"Error: Unknown provider '{provider}'. Available providers are: {', '.join(providers)}")
        return

    try:
        provider_instance = get_provider(provider)
        session_key = provider_instance.login()
        config.set('session_key', session_key)
        config.set('active_provider', provider)
        click.echo("Logged in successfully.")
    except ProviderError as e:
        click.echo(f"Error during login: {str(e)}")

@cli.command()
@click.pass_obj
def logout(config):
    click.echo("Logging out...")
    config.set('session_key', None)
    config.set('active_provider', None)
    config.set('active_organization_id', None)
    click.echo("Logged out successfully.")

@cli.group()
def organization():
    pass

@organization.command()
@click.pass_obj
def list(config):
    click.echo("Listing organizations...")

    try:
        provider = validate_and_get_provider(config, require_org=False)
        organizations = provider.get_organizations()

        if not organizations:
            click.echo("No organizations found.")
        else:
            click.echo("Available organizations:")
            for idx, org in enumerate(organizations, 1):
                click.echo(f"  {idx}. {org['name']} (ID: {org['id']})")
    except (ConfigurationError, ProviderError) as e:
        click.echo(f"Error: {str(e)}")

@organization.command()
@click.pass_obj
def select(config):
    click.echo("Selecting an organization...")

    try:
        # Note the False argument here to not require an organization
        provider = validate_and_get_provider(config, require_org=False)
        organizations = provider.get_organizations()

        if not organizations:
            click.echo("No organizations found.")
            return

        click.echo("Available organizations:")
        for idx, org in enumerate(organizations, 1):
            click.echo(f"  {idx}. {org['name']} (ID: {org['id']})")

        selection = click.prompt("Enter the number of the organization you want to select", type=int)
        if 1 <= selection <= len(organizations):
            selected_org = organizations[selection - 1]
            config.set('active_organization_id', selected_org['id'])
            click.echo(f"Selected organization: {selected_org['name']} (ID: {selected_org['id']})")
        else:
            click.echo("Invalid selection. Please run the command again and select a valid number.")
    except (ConfigurationError, ProviderError) as e:
        click.echo(f"Error: {str(e)}")

@cli.group()
def project():
    pass

@project.command()
@click.pass_obj
def select(config):
    click.echo("Selecting a project...")

    try:
        provider = validate_and_get_provider(config)
        active_organization_id = config.get('active_organization_id')
        if not active_organization_id:
            raise ConfigurationError("No active organization set. Please use 'claudesync organization select' to choose an organization.")

        projects = provider.get_projects(active_organization_id, include_archived=False)

        if not projects:
            click.echo("No active projects found.")
            return

        click.echo("Available projects:")
        for idx, project in enumerate(projects, 1):
            click.echo(f"  {idx}. {project['name']} (ID: {project['id']})")

        selection = click.prompt("Enter the number of the project you want to select", type=int)
        if 1 <= selection <= len(projects):
            selected_project = projects[selection - 1]
            config.set('active_project_id', selected_project['id'])
            config.set('active_project_name', selected_project['name'])
            click.echo(f"Selected project: {selected_project['name']} (ID: {selected_project['id']})")
        else:
            click.echo("Invalid selection. Please run the command again and select a valid number.")
    except (ConfigurationError, ProviderError) as e:
        click.echo(f"Error: {str(e)}")

@project.command()
@click.option('-a', '--all', 'show_all', is_flag=True, help="Show all projects, including archived ones")
@click.pass_obj
def ls(config, show_all):
    click.echo("Listing remote projects...")

    try:
        provider = validate_and_get_provider(config)
        active_organization_id = config.get('active_organization_id')
        if not active_organization_id:
            raise ConfigurationError("No active organization set. Please use 'claudesync organization select' to choose an organization.")

        projects = provider.get_projects(active_organization_id, include_archived=show_all)

        if not projects:
            click.echo("No projects found.")
        else:
            click.echo("Remote projects:")
            for project in projects:
                status = " (Archived)" if project.get('archived_at') else ""
                click.echo(f"  - {project['name']} (ID: {project['id']}){status}")
    except (ConfigurationError, ProviderError) as e:
        click.echo(f"Error: {str(e)}")

@project.command()
@click.argument('project_id')
@click.argument('local_path')
@click.pass_obj
def add(config, project_id, local_path):
    click.echo(f"Adding project {project_id} at {local_path}")
    projects = config.get('projects', {})
    projects[project_id] = local_path
    config.set('projects', projects)
    click.echo("Project added successfully.")

@project.command()
@click.argument('project_id')
@click.pass_obj
def rm(config, project_id):
    click.echo(f"Removing project {project_id}")
    projects = config.get('projects', {})
    if project_id in projects:
        del projects[project_id]
        config.set('projects', projects)
        click.echo("Project removed successfully.")
    else:
        click.echo("Project not found.")

@cli.command()
@click.pass_obj
def status(config):
    click.echo("ClaudeSync status:")
    active_provider = config.get('active_provider')
    if active_provider:
        click.echo(f"Active provider: {active_provider}")
    else:
        click.echo("No active provider set.")

    active_organization_id = config.get('active_organization_id')
    if active_organization_id:
        click.echo(f"Active organization ID: {active_organization_id}")
    else:
        click.echo("No active organization set.")

    projects = config.get('projects', {})
    if projects:
        click.echo("Synced projects:")
        for project_id, local_path in projects.items():
            click.echo(f"  - {project_id}: {local_path}")
    else:
        click.echo("No projects are currently being synced.")

@cli.group()
def config():
    pass

@config.command()
@click.argument('key')
@click.argument('value', required=False)
@click.pass_obj
def set(config, key, value):
    if key == 'log_level':
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if value not in valid_levels:
            click.echo(f"Invalid log level. Choose from: {', '.join(valid_levels)}")
            return
    if value:
        click.echo(f"Setting {key} to {value}")
        config.set(key, value)
    else:
        click.echo(f"Current value of {key}: {config.get(key)}")

@config.command()
@click.argument('key')
@click.pass_obj
def get(config, key):
    value = config.get(key)
    click.echo(f"{key}: {value}")

@cli.group()
def remote():
    pass

@remote.command()
@click.pass_obj
def ls(config):
    click.echo("Listing files in the active project...")

    try:
        provider = validate_and_get_provider(config)
        active_organization_id = config.get('active_organization_id')
        active_project_id = config.get('active_project_id')

        if not active_organization_id:
            raise ConfigurationError("No active organization set. Please use 'claudesync organization select' to choose an organization.")
        if not active_project_id:
            raise ConfigurationError("No active project set. Please use 'claudesync project select' to choose a project.")

        files = provider.list_files(active_organization_id, active_project_id)

        if not files:
            click.echo("No files found in the active project.")
        else:
            click.echo(f"Files in project '{config.get('active_project_name')}' (ID: {active_project_id}):")
            for file in files:
                click.echo(f"  - {file['file_name']} (ID: {file['id']}, Created: {file['created_at']})")
    except (ConfigurationError, ProviderError) as e:
        click.echo(f"Error: {str(e)}")

if __name__ == '__main__':
    cli()