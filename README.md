# ClaudeSync User Guide

This is a fork of the original [ClaudeSync](https://github.com/jahwag/ClaudeSync) repository. The fork adds the _simulate-push_ feature, which allows you to see which files will be pushed to Claude.ai before actually pushing them. In addition, it enables sharing project contexts with other team members.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Authentication](#authentication)
- [Project Setup](#project-setup)
- [Synchronization Configuration](#synchronization-configuration)
- [Working with Claude.ai](#working-with-claudeai)
- [Developing claudesync](#developing-claudesync)

## Prerequisites

Before installing ClaudeSync, ensure you have:
- Python 3.10 or higher
- A Claude.ai Pro or Team account
- A terminal or command prompt
- SSH key for secure credential storage. Follow [GitHub's guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh) to generate and add your SSH key.

## Installation and Upgrading

The recommendation is to install ClaudeSync in a virtual python environment in the folder you want to synchronize with Claude.ai.

### Unix based

```bash
rm -rf .venv; \
python3 -m venv .venv; \
echo "*" > .venv/.gitignore; \
source .venv/bin/activate; \
pip install https://github.com/tbuechner/ClaudeSync/raw/refs/heads/master/dist/claudesync_fork-0.1.10-py3-none-any.whl
```

### Windows git bash

```bash
rm -rf .venv; \
python3 -m venv .venv; \
echo "*" > .venv/.gitignore; \ 
source .venv/Scripts/activate; \
pip install https://github.com/tbuechner/ClaudeSync/raw/refs/heads/master/dist/claudesync_fork-0.1.10-py3-none-any.whl
```

## Authentication

Authentication with Claude.ai needs to be done once:

1. Run the authentication command:
```bash
claudesync auth login
```

Note: The ssh key must sit at the default location `~/.ssh/id_ed25519`.

If you see this error message: `Failed to retrieve organizations. Please enter a valid sessionKey.` have a look here: [ssl-error](known-issue-ssl-error.md)

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
- Title of the project (defaults to current directory name)
- Internal name of the project - used for config files (defaults to `all`)
- Description of the project - (defaults to "Project created with ClaudeSync")

```
❯ claudesync project create
Enter a title for your new project [cplace-paw]: cplace-paw - Draggable Page List
Enter the internal name for your project (used for config files) [all]: draggable-page-list
Enter the project description [Project created with ClaudeSync]: 
Project 'cplace-paw - Draggable Page List' (uuid: 1dfc27c5-971a-4046-b922-a833db7ef7cc) has been created successfully.

Project created and set as active:
  - Project location: /Users/thomasbuechner/dev/repos/cplace-paw
  - Project ID config: /Users/thomasbuechner/dev/repos/cplace-paw/.claudesync/draggable-page-list.project_id.json
  - Project config: /Users/thomasbuechner/dev/repos/cplace-paw/.claudesync/draggable-page-list.project.json
  - Remote URL: https://claude.ai/project/1dfc27c5-971a-4046-b922-a833db7ef7cc
```


2. The command will create:
   - A new project on Claude.ai
   - A `.claudesync` directory in your project folder - if it doesn't already exist
   - Two local configuration files:
      - `internal_name.project.json` - contains the description of the project and the context
      - `internal_name.project_id.json` - contains the ID of the project on Claude.ai

The `internal_name.project.json` file is intended to be shared with other team members. It can (and should) be checked into version history. It contains the project description and the specification of the context.

The `internal_name_of_the_project.project_id.json` file is intended to be kept private. It contains the ID of the project on Claude.ai and should not be shared. It should be excluded from version history:

```
# .gitignore
.claudesync/*.project_id.json
.claudesync/active_project.json
```

## Synchronization Configuration

### .claudeignore

Create a `.claudeignore` file in your project root to exclude files from synchronization. The `.claudeignore` file uses the same syntax as `.gitignore`:

```text
# Example .claudeignore
*.pyc
__pycache__/
.git/
.env
node_modules/
.venv/
```

The `.claudeignore` file is intended to be shared with other team members. It can (and should) be checked into version history. There is one version of the `.claudeignore` file per folder in which ClaudeSync is applied.

### Project Configuration

If you have a large codebase and want to synchronize only specific files with Claude.ai, you can configure one or multiple project contexts. A project context is a set of inclusion and exclusion patterns that define which files are synchronized with Claude.ai:

`xxx.project.json`:
```json
{
   "project_name": "cplace-paw - Draggable Page List",
   "project_description": "Project created with ClaudeSync",
   "includes": [
      "cf.cplace.draggablePageList/src",
      "cf.cplace.draggablePageList/assets/ts",
      "cf.cplace.draggablePageList/assets/less"
   ],
   "excludes": [],
   "use_ignore_files": false,
   "push_roots": [
      "cf.cplace.draggablePageList"
   ]
}
```

Recommendation regarding project files is to have multiple claude projects for a single codebase. Each project should have a different context. This way, the knowledge capacity of the project is not exceeded and the knowledge is more effective.

Before pushing for the first time make use of the _simulate-push_ feature to see which files will be pushed to Claude.ai:
```bash
claudesync simulate-push
```
### Project Configuration Properties

The `xxx.project.json` file contains several properties that control how files are synchronized with Claude.ai:

- `project_name`: The display name of the project shown in Claude.ai.
- `project_description`: A brief description of what the project is about.
- `includes`: An array of file path patterns to include in the synchronization. These can use glob patterns like `*.js` or specify directories like `src/components`. Paths are relative to the project root, not to the push roots.
- `excludes`: An array of file path patterns to exclude from synchronization. These patterns override matching patterns in the `includes` array. Paths are relative to the project root, not to the push roots.
- `use_ignore_files`: Boolean value (true/false) that determines whether to use `.gitignore` and `.claudeignore` files for additional exclusion rules.
- `push_roots`: An array of root directories to start the file search from. This is useful for large repositories where you only want to focus on specific subdirectories. Only files within these directories will be considered for synchronization, regardless of include patterns.

Example configuration:
```json
{
   "project_name": "My API Service",
   "project_description": "Backend service for user authentication and data management",
   "includes": [
      "src/**/*.ts",
      "config/*.json",
      "docs/README.md"
   ],
   "excludes": [
      "src/**/*.test.ts",
      "src/deprecated/**"
   ],
   "use_ignore_files": true,
   "push_roots": [
      "src",
      "config",
      "docs"
   ]
}
```

This configuration will:
1. Include all TypeScript files in the `src` directory and its subdirectories
2. Include all JSON files in the `config` directory
3. Include the README.md file from the `docs` directory
4. Exclude all test files (ending with `.test.ts`)
5. Exclude all files in the `src/deprecated` directory
6. Respect patterns in `.gitignore` and `.claudeignore` files
7. Only search for files within the `src`, `config`, and `docs` directories

**Important Note**: When using `push_roots`, only files in the specified root directories will be considered for synchronization, even if they match patterns in the `includes` array. Each file must both match an include pattern AND be in one of the push_roots directories to be synchronized.

## Working with ClaudeSync and Claude.ai

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

### Creating Projects from Templates

ClaudeSync allows you to create new projects using existing project configurations as templates. This is useful for:
- Sharing standardized project setups with team members
- Creating multiple projects with similar synchronization settings
- Ensuring consistent configurations across related projects

To create a project from a template:

```bash
claudesync project create --template existing-project-name
```

Where `existing-project-name` is the internal name of an existing project (without the `.project.json` extension).

This command will:
1. Copy the synchronization settings (includes/excludes patterns) from the template
2. Prompt you for a new project name (or use the template's name if not provided)
3. Create a new project on Claude.ai with these settings
4. Keep the existing file patterns and configuration

**Example workflow for team collaboration:**

1. Developer A creates an initial project with the right context configuration:
   ```bash
   claudesync project create
   # Configure includes/excludes for the project
   ```

2. Developer A commits the `.claudesync/project-name.project.json` file to version control

3. Developer B clones the repository and creates their own linked project:
   ```bash
   claudesync project create --template project-name
   ```

4. Developer B now has an identical project configuration but with their own Claude.ai project ID

This allows team members to share the same context definition while maintaining separate Claude.ai projects.

### Tips for Effective Collaboration

1. Keep conversations focused on specific features or issues
2. Push changes frequently to maintain context
3. If you have a large codebase, break it down into smaller pieces, try not to exceed 30% of the available knowledge capacity of the claude project. If you do, you increase the risk of running into the rate limit and the knowledge will be less effective. In file `.claudesync/example-file-categories.json` you can see an exemplary decomposition of this project into smaller subprojects.

### Prompt Templates

For effective communication with Claude AI, check out the [Useful Prompts](useful-prompts.md) document. It contains a collection of tested prompt templates for:
- Assessing context quality
- Planning implementations
- Creating documentation
- Validating changes
- Summarizing conversations

These templates can significantly improve your productivity when working with Claude AI projects.

## Support

- GitHub Issues: [Report bugs](https://github.com/tbuechner/claudesync/issues)
- Slack [#claude-ai-poc](https://collaborationfactory.slack.com/archives/C083AVA11KP)

### Developing claudesync

- Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for more information.

