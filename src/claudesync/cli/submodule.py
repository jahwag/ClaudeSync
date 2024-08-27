import os

import click
from claudesync.exceptions import ProviderError
from ..utils import (
    handle_errors,
    validate_and_get_provider,
    detect_submodules,
)


@click.group()
def submodule():
    """Manage submodules within the current project."""
    pass


@submodule.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List all detected submodules in the current project."""
    local_path = config.get("local_path")
    if not local_path:
        click.echo(
            "No local path set for this project. Please select an existing project or create a new one using "
            "'claudesync project select' or 'claudesync project create'."
        )
        return

    submodule_detect_filenames = config.get("submodule_detect_filenames", [])
    submodules = detect_submodules(local_path, submodule_detect_filenames)

    if not submodules:
        click.echo("No submodules detected in the current project.")
    else:
        click.echo("Detected submodules:")
        for submodule, detected_file in submodules:
            click.echo(f"  - {submodule} [{detected_file}]")


@submodule.command()
@click.pass_obj
@handle_errors
def create(config):
    """Create new projects for each detected submodule that doesn't already exist remotely."""
    provider = validate_and_get_provider(config, require_project=True)
    active_organization_id = config.get("active_organization_id")
    active_project_id = config.get("active_project_id")
    active_project_name = config.get("active_project_name")
    local_path = config.get("local_path")

    if not local_path:
        click.echo(
            "No local path set for this project. Please select an existing project or create a new one using "
            "'claudesync project select' or 'claudesync project create'."
        )
        return

    submodule_detect_filenames = config.get("submodule_detect_filenames", [])
    submodules_with_files = detect_submodules(local_path, submodule_detect_filenames)

    # Extract only the submodule paths from the list of tuples
    submodules = [submodule for submodule, _ in submodules_with_files]

    if not submodules:
        click.echo("No submodules detected in the current project.")
        return

    # Fetch all remote projects
    all_remote_projects = provider.get_projects(
        active_organization_id, include_archived=False
    )

    click.echo(
        f"Detected {len(submodules)} submodule(s). Checking for existing remote projects:"
    )

    for i, submodule in enumerate(submodules, 1):
        submodule_name = os.path.basename(submodule)
        new_project_name = f"{active_project_name}-SubModule-{submodule_name}"

        # Check if the submodule project already exists
        existing_project = next(
            (p for p in all_remote_projects if p["name"] == new_project_name), None
        )

        if existing_project:
            click.echo(
                f"{i}. Submodule '{submodule_name}' already exists as project "
                f"'{new_project_name}' (ID: {existing_project['id']}). Skipping."
            )
        else:
            description = f"Submodule '{submodule_name}' for project '{active_project_name}' (ID: {active_project_id})"
            try:
                new_project = provider.create_project(
                    active_organization_id, new_project_name, description
                )
                click.echo(
                    f"{i}. Created project '{new_project_name}' (ID: {new_project['uuid']}) for submodule '{submodule_name}'"
                )
            except ProviderError as e:
                click.echo(
                    f"Failed to create project for submodule '{submodule_name}': {str(e)}"
                )

    click.echo("\nSubmodule project creation process completed.")
