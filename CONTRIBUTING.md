# Contributing to Ubuntu Miracast Client

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to be respectful and considerate of others.

## Development Setup

### Prerequisites

Install system dependencies (Ubuntu 24.04):

```bash
sudo apt install python3-gi python3-cairo python3-gst-1.0 \
    gir1.2-gtk-4.0 gir1.2-adw-1 \
    gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 \
    wpasupplicant
```

Install [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setting Up the Environment

```bash
# Clone and enter the project
git clone https://github.com/yourusername/ubuntu-miracast-client.git
cd ubuntu-miracast-client

# Create virtual environment (uses system Python for GTK/GStreamer bindings)
uv venv .venv --python /usr/bin/python3 --system-site-packages
source .venv/bin/activate

# Install development tools
uv pip install pytest pytest-cov black isort flake8 mypy

# Install the project in editable mode (no-deps since GTK/GStreamer are system packages)
uv pip install -e . --no-deps
```

> **Why `--system-site-packages`?** PyGObject, pycairo, and GStreamer Python bindings are compiled against system libraries and must be installed via apt. The `--system-site-packages` flag lets the venv access these system packages while keeping dev tools isolated.

> **Why `--no-deps`?** The `install_requires` in setup.py lists PyGObject and pycairo for metadata purposes, but they can't be pip-installed without a C compiler and system headers. They're already available via system-site-packages.

### Alternative: Dev Container

```bash
docker-compose up -d dev
docker exec -it ubuntu-miracast-client-dev bash
```

## Project Structure

```
src/miracast_client/       # Main package
├── app.py                 # GTK application entry point
├── discovery.py           # Wi-Fi Direct device discovery (GObject signals)
├── capture.py             # Screen/window capture (GStreamer pipelines)
├── casting.py             # Streaming session management
├── history.py             # Session history (JSON persistence)
├── config.py              # Configuration management
├── service.py             # Systemd user service
└── ui/                    # GTK 4 / libadwaita UI components
tests/                     # Unit and integration tests
specs/                     # Project specifications
docs/                      # User-facing documentation
```

## Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/). Every commit message must follow this format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description | Version bump |
|------|-------------|-------------|
| `feat` | New feature | Minor (0.x.0) |
| `fix` | Bug fix | Patch (0.0.x) |
| `perf` | Performance improvement | Patch |
| `docs` | Documentation only | None |
| `style` | Code formatting | None |
| `refactor` | Code refactoring | None |
| `test` | Adding/fixing tests | None |
| `build` | Build system changes | None |
| `ci` | CI/CD changes | None |
| `chore` | Other maintenance | None |

### Breaking Changes

Append `!` after the type or add `BREAKING CHANGE:` in the footer:

```
feat!: redesign streaming API

BREAKING CHANGE: The start_casting() method now requires a StreamConfig object.
```

During the **unstable phase (0.x)**, breaking changes bump the minor version instead of major.

### Examples

```bash
git commit -m "feat(discovery): add mDNS fallback for device scanning"
git commit -m "fix(casting): handle dropped connection gracefully"
git commit -m "docs: update getting-started guide"
git commit -m "ci: add Python 3.13 to test matrix"
```

## Development Workflow

1. **Fork the repository** and clone your fork
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following the coding standards below
4. **Run tests**: `.venv/bin/python -m pytest tests/ -v`
5. **Run linting**: `.venv/bin/python -m flake8 src/ tests/`
6. **Format code**: `.venv/bin/python -m black src/ tests/ && .venv/bin/python -m isort src/ tests/`
7. **Commit** with clear messages
8. **Push** and open a Pull Request

## Running Tests

```bash
# Run all tests (73 tests across 7 test modules)
.venv/bin/python -m pytest tests/ -v

# Run with coverage report
.venv/bin/python -m pytest tests/ --cov=miracast_client --cov-report=html

# Run a specific module
.venv/bin/python -m pytest tests/test_casting.py -v

# Run a specific test
.venv/bin/python -m pytest tests/test_casting.py::TestCastManager::test_start_casting_success -v
```

### Test Organization

| File | Module Tested | Tests |
|------|--------------|-------|
| `test_capture.py` | `capture.py` | 20 — Source classes, pipeline generation |
| `test_casting.py` | `casting.py` | 11 — Session lifecycle, validation |
| `test_config.py` | `config.py` | 6 — Load/save, defaults |
| `test_discovery.py` | `discovery.py` | 5 — Device creation, signals |
| `test_history.py` | `history.py` | 11 — Serialization, persistence |
| `test_service.py` | `service.py` | 13 — Systemctl operations |
| `test_integration.py` | Cross-module | 7 — End-to-end flows |

### Writing Tests

- Use `unittest` and `unittest.mock` (patch, MagicMock)
- Mock system dependencies (subprocess, Gdk.Display) — never call real systemctl or require a display server
- Use `tempfile.TemporaryDirectory` for file I/O tests
- Core classes (MiracastDevice, CaptureSource, etc.) are GObject subclasses — they have normal Python attributes but inherit from `GObject.Object`

## Coding Standards

- **Style**: PEP 8, enforced by flake8
- **Formatting**: Black (line-length=100), isort
- **Type hints**: Encouraged, checked by mypy
- **Docstrings**: Required for all public functions, classes, and modules
- **Line length**: 100 characters max

## Building

```bash
# Build Python package
./scripts/build.sh

# Build Debian package
./scripts/build.sh --deb

# Or use Make
make package  # Python wheel/sdist
make deb      # Debian .deb
```

## Release Process

Releases are managed via the GitHub Actions **Release** workflow (`workflow_dispatch`):

1. Navigate to Actions → Release → Run workflow
2. Choose bump type (`auto`, `patch`, `minor`, or `major`)
   - `auto` reads your commit history and determines the bump from Conventional Commits
3. The workflow will:
   - Determine the new version based on commits since the last tag
   - Run the full test suite
   - Build Python and Debian packages
   - Update the `VERSION` file, commit, and tag
   - Publish to PyPI and create a GitHub Release with auto-generated release notes

### Version File

The single source of truth for the current version is the `VERSION` file at the project root. It is read by `__init__.py` and `setup.py` at runtime/build time.

### Snapshot Builds

Every push to `main` triggers a snapshot build that:
- Runs tests
- Computes the next anticipated version from commits (e.g., `0.0.2-dev.3`)
- Builds and publishes packages as a GitHub pre-release

## Pull Request Guidelines

1. Update documentation if your change affects usage
2. Add tests for new functionality
3. Ensure all 73+ tests pass
4. Follow semantic versioning for version bumps
5. Keep PRs focused — one feature or fix per PR

## Reporting Issues

Use GitHub issue templates:
- **Bug Report**: Include steps to reproduce, expected vs. actual behavior, and log output
- **Feature Request**: Describe the problem and proposed solution

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
