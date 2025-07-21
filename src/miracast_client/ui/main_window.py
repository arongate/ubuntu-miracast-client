"""Main window for the Ubuntu Miracast Client."""

import gi
import logging
from enum import Enum

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio, GdkPixbuf

from miracast_client.ui.source_selector import SourceSelector
from miracast_client.ui.device_selector import DeviceSelector
from miracast_client.ui.history_view import HistoryView
from miracast_client.ui.settings_view import SettingsView

logger = logging.getLogger(__name__)


class Page(Enum):
    """Enum for the different pages in the application."""
    SOURCE_SELECTION = 0
    DEVICE_SELECTION = 1
    CASTING = 2
    HISTORY = 3
    SETTINGS = 4


class MainWindow(Adw.ApplicationWindow):
    """Main window for the Ubuntu Miracast Client."""

    def __init__(self, application, discovery, cast_manager, session_history):
        """Initialize the main window."""
        super().__init__(application=application)
        
        self.discovery = discovery
        self.cast_manager = cast_manager
        self.session_history = session_history
        
        self.selected_source = None
        self.selected_device = None
        
        self._setup_ui()
        logger.info("Main window initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Set window properties
        self.set_title("Ubuntu Miracast Client")
        self.set_default_size(800, 600)
        
        # Create header bar
        header = Adw.HeaderBar()
        menu_button = Gtk.MenuButton()
        menu = Gio.Menu()
        menu.append("Settings", "app.settings")
        menu.append("About", "app.about")
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)
        
        # Create stack for different pages
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        # Create source selection page
        self.source_selector = SourceSelector()
        self.source_selector.connect("source-selected", self._on_source_selected)
        self.stack.add_titled(self.source_selector, "source", "Select Source")
        
        # Create device selection page
        self.device_selector = DeviceSelector(self.discovery)
        self.device_selector.connect("device-selected", self._on_device_selected)
        self.stack.add_titled(self.device_selector, "device", "Select Device")
        
        # Create history page
        self.history_view = HistoryView(self.session_history)
        self.history_view.connect("new-cast", self._on_new_cast_from_history)
        self.stack.add_titled(self.history_view, "history", "History")
        
        # Create settings page
        self.settings_view = SettingsView()
        self.stack.add_titled(self.settings_view, "settings", "Settings")
        
        # Create main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(header)
        main_box.append(self.stack)
        
        # Create status bar
        self.status_bar = Gtk.Label()
        self.status_bar.set_text("Ready")
        main_box.append(self.status_bar)
        
        # Set the content
        self.set_content(main_box)
        
        # Set up actions
        self._setup_actions()
        
        # Start with source selection
        self.show_page(Page.SOURCE_SELECTION)
    
    def _setup_actions(self):
        """Set up application actions."""
        # Settings action
        settings_action = Gio.SimpleAction.new("settings", None)
        settings_action.connect("activate", self._on_settings_action)
        self.add_action(settings_action)
        
        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about_action)
        self.add_action(about_action)
        
        # New cast action
        new_cast_action = Gio.SimpleAction.new("new-cast", None)
        new_cast_action.connect("activate", self._on_new_cast_action)
        self.add_action(new_cast_action)
        
        # Stop cast action
        stop_cast_action = Gio.SimpleAction.new("stop-cast", None)
        stop_cast_action.connect("activate", self._on_stop_cast_action)
        self.add_action(stop_cast_action)
    
    def show_page(self, page):
        """Show the specified page."""
        if page == Page.SOURCE_SELECTION:
            self.stack.set_visible_child_name("source")
        elif page == Page.DEVICE_SELECTION:
            self.stack.set_visible_child_name("device")
            self.device_selector.start_discovery()
        elif page == Page.HISTORY:
            self.stack.set_visible_child_name("history")
            self.history_view.refresh()
        elif page == Page.SETTINGS:
            self.stack.set_visible_child_name("settings")
    
    def _on_source_selected(self, selector, source):
        """Handle source selection."""
        self.selected_source = source
        logger.info(f"Source selected: {source.name}")
        self.show_page(Page.DEVICE_SELECTION)
    
    def _on_device_selected(self, selector, device):
        """Handle device selection."""
        self.selected_device = device
        logger.info(f"Device selected: {device.name}")
        self._start_casting()
    
    def _on_new_cast_from_history(self, history_view):
        """Handle new cast request from history view."""
        self.show_page(Page.SOURCE_SELECTION)
    
    def _on_settings_action(self, action, parameter):
        """Handle settings action."""
        self.show_page(Page.SETTINGS)
    
    def _on_about_action(self, action, parameter):
        """Show about dialog."""
        about = Adw.AboutWindow(
            transient_for=self,
            application_name="Ubuntu Miracast Client",
            application_icon="video-display",
            developer_name="Ubuntu Miracast Team",
            version="1.0.0",
            developers=["Ubuntu Miracast Team"],
            copyright="© 2023 Ubuntu Miracast Team",
            license_type=Gtk.License.MIT_X11,
            website="https://github.com/yourusername/ubuntu-miracast-client",
            issue_url="https://github.com/yourusername/ubuntu-miracast-client/issues"
        )
        about.present()
    
    def _on_new_cast_action(self, action, parameter):
        """Handle new cast action."""
        self.show_page(Page.SOURCE_SELECTION)
    
    def _on_stop_cast_action(self, action, parameter):
        """Handle stop cast action."""
        if self.cast_manager.is_casting():
            self._stop_casting()
    
    def _start_casting(self):
        """Start the casting session."""
        try:
            self.cast_manager.start_casting(self.selected_source, self.selected_device)
            self.status_bar.set_text(f"Casting to {self.selected_device.name}")
            logger.info(f"Started casting to {self.selected_device.name}")
            
            # Minimize window
            self.minimize()
        except Exception as e:
            logger.error(f"Failed to start casting: {e}")
            error_dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Casting Error",
                body=f"Failed to start casting: {str(e)}",
                buttons=["OK"]
            )
            error_dialog.present()
    
    def _stop_casting(self):
        """Stop the current casting session."""
        try:
            session_stats = self.cast_manager.stop_casting()
            self.session_history.add_session(
                self.selected_source,
                self.selected_device,
                session_stats
            )
            self.status_bar.set_text("Casting stopped")
            logger.info("Casting stopped")
            
            # Show history page
            self.show_page(Page.HISTORY)
        except Exception as e:
            logger.error(f"Failed to stop casting: {e}")
            error_dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Error",
                body=f"Failed to stop casting: {str(e)}",
                buttons=["OK"]
            )
            error_dialog.present()