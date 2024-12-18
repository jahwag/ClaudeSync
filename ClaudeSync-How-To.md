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

Make sure, that the virtual environment is added to your .gitignore file:
```
# .gitignore
.venv/
```

2. Install ClaudeSync fork with _simulate-push_ feature using pip:

```bash
pip install https://github.com/tbuechner/ClaudeSync/raw/refs/heads/master/dist/claudesync-0.6.6-py3-none-any.whl    
```

## Authentication

Authentication with Claude.ai needs to be done once:

1. Run the authentication command:
```bash
claudesync auth login
```

Note: The ssh key must sit at the default location `~/.ssh/id_ed25519`.

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
    - A `.claudesync` directory in your project folder - if it doesn't already exist
    - Two local configuration files:
        - `name_of_the_project.project.json` - contains the description of the project and the context
        - `name_of_the_project.project_id.json` - contains the ID of the project on Claude.ai

The `name_of_the_project.project.json` file is intended to be shared with other team members. It can (and should) be checked into version history. It contains the project description and the specification of the context.

The `name_of_the_project.project_id.json` file is intended to be kept private. It contains the ID of the project on Claude.ai and should not be shared. It should be excluded from version history:

```
# .gitignore
.claudesync/*.project_id.json
.claudesync/active_project.json
```

## Synchronization Configuration

### Using .claudeignore

Create a `.claudeignore` file in your project root to exclude files:

```text
# Example .claudeignore
*.pyc
__pycache__/
.git/
.env
node_modules/
```

### Using Project Configuration

If you have a large codebase and want to synchronize only specific files with Claude.ai, you can configure one or multiple project contexts. A project context is a set of inclusion and exclusion patterns that define which files are synchronized with Claude.ai:

`xxx.project.json`:
```json
{
   "project_name": "main - Persistence",
   "includes": [
      "cf.cplace.platform/src/main/java/cf/cplace/platform/core/datamodel/persistence/*.java",
      "cf.cplace.platform/src/main/java/cf/cplace/platform/core/datamodel/persistence/criteria/*.java",
      "cf.cplace.platform/src/main/java/cf/cplace/platform/core/datamodel/persistence/customquery/*.java"
   ],
   "excludes": [
      "BatchUpdatesLocalListeners.java",
      "ToStringQueryVisitorWithoutValues.java",
      "QueryUnaryOperator.java",
      "QueryBinaryOperator.java",
      "StatementProtocolWrapper.java",
      "ConnectionsTracker.java",
      "StatementWrapper.java",
      "DateAttributeForMigration.java"
   ],
   "simulate_push_roots": [
      "cf.cplace.platform/src/main/java/cf/cplace/platform/core/datamodel/persistence"
   ]
}
```

Recommendation regarding project files is to have multiple claude projects for a single codebase. Each project should have a different context. This way, the knowledge capacity of the project is not exceeded and the knowledge is more effective.

Before pushing for the first time make use of the _simulate-push_ feature to see which files will be pushed to Claude.ai:
```bash
claudesync simulate-push
```

## Working with Claude.ai

### Initial Push

Push your project files to Claude.ai:
```bash
claudesync push name-of-the-project
```

Visit the project on [Claude.ai](https://claude.ai) to see the synchronized files.

After pushing the specified project, the project is set to be the _active project_. The active project is used for all subsequent commands. To change the active project, use the following command:

```bash
claudesync project set name-of-the-project
```

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

- GitHub Issues: [Report bugs](https://github.com/tbuechner/claudesync/issues)
