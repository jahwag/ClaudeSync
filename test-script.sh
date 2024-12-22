#!/bin/zsh

# Exit on any error
set -e

# Check if session key is provided as argument
if [ -z "$1" ]; then
    echo "Usage: $0 <claude-session-key>"
    exit 1
fi

# Export the session key
export CLAUDE_SESSION_KEY=$1

# Run the test
python -m unittest -v tests/integration/test_auth.py
