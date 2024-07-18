import os
import hashlib
import mimetypes
import pathspec

def calculate_checksum(content):
    normalized_content = content.replace('\r\n', '\n').replace('\r', '\n').strip()
    return hashlib.md5(normalized_content.encode('utf-8')).hexdigest()

def load_gitignore(base_path):
    patterns = []
    current_dir = base_path
    while True:
        gitignore_path = os.path.join(current_dir, '.gitignore')
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                patterns.extend(f.read().splitlines())

        if os.path.exists(os.path.join(current_dir, '.git')):
            break  # Stop if we've reached the root of the Git repository

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir or parent_dir == base_path:
            break  # Stop if we've reached the filesystem root or the base watched directory
        current_dir = parent_dir

    return pathspec.PathSpec.from_lines('gitwildmatch', patterns) if patterns else None

def should_ignore(gitignore, local_path):
    # Check file type
    mime_type, _ = mimetypes.guess_type(local_path)
    if mime_type and not mime_type.startswith('text/'):
        return True
    # Check if .git dir
    if '.git' in local_path.split(os.sep):
        return True
    # Check if temporary editor file
    if local_path.endswith("~"):
        return True
    # Check if too big
    if os.path.getsize(local_path) > 200 * 1024:
        return True
    # Check .gitignore
    return gitignore.match_file(local_path) if gitignore else False

def get_local_files(local_path):
    gitignore = load_gitignore(local_path)
    files = {}
    for root, _, filenames in os.walk(local_path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            if not should_ignore(gitignore, file_path):
                rel_path = os.path.relpath(file_path, local_path)
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    files[rel_path] = calculate_checksum(content)
    return files