#!/bin/sh

# Set error handling
set -e
set -o pipefail

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Define log functions
log_info() {
    echo "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo "${RED}[ERROR]${NC} $1"
}

# Function to activate virtual environment based on platform
activate_venv() {
    if [ -f ".venv/Scripts/activate" ]; then
        . ".venv/Scripts/activate"
    elif [ -f ".venv/bin/activate" ]; then
        . ".venv/bin/activate"
    else
        log_error "Could not find virtual environment activation script"
        exit 1
    fi
}

# Determine current and next version
determine_version() {
    log_info "Determining version..."

    # Check if version was provided as argument
    if [ -n "$1" ]; then
        NEW_VERSION="$1"
        log_info "Using provided version: ${NEW_VERSION}"
    else
        # Try to determine current version from setup.py
        CURRENT_VERSION=$(grep -o 'version="[0-9]\+\.[0-9]\+\.[0-9]\+"' setup.py | cut -d'"' -f2)

        if [ -z "$CURRENT_VERSION" ]; then
            # Try to determine from dist directory
            if [ -d "dist" ]; then
                # Find the latest wheel file and extract its version
                LATEST_WHEEL=$(ls -t dist/claudesync_fork-*.whl 2>/dev/null | head -1)
                if [ -n "$LATEST_WHEEL" ]; then
                    CURRENT_VERSION=$(echo "$LATEST_WHEEL" | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1)
                fi
            fi
        fi

        if [ -z "$CURRENT_VERSION" ]; then
            log_warn "Could not determine current version. Defaulting to 0.1.0"
            CURRENT_VERSION="0.1.0"
        fi

        # Parse version components
        MAJOR=$(echo "$CURRENT_VERSION" | cut -d. -f1)
        MINOR=$(echo "$CURRENT_VERSION" | cut -d. -f2)
        PATCH=$(echo "$CURRENT_VERSION" | cut -d. -f3)

        # Increment patch version
        PATCH=$((PATCH + 1))
        NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"

        log_info "Current version: ${CURRENT_VERSION}, New version: ${NEW_VERSION}"
    fi

    # Export for use in other functions
    export CURRENT_VERSION
    export NEW_VERSION
}

# Update version in setup.py
update_setup_py() {
    log_info "Updating version in setup.py to ${NEW_VERSION}..."

    # Use sed to update the version in setup.py
    if [ "$(uname)" = "Darwin" ]; then
        # macOS requires an empty string for -i
        sed -i '' "s/version=\"[0-9]\+\.[0-9]\+\.[0-9]\+\"/version=\"${NEW_VERSION}\"/g" setup.py
    else
        # Linux
        sed -i "s/version=\"[0-9]\+\.[0-9]\+\.[0-9]\+\"/version=\"${NEW_VERSION}\"/g" setup.py
    fi

    log_info "Updated version in setup.py"
}

# Update version in README.md
update_readme() {
    log_info "Updating version in README.md..."

    # Define the pattern to look for (installation link with version)
    PATTERN="pip install https://github.com/tbuechner/ClaudeSync/raw/refs/heads/master/dist/claudesync_fork-[0-9]\+\.[0-9]\+\.[0-9]\+-py3-none-any\.whl"
    REPLACEMENT="pip install https://github.com/tbuechner/ClaudeSync/raw/refs/heads/master/dist/claudesync_fork-${NEW_VERSION}-py3-none-any.whl"

    # Use sed to update the version in README.md
    if [ "$(uname)" = "Darwin" ]; then
        # macOS requires an empty string for -i
        sed -i '' "s|${PATTERN}|${REPLACEMENT}|g" README.md
    else
        # Linux
        sed -i "s|${PATTERN}|${REPLACEMENT}|g" README.md
    fi

    log_info "Updated version in README.md"
}

