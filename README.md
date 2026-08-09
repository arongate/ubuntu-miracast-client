# Ubuntu Miracast Client

A desktop application for Ubuntu that enables screen and application casting to Miracast-compatible devices.

## ⚠️ Unstable Phase (0.x)

This project is in its initial development phase (`0.x.y`). Per [SemVer §4](https://semver.org/#spec-item-4), the public API is not yet stable — any release may introduce breaking changes. Pin your dependency to an exact version if you rely on this package.

## Features

- Cast your entire screen or specific application windows
- Discover Miracast receivers on your network via Wi-Fi Direct
- Real-time casting session statistics (bitrate, data transferred, dropped frames)
- Session history tracking with detailed statistics
- Optional systemd user service mode
- Modern GTK 4 + libadwaita interface
- Configurable video quality, frame rate, and audio streaming

## Prerequisites

- Ubuntu 24.04 LTS (or compatible Linux distribution)
- Python 3.10 or higher
- Network connection (5GHz Wi-Fi recommended for optimal performance)

### System Dependencies

```bash
sudo apt install python3-gi python3-cairo python3-gst-1.0 \
    gir1.2-gtk-4.0 gir1.2-adw-1 \
    gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 \
    wpasupplicant
```

## Installation

### From Debian Package

```bash
sudo apt install ./ubuntu-miracast-client_1.0.0_amd64.deb
```

### From Source (using uv)

```bash
git clone https://github.com/yourusername/ubuntu-miracast-client.git
cd ubuntu-miracast-client

# Create virtual environment with access to system GTK/GStreamer bindings
uv venv .venv --python /usr/bin/python3 --system-site-packages
source .venv/bin/activate

# Install dev tools and the project
uv pip install pytest pytest-cov black isort flake8 mypy
uv pip install -e . --no-deps

# Run the application
ubuntu-miracast-client
```

## Usage

Launch from your applications menu or run:

```bash
ubuntu-miracast-client
```

### Service Mode

Run as a background service:

```bash
ubuntu-miracast-client --service
```

## Development

### Quick Start

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt install python3-gi python3-cairo python3-gst-1.0 \
    gir1.2-gtk-4.0 gir1.2-adw-1 \
    gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0

# Set up development environment with uv
uv venv .venv --python /usr/bin/python3 --system-site-packages
source .venv/bin/activate
uv pip install pytest pytest-cov black isort flake8 mypy
uv pip install -e . --no-deps
```

### Running Tests

```bash
# Run all 73 tests
.venv/bin/python -m pytest tests/ -v

# Run with coverage
.venv/bin/python -m pytest tests/ --cov=miracast_client --cov-report=html

# Run specific test module
.venv/bin/python -m pytest tests/test_discovery.py -v
```

### Test Structure

| Module | Tests | Coverage |
|--------|-------|----------|
| `test_capture.py` | 20 | CaptureSource, ScreenSource, WindowSource, get_available_sources |
| `test_casting.py` | 11 | CastingStats, CastManager lifecycle and validation |
| `test_config.py` | 6 | Config load/save, defaults, get/set |
| `test_discovery.py` | 5 | MiracastDevice, MiracastDiscovery signals and lifecycle |
| `test_history.py` | 11 | SessionRecord serialization, SessionHistory persistence |
| `test_service.py` | 13 | ServiceManager systemctl operations |
| `test_integration.py` | 7 | Cross-module interactions |

### Code Quality

```bash
# Format code
.venv/bin/python -m black src/ tests/
.venv/bin/python -m isort src/ tests/

# Lint
.venv/bin/python -m flake8 src/ tests/

# Type check
.venv/bin/python -m mypy src/
```

### Using Make

```bash
make          # Build the application
make test     # Run tests
make lint     # Run linting checks
make package  # Build Python package
make deb      # Build Debian package
make clean    # Clean build artifacts
```

### Using Dev Container

```bash
docker-compose up -d dev
docker exec -it ubuntu-miracast-client-dev bash
./scripts/test.sh
```

## Project Structure

```
src/miracast_client/
├── __init__.py          # Package root, version
├── app.py               # Application entry point (Adw.Application)
├── discovery.py         # Wi-Fi Direct device discovery
├── capture.py           # Screen/window capture sources
├── casting.py           # Streaming session management
├── history.py           # Session history persistence
├── config.py            # Configuration management (JSON)
├── service.py           # Systemd service management
└── ui/
    ├── main_window.py   # Main window with navigation stack
    ├── source_selector.py
    ├── device_selector.py
    ├── history_view.py
    └── settings_view.py
```

## Versioning

This project follows [Semantic Versioning](https://semver.org/) with [Conventional Commits](https://www.conventionalcommits.org/).

| Commit prefix | Version bump | Example |
|---------------|-------------|---------|
| `fix:` | Patch (0.0.x) | Bug fix |
| `feat:` | Minor (0.x.0) | New feature |
| `feat!:` or `BREAKING CHANGE:` | Minor during 0.x, Major after 1.0 | Breaking change |

**Snapshot builds** are automatically created on every push to `main` and named as the next anticipated release with a dev suffix (e.g., `0.0.2-dev.3`).

**Releases** are triggered manually via `workflow_dispatch` and auto-determine the version bump from commit history.

## CI/CD

- **CI**: Runs on every push/PR to main. Tests across Python 3.10, 3.11, 3.12 with coverage reporting.
- **Release**: Triggered by version tags (`v*`). Runs tests → builds packages → publishes to PyPI and creates GitHub Release with Debian package.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and workflow.

## License

MIT License — see [LICENSE](LICENSE) for details.
