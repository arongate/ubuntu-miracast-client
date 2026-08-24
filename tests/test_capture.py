"""Tests for the capture module."""

from unittest.mock import MagicMock, patch

from miracast_client.capture import (
    CaptureSource,
    ScreenSource,
    WindowSource,
    _get_real_windows,
    get_available_sources,
)


class TestCaptureSource:
    """Tests for CaptureSource base class."""

    def test_creation_stores_id(self):
        source = CaptureSource(id="test-1", name="Test", description="Desc")
        assert source.id == "test-1"

    def test_creation_with_all_fields(self):
        source = CaptureSource(id="x", name="Name", description="Desc", icon="my-icon")
        assert source.name == "Name"
        assert source.description == "Desc"
        assert source.icon == "my-icon"

    def test_creation_default_icon(self):
        source = CaptureSource(id="x", name="Name", description="Desc")
        assert source.icon == "video-display"

    def test_is_gobject(self):
        from gi.repository import GObject

        source = CaptureSource(id="x", name="Name", description="Desc")
        assert isinstance(source, GObject.Object)


class TestScreenSource:
    """Tests for ScreenSource class."""

    def _make_mock_monitor(self, width=1920, height=1080, manufacturer="LG", model="27UK850"):
        """Create a mocked Gdk.Monitor."""
        geometry = MagicMock()
        geometry.width = width
        geometry.height = height

        monitor = MagicMock()
        monitor.get_geometry.return_value = geometry
        monitor.get_manufacturer.return_value = manufacturer
        monitor.get_model.return_value = model

        display = MagicMock()
        display.get_name.return_value = ":0"

        return display, monitor

    def test_creation_with_mocked_monitor(self):
        display, monitor = self._make_mock_monitor()
        source = ScreenSource(0, display, monitor)

        assert source.id == "screen-0"
        assert source.name == "Screen 1"
        assert "1920x1080" in source.description
        assert "LG" in source.description
        assert source.width == 1920
        assert source.height == 1080

    def test_creation_second_monitor(self):
        display, monitor = self._make_mock_monitor(width=2560, height=1440)
        source = ScreenSource(1, display, monitor)

        assert source.id == "screen-1"
        assert source.name == "Screen 2"
        assert "2560x1440" in source.description

    def test_creation_with_unknown_manufacturer(self):
        display, monitor = self._make_mock_monitor(manufacturer=None)
        source = ScreenSource(0, display, monitor)
        assert "Unknown" in source.description

    def test_creation_with_unknown_model(self):
        display, monitor = self._make_mock_monitor(model=None)
        source = ScreenSource(0, display, monitor)
        assert "Monitor" in source.description

    def test_start_capture_returns_gstreamer_pipeline(self):
        display, monitor = self._make_mock_monitor()
        source = ScreenSource(0, display, monitor)
        pipeline = source.start_capture()

        assert "ximagesrc" in pipeline
        assert "display-name=" in pipeline
        assert "show-pointer=true" in pipeline
        assert "framerate=30/1" in pipeline
        assert "videoconvert" in pipeline

    def test_start_capture_custom_framerate(self):
        display, monitor = self._make_mock_monitor()
        source = ScreenSource(0, display, monitor)
        pipeline = source.start_capture(framerate=60)

        assert "framerate=60/1" in pipeline

    def test_stores_monitor_reference(self):
        display, monitor = self._make_mock_monitor()
        source = ScreenSource(0, display, monitor)
        assert source.monitor is monitor
        assert source.display is display

    def test_is_gobject(self):
        from gi.repository import GObject

        display, monitor = self._make_mock_monitor()
        source = ScreenSource(0, display, monitor)
        assert isinstance(source, GObject.Object)


class TestWindowSource:
    """Tests for WindowSource class."""

    def test_creation_with_all_fields(self):
        source = WindowSource(
            window_id=0x1E00004, title="Firefox", app_name="Firefox", icon_name="firefox"
        )
        assert source.id == "window-31457284"
        assert source.name == "Firefox"
        assert source.app_name == "Firefox"
        assert source.icon == "firefox"
        assert "Application: Firefox" in source.description

    def test_creation_with_default_icon(self):
        source = WindowSource(window_id=123, title="Test", app_name="App")
        assert source.icon == "application-x-executable"

    def test_start_capture_returns_gstreamer_pipeline(self):
        source = WindowSource(window_id=0x1E00004, title="Firefox", app_name="Firefox")
        pipeline = source.start_capture()

        assert "ximagesrc" in pipeline
        assert "xid=0x1e00004" in pipeline
        assert "framerate=30/1" in pipeline
        assert "videoconvert" in pipeline

    def test_start_capture_custom_framerate(self):
        source = WindowSource(window_id=0x1E00004, title="Firefox", app_name="Firefox")
        pipeline = source.start_capture(framerate=24)
        assert "framerate=24/1" in pipeline

    def test_is_gobject(self):
        from gi.repository import GObject

        source = WindowSource(window_id=123, title="Test", app_name="App")
        assert isinstance(source, GObject.Object)


