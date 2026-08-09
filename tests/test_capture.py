"""Tests for the capture module."""

import unittest
from unittest.mock import patch, MagicMock

import gi
gi.require_version('GLib', '2.0')
from gi.repository import GObject

from miracast_client.capture import CaptureSource, ScreenSource, WindowSource, get_available_sources
import miracast_client.capture as capture_module


class TestCaptureSource(unittest.TestCase):
    """Test cases for the CaptureSource base class."""

    def test_creation_with_all_fields(self):
        """Test CaptureSource creation with all fields."""
        source = CaptureSource(
            id="test-1",
            name="Test Source",
            description="A test source",
            icon="custom-icon"
        )
        self.assertEqual(source.id, "test-1")
        self.assertEqual(source.name, "Test Source")
        self.assertEqual(source.description, "A test source")
        self.assertEqual(source.icon, "custom-icon")

    def test_creation_default_icon(self):
        """Test CaptureSource uses default icon when not specified."""
        source = CaptureSource(
            id="test-2",
            name="Test Source 2",
            description="Another test source"
        )
        self.assertEqual(source.icon, "video-display")

    def test_creation_stores_id(self):
        """Test CaptureSource stores the id correctly."""
        source = CaptureSource(id="unique-id-123", name="Name", description="Desc")
        self.assertEqual(source.id, "unique-id-123")

    def test_is_gobject(self):
        """Test CaptureSource is a GObject subclass."""
        source = CaptureSource(id="x", name="n", description="d")
        self.assertIsInstance(source, GObject.Object)


class TestScreenSource(unittest.TestCase):
    """Test cases for the ScreenSource class."""

    def _make_mock_monitor(self, width=1920, height=1080, manufacturer="Dell", model="U2722D"):
        """Create a mock monitor."""
        mock_monitor = MagicMock()
        mock_geometry = MagicMock()
        mock_geometry.width = width
        mock_geometry.height = height
        mock_monitor.get_geometry.return_value = mock_geometry
        mock_monitor.get_manufacturer.return_value = manufacturer
        mock_monitor.get_model.return_value = model
        return mock_monitor

    def _make_mock_display(self, name=":0"):
        """Create a mock display."""
        mock_display = MagicMock()
        mock_display.get_name.return_value = name
        return mock_display

    def test_creation_with_mocked_monitor(self):
        """Test ScreenSource creation with mocked Gdk.Monitor."""
        monitor = self._make_mock_monitor()
        display = self._make_mock_display()
        source = ScreenSource(0, display, monitor)

        self.assertEqual(source.id, "screen-0")
        self.assertEqual(source.name, "Screen 1")
        self.assertEqual(source.description, "1920x1080 | Dell U2722D")
        self.assertEqual(source.monitor_num, 0)
        self.assertEqual(source.width, 1920)
        self.assertEqual(source.height, 1080)

    def test_creation_second_monitor(self):
        """Test ScreenSource creation for monitor index 1."""
        monitor = self._make_mock_monitor()
        display = self._make_mock_display()
        source = ScreenSource(1, display, monitor)

        self.assertEqual(source.id, "screen-1")
        self.assertEqual(source.name, "Screen 2")

    def test_creation_with_unknown_manufacturer(self):
        """Test ScreenSource with None manufacturer."""
        monitor = self._make_mock_monitor(manufacturer=None)
        display = self._make_mock_display()
        source = ScreenSource(0, display, monitor)

        self.assertIn("Unknown", source.description)

    def test_creation_with_unknown_model(self):
        """Test ScreenSource with None model."""
        monitor = self._make_mock_monitor(model=None)
        display = self._make_mock_display()
        source = ScreenSource(0, display, monitor)

        self.assertIn("Monitor", source.description)

    def test_start_capture_returns_gstreamer_pipeline(self):
        """Test ScreenSource.start_capture() returns proper GStreamer pipeline string."""
        monitor = self._make_mock_monitor()
        display = self._make_mock_display(":0")
        source = ScreenSource(0, display, monitor)
        pipeline = source.start_capture()

        self.assertIsInstance(pipeline, str)
        self.assertIn("ximagesrc", pipeline)
        self.assertIn("display-name=:0", pipeline)
        self.assertIn("show-pointer=true", pipeline)
        self.assertIn("video/x-raw", pipeline)
        self.assertIn("framerate=30/1", pipeline)
        self.assertIn("videoconvert", pipeline)
        self.assertIn("queue", pipeline)

    def test_stores_monitor_reference(self):
        """Test ScreenSource stores the monitor and display references."""
        monitor = self._make_mock_monitor()
        display = self._make_mock_display()
        source = ScreenSource(0, display, monitor)
        self.assertEqual(source.monitor, monitor)
        self.assertEqual(source.display, display)

    def test_is_gobject(self):
        """Test ScreenSource is a GObject subclass."""
        monitor = self._make_mock_monitor()
        display = self._make_mock_display()
        source = ScreenSource(0, display, monitor)
        self.assertIsInstance(source, GObject.Object)


