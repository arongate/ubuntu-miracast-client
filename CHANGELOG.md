# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note:** This project is in the unstable phase (`0.x.y`). Breaking changes
> may occur in any minor release. See the [versioning policy](README.md#versioning).

## [Unreleased]

### Added
- Conventional Commits-based versioning with auto-generated release notes
- SemVer-compliant snapshot builds (e.g., `0.0.2-dev.3`)
- Release workflow with automatic version bump detection
- PR template with change type classification
- Breaking change issue template
- `VERSION` file as single source of truth
- `scripts/release_notes.py` for commit parsing and version management
- Comprehensive unit tests (73 tests across 7 modules)
- Integration tests for cross-module interactions
- flake8 configuration (`setup.cfg`) with line-length=100
- mypy configuration ignoring `gi` stubs
- uv-based development workflow

### Changed
- Switched from tag-push release to `workflow_dispatch` release
- Snapshot builds now use SemVer pre-release format instead of date-based
- Converted dataclasses to GObject subclasses for GTK4 Gio.ListStore compatibility
- Made Gdk import graceful for headless environments
- Fixed GTK4 ListItem factory pattern in UI modules
- Updated CI to use `libgirepository-2.0-dev` for PyGObject 3.56+
- All source formatted with Black (line-length=100)

### Fixed
- Missing `Gio` import in source_selector.py
- `CastingStats.end_time` type annotation (`Optional[datetime]`)
- flake8 unused imports across all modules
- test_discovery.py GObject compatibility

## [0.0.1] - 2024-05-01

### Added
- Initial release of Ubuntu Miracast Client
- Screen and application window casting via Miracast/Wi-Fi Direct
- Device discovery using wpa_supplicant P2P
- GTK 4 + libadwaita user interface
- Configurable video quality (Low/Medium/High/Very High)
- Session history tracking with statistics
- Optional systemd user service mode
- Debian package support
- GitHub Actions CI pipeline
- Development container support