class TestGetRealWindows:
    """Tests for _get_real_windows function."""

    @patch("miracast_client.capture.subprocess.run")
    def test_parses_real_window_list(self, mock_run):
        """Test parsing actual xprop output."""
        # Mock _NET_CLIENT_LIST
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="_NET_CLIENT_LIST(WINDOW): window id # 0x1e00004, 0x2000004\n",
            ),
            # First window xprop
            MagicMock(
                returncode=0,
                stdout=(
                    'WM_NAME(UTF8_STRING) = "VS Code"\n'
                    'WM_CLASS(STRING) = "code", "Code"\n'
                    "_NET_WM_PID(CARDINAL) = 1234\n"
                ),
            ),
            # Second window xprop
            MagicMock(
                returncode=0,
                stdout=(
                    'WM_NAME(UTF8_STRING) = "Google Chrome"\n'
                    'WM_CLASS(STRING) = "google-chrome", "Google-chrome"\n'
                    "_NET_WM_PID(CARDINAL) = 5678\n"
                ),
            ),
        ]

        windows = _get_real_windows()
        assert len(windows) == 2
        assert windows[0].name == "VS Code"
        assert windows[0].app_name == "Code"
        assert windows[0].window_id == 0x1E00004
        assert windows[1].name == "Google Chrome"
        assert windows[1].app_name == "Google-chrome"

    @patch("miracast_client.capture.subprocess.run")
    def test_skips_desktop_icons(self, mock_run):
        """Test that GNOME shell desktop icons are filtered out."""
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="_NET_CLIENT_LIST(WINDOW): window id # 0x3600008\n",
            ),
            MagicMock(
                returncode=0,
                stdout=(
                    'WM_NAME(STRING) = "Desktop Icons 1"\n'
                    'WM_CLASS(STRING) = "gjs", "Gjs"\n'
                    "_NET_WM_PID(CARDINAL) = 1234\n"
                ),
            ),
        ]

        windows = _get_real_windows()
        assert len(windows) == 0

    @patch("miracast_client.capture.subprocess.run")
    def test_handles_xprop_not_found(self, mock_run):
        """Test graceful handling when xprop is not installed."""
        mock_run.side_effect = FileNotFoundError("xprop not found")

        windows = _get_real_windows()
        assert windows == []

    @patch("miracast_client.capture.subprocess.run")
    def test_handles_xprop_failure(self, mock_run):
        """Test graceful handling when xprop fails."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error")

        windows = _get_real_windows()
        assert windows == []


class TestGetAvailableSources:
    """Tests for get_available_sources function."""

    @patch("miracast_client.capture._get_real_windows")
    @patch("miracast_client.capture.Gdk", None)
    def test_get_available_sources_gdk_none_with_windows(self, mock_windows):
        """Test that windows are returned even when Gdk is not available."""
        mock_windows.return_value = [
            WindowSource(window_id=123, title="Test", app_name="App"),
        ]
        sources = get_available_sources()
        assert any(isinstance(s, WindowSource) for s in sources)

    @patch("miracast_client.capture._get_real_windows")
    def test_get_available_sources_windows_only(self, mock_windows):
        """Test windows_only parameter."""
        mock_windows.return_value = [
            WindowSource(window_id=123, title="Test", app_name="App"),
        ]
        sources = get_available_sources(windows_only=True)
        # Should only have windows, no screens
        for s in sources:
            assert isinstance(s, WindowSource)

    @patch("miracast_client.capture._get_real_windows")
    @patch("miracast_client.capture.Gdk")
    def test_get_available_sources_screen_only(self, mock_gdk, mock_windows):
        """Test screen_only parameter - windows not included."""
        mock_windows.return_value = [
            WindowSource(window_id=123, title="Test", app_name="App"),
        ]
        # Mock Gdk to return no monitors (simplified)
        mock_display = MagicMock()
        mock_display.get_monitors.return_value = MagicMock(get_n_items=MagicMock(return_value=0))
        mock_gdk.Display.get_default.return_value = mock_display

        get_available_sources(screen_only=True)
        # _get_real_windows should not be called
        mock_windows.assert_not_called()

    @patch("miracast_client.capture.Gdk", None)
    @patch("miracast_client.capture._get_real_windows")
    def test_get_available_sources_gdk_none(self, mock_windows):
        """Test with Gdk not available and no windows."""
        mock_windows.return_value = []
        sources = get_available_sources(screen_only=True)
        # Should try xrandr fallback but we're not mocking that
        assert isinstance(sources, list)
