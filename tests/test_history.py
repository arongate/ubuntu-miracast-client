"""Tests for the history module."""

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock gi.repository before importing history module
mock_gi = MagicMock()
mock_gobject = MagicMock()
mock_gobject.Object = object
mock_glib = MagicMock()

with patch.dict('sys.modules', {
    'gi': mock_gi,
    'gi.repository': MagicMock(GObject=mock_gobject, GLib=mock_glib, Gdk=MagicMock(), Gio=MagicMock()),
}):
    mock_gi.require_version = MagicMock()
    from miracast_client.capture import CaptureSource
    from miracast_client.discovery import MiracastDevice
    from miracast_client.casting import CastingStats
    from miracast_client.history import SessionRecord, SessionHistory


class TestSessionRecord(unittest.TestCase):
    """Test cases for the SessionRecord class."""

    def _create_sample_record(self):
        """Helper to create a sample SessionRecord."""
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
        timestamp = datetime(2026, 8, 9, 10, 30, 0)
        return SessionRecord(source=source, device=device, stats=stats, timestamp=timestamp)

    def test_to_dict_serializes_correctly(self):
        """Test SessionRecord.to_dict() serializes correctly."""
        record = self._create_sample_record()
        data = record.to_dict()

        self.assertEqual(data["source"]["id"], "screen-0")
        self.assertEqual(data["source"]["name"], "Screen 1")
        self.assertEqual(data["source"]["description"], "1920x1080")
        self.assertEqual(data["source"]["icon"], "video-display")

        self.assertEqual(data["device"]["id"], "aa:bb:cc:dd:ee:01")
        self.assertEqual(data["device"]["name"], "Living Room TV")
        self.assertEqual(data["device"]["address"], "aa:bb:cc:dd:ee:01")
        self.assertEqual(data["device"]["model"], "Samsung Smart TV")
        self.assertEqual(data["device"]["signal_strength"], 85)

        self.assertEqual(data["stats"]["duration"], 1800)
        self.assertEqual(data["stats"]["data_transferred"], 500_000_000)
        self.assertEqual(data["stats"]["average_bitrate"], 5_000_000)
        self.assertEqual(data["stats"]["peak_bitrate"], 10_000_000)
        self.assertEqual(data["stats"]["dropped_frames"], 5)
        self.assertEqual(data["stats"]["errors"], 1)

        self.assertIn("timestamp", data)

    def test_from_dict_deserializes_correctly(self):
        """Test SessionRecord.from_dict() deserializes correctly."""
        data = {
            "source": {
                "id": "screen-0",
                "name": "Screen 1",
                "description": "1920x1080",
                "icon": "video-display"
            },
            "device": {
                "id": "device-1",
                "name": "Test TV",
                "address": "aa:bb:cc:dd:ee:01",
                "model": "Test Model",
                "signal_strength": 75
            },
            "stats": {
                "start_time": "2026-08-09T10:00:00",
                "end_time": "2026-08-09T10:30:00",
                "duration": 1800,
                "data_transferred": 500_000_000,
                "average_bitrate": 5_000_000,
                "peak_bitrate": 10_000_000,
                "dropped_frames": 5,
                "errors": 1
            },
            "timestamp": "2026-08-09T10:30:00"
        }

        record = SessionRecord.from_dict(data)

        self.assertEqual(record.source.id, "screen-0")
        self.assertEqual(record.source.name, "Screen 1")
        self.assertEqual(record.device.id, "device-1")
        self.assertEqual(record.device.name, "Test TV")
        self.assertEqual(record.stats.duration, 1800)
        self.assertEqual(record.timestamp, datetime(2026, 8, 9, 10, 30, 0))

    def test_roundtrip(self):
        """Test roundtrip: to_dict then from_dict preserves data."""
        original = self._create_sample_record()
        data = original.to_dict()
        restored = SessionRecord.from_dict(data)

        self.assertEqual(restored.source.id, original.source.id)
        self.assertEqual(restored.source.name, original.source.name)
        self.assertEqual(restored.device.id, original.device.id)
        self.assertEqual(restored.device.name, original.device.name)
        self.assertEqual(restored.stats.duration, original.stats.duration)
        self.assertEqual(restored.stats.data_transferred, original.stats.data_transferred)
        self.assertEqual(restored.stats.average_bitrate, original.stats.average_bitrate)
        self.assertEqual(restored.stats.peak_bitrate, original.stats.peak_bitrate)
        self.assertEqual(restored.stats.dropped_frames, original.stats.dropped_frames)
        self.assertEqual(restored.stats.errors, original.stats.errors)
        self.assertEqual(restored.timestamp, original.timestamp)

    def test_from_dict_with_none_end_time(self):
        """Test from_dict handles None end_time."""
        data = {
            "source": {"id": "s1", "name": "S1", "description": "d", "icon": "i"},
            "device": {"id": "d1", "name": "D1", "address": "a", "model": "m", "signal_strength": 50},
            "stats": {
                "start_time": "2026-08-09T10:00:00",
                "end_time": None,
                "duration": 0,
                "data_transferred": 0,
                "average_bitrate": 0,
                "peak_bitrate": 0,
                "dropped_frames": 0,
                "errors": 0
            },
            "timestamp": "2026-08-09T10:00:00"
        }

        record = SessionRecord.from_dict(data)
        self.assertIsNone(record.stats.end_time)


