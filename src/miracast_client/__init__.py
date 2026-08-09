"""Ubuntu Miracast Client - A desktop application for wireless display casting."""

from pathlib import Path

__version__ = (Path(__file__).parent.parent.parent / "VERSION").read_text().strip()
