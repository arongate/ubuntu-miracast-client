# Ubuntu Miracast Client

[![CI](https://github.com/arongate/ubuntu-miracast-client/actions/workflows/ci.yml/badge.svg)](https://github.com/arongate/ubuntu-miracast-client/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/arongate/ubuntu-miracast-client?include_prereleases)](https://github.com/arongate/ubuntu-miracast-client/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A desktop application for Ubuntu that enables screen and application casting to Miracast-compatible devices.

## ⚠️ Unstable Phase (0.x)

This project is in its initial development phase (`0.x.y`). Per [SemVer §4](https://semver.org/#spec-item-4), the public API is not yet stable — any release may introduce breaking changes. Pin your dependency to an exact version if you rely on this package.

## Features

- Cast your entire screen or specific application windows
- Discover Miracast receivers on your network via Wi-Fi Direct
- WFD protocol compliant — full RTSP M1-M7 session negotiation (Wi-Fi Display spec v2.3)
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
    gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly \
    wpasupplicant x11-utils
```

## Installation

### From Debian Package

```bash
sudo apt install ./ubuntu-miracast-client_0.0.1_amd64.deb
```

### From Source

```bash
git clone https://github.com/arongate/ubuntu-miracast-client.git
cd ubuntu-miracast-client

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment with access to system GTK/GStreamer bindings
uv venv .venv --python python3 --system-site-packages
source .venv/bin/activate

# Install the project
uv pip install -e .

# Run the application
ubuntu-miracast-client
```

## Usage

Launch from your applications menu or run:

```bash
sudo ubuntu-miracast-client
```

> **Note:** The application requires root privileges for Wi-Fi Direct P2P operations
> (device discovery and connection via `wpa_cli`). Alternatively, configure polkit
> rules for passwordless access to wpa_supplicant.

### Service Mode

Run as a background service:

```bash
sudo ubuntu-miracast-client --service
```

## Development

### Quick Start

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt install python3-gi python3-cairo python3-gst-1.0 \
    gir1.2-gtk-4.0 gir1.2-adw-1 \
    gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 \
    gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly \
    wpasupplicant x11-utils

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up development environment
uv venv .venv --python python3 --system-site-packages
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests (208 tests)
make test

# Run with coverage
make coverage

# Run specific test module
python -m pytest tests/test_rtsp_messages.py -v
```

### Test Structure

| Module | Tests | Coverage |
|--------|-------|----------|
| `test_rtsp_messages.py` | 35 | RTSP request/response parsing, serialization, roundtrips |
| `test_rtsp_wfd_params.py` | 54 | WFD video formats, audio codecs, RTP ports, parameters |
| `test_rtsp_session.py` | 19 | Full M1-M7 session flow with mock TCP sink |
| `test_capture.py` | 25 | CaptureSource, ScreenSource, WindowSource, X11 parsing |
| `test_casting.py` | 19 | CastingStats, CastManager, WifiDirectConnection lifecycle |
| `test_discovery.py` | 20 | WFD subelement parsing, MiracastDevice, P2P interface |
| `test_config.py` | 5 | Config load/save, defaults, get/set |
| `test_history.py` | 10 | SessionRecord serialization, SessionHistory persistence |
| `test_service.py` | 14 | ServiceManager systemctl operations |
| `test_integration.py` | 7 | Cross-module interactions |

### Code Quality

```bash
# Format code
make format

# Lint (ruff + mypy)
make lint

# Generate changelog
make changelog
```

### Using Make

```bash
make          # Build the application
make test     # Run tests
make lint     # Run linting (ruff + mypy)
make format   # Format code (ruff)
make coverage # Run tests with coverage report
make changelog# Generate CHANGELOG.md from git history
make package  # Build Python package (sdist + wheel)
make deb      # Build Debian package
make clean    # Clean build artifacts
```

## Project Structure

```
src/miracast_client/
├── __init__.py          # Package root, version
├── app.py               # Application entry point (Adw.Application)
├── discovery.py         # Wi-Fi Direct P2P discovery (wpa_cli)
├── capture.py           # Screen/window enumeration (xprop, Gdk)
├── casting.py           # GStreamer streaming + Wi-Fi Direct connection
├── history.py           # Session history persistence (JSON)
├── config.py            # Configuration management (JSON, XDG)
├── service.py           # Systemd user service management
├── rtsp/                # RTSP/WFD protocol implementation
│   ├── __init__.py
│   ├── messages.py      # RTSP 1.0 parser/builder (RFC 2326)
│   ├── wfd_params.py    # WFD parameter parsing (video, audio, RTP)
│   └── session.py       # M1-M7 session state machine
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

Changelog is auto-generated by [git-cliff](https://git-cliff.org/) from conventional commits.

## CI/CD

- **CI** (every push/PR): Lint (Ruff), Type check (mypy), Test (Python 3.10–3.12), Security (Bandit), Commit lint (conventional commits)
- **Release** (tag `v*`): Generate changelog (git-cliff) → Build Python package → Build Debian package → Create GitHub Release with artifacts

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and workflow.

## Related Projects

- [ubuntu-miracast-server](https://github.com/arongate/ubuntu-miracast-server) — the companion Miracast sink (receiver) application

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

- [gnome-network-displays](https://gitlab.gnome.org/GNOME/gnome-network-displays) for reference Miracast source implementation
- [wpa_supplicant](https://w1.fi/wpa_supplicant/) for Wi-Fi Direct P2P support
- [GStreamer](https://gstreamer.freedesktop.org/) for media pipeline infrastructure
- [GTK](https://gtk.org/) and [libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/) for the UI framework
- The Wi-Fi Display (Miracast) specification by the Wi-Fi Alliance
