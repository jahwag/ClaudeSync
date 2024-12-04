#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from pathlib import Path

def check_prerequisites():
    """Check if all required build tools are available."""
    # Check Python version
    if sys.version_info < (3, 8):
        raise RuntimeError("Python 3.8 or higher is required")

    # Check if npm is installed
    try:
        subprocess.run(['npm', '--version'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        raise RuntimeError("npm is not installed")
    except FileNotFoundError:
        raise RuntimeError("npm is not found in PATH")

    # Check if build tools are installed
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'show', 'build'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        raise RuntimeError("build package is not installed. Run: pip install build")

def clean_build_directories():
    """Clean up previous build artifacts."""
    directories_to_clean = [
        'build',
        'dist',
        'src/claudesync.egg-info'
    ]

    for directory in directories_to_clean:
        if os.path.exists(directory):
            print(f"Cleaning {directory}")
            shutil.rmtree(directory)

def build_frontend():
    """Build the Angular frontend application."""
    web_dir = Path('src/claudesync/web')

    # Check if frontend directory exists
    if not web_dir.exists():
        raise RuntimeError(f"Frontend directory not found at {web_dir}")

    print("Building frontend application...")

    # Install npm dependencies
    subprocess.run(['npm', 'install'], cwd=web_dir, check=True)

    # Build the Angular app
    subprocess.run(['npm', 'run', 'build'], cwd=web_dir, check=True)

    # Verify build output exists
    build_output = web_dir / 'dist'
    if not build_output.exists():
        raise RuntimeError("Frontend build failed - no dist directory created")

def create_manifest():
    """Create or update MANIFEST.in file."""
    manifest_content = """
# Include frontend dist files
recursive-include src/claudesync/web/dist *

# Include documentation
include README.md
include CONTRIBUTING.md
include SECURITY.md
include LICENSE

# Include additional files
include requirements.txt
""".strip()

    with open('MANIFEST.in', 'w') as f:
        f.write(manifest_content)

    print("Created MANIFEST.in")

def build_package():
    """Build both wheel and source distribution."""
    print("Building Python package...")
    try:
        env = os.environ.copy()
        env['SKIP_FRONTEND_BUILD'] = '1'  # Add flag to prevent recursive frontend builds
        subprocess.run([sys.executable, '-m', 'build'], env=env, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to build package: {e}")

def verify_dist():
    """Verify the built distributions."""
    dist_dir = Path('dist')
    if not dist_dir.exists():
        raise RuntimeError("Build failed - no dist directory created")

    distributions = list(dist_dir.glob('*'))
    if not distributions:
        raise RuntimeError("No distribution files were created")

    print("\nCreated distributions:")
    for dist in distributions:
        print(f"  - {dist.name}")

def main():
    try:
        # Ensure we're in the project root directory
        project_root = Path(__file__).resolve().parent
        os.chdir(project_root)

        # Check if we're in a recursive build
        if os.environ.get('SKIP_FRONTEND_BUILD'):
            print("Detected recursive build, skipping frontend build...")
            return

        print("Starting build process...")

        # Run all build steps
        check_prerequisites()
        clean_build_directories()
        build_frontend()
        create_manifest()
        build_package()
        verify_dist()

        print("\nBuild completed successfully!")
        print("\nTo publish to PyPI, run:")
        print("  python -m twine upload dist/*")

    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()