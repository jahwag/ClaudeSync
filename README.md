# ClaudeSync
[![Python Package](https://github.com/jahwag/ClaudeSync/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/jahwag/ClaudeSync/actions/workflows/publish-to-pypi.yml)

ClaudeSync is a Python tool that automatically synchronizes your local filesystem with Claude.ai projects.

## Installation

You can install ClaudeSync using pip:

```bash
pip install claudesync
```

## Setup

1. Create a `config.json` file in your working directory:
   ```json
   {
       "user_id": "your-user-id-here",
       "project_id": "your-project-id-here"
   }
   ```

2. Ensure you have your Claude.ai session key ready.

## Usage

After installation, you can use ClaudeSync as a command-line tool:

```bash
claudesync --session-key YOUR_SESSION_KEY --watch-dir /path/to/watch
```

### Parameters

- `--session-key`: Your Claude.ai session key (required)
- `--watch-dir`: Directory to watch for changes (required)
- `--user-id`: Override user ID from config
- `--project-id`: Override project ID from config
- `--delete-all`: Delete all project documents
- `--delay`: Delay in seconds before uploading (default: 5)

### Examples

Watch a directory and sync changes:
```bash
claudesync --session-key YOUR_SESSION_KEY --watch-dir /path/to/watch
```

Override config settings:
```bash
claudesync --session-key YOUR_SESSION_KEY --watch-dir /path/to/watch --user-id different-user-id --project-id different-project-id
```

Delete all documents in the project:
```bash
claudesync --session-key YOUR_SESSION_KEY --delete-all
```

Set a custom delay for file uploads:
```bash
claudesync --session-key YOUR_SESSION_KEY --watch-dir /path/to/watch --delay 10
```

## Features

- Watch local directories for file changes
- Automatically upload new or modified files to Claude.ai
- Delete outdated versions of files in Claude.ai
- Option to clear all documents in a Claude.ai project
- Configurable delay to prevent frequent uploads during active editing

## Development

To contribute to ClaudeSync:

1. Clone the repository:
   ```
   git clone https://github.com/jahwag/claudesync.git
   ```
2. Install development dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Make your changes and submit a pull request.

## License

[MIT License](https://opensource.org/licenses/MIT)

## Disclaimer

Ensure you have the necessary permissions to access and modify your Claude.ai projects. Keep your session key secure and do not share it publicly.