import os
import shutil
import stat
import subprocess
from pathlib import Path

import click

SUPPORTED_GIT_HOOKS = [
    "pre-commit",
]


def copy_hook(hooks_dir, hook_name):
    """
    Copy a specific hook from templates to git hooks directory.

    Args:
        hooks_dir: Path to the .git/hooks directory
        hook_name: Name of the hook to install
    """
    hook_path = hooks_dir / hook_name
    module_dir = Path(__file__).parent
    template_name = f"{hook_name.replace('-', '_')}.py"
    hook_template = module_dir / "hook_templates" / template_name

    if not hook_template.exists():
        click.echo(f"Warning: Template for {hook_name} not found at {hook_template}")
        return

    try:
        shutil.copy2(hook_template, hook_path)

        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IEXEC)

        click.echo(f"Successfully installed {hook_name} hook")
    except Exception as e:
        click.echo(f"Error installing {hook_name} hook: {e}")


def install_hooks():
    """Install all supported Git hooks for the project."""
    project_root = find_git_root()
    if not project_root:
        click.echo("Error: Not a git repository (or any of the parent directories)")
        return

    hooks_dir = project_root / ".git" / "hooks"
    if not hooks_dir.exists():
        click.echo(f"Creating hooks directory: {hooks_dir}")
        hooks_dir.mkdir(parents=True, exist_ok=True)

    for hook in SUPPORTED_GIT_HOOKS:
        copy_hook(hooks_dir, hook)

    click.echo("\nHook installation complete!")


def find_git_root():
    """Find the root directory of the Git repository"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return None


if __name__ == "__main__":
    install_hooks()