class TestWindowSource(unittest.TestCase):
    """Test cases for the WindowSource class."""

    def test_creation_with_all_fields(self):
        """Test WindowSource creation with all fields."""
        source = WindowSource(
            window_id=12345,
            title="My Firefox Window",
            app_name="Firefox Web Browser",
            icon_name="firefox"
        )

        self.assertEqual(source.id, "window-12345")
        self.assertEqual(source.name, "My Firefox Window")
        self.assertEqual(source.description, "Application: Firefox Web Browser")
        self.assertEqual(source.icon, "firefox")
        self.assertEqual(source.window_id, 12345)
        self.assertEqual(source.app_name, "Firefox Web Browser")

    def test_creation_with_default_icon(self):
        """Test WindowSource uses default icon when icon_name is None."""
        source = WindowSource(
            window_id=99999,
            title="Some Window",
            app_name="Unknown App",
            icon_name=None
        )

        self.assertEqual(source.icon, "application-x-executable")

    def test_start_capture_returns_gstreamer_pipeline(self):
        """Test WindowSource.start_capture() returns proper GStreamer pipeline string."""
        source = WindowSource(
            window_id=12345,
            title="Test Window",
            app_name="Test App"
        )
        pipeline = source.start_capture()

        self.assertIsInstance(pipeline, str)
        self.assertIn("ximagesrc", pipeline)
        self.assertIn("xid=12345", pipeline)
        self.assertIn("video/x-raw", pipeline)
        self.assertIn("framerate=30/1", pipeline)
        self.assertIn("videoconvert", pipeline)
        self.assertIn("queue", pipeline)

    def test_is_gobject(self):
        """Test WindowSource is a GObject subclass."""
        source = WindowSource(window_id=1, title="t", app_name="a")
        self.assertIsInstance(source, GObject.Object)


class TestGetAvailableSources(unittest.TestCase):
    """Test cases for the get_available_sources function."""

    def _create_mock_gdk_module(self, num_monitors=2):
        """Create a mock Gdk module with Display."""
        mock_gdk = MagicMock()
        mock_display = MagicMock()
        mock_display.get_n_monitors.return_value = num_monitors
        mock_display.get_name.return_value = ":0"

        monitors = []
        for i in range(num_monitors):
            monitor = MagicMock()
            geometry = MagicMock()
            geometry.width = 1920
            geometry.height = 1080
            monitor.get_geometry.return_value = geometry
            monitor.get_manufacturer.return_value = f"Manufacturer{i}"
            monitor.get_model.return_value = f"Model{i}"
            monitors.append(monitor)

        mock_display.get_monitor.side_effect = lambda i: monitors[i]
        mock_gdk.Display.get_default.return_value = mock_display
        return mock_gdk

    def test_get_available_sources_with_display(self):
        """Test get_available_sources() with mocked Gdk.Display."""
        mock_gdk = self._create_mock_gdk_module(2)
        original_gdk = capture_module.Gdk
        capture_module.Gdk = mock_gdk
        try:
            sources = get_available_sources()

            screen_sources = [s for s in sources if isinstance(s, ScreenSource)]
            window_sources = [s for s in sources if isinstance(s, WindowSource)]

            self.assertEqual(len(screen_sources), 2)
            self.assertEqual(len(window_sources), 3)
        finally:
            capture_module.Gdk = original_gdk

    def test_get_available_sources_screen_only(self):
        """Test get_available_sources(screen_only=True) only returns screens."""
        mock_gdk = self._create_mock_gdk_module(2)
        original_gdk = capture_module.Gdk
        capture_module.Gdk = mock_gdk
        try:
            sources = get_available_sources(screen_only=True)

            for source in sources:
                self.assertIsInstance(source, ScreenSource)
            self.assertEqual(len(sources), 2)
        finally:
            capture_module.Gdk = original_gdk

    def test_get_available_sources_windows_only(self):
        """Test get_available_sources(windows_only=True) only returns windows."""
        sources = get_available_sources(windows_only=True)

        for source in sources:
            self.assertIsInstance(source, WindowSource)
        self.assertEqual(len(sources), 3)

    def test_get_available_sources_gdk_none(self):
        """Test graceful handling when Gdk is None (headless environment)."""
        original_gdk = capture_module.Gdk
        capture_module.Gdk = None
        try:
            sources = get_available_sources(screen_only=True)
            self.assertEqual(len(sources), 0)
        finally:
            capture_module.Gdk = original_gdk

    def test_get_available_sources_gdk_none_with_windows(self):
        """Test that windows are still returned when Gdk is None."""
        original_gdk = capture_module.Gdk
        capture_module.Gdk = None
        try:
            sources = get_available_sources()

            window_sources = [s for s in sources if isinstance(s, WindowSource)]
            self.assertEqual(len(window_sources), 3)
        finally:
            capture_module.Gdk = original_gdk

    def test_get_available_sources_display_returns_none(self):
        """Test graceful handling when display.get_default() returns None."""
        mock_gdk = MagicMock()
        mock_gdk.Display.get_default.return_value = None
        original_gdk = capture_module.Gdk
        capture_module.Gdk = mock_gdk
        try:
            sources = get_available_sources(screen_only=True)
            self.assertEqual(len(sources), 0)
        finally:
            capture_module.Gdk = original_gdk


if __name__ == '__main__':
    unittest.main()
