#!/usr/bin/env python3
"""Setup script for Ubuntu Miracast Client."""

from setuptools import setup, find_packages
import os
from pathlib import Path

# Get the long description from the README file
readme_path = Path(__file__).parent / "README.md"
with open(readme_path, encoding="utf-8") as f:
    long_description = f.read()

# Get version from package
with open(Path(__file__).parent / "src" / "miracast_client" / "__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break
    else:
        version = "0.0.1"

setup(
    name="ubuntu-miracast-client",
    version=version,
    description="Miracast client for Ubuntu",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Ubuntu Miracast Team",
    author_email="example@example.com",
    url="https://github.com/yourusername/ubuntu-miracast-client",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: System :: Networking",
    ],
    python_requires=">=3.10",
    install_requires=[
        # NOTE: PyGObject and pycairo require system libraries.
        # On Ubuntu: sudo apt install python3-gi python3-cairo python3-gst-1.0
        # They are listed here for metadata but may fail to install via pip
        # in environments without the required C libraries and compiler.
        "PyGObject>=3.42.0",
        "pycairo>=1.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ubuntu-miracast-client=miracast_client.app:main",
        ],
    },
    data_files=[
        ("share/applications", ["data/ubuntu-miracast-client.desktop"]),
        ("share/icons/hicolor/scalable/apps", ["data/ubuntu-miracast-client.svg"]),
    ],
    include_package_data=True,
    zip_safe=False,
)