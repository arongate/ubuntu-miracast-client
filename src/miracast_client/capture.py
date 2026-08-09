"""Screen and window capture functionality."""

import gi
import logging
import uuid

gi.require_version('GLib', '2.0')
from gi.repository import GObject

try:
    gi.require_version('Gdk', '4.0')
    from gi.repository import Gdk
except (ValueError, ImportError):
    Gdk = None  # Gdk not available (e.g., in headless test environment)

logger = logging.getLogger(__name__)


class CaptureSource(GObject.Object):
    """Base class for capture sources."""

    def __init__(self, id, name, description, icon="video-display"):
        super().__init__()
        self.id = id
        self.name = name
        self.description = description
        self.icon = icon


class ScreenSource(CaptureSource):
    """Represents a screen/monitor for capturing."""
    
    def __init__(self, monitor_num, display, monitor):
        """Initialize a screen source.
        
        Args:
            monitor_num: Monitor number
            display: Gdk.Display object
            monitor: Gdk.Monitor object
        """
        geometry = monitor.get_geometry()
        width = geometry.width
        height = geometry.height
        
        super().__init__(
            id=f"screen-{monitor_num}",
            name=f"Screen {monitor_num + 1}",
            description=f"{width}x{height} | {monitor.get_manufacturer() or 'Unknown'} {monitor.get_model() or 'Monitor'}"
        )
        
        self.monitor_num = monitor_num
        self.display = display
        self.monitor = monitor
        self.width = width
        self.height = height
    
    def start_capture(self):
        """Start capturing this screen.
        
        Returns:
            A GStreamer pipeline string for capturing this screen
        """
        # In a real implementation, this would return a GStreamer pipeline
        # for capturing the screen using ximagesrc or similar.
        return f"ximagesrc display-name={self.display.get_name()} show-pointer=true ! video/x-raw,framerate=30/1 ! videoconvert ! queue"


class WindowSource(CaptureSource):
    """Represents an application window for capturing."""
    
    def __init__(self, window_id, title, app_name, icon_name=None):
        """Initialize a window source.
        
        Args:
            window_id: Window ID
            title: Window title
            app_name: Application name
            icon_name: Icon name for the application
        """
        super().__init__(
            id=f"window-{window_id}",
            name=title,
            description=f"Application: {app_name}",
            icon=icon_name or "application-x-executable"
        )
        
        self.window_id = window_id
        self.app_name = app_name
    
    def start_capture(self):
        """Start capturing this window.
        
        Returns:
            A GStreamer pipeline string for capturing this window
        """
        # In a real implementation, this would return a GStreamer pipeline
        # for capturing the window using ximagesrc with xid property or similar.
        return f"ximagesrc xid={self.window_id} ! video/x-raw,framerate=30/1 ! videoconvert ! queue"


def get_available_sources(screen_only=False, windows_only=False):
    """Get available capture sources.
    
    Args:
        screen_only: Only return screen sources
        windows_only: Only return window sources
    
    Returns:
        List of CaptureSource objects
    """
    sources = []
    
    # Get screens/monitors
    if not windows_only:
        try:
            if Gdk is None:
                logger.warning("Gdk not available, cannot enumerate screens")
            else:
                display = Gdk.Display.get_default()
                if display:
                    for i in range(display.get_n_monitors()):
                        monitor = display.get_monitor(i)
                        sources.append(ScreenSource(i, display, monitor))
        except Exception as e:
            logger.error(f"Failed to get monitors: {e}")
    
    # Get windows
    if not screen_only:
        try:
            # In a real implementation, we would use Wnck or similar to get window list
            # For this example, we'll simulate some windows
            sample_windows = [
                {"id": 12345, "title": "Firefox", "app": "Firefox Web Browser", "icon": "firefox"},
                {"id": 12346, "title": "Terminal", "app": "GNOME Terminal", "icon": "org.gnome.Terminal"},
                {"id": 12347, "title": "Document1.txt - Text Editor", "app": "GNOME Text Editor", "icon": "org.gnome.TextEditor"}
            ]
            
            for window in sample_windows:
                sources.append(WindowSource(
                    window["id"],
                    window["title"],
                    window["app"],
                    window["icon"]
                ))
        except Exception as e:
            logger.error(f"Failed to get windows: {e}")
    
    return sources