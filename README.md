# ClaudeSync

[![GitHub Actions](https://github.com/jahwag/ClaudeSync/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/jahwag/ClaudeSync/actions/workflows/publish-to-pypi.yml)

ClaudeSync is a powerful tool designed to seamlessly synchronize your local files with [Claude.ai](https://www.anthropic.com/claude) projects.

## 🤖 What is Claude.ai?

[Claude.ai](https://www.anthropic.com/claude) is an advanced AI assistant created by Anthropic, capable of engaging in various tasks including analysis, coding, and creative writing. ClaudeSync bridges the gap between your local development environment and Claude.ai's knowledge base.

## 🚀 Key Features

- **Real-time synchronization** with Claude.ai projects
- **Command-line interface (CLI)** for easy management
- **Multiple organization and project support**
- **Automatic handling** of file creation, modification, and deletion
- **Intelligent file filtering** based on .gitignore rules
- **Configurable sync interval** with cron job support
- **Seamless integration** with your existing workflow

## 🚀 Quick Start

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

5. **Set the local path to sync:**
   ```bash
   claudesync config set local_path /path/to/your/project
   ```

6. **Start syncing:**
   ```bash
   claudesync sync
   ```

## 🛠️ Advanced Usage

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
- Set configuration: `claudesync config set <key> <value>`

### Scheduled Sync
Set up automatic syncing at regular intervals:
```bash
claudesync schedule
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more information.

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## ⚠️ Disclaimer

Ensure you have the necessary permissions to access and modify your Claude.ai projects. Keep your session key secure and do not share it publicly.

## 📞 Support

If you encounter any issues or have questions, please [open an issue](https://github.com/jahwag/ClaudeSync/issues) on our GitHub repository.

---

Made with ❤️ by the ClaudeSync team