# Check required tools
check_requirements() {
    log_info "Checking build requirements..."

    # Check Node.js
    if ! command -v node >/dev/null 2>&1; then
        log_error "Node.js is required but not installed. Please install Node.js first."
        exit 1
    fi

    # Check npm
    if ! command -v npm >/dev/null 2>&1; then
        log_error "npm is required but not installed. Please install npm first."
        exit 1
    fi

    # Check Python
    if ! command -v python3 >/dev/null 2>&1; then
        log_error "Python 3 is required but not installed. Please install Python 3 first."
        exit 1
    fi

    # Check pip
    if ! command -v pip3 >/dev/null 2>&1; then
        log_error "pip3 is required but not installed. Please install pip3 first."
        exit 1
    fi

    log_info "All required tools are available."
}

# Clean previous builds
clean_builds() {
    log_info "Cleaning previous builds..."

    # Clean frontend builds
    if [ -d "src/claudesync/web/dist" ]; then
        rm -rf src/claudesync/web/dist
        log_info "Cleaned frontend dist directory"
    fi

    # Clean Python builds
    if [ -d "build" ]; then
        rm -rf build
        log_info "Cleaned Python build directory"
    fi
    if [ -d "src/claudesync.egg-info" ]; then
        rm -rf src/claudesync.egg-info
        log_info "Cleaned egg-info directory"
    fi
}

# Build frontend
build_frontend() {
    log_info "Building frontend..."

    # Navigate to frontend directory
    cd src/claudesync/web

    # Install dependencies
    log_info "Installing frontend dependencies..."
    npm install || {
        log_error "Failed to install frontend dependencies"
        exit 1
    }

    # Build frontend
    log_info "Running frontend build..."
    npm run build || {
        log_error "Frontend build failed"
        exit 1
    }

    # Navigate back to root
    cd ../../..

    log_info "Frontend build completed successfully"
}

# Build Python package
build_python() {
    log_info "Building Python package..."

    #setting utf-8 needed for windows
    export PYTHONUTF8=1
    export PYTHONIOENCODING=utf8

    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment..."
        python -m venv .venv || {
            log_error "Failed to create virtual environment"
            exit 1
        }
    fi

    # Activate virtual environment
    log_info "Activating virtual environment..."
    activate_venv || {
        log_error "Failed to activate virtual environment"
        exit 1
    }

    # Install build dependencies
    log_info "Installing build dependencies..."
    #pip3 install --upgrade pip || {
    #    log_error "Failed to upgrade pip"
    #    exit 1
    #}
    pip3 install build wheel || {
        log_error "Failed to install build dependencies"
        exit 1
    }

    # Build package
    log_info "Building Python package..."
    python -m build . || {
        log_error "Python build failed"
        exit 1
    }

    # Deactivate virtual environment (if we're in one)
    if [ -n "$VIRTUAL_ENV" ]; then
        # Some shells might not have deactivate function
        if command -v deactivate >/dev/null 2>&1; then
            deactivate
        else
            log_warn "Could not deactivate virtual environment automatically"
        fi
    fi

    log_info "Python build completed successfully"
}

# Display version info after build
display_version_info() {
    log_info "Build completed for version ${NEW_VERSION}"
    log_info "Built packages:"
    ls -lh dist/claudesync_fork-${NEW_VERSION}*

    log_info "Installation command:"
    echo "pip install https://github.com/tbuechner/ClaudeSync/raw/refs/heads/master/dist/claudesync_fork-${NEW_VERSION}-py3-none-any.whl"
}

# Display usage information
display_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -v, --version VERSION   Specify version number (format: X.Y.Z)"
    echo "  -h, --help              Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Auto-increment version"
    echo "  $0 -v 1.0.0             # Set specific version 1.0.0"
}

# Parse command line arguments
parse_args() {
    VERSION=""

    while [ "$#" -gt 0 ]; do
        case "$1" in
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -h|--help)
                display_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                display_usage
                exit 1
                ;;
        esac
    done

    return 0
}

# Main build process
main() {
    log_info "Starting ClaudeSync build process..."

    # Parse command line arguments
    parse_args "$@"

    # Determine version
    determine_version "$VERSION"

    # Update version in files
    update_setup_py
    update_readme

    # Check requirements
    check_requirements

    # Clean previous builds
    clean_builds

    # Build frontend
    build_frontend

    # Build Python package
    build_python

    # Display version info
    display_version_info

    log_info "Build process completed successfully!"
    log_info "Built packages can be found in the 'dist' directory"
}

# Run the main build process
main "$@"