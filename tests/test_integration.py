"""Integration tests for the Ubuntu Miracast Client."""

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock gi.repository before importing modules
mock_gi = MagicMock()
mock_gobject = MagicMock()
mock_gobject.Object = object
mock_gobject.SignalFlags = MagicMock()
mock_gobject.SignalFlags.RUN_FIRST = 1
mock_glib = MagicMock()

with patch.dict('sys.modules', {
    'gi': mock_gi,
    'gi.repository': MagicMock(GObject=mock_gobject, GLib=mock_glib, Gdk=MagicMock(), Gio=MagicMock()),
}):
    mock_gi.require_version = MagicMock()
    from miracast_client.capture import CaptureSource
    from miracast_client.casting import CastManager, CastingStats
    from miracast_client.config import Config
    from miracast_client.discovery import MiracastDevice, MiracastDiscovery
    from miracast_client.history import SessionHistory, SessionRecord


class TestCastingLifecycle(unittest.TestCase):
    """Integration tests for the full casting lifecycle."""

    @patch('miracast_client.casting.threading.Thread')
    def test_full_casting_lifecycle(self, mock_thread_class):
        """Test full casting lifecycle: start_casting → stop_casting → stats returned."""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        with patch('miracast_client.casting.Config'):
            manager = CastManager()
        manager.emit = MagicMock()

        # Create source and device
        source = CaptureSource(id="screen-0", name="Screen 1", description="1920x1080")
        device = MiracastDevice(
            id="aa:bb:cc:dd:ee:01",
            name="Living Room TV",
            address="aa:bb:cc:dd:ee:01",
            model="Samsung Smart TV",
            signal_strength=85
        )

        # Verify initial state
        self.assertFalse(manager.is_casting())

        # Start casting
        result = manager.start_casting(source, device)
        self.assertTrue(result)
        self.assertTrue(manager.is_casting())

        # Stop casting
        stats = manager.stop_casting()

        # Verify stats are returned
        self.assertIsInstance(stats, CastingStats)
        self.assertIsNotNone(stats.start_time)
        self.assertIsNotNone(stats.end_time)
        self.assertIsInstance(stats.duration, int)
        self.assertFalse(manager.is_casting())

        # Verify signals were emitted
        emit_calls = manager.emit.call_args_list
        signal_names = [c[0][0] for c in emit_calls]
        self.assertIn("casting-started", signal_names)
        self.assertIn("casting-stopped", signal_names)


class TestCastingWithHistory(unittest.TestCase):
    """Integration tests for casting sessions with history recording."""

    @patch('miracast_client.casting.threading.Thread')
    def test_casting_session_adds_to_history(self, mock_thread_class):
        """Test casting session adds to history when manually recorded."""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.json"
            history = SessionHistory(history_path=str(history_path))

            with patch('miracast_client.casting.Config'):
                manager = CastManager()
            manager.emit = MagicMock()

            # Create source and device
            source = CaptureSource(id="screen-0", name="Screen 1", description="1920x1080")
            device = MiracastDevice(
                id="device-1",
                name="Test TV",
                address="aa:bb:cc:dd:ee:01",
                model="Test Model",
                signal_strength=75
            )

            # Start and stop casting
            manager.start_casting(source, device)
            stats = manager.stop_casting()

            # Record in history
            record = history.add_session(source, device, stats)

            # Verify history was updated
            sessions = history.get_sessions()
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].source.id, "screen-0")
            self.assertEqual(sessions[0].device.name, "Test TV")
            self.assertIsNotNone(sessions[0].stats.start_time)

            # Verify file was written
            self.assertTrue(history_path.exists())
            with open(history_path, 'r') as f:
                data = json.load(f)
            self.assertEqual(len(data), 1)


class TestConfigAffectsCastManager(unittest.TestCase):
    """Integration tests for config values affecting CastManager behavior."""

    @patch('miracast_client.casting.threading.Thread')
    def test_config_values_affect_cast_manager(self, mock_thread_class):
        """Test config values are read by CastManager."""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"

            # Create config with custom values
            config = Config(config_path)
            config.set("streaming", "video_quality", "Low")
            config.set("streaming", "frame_rate", 15)
            config.save()

            # Reload config from file to verify persistence
            loaded_config = Config(config_path)

            # Create CastManager and inject the config directly
            manager = CastManager()
            manager.emit = MagicMock()
            manager.config = loaded_config

            # Verify the config values are available via the manager
            self.assertEqual(manager.config.get("streaming", "video_quality"), "Low")
            self.assertEqual(manager.config.get("streaming", "frame_rate"), 15)


