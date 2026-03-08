# Contributing to ClaudeSync

We're excited that you're interested in contributing to ClaudeSync! This document outlines the process for contributing to this project.

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```
   git clone https://github.com/your-username/claudesync.git
   ```
3. Create a new branch for your feature or bug fix:
   ```
   git checkout -b feature/your-feature-name
   ```

## Setting Up the Development Environment

1. Ensure you have Python 3.10 or later installed.
2. Install the development dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install linting tools (required by CI but not in requirements.txt):
   ```
   pip install black flake8
   ```
4. Install the package in editable mode:
   ```
   pip install -e .
   ```

## Making Changes

1. Make your changes in your feature branch.
2. Add or update tests as necessary.
3. Run the tests to ensure they pass:
   ```
   python -m unittest discover tests
   ```
4. Update the documentation if you've made changes to the API or added new features.

## Code Style

We use [Black](https://black.readthedocs.io/) for formatting and [flake8](https://flake8.pycqa.org/) for linting. Run both locally before pushing:

```
black .
flake8 . --max-line-length=127 --extend-ignore=E203,E701 --max-complexity=10
```

These flags match the CI configuration exactly. The build will fail if either check fails.

Use `logging`/`logger` for all output — do **not** use `print()`.

## Version Bump

Every PR must include a version bump in `pyproject.toml`:

```toml
[project]
version = "x.y.z"
```

Increment the patch version for bug fixes, the minor version for new features, and the major version for breaking changes. PRs without a version bump cannot be released.

## Signed Commits

All commits require **both**:

- `-s` — DCO sign-off, certifying you wrote or have the right to submit the code
- `-S` — cryptographic signature (GPG or SSH), producing a verified badge on GitHub

```
git commit -s -S -am "Add a brief description of your changes"
```

Set up commit signing: https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits

PRs with unverified commits will not be merged.

## PR Checklist

Before submitting a pull request, confirm all of the following:

- [ ] Tests pass: `python -m unittest discover tests`
- [ ] Black check passes: `black --check .`
- [ ] flake8 passes: `flake8 . --max-line-length=127 --extend-ignore=E203,E701 --max-complexity=10`
- [ ] Version bumped in `pyproject.toml`
- [ ] All commits signed off and cryptographically signed (`git commit -s -S`)
- [ ] No `print()` calls — use `logger` instead

## Submitting Changes

1. Commit your changes:
   ```
   git commit -s -S -am "Add a brief description of your changes"
   ```
2. Push to your fork:
   ```
   git push origin feature/your-feature-name
   ```
3. Submit a pull request through the GitHub website.

## Reporting Bugs

If you find a bug, please open an issue on the GitHub repository using our bug report template. To do this:

1. Go to the [Issues](https://github.com/jahwag/claudesync/issues) page of the ClaudeSync repository.
2. Click on "New Issue".
3. Select the "Bug Report" template.
4. Fill out the template with as much detail as possible.

When reporting a bug, please include:

- A clear and concise description of the bug
- Steps to reproduce the behavior
- Expected behavior
- Any error messages or stack traces
- Your environment details (OS, Python version, ClaudeSync version)
- Your ClaudeSync configuration (use `claudesync config list`)
- Any relevant logs (you can increase log verbosity with `claudesync config set log_level DEBUG`)

The more information you provide, the easier it will be for us to reproduce and fix the bug.

## Requesting Features

If you have an idea for a new feature, please open an issue on the GitHub repository. Describe the feature and why you think it would be useful for the project.

## Questions

If you have any questions about contributing, feel free to open an issue for discussion.

Thank you for your interest in improving ClaudeSync!
