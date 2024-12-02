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
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

2. Install ClaudeSync using pip:

```bash
pip install claudesync
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

File categories can be configured in two ways:

1. Using CLI commands:
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

2. Directly editing `.claudesync/config.local.json`:
```json
{
  "file_categories": {
    "mycategory": {
      "description": "My custom file selection",
      "patterns": [
        "*.py",
        "*.md",
        "src/**/*.js"
      ]
    }
  }
}
```

## Working with Claude.ai

### Initial Push

Push your project files to Claude.ai:
```bash
claudesync push
```

### Development Workflow Example

1. Visit [Claude.ai](https://claude.ai) in your browser and start a new chat in your project.

2. Ask Claude about a feature you want to implement. For example:
   "How can I implement error handling for network timeouts in my Python application?"

3. Implement the suggested changes locally in your development environment.

4. Push the updated files to Claude:
```bash
claudesync push
```

5. Return to your [Claude.ai](https://claude.ai) chat in the browser to discuss the implementation and ask for improvements or additional features.

### Tips for Effective Collaboration

1. Keep conversations focused on specific features or issues
2. Push changes frequently to maintain context
3. If you have a large codebase, break it down into smaller pieces, try not to exceed 30% of the available knowledge capacity of the claude project. If you do, you increase the risk of running into the rate limit and the knowledge will be less effective. In file `.claudesync/file_categories.json` you can see an exemplary decomposition of this project into smaller subprojects.

## Support

- GitHub Issues: [Report bugs](https://github.com/jahwag/claudesync/issues)
- Discord: [Join community](https://discord.gg/pR4qeMH4u4)
- Documentation: [Wiki](https://github.com/jahwag/claudesync/wiki)
