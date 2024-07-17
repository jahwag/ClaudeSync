import os
import pathspec

def load_gitignore(base_path):
    patterns = []
    current_dir = base_path
    while True:
        gitignore_path = os.path.join(current_dir, '.gitignore')
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                patterns.extend(f.read().splitlines())

        if os.path.exists(os.path.join(current_dir, '.git')):
            # Stop if we've reached the root of the Git repository
            break

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir or parent_dir == base_path:
            # Stop if we've reached the filesystem root or the base watched directory
            break
        current_dir = parent_dir

    if patterns:
        return pathspec.PathSpec.from_lines('gitwildmatch', patterns)
    return None

def should_ignore(gitignore, file_path, base_path):
    if gitignore is None:
        return False
    rel_path = os.path.relpath(file_path, base_path)
    return gitignore.match_file(rel_path)