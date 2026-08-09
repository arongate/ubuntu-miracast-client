"""Device selector UI component for Ubuntu Miracast Client."""

import gi
import logging

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, Gio, GLib

from miracast_client.discovery import MiracastDevice

logger = logging.getLogger(__name__)


class DeviceSelector(Gtk.Box):
    """UI component for selecting a Miracast device."""
    
    __gsignals__ = {
        'device-selected': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }
    
    def __init__(self, discovery):
        """Initialize the device selector."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        
        self.discovery = discovery
        self.discovery.connect("device-found", self._on_device_found)
        self.discovery.connect("device-lost", self._on_device_lost)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Header
        header = Gtk.Label()
        header.set_markup("<span size='x-large'>Select a Device</span>")
        header.set_margin_bottom(24)
        self.append(header)
        
        # Status indicator
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.status_box.set_margin_bottom(12)
        
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(16, 16)
        self.status_box.append(self.spinner)
        
        self.status_label = Gtk.Label()
        self.status_label.set_text("Searching for devices...")
        self.status_box.append(self.status_label)
        
        self.append(self.status_box)
        
        # Device list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(300)
        scrolled.set_vexpand(True)
        
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
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(24)
        
        self.refresh_button = Gtk.Button()
        self.refresh_button.set_label("Refresh")
        self.refresh_button.connect("clicked", self._on_refresh_clicked)
        
        self.connect_button = Gtk.Button()
        self.connect_button.set_label("Connect")
        self.connect_button.add_css_class("suggested-action")
        self.connect_button.connect("clicked", self._on_connect_clicked)
        self.connect_button.set_sensitive(False)
        
        button_box.append(self.refresh_button)
        button_box.append(self.connect_button)
        self.append(button_box)
        
        # Connect selection changed signal
        self.device_selection.connect("selection-changed", self._on_selection_changed)
    
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
    
    def _on_device_lost(self, discovery, device_id):
        """Handle device lost event."""
        for i in range(self.device_model.get_n_items()):
            device = self.device_model.get_item(i)
            if device.id == device_id:
                self.device_model.remove(i)
                self.status_label.set_text(f"Found {self.device_model.get_n_items()} devices")
                logger.info(f"Device lost: {device_id}")
                break
    
    def _on_selection_changed(self, selection, position, n_items):
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