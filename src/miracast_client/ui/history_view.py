"""History view UI component for Ubuntu Miracast Client."""

import logging
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, GObject, Gtk

logger = logging.getLogger(__name__)


class HistoryView(Gtk.Box):
    """UI component for viewing casting session history."""

    __gsignals__ = {
        "new-cast": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, session_history):
        """Initialize the history view."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_vexpand(True)

        self.session_history = session_history

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        # Header with action button (fixed)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.set_margin_top(24)
        header_box.set_margin_bottom(12)
        header_box.set_margin_start(24)
        header_box.set_margin_end(24)

        header = Gtk.Label()
        header.set_markup("<span size='x-large'>Casting History</span>")
        header.set_hexpand(True)
        header.set_halign(Gtk.Align.START)
        header_box.append(header)

        new_cast_button = Gtk.Button()
        new_cast_button.set_label("New Cast")
        new_cast_button.add_css_class("suggested-action")
        new_cast_button.connect("clicked", self._on_new_cast_clicked)
        header_box.append(new_cast_button)

        self.append(header_box)

        # Session list (scrollable)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_margin_start(24)
        scrolled.set_margin_end(24)

        self.session_list = Gtk.ListView()
        self.session_model = Gio.ListStore()
        self.session_selection = Gtk.SingleSelection.new(self.session_model)
        self.session_list.set_model(self.session_selection)

        # Create factory for session items
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_session_item)
        factory.connect("bind", self._bind_session_item)
        self.session_list.set_factory(factory)

        scrolled.set_child(self.session_list)
        self.append(scrolled)

        # Details view (shown when a session is selected)
        self.details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.details_box.set_margin_top(12)
        self.details_box.set_margin_bottom(24)
        self.details_box.set_margin_start(24)
        self.details_box.set_margin_end(24)
        self.details_box.set_visible(False)

        details_header = Gtk.Label()
        details_header.set_markup("<span size='large'>Session Details</span>")
        details_header.set_halign(Gtk.Align.START)
        details_header.set_margin_bottom(12)
        self.details_box.append(details_header)

        # Session details grid
        details_grid = Gtk.Grid()
        details_grid.set_column_spacing(24)
        details_grid.set_row_spacing(6)

        # Source
        source_label = Gtk.Label(label="Source:")
        source_label.set_halign(Gtk.Align.START)
        source_label.add_css_class("dim-label")
        details_grid.attach(source_label, 0, 0, 1, 1)

        self.source_value = Gtk.Label()
        self.source_value.set_halign(Gtk.Align.START)
        details_grid.attach(self.source_value, 1, 0, 1, 1)

        # Destination
        dest_label = Gtk.Label(label="Destination:")
        dest_label.set_halign(Gtk.Align.START)
        dest_label.add_css_class("dim-label")
        details_grid.attach(dest_label, 0, 1, 1, 1)

        self.dest_value = Gtk.Label()
        self.dest_value.set_halign(Gtk.Align.START)
        details_grid.attach(self.dest_value, 1, 1, 1, 1)

        # Start time
        start_label = Gtk.Label(label="Started:")
        start_label.set_halign(Gtk.Align.START)
        start_label.add_css_class("dim-label")
        details_grid.attach(start_label, 0, 2, 1, 1)

        self.start_value = Gtk.Label()
        self.start_value.set_halign(Gtk.Align.START)
        details_grid.attach(self.start_value, 1, 2, 1, 1)

        # Duration
        duration_label = Gtk.Label(label="Duration:")
        duration_label.set_halign(Gtk.Align.START)
        duration_label.add_css_class("dim-label")
        details_grid.attach(duration_label, 0, 3, 1, 1)

        self.duration_value = Gtk.Label()
        self.duration_value.set_halign(Gtk.Align.START)
        details_grid.attach(self.duration_value, 1, 3, 1, 1)

        # Data transferred
        data_label = Gtk.Label(label="Data Transferred:")
        data_label.set_halign(Gtk.Align.START)
        data_label.add_css_class("dim-label")
        details_grid.attach(data_label, 0, 4, 1, 1)

        self.data_value = Gtk.Label()
        self.data_value.set_halign(Gtk.Align.START)
        details_grid.attach(self.data_value, 1, 4, 1, 1)

        # Average bitrate
        bitrate_label = Gtk.Label(label="Average Bitrate:")
        bitrate_label.set_halign(Gtk.Align.START)
        bitrate_label.add_css_class("dim-label")
        details_grid.attach(bitrate_label, 0, 5, 1, 1)

        self.bitrate_value = Gtk.Label()
        self.bitrate_value.set_halign(Gtk.Align.START)
        details_grid.attach(self.bitrate_value, 1, 5, 1, 1)

        self.details_box.append(details_grid)
        self.append(self.details_box)

        # Connect selection changed signal
        self.session_selection.connect("selection-changed", self._on_selection_changed)

    def _setup_session_item(self, factory, list_item):
        """Set up a session list item."""
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

        subtitle = Gtk.Label()
        subtitle.set_halign(Gtk.Align.START)
        text_box.append(subtitle)

        timestamp = Gtk.Label()
        timestamp.set_halign(Gtk.Align.START)
        timestamp.add_css_class("caption")
        timestamp.add_css_class("dim-label")
        text_box.append(timestamp)

        box.append(text_box)
        list_item.set_child(box)

    def _bind_session_item(self, factory, list_item):
        """Bind data to a session list item."""
        session = list_item.get_item()
        box = list_item.get_child()
        text_box = box.get_last_child()
        title = text_box.get_first_child()
        subtitle = title.get_next_sibling()
        timestamp = subtitle.get_next_sibling()

        title.set_text(f"{session.source.name} → {session.device.name}")

        duration_mins = session.stats.duration // 60
        duration_secs = session.stats.duration % 60
        subtitle.set_text(
            f"Duration: {duration_mins}m {duration_secs}s"
            f" | {self._format_data_size(session.stats.data_transferred)}"
        )

        timestamp_str = session.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        timestamp.set_text(timestamp_str)

    def refresh(self):
        """Refresh the session list."""
        self.session_model.remove_all()

        sessions = self.session_history.get_sessions()
        for session in reversed(sessions):  # Show newest first
            self.session_model.append(session)

        logger.info(f"Loaded {len(sessions)} history sessions")

    def _on_selection_changed(self, selection, position, n_items):
        """Handle session selection change."""
        if position != Gtk.INVALID_LIST_POSITION:
            session = self.session_model.get_item(position)
            self._show_session_details(session)
            self.details_box.set_visible(True)
        else:
            self.details_box.set_visible(False)

    def _show_session_details(self, session):
        """Show details for the selected session."""
        self.source_value.set_text(session.source.name)
        self.dest_value.set_text(session.device.name)
        self.start_value.set_text(session.timestamp.strftime("%Y-%m-%d %H:%M:%S"))

        duration_mins = session.stats.duration // 60
        duration_secs = session.stats.duration % 60
        self.duration_value.set_text(f"{duration_mins}m {duration_secs}s")

        self.data_value.set_text(self._format_data_size(session.stats.data_transferred))
        self.bitrate_value.set_text(f"{session.stats.average_bitrate / 1000:.1f} Mbps")

    def _format_data_size(self, size_bytes):
        """Format data size in human-readable form."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def _on_new_cast_clicked(self, button):
        """Handle new cast button click."""
        self.emit("new-cast")
