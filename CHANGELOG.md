# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Switched development workflow from pip/venv to uv
- Replaced `@dataclass` with `GObject.Object` subclasses for GTK4 `Gio.ListStore` compatibility (`MiracastDevice`, `CaptureSource`, `SessionRecord`)
- Made Gdk import graceful in `capture.py` — works in headless/test environments
- Fixed GTK4 `ListItem` factory pattern in all UI modules (device_selector, source_selector, history_view) to use widget tree navigation instead of attribute storage
- Added missing `Gio` import in `source_selector.py`
- Removed `gstreamer-python` from `install_requires` (Linux system package only, not available on PyPI for Linux)
- Updated CI workflow to use actions v4/v5 with Python 3.10/3.11/3.12 matrix
- Updated release workflow to 3-job pipeline (test → build → publish) with version verification, changelog generation, PyPI publishing, and build attestation

### Added
- Comprehensive unit tests for all core modules (73 total tests):
  - `test_capture.py` — 20 tests for capture sources and pipeline generation
  - `test_casting.py` — 11 tests for session lifecycle and validation
  - `test_history.py` — 11 tests for serialization and persistence
  - `test_service.py` — 13 tests for systemctl operations
  - `test_integration.py` — 7 tests for cross-module interactions
- Project specifications in `specs/` directory:
  - `requirements.md` — functional and non-functional requirements
  - `architecture.md` — architecture and design specification
  - `api.md` — complete module API documentation
  - `testing.md` — testing strategy and test case specifications
- uv-based development workflow documentation

### Fixed
- `test_discovery.py` — fixed for GObject subclass compatibility (was patching threading at module level breaking GObject init)
- Discovery module `stop_discovery()` properly sets `_thread = None` after joining

## [1.0.0] - 2024-05-01

### Added
- Initial release of Ubuntu Miracast Client
- Screen and application window casting via Miracast/Wi-Fi Direct
- Device discovery using wpa_supplicant P2P
- GTK 4 + libadwaita user interface
- Configurable video quality (Low/Medium/High/Very High)
- Session history tracking with statistics
- Optional systemd user service mode
- Debian package support
- GitHub Actions CI/CD pipeline
- Development container support
