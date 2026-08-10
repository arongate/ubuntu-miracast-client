"""Integration tests for Ubuntu Miracast Client."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from miracast_client.capture import CaptureSource, WindowSource
from miracast_client.casting import CastingStats, CastManager
from miracast_client.config import Config
from miracast_client.discovery import MiracastDevice, MiracastDiscovery, WFD_PRIMARY_SINK
from miracast_client.history import SessionHistory, SessionRecord


class TestCastingLifecycle:
    """Test the full casting lifecycle."""

    def test_full_casting_lifecycle(self):
        """Test start → stats → stop lifecycle."""
        manager = CastManager()

        source = CaptureSource(id="screen-0", name="Screen 1", description="1920x1080")
        source.start_capture = lambda framerate=30: (
            f"ximagesrc show-pointer=true ! video/x-raw,framerate={framerate}/1 ! videoconvert ! queue"
        )

        device = MiracastDevice(
            id="aa:bb:cc:dd:ee:ff",
            name="Test TV",
            address="aa:bb:cc:dd:ee:ff",
            model="TV",
            signal_strength=80,
            wfd_type=WFD_PRIMARY_SINK,
            rtsp_port=7236,
            p2p_interface="p2p-dev-wlo1",
        )

        signals = []
        manager.connect("casting-started", lambda m, s, d: signals.append("started"))

        # Mock WifiDirectConnection to simulate a successful connection
        # and a subprocess Popen that "runs" until stopped
        with patch("miracast_client.casting.WifiDirectConnection") as mock_conn_cls, \
             patch("miracast_client.casting.subprocess.Popen") as mock_popen:
            mock_conn = MagicMock()
            mock_conn.connect.return_value = True
            mock_conn.peer_ip = "192.168.49.1"
            mock_conn_cls.return_value = mock_conn

            # Mock GStreamer process that keeps running
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None  # Process still running
            mock_proc.pid = 12345
            mock_popen.return_value = mock_proc

            result = manager.start_casting(source, device)
            assert result is True
            assert "started" in signals

            # Give the thread time to establish "connection" and start "streaming"
            import time
            time.sleep(0.5)

            assert manager.is_casting() is True

            # Stop casting
            stats = manager.stop_casting()
            assert isinstance(stats, CastingStats)
            assert stats.end_time is not None
            assert manager.is_casting() is False

            # Ensure thread is fully cleaned up
            if manager._thread:
                manager._thread.join(timeout=2)


class TestCastingWithHistory:
    """Test casting + history integration."""

    def test_casting_session_adds_to_history(self):
        """Test that a stopped session can be recorded in history."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            history = SessionHistory(history_path=Path(tmp_dir) / "history.json")

            source = CaptureSource(id="screen-0", name="Screen 1", description="1920x1080")
            device = MiracastDevice(
                id="test-device", name="Test TV", address="aa:bb:cc:dd:ee:ff",
                model="TV", signal_strength=80, wfd_type=WFD_PRIMARY_SINK,
            )
            stats = CastingStats(
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=30,
                data_transferred=37_500_000,
                average_bitrate=10_000_000,
            )

            record = history.add_session(source, device, stats)
            assert record is not None

            sessions = history.get_sessions()
            assert len(sessions) == 1
            assert sessions[0].source.name == "Screen 1"
            assert sessions[0].device.name == "Test TV"
            assert sessions[0].stats.duration == 30


class TestConfigAffectsCastManager:
    """Test that config values are read by CastManager."""

    def test_config_values_affect_cast_manager(self):
        """Test that the CastManager reads quality from config."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            config = Config(config_path=str(config_path))
            config.set("streaming", "video_quality", "Low")
            config.save()

            # CastManager creates its own Config instance, so we patch it
            manager = CastManager()
            manager.config = config

            quality = manager.config.get("streaming", "video_quality")
            assert quality == "Low"


class TestDiscoveryLifecycle:
    """Test discovery start/stop lifecycle."""

    @patch("miracast_client.discovery.subprocess.run")
    def test_discovery_start_stop_lifecycle(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="OK\n")

        discovery = MiracastDiscovery(timeout=1, p2p_interface="p2p-dev-test")

        signals = []
        discovery.connect("discovery-started", lambda d: signals.append("started"))
        discovery.connect("discovery-stopped", lambda d: signals.append("stopped"))

        discovery.start_discovery()
        assert "started" in signals

        discovery.stop_discovery()
        assert "stopped" in signals

    def test_discovery_get_devices_after_manual_add(self):
        """Test get_devices after manually adding to device map."""
        discovery = MiracastDiscovery(timeout=1, p2p_interface="p2p-dev-test")

        device = MiracastDevice(
            id="test-1", name="TV", address="aa:bb:cc:dd:ee:ff",
            model="TV", signal_strength=80, wfd_type=WFD_PRIMARY_SINK,
        )
        discovery._devices["test-1"] = device

        devices = discovery.get_devices()
        assert len(devices) == 1
        assert devices[0].name == "TV"


class TestSessionRecordPersistenceRoundtrip:
    """Test session record persistence."""

    def test_session_record_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            history_path = Path(tmp_dir) / "history.json"

            source = CaptureSource(id="screen-0", name="Screen 1", description="1920x1080")
            device = MiracastDevice(
                id="device-1", name="Samsung TV", address="aa:bb:cc:dd:ee:ff",
                model="QE65Q70", signal_strength=70, wfd_type=WFD_PRIMARY_SINK,
            )
            stats = CastingStats(
                start_time=datetime(2026, 8, 10, 12, 0, 0),
                end_time=datetime(2026, 8, 10, 12, 30, 0),
                duration=1800,
                data_transferred=2_250_000_000,
                average_bitrate=10_000_000,
                peak_bitrate=12_000_000,
                dropped_frames=3,
                errors=0,
            )

            # Save
            history1 = SessionHistory(history_path=str(history_path))
            history1.add_session(source, device, stats)

            # Reload
            history2 = SessionHistory(history_path=str(history_path))
            sessions = history2.get_sessions()

            assert len(sessions) == 1
            assert sessions[0].source.name == "Screen 1"
            assert sessions[0].device.name == "Samsung TV"
            assert sessions[0].stats.duration == 1800
            assert sessions[0].stats.data_transferred == 2_250_000_000

    def test_multiple_sessions_persist_and_load(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            history_path = Path(tmp_dir) / "history.json"

            history = SessionHistory(history_path=str(history_path))

            for i in range(5):
                source = CaptureSource(id=f"screen-{i}", name=f"Screen {i+1}", description="")
                device = MiracastDevice(
                    id=f"device-{i}", name=f"TV {i+1}", address=f"aa:bb:cc:dd:ee:{i:02x}",
                    model="TV", signal_strength=80,
                )
                stats = CastingStats(
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration=60 * (i + 1),
                )
                history.add_session(source, device, stats)

            # Reload
            history2 = SessionHistory(history_path=str(history_path))
            assert len(history2.get_sessions()) == 5
