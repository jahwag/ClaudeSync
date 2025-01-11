#!/usr/bin/env python3
import os
import subprocess
import sys


def get_changed_files() -> list[str]:
    """Get list of Python files that are staged for commit."""
    try:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        files = result.stdout.strip().split("\n")
        return [f for f in files if f.endswith(".py") and os.path.exists(f)]
    except subprocess.CalledProcessError:
        print("Failed to get changed files")
        return []


def format_files(files: list[str]) -> tuple[bool, list[str]]:
    """Format the given files using black."""
    if not files:
        return True, []

    formatted_files = []
    try:
        subprocess.run(["black", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(
            "Error: black is not installed. Please install it with: pip install black"
        )
        return False, []

    for file_path in files:
        try:
            subprocess.run(
                ["black", "--quiet", file_path], capture_output=True, check=True
            )
            formatted_files.append(file_path)
        except subprocess.CalledProcessError as e:
            print(f"Failed to format {file_path}: {e}")
            return False, formatted_files

    return True, formatted_files


def main():
    files = get_changed_files()
    if not files:
        print("No Python files to format")
        sys.exit(0)

    print("Formatting Python files with black...")
    success, formatted_files = format_files(files)

    if formatted_files:
        print("\nFormatted files:")
        for file in formatted_files:
            print(f"  - {file}")

        # Re-stage formatted files
        try:
            subprocess.run(["git", "add"] + formatted_files, check=True)
            print("\nFormatted files have been re-staged")
        except subprocess.CalledProcessError:
            print("Failed to re-stage formatted files")
            sys.exit(1)

    if not success:
        print("\nSome files could not be formatted")
        sys.exit(1)

    print("\nAll files formatted successfully")
    sys.exit(0)


if __name__ == "__main__":
    main()
