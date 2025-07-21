#!/bin/bash
set -e

# Build script for Ubuntu Miracast Client

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Parse arguments
BUILD_DEB=false
CLEAN=false
VERBOSE=false

for arg in "$@"; do
    case $arg in
        --deb)
            BUILD_DEB=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --deb      Build Debian package"
            echo "  --clean    Clean build artifacts before building"
            echo "  --verbose  Show verbose output"
            echo "  --help     Show this help message"
            exit 0
            ;;
    esac
done

# Set up logging
if [ "$VERBOSE" = true ]; then
    exec 3>&1
else
    exec 3>/dev/null
fi

# Clean build artifacts if requested
if [ "$CLEAN" = true ]; then
    echo "Cleaning build artifacts..."
    rm -rf build/ dist/ *.egg-info/ debian/.debhelper/ debian/ubuntu-miracast-client/ debian/files debian/*.log debian/*.substvars
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -delete
fi

# Create build directory
mkdir -p dist

# Build Python package
echo "Building Python package..."
python3 setup.py sdist bdist_wheel >&3

# Build Debian package if requested
if [ "$BUILD_DEB" = true ]; then
    echo "Building Debian package..."
    
    # Make sure debian scripts are executable
    chmod +x debian/rules
    chmod +x debian/ubuntu-miracast-client.postinst
    chmod +x debian/ubuntu-miracast-client.postrm
    
    # Build the package
    dpkg-buildpackage -us -uc -b >&3
    
    # Move the .deb file to dist directory
    mv ../ubuntu-miracast-client_*.deb dist/
    
    echo "Debian package built successfully!"
fi

echo "Build completed successfully!"
echo "Artifacts can be found in the 'dist' directory."