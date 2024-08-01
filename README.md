```
  .oooooo.   oooo                              .o8                .oooooo..o                                   
 d8P'  `Y8b  `888                             "888               d8P'    `Y8                                   
888           888   .oooo.   oooo  oooo   .oooo888   .ooooo.     Y88bo.      oooo    ooo ooo. .oo.    .ooooo.  
888           888  `P  )88b  `888  `888  d88' `888  d88' `88b     `"Y8888o.   `88.  .8'  `888P"Y88b  d88' `"Y8 
888           888   .oP"888   888   888  888   888  888ooo888         `"Y88b   `88..8'    888   888  888       
`88b    ooo   888  d8(  888   888   888  888   888  888    .o    oo     .d8P    `888'     888   888  888   .o8 
 `Y8bood8P'  o888o `Y888""8o  `V88V"V8P' `Y8bod88P" `Y8bod8P'    8""88888P'      .8'     o888o o888o `Y8bod8P' 
                                                                             .o..P'                            
                                                                             `Y8P'                              
```
[![Python package](https://github.com/jahwag/ClaudeSync/actions/workflows/python-package.yml/badge.svg)](https://github.com/jahwag/ClaudeSync/actions/workflows/python-package.yml)
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
- Optional two-way synchronization support
- Configuration management through CLI
- Chat and artifact synchronization and management

**Important Note**: ClaudeSync requires a Claude.ai Professional plan to function properly. Make sure you have an active Professional subscription before using this tool.

## Important Disclaimers

- **Data Privacy**: ClaudeSync does not share any personal data or project data with anyone other than Anthropic (through Claude.ai) and yourself. Your data remains private and secure.
- **Open Source Transparency**: We are committed to transparency. Our entire codebase is open source, allowing you to review and verify our practices.
- **Affiliation**: ClaudeSync is not affiliated with, endorsed by, or sponsored by Anthropic. It is an independent tool created by enthusiasts for enthusiasts of Claude.ai.
- **Use at Your Own Risk**: While we strive for reliability, please use ClaudeSync at your own discretion and risk. Always maintain backups of your important data.

## Quick Start

1. **Install ClaudeSync:**
   ```bash
   pip install claudesync
   ```

2. **Login to Claude.ai:**
   ```bash
   claudesync api login claude.ai
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

### API Management
- Login to Claude.ai: `claudesync api login claude.ai`
- Logout: `claudesync api logout`
- Set upload delay: `claudesync api ratelimit --delay <seconds>`

### Organization Management
- List organizations: `claudesync organization ls`
- Select active organization: `claudesync organization select`

### Project Management
- List projects: `claudesync project ls`
- Create a new project: `claudesync project create`
- Archive a project: `claudesync project archive`
- Select active project: `claudesync project select`

### File Management
- List remote files: `claudesync ls`
- Sync files: `claudesync sync`

### Chat Management
- List chats: `claudesync chat ls`
- Sync chats and artifacts: `claudesync chat sync`
- Delete chats: `claudesync chat rm`
- Delete all chats: `claudesync chat rm -a`

### Configuration
- View current status: `claudesync status`
- Set configuration values: `claudesync config set <key> <value>`
- Get configuration values: `claudesync config get <key>`
- List all configuration values: `claudesync config list`

### Synchronization Modes

#### One-Way Sync (Default)
By default, ClaudeSync operates in one-way sync mode, pushing changes from your local environment to Claude.ai. This ensures that your local files are the source of truth and prevents unexpected modifications to your local files.

#### Two-Way Sync (Experimental)
Two-way synchronization is available as an experimental feature. This mode allows changes made on the remote Claude.ai project to be reflected in your local files. However, please be aware of the following:

1. To enable two-way synchronization:
   ```bash
   claudesync config set two_way_sync true
   ```

2. **Caution**: Claude.ai has a tendency to modify filenames, often appending descriptive text. For example, "README.md" might become "Updated README.md with config and two-way sync info.md". This behavior is currently beyond ClaudeSync's control.

3. **Potential Data Loss**: Due to the filename modification issue, there's a risk of unintended file duplication or data loss. Always maintain backups of your important files when using two-way sync.

4. **Future Improvements**: We're actively exploring ways to mitigate these issues, possibly through prompt engineering or updates to ClaudeSync. For now, this feature is provided as-is and should be used with understanding of its limitations.

### Scheduled Sync
Set up automatic syncing at regular intervals:
```bash
claudesync schedule
```

### Providers

ClaudeSync offers two providers for interacting with the Claude.ai API:

1. **claude.ai (Default)**:
   - Uses built-in Python libraries to make API requests.
   - No additional dependencies required.
   - Recommended for most users.

2. **claude.ai-curl**:
   - Uses cURL to make API requests.
   - Requires cURL to be installed on your system.
   - Can be used as a workaround for certain issues, such as 403 Forbidden errors.

   **Note for Windows Users**: To use the claude.ai-curl provider on Windows, you need to have cURL installed. This can be done by:
   - Installing [Git for Windows](https://git-scm.com/download/win) (which includes cURL)
   - Installing [Windows Subsystem for Linux (WSL)](https://learn.microsoft.com/en-us/windows/wsl/install)

   Make sure cURL is accessible from your command line before using this provider.

### Troubleshooting

#### 403 Forbidden Error
If you encounter a 403 Forbidden error when using ClaudeSync, it might be due to an issue with the session key or API access. Here are some steps to resolve this:

1. Ensure you have an active Claude.ai Professional plan subscription.
2. Try logging out and logging in again:
   ```bash
   claudesync api logout
   claudesync api login claude.ai
   ```
3. If the issue persists, you can try using the claude.ai-curl provider as a workaround:
   ```bash
   claudesync api logout
   claudesync api login claude.ai-curl
   ```

If you continue to experience issues, please check your network connection and ensure that you have the necessary permissions to access Claude.ai.

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more information.

## Communication Channels

- **Issues**: For bug reports and feature requests, please use our [GitHub Issues](https://github.com/jahwag/claudesync/issues).
- **Discord**: For general development discussions, visit our [Discord server](https://discord.gg/cCeA2Rng).

## License

ClaudeSync is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Related Projects

- [Claude.ai](https://www.anthropic.com/claude): The AI assistant that ClaudeSync integrates with.

---

Made with ❤️ by the ClaudeSync team
