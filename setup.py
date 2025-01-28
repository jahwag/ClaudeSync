from setuptools import setup, find_packages

setup(
    name="claudesync",
    version="0.1.2",
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
            'web/dist/claudesync-simulate/**/*',  # Include frontend build artifacts
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
        "tiktoken",
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
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.10",
)