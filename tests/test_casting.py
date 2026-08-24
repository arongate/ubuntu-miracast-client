"""Tests for the casting module."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from miracast_client.casting import (
    QUALITY_BITRATES,
    CastingStats,
    CastManager,
    WifiDirectConnection,
)


class TestCastingStats:
    """Tests for CastingStats dataclass."""

    def test_default_values(self):
        stats = CastingStats()
        assert stats.end_time is None
        assert stats.duration == 0
        assert stats.data_transferred == 0
        assert stats.average_bitrate == 0
        assert stats.peak_bitrate == 0
        assert stats.dropped_frames == 0
        assert stats.errors == 0

    def test_with_populated_fields(self):
        now = datetime.now()
        stats = CastingStats(
            start_time=now,
            duration=60,
            data_transferred=75_000_000,
            average_bitrate=10_000_000,
            peak_bitrate=12_000_000,
            dropped_frames=5,
            errors=1,
        )
        assert stats.start_time == now
        assert stats.duration == 60
        assert stats.data_transferred == 75_000_000


class TestQualityBitrates:
    """Tests for quality presets."""

    def test_all_qualities_defined(self):
        assert "Low" in QUALITY_BITRATES
        assert "Medium" in QUALITY_BITRATES
        assert "High" in QUALITY_BITRATES
        assert "Very High" in QUALITY_BITRATES

    def test_bitrate_ordering(self):
        assert QUALITY_BITRATES["Low"] < QUALITY_BITRATES["Medium"]
        assert QUALITY_BITRATES["Medium"] < QUALITY_BITRATES["High"]
        assert QUALITY_BITRATES["High"] < QUALITY_BITRATES["Very High"]


class TestCastManager:
    """Tests for CastManager class."""

    def test_initial_state(self):
        manager = CastManager()
        assert manager.is_casting() is False
        assert manager._gst_process is None
        assert manager._connection is None

    def test_start_casting_raises_value_error_with_none_source(self):
        manager = CastManager()
        device = MagicMock()
        with pytest.raises(ValueError, match="No source specified"):
            manager.start_casting(None, device)

    def test_start_casting_raises_value_error_with_none_device(self):
        manager = CastManager()
        source = MagicMock()
        with pytest.raises(ValueError, match="No device specified"):
            manager.start_casting(source, None)

    def test_start_casting_raises_runtime_error_if_already_casting(self):
        manager = CastManager()
        manager._casting = True
        with pytest.raises(RuntimeError, match="already active"):
            manager.start_casting(MagicMock(), MagicMock())

    @patch("miracast_client.casting.subprocess.Popen")
    @patch("miracast_client.casting.WifiDirectConnection")
    def test_start_casting_success(self, mock_conn_class, mock_popen):
        """Test that start_casting sets state correctly."""
        mock_conn = MagicMock()
        mock_conn.connect.return_value = True
        mock_conn.peer_ip = "192.168.49.1"
        mock_conn_class.return_value = mock_conn

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 99999
        mock_popen.return_value = mock_proc

        manager = CastManager()
        source = MagicMock()
        source.name = "Screen 1"
        source.start_capture.return_value = "ximagesrc ! videoconvert ! queue"

        device = MagicMock()
        device.name = "Test TV"
        device.address = "aa:bb:cc:dd:ee:ff"
        device.rtsp_port = 7236

        signals = []
        manager.connect("casting-started", lambda m, s, d: signals.append(("started", s, d)))

        result = manager.start_casting(source, device)

        assert result is True
        assert manager.is_casting() is True
        assert manager._stats is not None
        assert ("started", source, device) in signals

        # Clean up: stop the casting thread
        manager._stop_event.set()
        if manager._thread:
            manager._thread.join(timeout=2)

    def test_stop_casting_raises_runtime_error_if_not_casting(self):
        manager = CastManager()
        with pytest.raises(RuntimeError, match="No active casting session"):
            manager.stop_casting()

    def test_stop_casting_returns_stats(self):
        """Test that stop_casting returns stats with end time."""
        manager = CastManager()
        manager._casting = True
        manager._stats = CastingStats(start_time=datetime.now())
        manager._stop_event = MagicMock()
        manager._gst_process = None
        manager._connection = None
        manager._thread = None

        stats = manager.stop_casting()

        assert stats.end_time is not None
        assert stats.duration >= 0
        assert manager.is_casting() is False

    def test_stop_casting_emits_signal(self):
        """Test that stop_casting emits casting-stopped signal."""
        manager = CastManager()
        manager._casting = True
        manager._stats = CastingStats(start_time=datetime.now())
        manager._stop_event = MagicMock()
        manager._gst_process = None
        manager._connection = None
        manager._thread = None

        signals = []
        manager.connect("casting-stopped", lambda m, s: signals.append(s))

        manager.stop_casting()
        assert len(signals) == 1

    def test_stop_casting_resets_is_casting(self):
        manager = CastManager()
        manager._casting = True
        manager._stats = CastingStats(start_time=datetime.now())
        manager._stop_event = MagicMock()
        manager._gst_process = None
        manager._connection = None
        manager._thread = None

        manager.stop_casting()
        assert manager.is_casting() is False

    def test_stop_casting_terminates_gst_process(self):
        """Test that stop_casting kills the GStreamer subprocess."""
        manager = CastManager()
        manager._casting = True
        manager._stats = CastingStats(start_time=datetime.now())
        manager._stop_event = MagicMock()
        manager._thread = None
        manager._connection = None

        mock_process = MagicMock()
        manager._gst_process = mock_process

        manager.stop_casting()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()

    def test_stop_casting_disconnects_wifi_direct(self):
        """Test that stop_casting disconnects Wi-Fi Direct."""
        manager = CastManager()
        manager._casting = True
        manager._stats = CastingStats(start_time=datetime.now())
        manager._stop_event = MagicMock()
        manager._thread = None
        manager._gst_process = None

        mock_conn = MagicMock()
        manager._connection = mock_conn

        manager.stop_casting()

        mock_conn.disconnect.assert_called_once()


class TestWifiDirectConnection:
    """Tests for WifiDirectConnection class."""

    def test_initial_state(self):
        device = MagicMock()
        device.address = "aa:bb:cc:dd:ee:ff"
        device.p2p_interface = "p2p-dev-wlo1"

        conn = WifiDirectConnection(device)
        assert conn.is_connected is False
        assert conn.peer_ip is None
        assert conn.group_interface is None

    @patch("miracast_client.casting.subprocess.run")
    def test_connect_success(self, mock_run):
        """Test successful P2P connection."""
        device = MagicMock()
        device.address = "aa:bb:cc:dd:ee:ff"
        device.name = "Test TV"
        device.p2p_interface = "p2p-dev-wlo1"

        conn = WifiDirectConnection(device)

        # Mock the sequence of subprocess calls
        mock_run.side_effect = [
            # p2p_connect
            MagicMock(returncode=0, stdout="OK\n"),
            # ip link show (find group interface)
            MagicMock(returncode=0, stdout="5: p2p-wlo1-0: <BROADCAST> ...\n"),
            # ip addr show (get our IP)
            MagicMock(returncode=0, stdout="    inet 192.168.49.10/24 ...\n"),
            # ip neigh show (find peer IP)
            MagicMock(returncode=0, stdout="192.168.49.1 dev p2p-wlo1-0 lladdr ...\n"),
        ]

        result = conn.connect(timeout=5)
        assert result is True
        assert conn.is_connected is True
        assert conn.peer_ip == "192.168.49.1"

    @patch("miracast_client.casting.subprocess.run")
    def test_connect_failure(self, mock_run):
        """Test P2P connection failure."""
        device = MagicMock()
        device.address = "aa:bb:cc:dd:ee:ff"
        device.name = "Test TV"
        device.p2p_interface = "p2p-dev-wlo1"

        conn = WifiDirectConnection(device)
        mock_run.return_value = MagicMock(returncode=1, stdout="FAIL\n", stderr="")

        with pytest.raises(RuntimeError, match="P2P connect failed"):
            conn.connect(timeout=2)

    @patch("miracast_client.casting.subprocess.run")
    def test_disconnect(self, mock_run):
        """Test P2P disconnection."""
        device = MagicMock()
        device.address = "aa:bb:cc:dd:ee:ff"
        device.p2p_interface = "p2p-dev-wlo1"

        conn = WifiDirectConnection(device)
        conn._connected = True
        conn.group_interface = "p2p-wlo1-0"

        mock_run.return_value = MagicMock(returncode=0, stdout="OK\n")

        conn.disconnect()
        assert conn.is_connected is False
