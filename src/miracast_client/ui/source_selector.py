"""Source selector UI component for Ubuntu Miracast Client."""

import gi
import logging

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, Gdk, Gio

from miracast_client.capture import ScreenSource, WindowSource, get_available_sources

logger = logging.getLogger(__name__)


class SourceSelector(Gtk.Box):
    """UI component for selecting a casting source."""
    
    __gsignals__ = {
        'source-selected': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }
    
    def __init__(self):
        """Initialize the source selector."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        
        self._setup_ui()
        self._load_sources()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Header
        header = Gtk.Label()
        header.set_markup("<span size='x-large'>Select What to Cast</span>")
        header.set_margin_bottom(24)
        self.append(header)
        
        # Source type selection
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self.screen_radio = Gtk.CheckButton()
        self.screen_radio.set_label("Entire Screen")
        self.screen_radio.set_active(True)
        self.screen_radio.connect("toggled", self._on_source_type_changed)
        
        self.window_radio = Gtk.CheckButton()
        self.window_radio.set_label("Application Window")
        self.window_radio.set_group(self.screen_radio)
        self.window_radio.connect("toggled", self._on_source_type_changed)
        
        type_box.append(self.screen_radio)
        type_box.append(self.window_radio)
        self.append(type_box)
        
        # Source list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(300)
        scrolled.set_vexpand(True)
        
        self.source_list = Gtk.ListView()
        self.source_model = Gio.ListStore()
        self.source_selection = Gtk.SingleSelection.new(self.source_model)
        self.source_list.set_model(self.source_selection)
        
        # Create factory for source items
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_source_item)
        factory.connect("bind", self._bind_source_item)
        self.source_list.set_factory(factory)
        
        scrolled.set_child(self.source_list)
        self.append(scrolled)
        
        # Select button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(24)
        
        self.select_button = Gtk.Button()
        self.select_button.set_label("Select")
        self.select_button.add_css_class("suggested-action")
        self.select_button.connect("clicked", self._on_select_clicked)
        self.select_button.set_sensitive(False)
        
        button_box.append(self.select_button)
        self.append(button_box)
        
        # Connect selection changed signal
        self.source_selection.connect("selection-changed", self._on_selection_changed)
    
    def _setup_source_item(self, factory, list_item):
        """Set up a source list item."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        icon = Gtk.Image()
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
    
    def _bind_source_item(self, factory, list_item):
        """Bind data to a source list item."""
        source = list_item.get_item()
        box = list_item.get_child()
        icon = box.get_first_child()
        text_box = box.get_last_child()
        title = text_box.get_first_child()
        description = title.get_next_sibling()
        
        title.set_text(source.name)
        description.set_text(source.description)
        
        if hasattr(source, 'icon') and source.icon:
            icon.set_from_icon_name(source.icon)
        else:
            icon.set_from_icon_name("video-display")
    
    def _load_sources(self):
        """Load available sources based on the selected type."""
        self.source_model.remove_all()
        
        try:
            if self.screen_radio.get_active():
                sources = get_available_sources(screen_only=True)
            else:
                sources = get_available_sources(windows_only=True)
            
            for source in sources:
                self.source_model.append(source)
            
            logger.info(f"Loaded {len(sources)} sources")
        except Exception as e:
            logger.error(f"Failed to load sources: {e}")
    
    def _on_source_type_changed(self, button):
        """Handle source type selection change."""
        self._load_sources()
    
    def _on_selection_changed(self, selection, position, n_items):
        """Handle source selection change."""
        self.select_button.set_sensitive(selection.get_selected() != Gtk.INVALID_LIST_POSITION)
    
    def _on_select_clicked(self, button):
        """Handle select button click."""
        position = self.source_selection.get_selected()
        if position != Gtk.INVALID_LIST_POSITION:
            source = self.source_model.get_item(position)
            self.emit("source-selected", source)