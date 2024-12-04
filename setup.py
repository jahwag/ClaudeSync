from setuptools import setup, find_packages
import os
import subprocess
from setuptools.command.build_py import build_py

class BuildPyCommand(build_py):
    """Custom build command to build Angular app before Python package"""

    def run(self):
        # Only build frontend if not in a recursive build
        if not os.environ.get('SKIP_FRONTEND_BUILD'):
            # Current directory
            cwd = os.path.dirname(os.path.abspath(__file__))
            angular_dir = os.path.join(cwd, 'src', 'claudesync', 'web')

            if os.path.exists(angular_dir):
                # Only build if dist directory doesn't exist
                dist_dir = os.path.join(angular_dir, 'dist')
                if not os.path.exists(dist_dir):
                    print("Building Angular application...")
                    try:
                        # Install npm dependencies
                        subprocess.check_call(['npm', 'install'], cwd=angular_dir)
                        # Build the Angular app
                        subprocess.check_call(['npm', 'run', 'build'], cwd=angular_dir)
                    except subprocess.CalledProcessError as e:
                        print(f"Failed to build Angular application: {e}")
                        raise
                    except FileNotFoundError:
                        print("npm not found. Please install Node.js and npm first.")
                        raise

        # Run the standard build command
        build_py.run(self)

setup(
    name="claudesync",
    version="0.1.0",
    description="Synchronize local files with Claude AI projects",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Thomas Büchner",
    author_email="thomas.buechner@cplace.com",
    url="https://github.com/tbuechner/claudesync",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        'claudesync': [
            'web/dist/claudesync-simulate/**/*',  # Include all files in dist
        ]
    },
    include_package_data=True,
    install_requires=[
        "click",
        "click-completion",
        "tqdm",
        "pathspec",
        "python-crontab",
        "cryptography",
        "anthropic",
        "sseclient-py",
        "brotli",
    ],
    entry_points={
        "console_scripts": [
            "claudesync=claudesync.cli.main:cli",
        ],
    },
    cmdclass={
        'build_py': BuildPyCommand,
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)