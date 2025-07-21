# Contributing to Ubuntu Miracast Client

Thank you for your interest in contributing to Ubuntu Miracast Client! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and considerate of others.

## Getting Started

### Development Environment

We recommend using the provided development container for a consistent development environment:

```bash
# Start the dev container
docker-compose up -d dev

# Enter the container
docker exec -it ubuntu-miracast-client-dev bash
```

Alternatively, you can set up your local environment:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"
```

### Project Structure

- `src/miracast_client/`: Main package source code
- `tests/`: Test suite
- `docs/`: Documentation
- `scripts/`: Build and utility scripts
- `data/`: Application data files
- `debian/`: Debian packaging files

## Development Workflow

1. **Fork the repository** and clone your fork
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes** following our coding standards
4. **Run tests** to ensure your changes don't break existing functionality
5. **Commit your changes** with clear commit messages
6. **Push to your branch** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request** with a clear description of the changes

### Coding Standards

- Follow PEP 8 style guide for Python code
- Use type hints where appropriate
- Write docstrings for all functions, classes, and modules
- Keep lines under 100 characters
- Use meaningful variable and function names

### Running Tests

```bash
# Run all tests
./scripts/test.sh

# Run tests with coverage report
./scripts/test.sh --coverage

# Or use Make
make test
```

### Building the Package

```bash
# Build Python package
./scripts/build.sh

# Build Debian package
./scripts/build.sh --deb

# Or use Make
make package  # Python package
make deb      # Debian package
```

### Using Make

The project includes a Makefile for common development tasks:

```bash
make        # Build the application
make test    # Run tests
make lint    # Run linting checks
make docs    # Generate documentation
make clean   # Clean build artifacts
```

Run `make help` to see all available targets.

## Pull Request Process

1. Update the README.md or documentation with details of changes if appropriate
2. Update the version number following semantic versioning
3. The PR will be merged once it receives approval from maintainers

## Release Process

Releases are managed by maintainers using the `./scripts/release.sh` script:

```bash
./scripts/release.sh --version=X.Y.Z
```

## Reporting Bugs

Please use the GitHub issue tracker to report bugs. Use the bug report template and provide as much information as possible, including:

- A clear description of the issue
- Steps to reproduce
- Expected behavior
- Screenshots if applicable
- System information
- Log files

## Feature Requests

Feature requests are welcome! Please use the feature request template on the GitHub issue tracker and provide:

- A clear description of the feature
- The problem it solves
- Any alternative solutions you've considered

## License

By contributing to this project, you agree that your contributions will be licensed under the project's MIT License.