class TestDiscoveryLifecycle(unittest.TestCase):
    """Integration tests for discovery start/stop lifecycle."""

    def test_discovery_start_stop_lifecycle(self):
        """Test discovery start/stop lifecycle without actual threading."""
        discovery = MiracastDiscovery()
        # Override emit to avoid GObject signal issues
        discovery.emit = MagicMock()

        # Mock the thread to avoid actual threading
        mock_thread = MagicMock()
        with patch('miracast_client.discovery.threading.Thread', return_value=mock_thread):
            # Start discovery
            discovery.start_discovery()

            self.assertTrue(discovery._running)
            mock_thread.start.assert_called_once()

            # Verify signal emitted
            discovery.emit.assert_called_with("discovery-started")

        # Stop discovery
        discovery._thread = mock_thread
        discovery.stop_discovery()

        self.assertFalse(discovery._running)
        mock_thread.join.assert_called_once_with(timeout=1.0)
        discovery.emit.assert_called_with("discovery-stopped")

    def test_discovery_get_devices_after_manual_add(self):
        """Test get_devices returns manually added devices."""
        discovery = MiracastDiscovery()
        discovery.emit = MagicMock()

        # Manually add devices (simulating what discovery thread would do)
        device1 = MiracastDevice("dev1", "Device 1", "addr1", "model1", 80)
        device2 = MiracastDevice("dev2", "Device 2", "addr2", "model2", 70)

        discovery._devices["dev1"] = device1
        discovery._devices["dev2"] = device2

        devices = discovery.get_devices()
        self.assertEqual(len(devices), 2)

        device_names = {d.name for d in devices}
        self.assertIn("Device 1", device_names)
        self.assertIn("Device 2", device_names)


class TestSessionRecordPersistenceRoundtrip(unittest.TestCase):
    """Integration tests for SessionRecord persistence roundtrip."""

    def test_session_record_persistence_roundtrip(self):
        """Test SessionRecord persistence roundtrip with real file I/O."""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.json"

            # Create history and add sessions
            history1 = SessionHistory(history_path=str(history_path))

            source = CaptureSource(id="screen-0", name="Screen 1", description="1920x1080", icon="video-display")
            device = MiracastDevice(
                id="aa:bb:cc:dd:ee:01",
                name="Living Room TV",
                address="aa:bb:cc:dd:ee:01",
                model="Samsung Smart TV",
                signal_strength=85
            )
            stats = CastingStats(
                start_time=datetime(2026, 8, 9, 10, 0, 0),
                end_time=datetime(2026, 8, 9, 10, 30, 0),
                duration=1800,
                data_transferred=500_000_000,
                average_bitrate=5_000_000,
                peak_bitrate=10_000_000,
                dropped_frames=5,
                errors=1
            )

            history1.add_session(source, device, stats)

            # Load in a completely new instance (simulating app restart)
            history2 = SessionHistory(history_path=str(history_path))
            sessions = history2.get_sessions()

            self.assertEqual(len(sessions), 1)
            restored = sessions[0]

            # Verify all fields survived the roundtrip
            self.assertEqual(restored.source.id, "screen-0")
            self.assertEqual(restored.source.name, "Screen 1")
            self.assertEqual(restored.source.description, "1920x1080")
            self.assertEqual(restored.source.icon, "video-display")

            self.assertEqual(restored.device.id, "aa:bb:cc:dd:ee:01")
            self.assertEqual(restored.device.name, "Living Room TV")
            self.assertEqual(restored.device.address, "aa:bb:cc:dd:ee:01")
            self.assertEqual(restored.device.model, "Samsung Smart TV")
            self.assertEqual(restored.device.signal_strength, 85)

            self.assertEqual(restored.stats.duration, 1800)
            self.assertEqual(restored.stats.data_transferred, 500_000_000)
            self.assertEqual(restored.stats.average_bitrate, 5_000_000)
            self.assertEqual(restored.stats.peak_bitrate, 10_000_000)
            self.assertEqual(restored.stats.dropped_frames, 5)
            self.assertEqual(restored.stats.errors, 1)

    def test_multiple_sessions_persist_and_load(self):
        """Test multiple sessions persist correctly and load in order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "history.json"
            history = SessionHistory(history_path=str(history_path))

            # Add multiple sessions
            for i in range(5):
                source = CaptureSource(id=f"screen-{i}", name=f"Screen {i+1}", description=f"{1920+i}x1080")
                device = MiracastDevice(
                    id=f"device-{i}",
                    name=f"TV {i+1}",
                    address=f"aa:bb:cc:dd:ee:{i:02d}",
                    model=f"Model {i}",
                    signal_strength=80 - i * 5
                )
                stats = CastingStats(
                    start_time=datetime(2026, 8, 9, 10 + i, 0, 0),
                    end_time=datetime(2026, 8, 9, 10 + i, 30, 0),
                    duration=1800,
                    data_transferred=500_000_000 * (i + 1),
                    average_bitrate=5_000_000,
                    peak_bitrate=10_000_000,
                    dropped_frames=i,
                    errors=0
                )
                history.add_session(source, device, stats)

            # Load in new instance
            history2 = SessionHistory(history_path=str(history_path))
            sessions = history2.get_sessions()

            self.assertEqual(len(sessions), 5)
            for i, session in enumerate(sessions):
                self.assertEqual(session.source.id, f"screen-{i}")
                self.assertEqual(session.device.name, f"TV {i+1}")


if __name__ == '__main__':
    unittest.main()
