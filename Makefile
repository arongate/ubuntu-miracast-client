.PHONY: all clean build test lint package deb install uninstall docs help

# Default target
all: build

# Help message
help:
	@echo "Ubuntu Miracast Client - Make targets:"
	@echo "  make              Build the application"
	@echo "  make test         Run tests"
	@echo "  make lint         Run linting checks"
	@echo "  make package      Build Python package"
	@echo "  make deb          Build Debian package"
	@echo "  make install      Install the application"
	@echo "  make uninstall    Uninstall the application"
	@echo "  make docs         Generate documentation"
	@echo "  make clean        Clean build artifacts"

# Build the application
build:
	python3 -m pip install -e .

# Run tests
test:
	./scripts/test.sh

# Run linting
lint:
	flake8 src tests
	mypy src
	black --check src tests

# Build Python package
package:
	./scripts/build.sh

# Build Debian package
deb:
	./scripts/build.sh --deb

# Install the application
install:
	python3 -m pip install -e .

# Uninstall the application
uninstall:
	python3 -m pip uninstall -y ubuntu-miracast-client

# Generate documentation
docs:
	mkdir -p docs/api
	pdoc --html --output-dir docs/api src/miracast_client

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ debian/.debhelper/ debian/ubuntu-miracast-client/ debian/files debian/*.log debian/*.substvars
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf docs/api/