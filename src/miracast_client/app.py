#!/usr/bin/env python3
"""
Main application module for Ubuntu Miracast Client.
"""

import logging
import os
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from miracast_client.casting import CastManager
from miracast_client.config import Config
from miracast_client.discovery import MiracastDiscovery
from miracast_client.history import SessionHistory
from miracast_client.service import ServiceManager
from miracast_client.ui.main_window import MainWindow

# Configure logging
log_dir = Path.home() / ".local" / "share" / "ubuntu-miracast-client" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "miracast-client.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class MiracastClientApp(Adw.Application):
    """Main application class for Ubuntu Miracast Client."""

    def __init__(self):
        """Initialize the application."""
        super().__init__(
            application_id="com.ubuntu.miracast-client", flags=Gio.ApplicationFlags.FLAGS_NONE
        )

        # Initialize components
        self.config = Config()
        self.discovery = MiracastDiscovery()
        self.cast_manager = CastManager()
        self.session_history = SessionHistory()
        self.service_manager = ServiceManager()

        # Connect signals
        self.connect("activate", self.on_activate)

        logger.info("Application initialized")

    def on_activate(self, app):
        """Handle application activation."""
        # Create the main window
        win = MainWindow(
            application=app,
            discovery=self.discovery,
            cast_manager=self.cast_manager,
            session_history=self.session_history,
        )
        win.present()

        logger.info("Application activated")


def main():
    """Run the application."""
    # Check for service mode
    if len(sys.argv) > 1 and sys.argv[1] == "--service":
        from miracast_client.service import run_as_service

        return run_as_service()

    # Run as normal application
    app = MiracastClientApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
