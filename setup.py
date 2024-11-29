from setuptools import setup, find_packages

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