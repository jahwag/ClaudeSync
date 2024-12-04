#!/bin/zsh

# Exit on any error
set -e

# Navigate to the web directory
cd "$(dirname "$0")/src/claudesync/web"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed. Please install Node.js and npm first."
    exit 1
fi

# Clean up previous build artifacts
echo "Cleaning up previous build artifacts..."
rm -rf dist/
rm -rf node_modules/
rm -f package-lock.json

# Install dependencies
echo "Installing dependencies..."
npm install

# Build the frontend
echo "Building frontend..."
npm run build

echo "Frontend build completed successfully!"

# Optional: Display build size
if [ -d "dist" ]; then
    echo "Build size:"
    du -sh dist/
fi