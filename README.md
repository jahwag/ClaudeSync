# ClaudeSync

![License](https://img.shields.io/badge/License-MIT-blue.svg)
[![PyPI version](https://badge.fury.io/py/claudesync.svg)](https://badge.fury.io/py/claudesync)

ClaudeSync is a powerful tool designed to seamlessly synchronize your local files with [Claude.ai](https://www.anthropic.com/claude) projects.

## Overview and Scope

ClaudeSync bridges the gap between your local development environment and Claude.ai's knowledge base. At a high level, the scope of ClaudeSync includes:

- Real-time synchronization with Claude.ai projects
- Command-line interface (CLI) for easy management
- Multiple organization and project support
- Automatic handling of file creation, modification, and deletion
- Intelligent file filtering based on .gitignore rules
- Configurable sync interval with cron job support
- Seamless integration with your existing workflow

## Roadmap

1. Enhanced support for large file synchronization
2. Improved conflict resolution mechanisms
3. GUI client for easier management
4. Integration with popular IDEs and text editors
5. Support for additional AI platforms beyond Claude.ai

## Quick Start

1. **Install ClaudeSync:**
   ```bash
   pip install claudesync
   ```

2. **Login to Claude.ai:**
   ```bash
   claudesync login claude.ai
   ```

3. **Select an organization:**
   ```bash
   claudesync organization select
   ```

4. **Select or create a project:**
   ```bash
   claudesync project select
   # or
   claudesync project create
   ```

5. **Start syncing:**
   ```bash
   claudesync sync
   ```

## Advanced Usage

### Organization Management
- List organizations: `claudesync organization list`
- Select active organization: `claudesync organization select`

### Project Management
- List projects: `claudesync project ls`
- Create a new project: `claudesync project create`
- Archive a project: `claudesync project archive`
- Select active project: `claudesync project select`

### File Management
- List remote files: `claudesync ls`
- Sync files: `claudesync sync`

### Configuration
- View current status: `claudesync status`

### Scheduled Sync
Set up automatic syncing at regular intervals:
```bash
claudesync schedule
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more information.

## Communication Channels

- **Issues**: For bug reports and feature requests, please use our [GitHub Issues](https://github.com/jahwag/claudesync/issues).

## License

ClaudeSync is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Related Projects

- [Claude.ai](https://www.anthropic.com/claude): The AI assistant that ClaudeSync integrates with.

---

Made with ❤️ by the ClaudeSync team