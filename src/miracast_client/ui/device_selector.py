"""Device selector UI component for Ubuntu Miracast Client."""

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, GObject, Gtk

from miracast_client.discovery import MiracastDevice

logger = logging.getLogger(__name__)


class DeviceSelector(Gtk.Box):
    """UI component for selecting a Miracast device."""

    __gsignals__ = {
        "device-selected": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, discovery):
        """Initialize the device selector."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_vexpand(True)

        self.discovery = discovery
        self.discovery.connect("device-found", self._on_device_found)
        self.discovery.connect("device-lost", self._on_device_lost)
        self.discovery.connect("discovery-stopped", self._on_discovery_stopped)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        # Header area with buttons (fixed at top)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_top(24)
        header_box.set_margin_start(24)
        header_box.set_margin_end(24)
        header_box.set_margin_bottom(12)

        header = Gtk.Label()
        header.set_markup("<span size='x-large'>Select a Device</span>")
        header.set_hexpand(True)
        header.set_halign(Gtk.Align.START)
        header_box.append(header)

        self.refresh_button = Gtk.Button()
        self.refresh_button.set_label("Refresh")
        self.refresh_button.connect("clicked", self._on_refresh_clicked)
        header_box.append(self.refresh_button)

        self.connect_button = Gtk.Button()
        self.connect_button.set_label("Connect")
        self.connect_button.add_css_class("suggested-action")
        self.connect_button.connect("clicked", self._on_connect_clicked)
        self.connect_button.set_sensitive(False)
        header_box.append(self.connect_button)

        self.append(header_box)

        # Status indicator
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.status_box.set_margin_start(24)
        self.status_box.set_margin_end(24)
        self.status_box.set_margin_bottom(6)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(16, 16)
        self.status_box.append(self.spinner)

        self.status_label = Gtk.Label()
        self.status_label.set_text("Searching for devices...")
        self.status_box.append(self.status_label)

        self.append(self.status_box)

        # Device list (scrollable, takes all remaining space)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_margin_top(6)
        scrolled.set_margin_start(24)
        scrolled.set_margin_end(24)

        self.device_list = Gtk.ListView()
        self.device_model = Gio.ListStore()
        self.device_selection = Gtk.SingleSelection.new(self.device_model)
        self.device_list.set_model(self.device_selection)

        # Create factory for device items
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_device_item)
        factory.connect("bind", self._bind_device_item)
        self.device_list.set_factory(factory)

        scrolled.set_child(self.device_list)
        self.append(scrolled)

        # Connect to notify::selected for reliable selection tracking.
        # SelectionModel::selection-changed may not fire on initial auto-selection.
        self.device_selection.connect("notify::selected", self._on_selection_changed)

    def _setup_device_item(self, factory, list_item):
        """Set up a device list item."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(12)
        box.set_margin_end(12)

        icon = Gtk.Image()
        icon.set_from_icon_name("video-display")
        icon.set_size_request(48, 48)
        box.append(icon)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)

        title = Gtk.Label()
        title.set_halign(Gtk.Align.START)
        title.add_css_class("heading")
        text_box.append(title)

        description = Gtk.Label()
        description.set_halign(Gtk.Align.START)
        description.add_css_class("caption")
        text_box.append(description)

        box.append(text_box)
        list_item.set_child(box)

    def _bind_device_item(self, factory, list_item):
        """Bind data to a device list item."""
        device = list_item.get_item()
        box = list_item.get_child()
        text_box = box.get_last_child()
        title = text_box.get_first_child()
        description = title.get_next_sibling()

        title.set_text(device.name)
        description.set_text(f"Model: {device.model} | Signal: {device.signal_strength}%")

    def start_discovery(self):
        """Start device discovery."""
        self.device_model.remove_all()
        self.spinner.start()
        self.status_label.set_text("Searching for devices...")
        self.discovery.start_discovery()

    def stop_discovery(self):
        """Stop device discovery."""
        self.spinner.stop()
        self.status_label.set_text(f"Found {self.device_model.get_n_items()} devices")
        self.discovery.stop_discovery()

    def _on_device_found(self, discovery, device):
        """Handle device found event."""
        # Check if device already exists
        for i in range(self.device_model.get_n_items()):
            existing_device = self.device_model.get_item(i)
            if existing_device.id == device.id:
                # Update existing device
                self.device_model.remove(i)
                self.device_model.insert(i, device)
                return

        # Add new device
        self.device_model.append(device)
        self.status_label.set_text(f"Found {self.device_model.get_n_items()} devices")
        logger.info(f"Device found: {device.name} ({device.id})")

        # Enable connect button if a device is auto-selected
        if self.device_selection.get_selected() != Gtk.INVALID_LIST_POSITION:
            self.connect_button.set_sensitive(True)

    def _on_device_lost(self, discovery, device_id):
        """Handle device lost event."""
        for i in range(self.device_model.get_n_items()):
            device = self.device_model.get_item(i)
            if device.id == device_id:
                self.device_model.remove(i)
                self.status_label.set_text(f"Found {self.device_model.get_n_items()} devices")
                logger.info(f"Device lost: {device_id}")
                break

    def _on_discovery_stopped(self, discovery):
        """Handle discovery stopped event (e.g. after timeout)."""
        self.spinner.stop()
        n_devices = self.device_model.get_n_items()
        if n_devices > 0:
            self.status_label.set_text(f"Discovery complete — {n_devices} devices found")
        else:
            self.status_label.set_text("Discovery complete — no devices found")

    def _on_selection_changed(self, selection, pspec):
        """Handle device selection change."""
        self.connect_button.set_sensitive(selection.get_selected() != Gtk.INVALID_LIST_POSITION)

    def _on_refresh_clicked(self, button):
        """Handle refresh button click."""
        self.start_discovery()

    def _on_connect_clicked(self, button):
        """Handle connect button click."""
        position = self.device_selection.get_selected()
        if position != Gtk.INVALID_LIST_POSITION:
            device = self.device_model.get_item(position)
            self.stop_discovery()
            self.emit("device-selected", device)
