# Ubuntu Miracast Client Documentation

This directory contains documentation for the Ubuntu Miracast Client application.

## Contents

- [Getting Started Guide](getting-started.md): Instructions for installing and using the application
- [Miracast Protocol](miracast-protocol.md): Technical overview of the Miracast protocol

## Additional Resources

- [Project README](../README.md): Overview of the project
- [Contributing Guide](../CONTRIBUTING.md): Information for contributors
- [Project Summary](../PROJECT_SUMMARY.md): Detailed project architecture and features

## API Documentation

For detailed API documentation, you can generate it using:

```bash
cd /path/to/ubuntu-miracast-client
pip install pdoc3
pdoc --html --output-dir docs/api src/miracast_client
```

This will generate HTML documentation in the `docs/api` directory.