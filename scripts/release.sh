#!/bin/bash
set -e

# Release script for Ubuntu Miracast Client

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Parse arguments
VERSION=""
SKIP_TESTS=false
SKIP_CHANGELOG=false

for arg in "$@"; do
    case $arg in
        --version=*)
            VERSION="${arg#*=}"
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-changelog)
            SKIP_CHANGELOG=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --version=X.Y.Z  Set release version"
            echo "  --skip-tests     Skip running tests"
            echo "  --skip-changelog Skip updating changelog"
            echo "  --help           Show this help message"
            exit 0
            ;;
    esac
done

# Check if version is provided
if [ -z "$VERSION" ]; then
    echo "Error: Version not specified. Use --version=X.Y.Z"
    exit 1
fi

# Validate version format
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Invalid version format. Use semantic versioning (X.Y.Z)"
    exit 1
fi

echo "Preparing release v$VERSION..."

# Update version in __init__.py
echo "Updating version in __init__.py..."
sed -i "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" src/miracast_client/__init__.py

# Update changelog if not skipped
if [ "$SKIP_CHANGELOG" = false ]; then
    echo "Updating debian/changelog..."
    TIMESTAMP=$(date -R)
    CHANGELOG_ENTRY="ubuntu-miracast-client ($VERSION) unstable; urgency=medium

  * Release version $VERSION.

 -- Ubuntu Miracast Team <example@example.com>  $TIMESTAMP"
    
    # Create new changelog entry
    echo "$CHANGELOG_ENTRY" > debian/changelog.new
    cat debian/changelog >> debian/changelog.new
    mv debian/changelog.new debian/changelog
fi

# Run tests if not skipped
if [ "$SKIP_TESTS" = false ]; then
    echo "Running tests..."
    ./scripts/test.sh
fi

# Build packages
echo "Building packages..."
./scripts/build.sh --clean --deb

# Create git tag
echo "Creating git tag v$VERSION..."
git add src/miracast_client/__init__.py debian/changelog
git commit -m "Release v$VERSION"
git tag -a "v$VERSION" -m "Release v$VERSION"

echo "Release v$VERSION prepared successfully!"
echo "To complete the release, push the changes and tag:"
echo "  git push origin main"
echo "  git push origin v$VERSION"