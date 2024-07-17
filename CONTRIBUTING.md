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

1. Ensure you have Python 3.6 or later installed.
2. Install the development dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install the package in editable mode:
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

## Submitting Changes

1. Commit your changes:
   ```
   git commit -am "Add a brief description of your changes"
   ```
2. Push to your fork:
   ```
   git push origin feature/your-feature-name
   ```
3. Submit a pull request through the GitHub website.

## Code Style

We follow the PEP 8 style guide for Python code. Please ensure your code adheres to this style.

## Reporting Bugs

If you find a bug, please open an issue on the GitHub repository. Include as much detail as possible, including:

- Steps to reproduce the bug
- Expected behavior
- Actual behavior
- Any error messages or stack traces

## Requesting Features

If you have an idea for a new feature, please open an issue on the GitHub repository. Describe the feature and why you think it would be useful for the project.

## Questions

If you have any questions about contributing, feel free to open an issue for discussion.

Thank you for your interest in improving ClaudeSync!