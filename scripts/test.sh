#!/bin/bash
set -e

# Test script for Ubuntu Miracast Client

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Parse arguments
COVERAGE=false
VERBOSE=false

for arg in "$@"; do
    case $arg in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --coverage  Generate coverage report"
            echo "  --verbose   Show verbose output"
            echo "  --help      Show this help message"
            exit 0
            ;;
    esac
done

# Set up logging
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="-v"
else
    PYTEST_ARGS="-q"
fi

# Run linting
echo "Running linting..."
flake8 src tests

# Run type checking
echo "Running type checking..."
mypy src

# Run tests
echo "Running tests..."
if [ "$COVERAGE" = true ]; then
    pytest $PYTEST_ARGS --cov=miracast_client tests/
    
    # Generate coverage report
    echo "Generating coverage report..."
    coverage html
    echo "Coverage report generated in htmlcov/"
else
    pytest $PYTEST_ARGS tests/
fi

echo "All tests passed!"