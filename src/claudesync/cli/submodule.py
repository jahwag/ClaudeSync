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
        click.echo("No local path set. Please select or create a project first.")
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
    """Create new projects for each detected submodule."""
    provider = validate_and_get_provider(config, require_project=True)
    active_organization_id = config.get("active_organization_id")
    active_project_id = config.get("active_project_id")
    active_project_name = config.get("active_project_name")
    local_path = config.get("local_path")

    if not local_path:
        click.echo("No local path set. Please select or create a project first.")
        return

    submodule_detect_filenames = config.get("submodule_detect_filenames", [])
    submodules = detect_submodules(local_path, submodule_detect_filenames)

    if not submodules:
        click.echo("No submodules detected in the current project.")
        return

    click.echo(f"Detected {len(submodules)} submodule(s). Creating projects for each:")

    for i, submodule in enumerate(submodules, 1):
        submodule_name = os.path.basename(submodule)
        new_project_name = f"{active_project_name}-SubModule-{submodule_name}"
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

    click.echo(
        "\nSubmodule projects created successfully. You can now select and sync these projects individually."
    )