class TestSessionHistory(unittest.TestCase):
    """Test cases for the SessionHistory class."""

    def setUp(self):
        """Set up test environment with temp directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.history_path = Path(self.temp_dir.name) / "history.json"

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def _create_sample_source(self):
        """Helper to create a sample CaptureSource."""
        return CaptureSource(id="screen-0", name="Screen 1", description="1920x1080")

    def _create_sample_device(self):
        """Helper to create a sample MiracastDevice."""
        return MiracastDevice(
            id="aa:bb:cc:dd:ee:01",
            name="Test TV",
            address="aa:bb:cc:dd:ee:01",
            model="Test Model",
            signal_strength=80
        )

    def _create_sample_stats(self):
        """Helper to create sample CastingStats."""
        return CastingStats(
            start_time=datetime(2026, 8, 9, 10, 0, 0),
            end_time=datetime(2026, 8, 9, 10, 30, 0),
            duration=1800,
            data_transferred=500_000_000,
            average_bitrate=5_000_000,
            peak_bitrate=10_000_000,
            dropped_frames=5,
            errors=0
        )

    def test_empty_file_new_install(self):
        """Test SessionHistory with empty file (new install)."""
        history = SessionHistory(history_path=str(self.history_path))
        sessions = history.get_sessions()
        self.assertEqual(len(sessions), 0)

    def test_add_session_creates_record(self):
        """Test add_session creates record and persists."""
        history = SessionHistory(history_path=str(self.history_path))
        source = self._create_sample_source()
        device = self._create_sample_device()
        stats = self._create_sample_stats()

        record = history.add_session(source, device, stats)

        self.assertIsNotNone(record)
        self.assertEqual(record.source.id, "screen-0")
        self.assertEqual(record.device.name, "Test TV")

        # Verify persisted to file
        self.assertTrue(self.history_path.exists())
        with open(self.history_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)

    def test_get_sessions_returns_all_records(self):
        """Test get_sessions returns all records."""
        history = SessionHistory(history_path=str(self.history_path))
        source = self._create_sample_source()
        device = self._create_sample_device()
        stats = self._create_sample_stats()

        history.add_session(source, device, stats)
        history.add_session(source, device, stats)
        history.add_session(source, device, stats)

        sessions = history.get_sessions()
        self.assertEqual(len(sessions), 3)

    def test_clear_removes_all_records(self):
        """Test clear removes all records and updates file."""
        history = SessionHistory(history_path=str(self.history_path))
        source = self._create_sample_source()
        device = self._create_sample_device()
        stats = self._create_sample_stats()

        history.add_session(source, device, stats)
        history.add_session(source, device, stats)
        self.assertEqual(len(history.get_sessions()), 2)

        history.clear()
        self.assertEqual(len(history.get_sessions()), 0)

        # Verify file was updated
        with open(self.history_path, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data), 0)

    def test_loading_corrupted_json(self):
        """Test loading corrupted JSON handles gracefully."""
        # Write corrupted JSON to file
        with open(self.history_path, 'w') as f:
            f.write("{invalid json content!!")

        # Should not raise, just return empty list
        history = SessionHistory(history_path=str(self.history_path))
        sessions = history.get_sessions()
        self.assertEqual(len(sessions), 0)

    def test_loading_persisted_sessions(self):
        """Test loading previously persisted sessions."""
        # Create and save a session
        history1 = SessionHistory(history_path=str(self.history_path))
        source = self._create_sample_source()
        device = self._create_sample_device()
        stats = self._create_sample_stats()
        history1.add_session(source, device, stats)

        # Load in a new instance
        history2 = SessionHistory(history_path=str(self.history_path))
        sessions = history2.get_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].source.id, "screen-0")
        self.assertEqual(sessions[0].device.name, "Test TV")


if __name__ == '__main__':
    unittest.main()
