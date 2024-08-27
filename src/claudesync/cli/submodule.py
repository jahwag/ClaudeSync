import json
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
    local_path = config.get_local_path()
    if not local_path:
        click.echo(
            "No local project path found. Please select an existing project or create a new one using "
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
    """Creates new projects for each detected submodule that doesn't already exist remotely."""
    provider = validate_and_get_provider(config, require_project=True)
    active_organization_id = config.get("active_organization_id")
    active_project_id = config.get("active_project_id")
    active_project_name = config.get("active_project_name")
    local_path = config.get_local_path()

    if not local_path:
        click.echo(
            "No local project path found. Please select an existing project or create a new one using "
            "'claudesync project select' or 'claudesync project create'."
        )
        return

    submodule_detect_filenames = config.get("submodule_detect_filenames", [])
    submodules_with_files = detect_submodules(local_path, submodule_detect_filenames)

    if not submodules_with_files:
        click.echo("No submodules detected in the current project.")
        return

    # Fetch all remote projects
    all_remote_projects = provider.get_projects(
        active_organization_id, include_archived=False
    )

    click.echo(
        f"Detected {len(submodules_with_files)} submodule(s). Checking for existing remote projects:"
    )

    # Load existing local config
    local_config_path = os.path.join(local_path, ".claudesync", "config.local.json")
    with open(local_config_path, "r") as f:
        local_config = json.load(f)

    # Initialize submodules list if it doesn't exist
    if "submodules" not in local_config:
        local_config["submodules"] = []

    for i, (submodule, detected_file) in enumerate(submodules_with_files, 1):
        submodule_name = os.path.basename(submodule)
        new_project_name = f"{active_project_name}-SubModule-{submodule_name}"

        # Check if the submodule project already exists
        existing_project = next(
            (p for p in all_remote_projects if p["name"] == new_project_name), None
        )

        if existing_project:
            click.echo(
                f"{i}. Submodule '{submodule_name}' already exists as project "
                f"'{new_project_name}' (ID: {existing_project['id']}). Updating local config."
            )
            project_id = existing_project["id"]
        else:
            description = f"Submodule '{submodule_name}' for project '{active_project_name}' (ID: {active_project_id})"
            try:
                new_project = provider.create_project(
                    active_organization_id, new_project_name, description
                )
                project_id = new_project["uuid"]
                click.echo(
                    f"{i}. Created project '{new_project_name}' (ID: {project_id}) for submodule '{submodule_name}'"
                )
            except ProviderError as e:
                click.echo(
                    f"Failed to create project for submodule '{submodule_name}': {str(e)}"
                )
                continue

        # Update or add submodule information in local config
        submodule_config = {
            "active_provider": config.get("active_provider"),
            "active_organization_id": active_organization_id,
            "active_project_id": project_id,
            "active_project_name": new_project_name,
            "relative_path": submodule,
        }

        # Check if submodule already exists in config and update it, or append new entry
        submodule_index = next(
            (
                index
                for (index, d) in enumerate(local_config["submodules"])
                if d["relative_path"] == submodule
            ),
            None,
        )
        if submodule_index is not None:
            local_config["submodules"][submodule_index] = submodule_config
        else:
            local_config["submodules"].append(submodule_config)

    # Save updated local config
    with open(local_config_path, "w") as f:
        json.dump(local_config, f, indent=2)

    click.echo("\nSubmodule project creation and configuration update completed.")
