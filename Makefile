.PHONY: all clean build test lint format coverage changelog package deb install uninstall help

# Default target
all: build

# Help message
help:
	@echo "Ubuntu Miracast Client - Make targets:"
	@echo "  make              Build the application"
	@echo "  make test         Run tests"
	@echo "  make lint         Run linting checks (ruff + mypy)"
	@echo "  make format       Format code with ruff"
	@echo "  make coverage     Run tests with coverage"
	@echo "  make changelog    Generate CHANGELOG.md from git history"
	@echo "  make package      Build Python package (sdist + wheel)"
	@echo "  make deb          Build Debian package"
	@echo "  make install      Install the application"
	@echo "  make uninstall    Uninstall the application"
	@echo "  make clean        Clean build artifacts"

# Build the application
build:
	uv pip install -e .

# Run tests
test:
	uv run pytest tests/ -v

# Run linting (ruff check + format check + mypy)
lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/
	uv run mypy src/ --ignore-missing-imports

# Format code with ruff
format:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

# Run tests with coverage
coverage:
	uv run pytest tests/ -v --cov=miracast_client --cov-report=html --cov-report=term

# Generate changelog from conventional commits
changelog:
	git-cliff --config cliff.toml --output CHANGELOG.md

# Build Python package
package:
	uv build

# Build Debian package
deb:
	dpkg-buildpackage -us -uc -b

# Install the application
install:
	uv pip install -e .

# Uninstall the application
uninstall:
	uv pip uninstall ubuntu-miracast-client

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ src/*.egg-info/
	rm -rf debian/.debhelper/ debian/ubuntu-miracast-client/ debian/files debian/*.log debian/*.substvars
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
