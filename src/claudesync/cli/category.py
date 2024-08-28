import click
from ..utils import handle_errors


@click.group()
def category():
    """Manage file categories."""
    pass


@category.command()
@click.argument("name")
@click.option("--description", required=True, help="Description of the category")
@click.option(
    "--patterns", required=True, multiple=True, help="File patterns for the category"
)
@click.pass_obj
@handle_errors
def add(config, name, description, patterns):
    """Add a new file category."""
    config.add_file_category(name, description, list(patterns))
    click.echo(f"File category '{name}' added successfully.")


@category.command()
@click.argument("name")
@click.pass_obj
@handle_errors
def rm(config, name):
    """Remove a file category."""
    config.remove_file_category(name)
    click.echo(f"File category '{name}' removed successfully.")


@category.command()
@click.argument("name")
@click.option("--description", help="New description for the category")
@click.option("--patterns", multiple=True, help="New file patterns for the category")
@click.pass_obj
@handle_errors
def update(config, name, description, patterns):
    """Update an existing file category."""
    config.update_file_category(name, description, list(patterns) if patterns else None)
    click.echo(f"File category '{name}' updated successfully.")


@category.command()
@click.pass_obj
@handle_errors
def ls(config):
    """List all file categories."""
    categories = config.get("file_categories", {})
    if not categories:
        click.echo("No file categories defined.")
    else:
        for name, data in categories.items():
            click.echo(f"\nCategory: {name}")
            click.echo(f"Description: {data['description']}")
            click.echo("Patterns:")
            for pattern in data["patterns"]:
                click.echo(f"  - {pattern}")


@category.command()
@click.argument("category", required=True)
@click.pass_obj
@handle_errors
def set_default(config, category):
    """Set the default category for synchronization."""
    config.set_default_category(category)
    click.echo(f"Default sync category set to: {category}")
