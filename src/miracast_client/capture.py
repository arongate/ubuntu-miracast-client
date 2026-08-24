"""Screen and window capture functionality using real X11/GStreamer."""

import logging
import os
import re
import subprocess

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GObject

try:
    gi.require_version("Gdk", "4.0")
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
            description=(
                f"{width}x{height} | "
                f"{monitor.get_manufacturer() or 'Unknown'} "
                f"{monitor.get_model() or 'Monitor'}"
            ),
        )

        self.monitor_num = monitor_num
        self.display = display
        self.monitor = monitor
        self.width = width
        self.height = height

    def start_capture(self, framerate=30):
        """Generate a GStreamer pipeline string for capturing this screen.

        Args:
            framerate: Target frame rate (default: 30).

        Returns:
            A GStreamer pipeline string element for capturing this screen.
        """
        # Use DISPLAY env variable as the authoritative source
        # Gdk display name may differ from what GStreamer expects
        display_name = os.environ.get("DISPLAY", ":0")
        return (
            f"ximagesrc display-name={display_name} show-pointer=true use-damage=false"
            f" ! video/x-raw,framerate={framerate}/1"
            f" ! videoconvert"
            f" ! queue"
        )


class WindowSource(CaptureSource):
    """Represents an application window for capturing."""

    def __init__(self, window_id, title, app_name, icon_name=None):
        """Initialize a window source.

        Args:
            window_id: X11 Window ID (integer)
            title: Window title
            app_name: Application name (from WM_CLASS)
            icon_name: Icon name for the application
        """
        super().__init__(
            id=f"window-{window_id}",
            name=title,
            description=f"Application: {app_name}",
            icon=icon_name or "application-x-executable",
        )

        self.window_id = window_id
        self.app_name = app_name

    def start_capture(self, framerate=30):
        """Generate a GStreamer pipeline string for capturing this window.

        Args:
            framerate: Target frame rate (default: 30).

        Returns:
            A GStreamer pipeline string element for capturing this window.
        """
        return (
            f"ximagesrc xid=0x{self.window_id:x} show-pointer=true use-damage=false"
            f" ! video/x-raw,framerate={framerate}/1"
            f" ! videoconvert"
            f" ! queue"
        )


def _get_real_windows():
    """Get list of real X11 windows using xprop.

    Returns:
        List of WindowSource objects for real visible windows.
    """
    windows: list[dict] = []

    try:
        # Get client window list from root window
        result = subprocess.run(
            ["xprop", "-root", "_NET_CLIENT_LIST"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.warning(f"xprop failed: {result.stderr}")
            return windows

        # Parse window IDs
        match = re.search(r"window id #\s*(.+)", result.stdout)
        if not match:
            return windows

        window_ids_str = match.group(1)
        window_ids = [wid.strip().rstrip(",") for wid in window_ids_str.split(",")]

        for wid_str in window_ids:
            try:
                wid = int(wid_str, 16)

                # Get window properties
                result = subprocess.run(
                    ["xprop", "-id", wid_str, "WM_NAME", "WM_CLASS", "_NET_WM_PID"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode != 0:
                    continue

                # Parse WM_NAME
                title = "Unknown"
                for line in result.stdout.split("\n"):
                    if "WM_NAME" in line and "=" in line:
                        # Handle both UTF8_STRING and STRING types
                        name_match = re.search(r'=\s*"(.+)"', line)
                        if name_match:
                            title = name_match.group(1)
                        break

                # Parse WM_CLASS (gives us app name)
                app_name = "Unknown"
                for line in result.stdout.split("\n"):
                    if "WM_CLASS" in line and "=" in line:
                        class_match = re.findall(r'"([^"]+)"', line)
                        if len(class_match) >= 2:
                            app_name = class_match[1]  # Second value is the class name
                        elif class_match:
                            app_name = class_match[0]
                        break

                # Skip desktop icon windows and other non-user windows
                if app_name.lower() in ("gjs", "gnome-shell"):
                    continue
                if "desktop icons" in title.lower():
                    continue

                # Determine icon name from app class
                icon_name = app_name.lower().replace(" ", "-")

                windows.append(
                    WindowSource(
                        window_id=wid,
                        title=title,
                        app_name=app_name,
                        icon_name=icon_name,
                    )
                )

            except (ValueError, subprocess.TimeoutExpired) as e:
                logger.debug(f"Error processing window {wid_str}: {e}")
                continue

    except FileNotFoundError:
        logger.warning("xprop not found. Install x11-utils for window enumeration.")
    except subprocess.TimeoutExpired:
        logger.warning("Timeout getting window list")
    except Exception as e:
        logger.error(f"Error enumerating windows: {e}")

    return windows


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
                # Fallback: create a single screen source using DISPLAY env
                display_name = os.environ.get("DISPLAY", ":0")
                # Try to get screen resolution via xrandr
                try:
                    result = subprocess.run(
                        ["xrandr", "--current"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    for line in result.stdout.split("\n"):
                        if " connected " in line and "primary" in line:
                            res_match = re.search(r"(\d+)x(\d+)", line)
                            if res_match:
                                w, h = int(res_match.group(1)), int(res_match.group(2))
                                # Create a minimal screen source without Gdk
                                source = CaptureSource(
                                    id="screen-0",
                                    name="Screen 1",
                                    description=f"{w}x{h} | Primary Display",
                                    icon="video-display",
                                )
                                # Add capture method
                                source.width = w
                                source.height = h
                                source.start_capture = lambda fr=30: (
                                    f"ximagesrc display-name={display_name}"
                                    f" show-pointer=true use-damage=false"
                                    f" ! video/x-raw,framerate={fr}/1"
                                    f" ! videoconvert ! queue"
                                )
                                sources.append(source)
                                break
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
            else:
                display = Gdk.Display.get_default()
                if display:
                    monitors = display.get_monitors()
                    for i in range(monitors.get_n_items()):
                        monitor = monitors.get_item(i)
                        sources.append(ScreenSource(i, display, monitor))
        except Exception as e:
            logger.error(f"Failed to get monitors: {e}")

    # Get windows (real X11 windows)
    if not screen_only:
        try:
            windows = _get_real_windows()
            sources.extend(windows)
        except Exception as e:
            logger.error(f"Failed to get windows: {e}")

    return sources
