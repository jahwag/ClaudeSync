# ClaudeSync
[![GitHub Actions](https://github.com/jahwag/ClaudeSync/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/jahwag/ClaudeSync/actions/workflows/publish-to-pypi.yml)

ClaudeSync is a Python tool that automates the synchronization of local files with Claude.ai Projects. It watches specified directories and automatically uploads modified files to your Claude.ai Project's knowledge base.

Key features:
- Monitors local directories for file changes
- Automatically uploads new or modified files to Claude.ai Projects
- Configurable delay to prevent excessive uploads during active editing
- Supports both command-line arguments and config file for flexibility
- Handles recursive directory watching
- User-friendly Terminal User Interface (TUI)

Use ClaudeSync if you're working with Claude.ai Projects and want to keep your project's knowledge base updated with your local files without manual uploads.

![Illustration](https://raw.githubusercontent.com/jahwag/ClaudeSync/master/screen.png)

## Installation

Install ClaudeSync using pip:

```bash
pip install claudesync
```

## Configuration

You have two options for configuring ClaudeSync:

1. Command-line arguments (recommended for one-time use or testing)
2. Configuration file (recommended for repeated use)

### Option 1: Command-line Arguments

Provide your session key and watch directory directly in the command:

```bash
claudesync --session-key YOUR_SESSION_KEY --watch-dir /path/to/watch
```

### Option 2: Configuration File

Create a `config.json` file in your working directory:

```json
{
    "user_id": "your-user-id-here",
    "project_id": "your-project-id-here"
}
```

Then run ClaudeSync:

```bash
claudesync --session-key YOUR_SESSION_KEY --watch-dir /path/to/watch
```

## Usage

### Basic Usage

```bash
claudesync --session-key YOUR_SESSION_KEY --watch-dir /path/to/watch
```

### Parameters

- `--session-key`: Your Claude.ai session key (required)
- `--watch-dir`: Directory to watch for changes (default: current directory)
- `--user-id`: User ID for Claude API (optional if in config.json)
- `--project-id`: Project ID for Claude API (optional if in config.json)
- `--delay`: Delay in seconds before uploading (default: 5)

### Examples

Watch the current directory and sync changes:
```bash
claudesync --session-key YOUR_SESSION_KEY
```

Watch a specific directory with a custom delay:
```bash
claudesync --session-key YOUR_SESSION_KEY --watch-dir /path/to/watch --delay 10
```

## Terminal User Interface (TUI)

ClaudeSync now features a user-friendly TUI that displays:

- Watched directory
- Upload delay
- User ID
- Project ID
- Recent activity log

To exit the TUI, press 'q'.

## Contributing

We welcome contributions to ClaudeSync! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more information on how to get started.

## License

[MIT License](https://opensource.org/licenses/MIT)

## Disclaimer

Ensure you have the necessary permissions to access and modify your Claude.ai projects. Keep your session key secure and do not share it publicly.