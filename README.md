# Ubuntu Miracast Client

A desktop application for Ubuntu 24.04 LTS that enables screen and application casting to Miracast-compatible devices.

## Short Description

Ubuntu Miracast Client is an open-source application that allows Ubuntu users to wirelessly cast their screen or specific applications to Miracast-compatible receivers such as smart TVs, wireless display adapters, and other devices that support the Miracast protocol.

## Features

- Cast your entire screen or specific applications
- Discover Miracast receivers on your network
- View casting session statistics
- Session history tracking
- Optional system service mode
- Secure and fault-tolerant implementation

## Getting Started

### Prerequisites

- Ubuntu 24.04 LTS
- Python 3.12 or higher
- Network connection (preferably 5GHz WiFi for optimal performance)

### Installation

#### From Debian Package

```bash
sudo apt install ./ubuntu-miracast-client_1.0.0_amd64.deb
```

#### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/ubuntu-miracast-client.git
cd ubuntu-miracast-client

# Using the development container (recommended)
docker-compose up -d dev
docker exec -it ubuntu-miracast-client-dev bash
./scripts/build.sh

# Or build directly on your system
pip install -e .
```

### Usage

Launch the application from your applications menu or run:

```bash
ubuntu-miracast-client
```

## Development Process

### Using Dev Container

We provide a development container with all necessary tools pre-installed:

```bash
# Start the dev container
docker-compose up -d dev

# Enter the container
docker exec -it ubuntu-miracast-client-dev bash

# Run tests
./scripts/test.sh

# Build the package
./scripts/build.sh
```

### Manual Development Setup

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Build the package
./scripts/build.sh
```

### Using Make

We provide a Makefile for common development tasks:

```bash
# Build the application
make

# Run tests
make test

# Run linting checks
make lint

# Build Python package
make package

# Build Debian package
make deb

# Generate documentation
make docs

# Clean build artifacts
make clean
```

Run `make help` to see all available targets.

## Contribution Rules

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

The CI pipeline will automatically run tests and linting checks on your pull request.

Please make sure your code follows our coding standards and includes appropriate tests.

## Releases

Releases are automatically built and published using GitHub Actions when a new tag is pushed:

```bash
# Tag a new version
git tag -a v1.0.1 -m "Release v1.0.1"

# Push the tag
git push origin v1.0.1
```

This will trigger the release workflow which builds and publishes Python and Debian packages.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The Miracast protocol specification
- Contributors and maintainers