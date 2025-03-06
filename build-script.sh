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

# Main build process
main() {
    log_info "Starting ClaudeSync build process..."

    # Check requirements
    check_requirements

    # Clean previous builds
    clean_builds

    # Build frontend
    build_frontend

    # Build Python package
    build_python

    log_info "Build process completed successfully!"
    log_info "Built packages can be found in the 'dist' directory"
}

# Run the main build process
main "$@"