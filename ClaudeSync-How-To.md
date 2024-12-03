# ClaudeSync User Guide

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Authentication](#authentication)
- [Project Setup](#project-setup)
- [Synchronization Configuration](#synchronization-configuration)
- [Working with Claude.ai](#working-with-claudeai)

## Prerequisites

Before installing ClaudeSync, ensure you have:
- Python 3.10 or higher
- A Claude.ai Pro or Team account
- A terminal or command prompt
- SSH key for secure credential storage. Follow [GitHub's guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh) to generate and add your SSH key.

## Installation

1. Create and activate a virtual environment:

```bash
# Create a new virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

Make sure, that the virtual environment is added to your .gitignore file.

2. Install ClaudeSync fork with _simulate-push_ feature using pip:

```bash
pip install git+ssh://git@github.com/tbuechner/ClaudeSync.git    
```

## Authentication

Authentication with Claude.ai needs to be done once:

1. Run the authentication command:
```bash
claudesync auth login
```

2. Follow the on-screen instructions:
    - Open Claude.ai in your browser
    - Open Developer Tools (F12 or Ctrl+Shift+I)
    - Go to Application/Storage tab
    - Find the `sessionKey` cookie
    - Copy its value (starts with `sk-ant`)
    - Paste it into the terminal when prompted
    - Enter or confirm the expiration date

## Project Setup

1. Create a new project:
```bash
claudesync project create
```

You'll be prompted for:
- Project name (defaults to current directory name)
- Project description
- Local path (defaults to current directory)
- Provider (select claude.ai)
- Organization (if you have multiple)

2. The command will create:
    - A new project on Claude.ai
    - A `.claudesync` directory in your project folder
    - Local configuration files

## Synchronization Configuration

### Option 1: Using .claudeignore

Create a `.claudeignore` file in your project root to exclude files:

```text
# Example .claudeignore
*.pyc
__pycache__/
.git/
.env
node_modules/
```

### Option 2: Using File Categories

File categories are important if you have a large codebase and want to synchronize only specific files with Claude.ai.

File categories can be configured in two ways:

1. Directly editing `.claudesync/config.local.json`:
```json
{
   "active_provider": "claude.ai",
   "active_organization_id": "xxx",
   "active_project_id": "xxx",
   "active_project_name": "ClaudeSync - BE",
   "local_path": "/Users/thomasbuechner/dev/tmp/ClaudeSync",
   "file_categories": {
      "main": {
         "description": "Active Category",
         "patterns": [
            "*.py"
         ]
      }
   },
   "default_sync_category": "main"
}
```

2. Using CLI commands:
```bash
# List available categories
claudesync config category ls

# Create a custom category
claudesync config category add mycategory \
  --description "My custom file selection" \
  --patterns "*.py" "*.md" "src/**/*.js"

# Set as default category
claudesync config category set_default mycategory
```

Recommendation regarding file categories is to have multiple claude projects for a single codebase. We recommend having multiple `config.local.json` files, each with one file category and one project. Switch between them by renaming the desired `xx-config.local.json` to `config.local.json` and running `claudesync push`.

Before pushing for the first time make use of the _simulate-push_ feature to see which files will be pushed to Claude.ai:
```bash
claudesync simulate-push
```

## Working with Claude.ai

### Initial Push

Push your project files to Claude.ai:
```bash
claudesync push
```

Visit the project on [Claude.ai](https://claude.ai) to see the synchronized files.

### Development Workflow Example

1. Visit [Claude.ai](https://claude.ai), browse to your project and ask Claude about a feature you want to implement. For example:
   "How can I implement error handling for network timeouts in my Python application?"

2. Implement the suggested changes locally in your development environment.

3. Push the updated files to Claude:
```bash
claudesync push
```

4. Return to your [Claude.ai](https://claude.ai) project in the browser to discuss the implementation and ask for improvements or additional features.

### Tips for Effective Collaboration

1. Keep conversations focused on specific features or issues
2. Push changes frequently to maintain context
3. If you have a large codebase, break it down into smaller pieces, try not to exceed 30% of the available knowledge capacity of the claude project. If you do, you increase the risk of running into the rate limit and the knowledge will be less effective. In file `.claudesync/example-file-categories.json` you can see an exemplary decomposition of this project into smaller subprojects.

## Support

- GitHub Issues: [Report bugs](https://github.com/jahwag/claudesync/issues)
- Discord: [Join community](https://discord.gg/pR4qeMH4u4)
- Documentation: [Wiki](https://github.com/jahwag/claudesync/wiki)
