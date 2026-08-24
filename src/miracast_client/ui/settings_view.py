"""Settings view UI component for Ubuntu Miracast Client."""

import logging
import os
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, GObject, Gtk

from miracast_client.config import Config
from miracast_client.service import ServiceManager

logger = logging.getLogger(__name__)


class SettingsView(Gtk.Box):
    """UI component for application settings."""

    def __init__(self):
        """Initialize the settings view."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)

        self.config = Config()
        self.service_manager = ServiceManager()

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        # Header
        header = Gtk.Label()
        header.set_markup("<span size='x-large'>Settings</span>")
        header.set_halign(Gtk.Align.START)
        header.set_margin_bottom(24)
        self.append(header)

        # Settings groups
        self._add_general_settings()
        self._add_streaming_settings()
        self._add_service_settings()
        self._add_advanced_settings()

        # Save button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(24)

        self.save_button = Gtk.Button()
        self.save_button.set_label("Save Settings")
        self.save_button.add_css_class("suggested-action")
        self.save_button.connect("clicked", self._on_save_clicked)

        button_box.append(self.save_button)
        self.append(button_box)

    def _add_general_settings(self):
        """Add general settings group."""
        group = Adw.PreferencesGroup()
        group.set_title("General")

        # Minimize to system tray
        row = Adw.ActionRow()
        row.set_title("Minimize to System Tray")
        row.set_subtitle("Keep the application running in the system tray when minimized")

        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.set_active(self.config.get("general", "minimize_to_tray", True))
        row.add_suffix(switch)
        row.set_activatable_widget(switch)
        self.minimize_to_tray_switch = switch

        group.add(row)

        # Start minimized
        row = Adw.ActionRow()
        row.set_title("Start Minimized")
        row.set_subtitle("Start the application minimized to the system tray")

        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.set_active(self.config.get("general", "start_minimized", False))
        row.add_suffix(switch)
        row.set_activatable_widget(switch)
        self.start_minimized_switch = switch

        group.add(row)

        # Log level
        row = Adw.ActionRow()
        row.set_title("Log Level")
        row.set_subtitle("Set the application log level")

        dropdown = Gtk.DropDown.new_from_strings(["DEBUG", "INFO", "WARNING", "ERROR"])
        dropdown.set_valign(Gtk.Align.CENTER)

        current_level = self.config.get("general", "log_level", "INFO")
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if current_level in levels:
            dropdown.set_selected(levels.index(current_level))

        row.add_suffix(dropdown)
        self.log_level_dropdown = dropdown

        group.add(row)

        self.append(group)

    def _add_streaming_settings(self):
        """Add streaming settings group."""
        group = Adw.PreferencesGroup()
        group.set_title("Streaming")

        # Video quality
        row = Adw.ActionRow()
        row.set_title("Video Quality")
        row.set_subtitle("Set the video streaming quality")

        dropdown = Gtk.DropDown.new_from_strings(["Low", "Medium", "High", "Very High"])
        dropdown.set_valign(Gtk.Align.CENTER)

        current_quality = self.config.get("streaming", "video_quality", "High")
        qualities = ["Low", "Medium", "High", "Very High"]
        if current_quality in qualities:
            dropdown.set_selected(qualities.index(current_quality))

        row.add_suffix(dropdown)
        self.video_quality_dropdown = dropdown

        group.add(row)

        # Frame rate
        row = Adw.ActionRow()
        row.set_title("Frame Rate")
        row.set_subtitle("Set the target frame rate for streaming")

        dropdown = Gtk.DropDown.new_from_strings(["15 fps", "24 fps", "30 fps", "60 fps"])
        dropdown.set_valign(Gtk.Align.CENTER)

        current_fps = self.config.get("streaming", "frame_rate", 30)
        fps_options = [15, 24, 30, 60]
        if current_fps in fps_options:
            dropdown.set_selected(fps_options.index(current_fps))

        row.add_suffix(dropdown)
        self.frame_rate_dropdown = dropdown

        group.add(row)

        # Audio enabled
        row = Adw.ActionRow()
        row.set_title("Enable Audio")
        row.set_subtitle("Stream audio along with video")

        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.set_active(self.config.get("streaming", "audio_enabled", True))
        row.add_suffix(switch)
        row.set_activatable_widget(switch)
        self.audio_enabled_switch = switch

        group.add(row)

        self.append(group)

    def _add_service_settings(self):
        """Add service settings group."""
        group = Adw.PreferencesGroup()
        group.set_title("Service")

        # Run as service
        row = Adw.ActionRow()
        row.set_title("Run as System Service")
        row.set_subtitle("Run the application as a system service")

        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.set_active(self.service_manager.is_service_enabled())
        switch.connect("state-set", self._on_service_switch_toggled)
        row.add_suffix(switch)
        row.set_activatable_widget(switch)
        self.service_switch = switch

        group.add(row)

        # Service status
        row = Adw.ActionRow()
        row.set_title("Service Status")

        status_label = Gtk.Label()
        if self.service_manager.is_service_running():
            status_label.set_text("Running")
            status_label.add_css_class("success")
        else:
            status_label.set_text("Stopped")
            status_label.add_css_class("error")

        status_label.set_valign(Gtk.Align.CENTER)
        row.add_suffix(status_label)
        self.service_status_label = status_label

        group.add(row)

        # Service control buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(12)

        start_button = Gtk.Button()
        start_button.set_label("Start Service")
        start_button.connect("clicked", self._on_start_service_clicked)
        button_box.append(start_button)
        self.start_service_button = start_button

        stop_button = Gtk.Button()
        stop_button.set_label("Stop Service")
        stop_button.connect("clicked", self._on_stop_service_clicked)
        button_box.append(stop_button)
        self.stop_service_button = stop_button

        group.add(button_box)

        self.append(group)

        # Update service control button states
        self._update_service_controls()

    def _add_advanced_settings(self):
        """Add advanced settings group."""
        group = Adw.PreferencesGroup()
        group.set_title("Advanced")

        # Discovery timeout
        row = Adw.ActionRow()
        row.set_title("Discovery Timeout")
        row.set_subtitle("Time in seconds to search for devices")

        adjustment = Gtk.Adjustment(
            value=self.config.get("advanced", "discovery_timeout", 10),
            lower=5,
            upper=60,
            step_increment=1,
        )

        spin = Gtk.SpinButton()
        spin.set_adjustment(adjustment)
        spin.set_valign(Gtk.Align.CENTER)
        row.add_suffix(spin)
        self.discovery_timeout_spin = spin

        group.add(row)

        # Connection timeout
        row = Adw.ActionRow()
        row.set_title("Connection Timeout")
        row.set_subtitle("Time in seconds to establish connection")

        adjustment = Gtk.Adjustment(
            value=self.config.get("advanced", "connection_timeout", 15),
            lower=5,
            upper=60,
            step_increment=1,
        )

        spin = Gtk.SpinButton()
        spin.set_adjustment(adjustment)
        spin.set_valign(Gtk.Align.CENTER)
        row.add_suffix(spin)
        self.connection_timeout_spin = spin

        group.add(row)

        # Clear history button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(12)

        clear_button = Gtk.Button()
        clear_button.set_label("Clear History")
        clear_button.connect("clicked", self._on_clear_history_clicked)
        button_box.append(clear_button)

        group.add(button_box)

        self.append(group)

    def _on_save_clicked(self, button):
        """Handle save button click."""
        try:
            # General settings
            self.config.set(
                "general", "minimize_to_tray", self.minimize_to_tray_switch.get_active()
            )
            self.config.set("general", "start_minimized", self.start_minimized_switch.get_active())

            levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
            selected_level = levels[self.log_level_dropdown.get_selected()]
            self.config.set("general", "log_level", selected_level)

            # Streaming settings
            qualities = ["Low", "Medium", "High", "Very High"]
            selected_quality = qualities[self.video_quality_dropdown.get_selected()]
            self.config.set("streaming", "video_quality", selected_quality)

            fps_options = [15, 24, 30, 60]
            selected_fps = fps_options[self.frame_rate_dropdown.get_selected()]
            self.config.set("streaming", "frame_rate", selected_fps)

            self.config.set("streaming", "audio_enabled", self.audio_enabled_switch.get_active())

            # Advanced settings
            self.config.set(
                "advanced", "discovery_timeout", self.discovery_timeout_spin.get_value_as_int()
            )
            self.config.set(
                "advanced", "connection_timeout", self.connection_timeout_spin.get_value_as_int()
            )

            # Save config
            self.config.save()

            # Show success message
            dialog = Adw.MessageDialog(
                transient_for=self.get_root(),
                heading="Settings Saved",
                body="Your settings have been saved successfully.",
            )
            dialog.add_response("ok", "OK")
            dialog.present()

            logger.info("Settings saved successfully")
        except Exception as e:
            # Show error message
            dialog = Adw.MessageDialog(
                transient_for=self.get_root(),
                heading="Error",
                body=f"Failed to save settings: {e!s}",
            )
            dialog.add_response("ok", "OK")
            dialog.present()

            logger.error(f"Failed to save settings: {e}")

    def _on_service_switch_toggled(self, switch, state):
        """Handle service switch toggle."""
        try:
            if state:
                self.service_manager.enable_service()
                logger.info("Service enabled")
            else:
                self.service_manager.disable_service()
                logger.info("Service disabled")

            self._update_service_controls()
            return False  # Allow the switch to change state
        except Exception as e:
            logger.error(f"Failed to change service state: {e}")

            # Show error message
            dialog = Adw.MessageDialog(
                transient_for=self.get_root(),
                heading="Service Error",
                body=f"Failed to change service state: {e!s}",
            )
            dialog.add_response("ok", "OK")
            dialog.present()

            return True  # Prevent the switch from changing state

    def _on_start_service_clicked(self, button):
        """Handle start service button click."""
        try:
            self.service_manager.start_service()
            self._update_service_controls()
            logger.info("Service started")
        except Exception as e:
            logger.error(f"Failed to start service: {e}")

            # Show error message
            dialog = Adw.MessageDialog(
                transient_for=self.get_root(),
                heading="Service Error",
                body=f"Failed to start service: {e!s}",
            )
            dialog.add_response("ok", "OK")
            dialog.present()

    def _on_stop_service_clicked(self, button):
        """Handle stop service button click."""
        try:
            self.service_manager.stop_service()
            self._update_service_controls()
            logger.info("Service stopped")
        except Exception as e:
            logger.error(f"Failed to stop service: {e}")

            # Show error message
            dialog = Adw.MessageDialog(
                transient_for=self.get_root(),
                heading="Service Error",
                body=f"Failed to stop service: {e!s}",
            )
            dialog.add_response("ok", "OK")
            dialog.present()

    def _update_service_controls(self):
        """Update service control button states."""
        is_running = self.service_manager.is_service_running()
        is_enabled = self.service_manager.is_service_enabled()

        self.service_switch.set_active(is_enabled)

        if is_running:
            self.service_status_label.set_text("Running")
            self.service_status_label.remove_css_class("error")
            self.service_status_label.add_css_class("success")

            self.start_service_button.set_sensitive(False)
            self.stop_service_button.set_sensitive(True)
        else:
            self.service_status_label.set_text("Stopped")
            self.service_status_label.remove_css_class("success")
            self.service_status_label.add_css_class("error")

            self.start_service_button.set_sensitive(True)
            self.stop_service_button.set_sensitive(False)

    def _on_clear_history_clicked(self, button):
        """Handle clear history button click."""
        # Show confirmation dialog
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Clear History",
            body="Are you sure you want to clear all casting history?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_clear_history_confirmed)
        dialog.present()

    def _on_clear_history_confirmed(self, dialog, response):
        """Handle clear history confirmation."""
        if response == "clear":
            try:
                from miracast_client.history import SessionHistory

                history = SessionHistory()
                history.clear()

                # Show success message
                success_dialog = Adw.MessageDialog(
                    transient_for=self.get_root(),
                    heading="History Cleared",
                    body="Your casting history has been cleared.",
                )
                success_dialog.add_response("ok", "OK")
                success_dialog.present()

                logger.info("Casting history cleared")
            except Exception as e:
                logger.error(f"Failed to clear history: {e}")

                # Show error message
                error_dialog = Adw.MessageDialog(
                    transient_for=self.get_root(),
                    heading="Error",
                    body=f"Failed to clear history: {e!s}",
                )
                error_dialog.add_response("ok", "OK")
                error_dialog.present()
