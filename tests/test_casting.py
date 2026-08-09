"""Tests for the casting module."""

import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Mock gi.repository before importing casting module
mock_gi = MagicMock()
mock_gobject = MagicMock()
mock_gobject.Object = object
mock_gobject.SignalFlags = MagicMock()
mock_gobject.SignalFlags.RUN_FIRST = 1
mock_glib = MagicMock()

with patch.dict('sys.modules', {
    'gi': mock_gi,
    'gi.repository': MagicMock(GObject=mock_gobject, GLib=mock_glib),
}):
    mock_gi.require_version = MagicMock()
    from miracast_client.casting import CastingStats, CastManager


class TestCastingStats(unittest.TestCase):
    """Test cases for the CastingStats dataclass."""

    def test_default_values(self):
        """Test CastingStats default values."""
        now = datetime.now()
        stats = CastingStats(start_time=now)

        self.assertEqual(stats.start_time, now)
        self.assertIsNone(stats.end_time)
        self.assertEqual(stats.duration, 0)
        self.assertEqual(stats.data_transferred, 0)
        self.assertEqual(stats.average_bitrate, 0)
        self.assertEqual(stats.peak_bitrate, 0)
        self.assertEqual(stats.dropped_frames, 0)
        self.assertEqual(stats.errors, 0)

    def test_with_populated_fields(self):
        """Test CastingStats with all fields populated."""
        start = datetime(2026, 8, 9, 10, 0, 0)
        end = datetime(2026, 8, 9, 10, 30, 0)
        stats = CastingStats(
            start_time=start,
            end_time=end,
            duration=1800,
            data_transferred=500_000_000,
            average_bitrate=5_000_000,
            peak_bitrate=10_000_000,
            dropped_frames=5,
            errors=1
        )

        self.assertEqual(stats.start_time, start)
        self.assertEqual(stats.end_time, end)
        self.assertEqual(stats.duration, 1800)
        self.assertEqual(stats.data_transferred, 500_000_000)
        self.assertEqual(stats.average_bitrate, 5_000_000)
        self.assertEqual(stats.peak_bitrate, 10_000_000)
        self.assertEqual(stats.dropped_frames, 5)
        self.assertEqual(stats.errors, 1)


class TestCastManager(unittest.TestCase):
    """Test cases for the CastManager class."""

    def setUp(self):
        """Set up test environment."""
        with patch('miracast_client.casting.Config'):
            self.manager = CastManager()
        # Override the emit method to avoid GObject signal issues
        self.manager.emit = MagicMock()

    def test_initial_state(self):
        """Test CastManager initial state - is_casting() should be False."""
        self.assertFalse(self.manager.is_casting())

    def test_start_casting_raises_runtime_error_if_already_casting(self):
        """Test start_casting raises RuntimeError if already casting."""
        self.manager._casting = True
        mock_source = MagicMock()
        mock_device = MagicMock()

        with self.assertRaises(RuntimeError) as ctx:
            self.manager.start_casting(mock_source, mock_device)
        self.assertIn("already active", str(ctx.exception))

    def test_start_casting_raises_value_error_with_none_source(self):
        """Test start_casting raises ValueError with None source."""
        mock_device = MagicMock()

        with self.assertRaises(ValueError) as ctx:
            self.manager.start_casting(None, mock_device)
        self.assertIn("No source", str(ctx.exception))

    def test_start_casting_raises_value_error_with_none_device(self):
        """Test start_casting raises ValueError with None device."""
        mock_source = MagicMock()

        with self.assertRaises(ValueError) as ctx:
            self.manager.start_casting(mock_source, None)
        self.assertIn("No device", str(ctx.exception))

    @patch('miracast_client.casting.threading.Thread')
    @patch('miracast_client.casting.threading.Event')
    def test_start_casting_success(self, mock_event_class, mock_thread_class):
        """Test start_casting success sets state correctly."""
        mock_source = MagicMock()
        mock_source.name = "Test Screen"
        mock_device = MagicMock()
        mock_device.name = "Test TV"

        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Re-create manager to get fresh threading mocks
        with patch('miracast_client.casting.Config'):
            manager = CastManager()
        manager.emit = MagicMock()

        result = manager.start_casting(mock_source, mock_device)

        self.assertTrue(result)
        self.assertTrue(manager.is_casting())
        self.assertEqual(manager._source, mock_source)
        self.assertEqual(manager._device, mock_device)
        self.assertIsNotNone(manager._stats)
        self.assertIsInstance(manager._stats.start_time, datetime)
        manager.emit.assert_called_with("casting-started", mock_source, mock_device)

    def test_stop_casting_raises_runtime_error_if_not_casting(self):
        """Test stop_casting raises RuntimeError if not casting."""
        with self.assertRaises(RuntimeError) as ctx:
            self.manager.stop_casting()
        self.assertIn("No active casting session", str(ctx.exception))

    @patch('miracast_client.casting.threading.Thread')
    def test_stop_casting_returns_stats(self, mock_thread_class):
        """Test stop_casting returns CastingStats with populated fields."""
        mock_source = MagicMock()
        mock_source.name = "Test Screen"
        mock_device = MagicMock()
        mock_device.name = "Test TV"

        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        with patch('miracast_client.casting.Config'):
            manager = CastManager()
        manager.emit = MagicMock()

        manager.start_casting(mock_source, mock_device)
        stats = manager.stop_casting()

        self.assertIsInstance(stats, CastingStats)
        self.assertIsNotNone(stats.start_time)
        self.assertIsNotNone(stats.end_time)
        self.assertIsInstance(stats.duration, int)

    @patch('miracast_client.casting.threading.Thread')
    def test_stop_casting_resets_is_casting(self, mock_thread_class):
        """Test stop_casting resets is_casting to False."""
        mock_source = MagicMock()
        mock_source.name = "Test Screen"
        mock_device = MagicMock()
        mock_device.name = "Test TV"

        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        with patch('miracast_client.casting.Config'):
            manager = CastManager()
        manager.emit = MagicMock()

        manager.start_casting(mock_source, mock_device)
        self.assertTrue(manager.is_casting())

        manager.stop_casting()
        self.assertFalse(manager.is_casting())

    @patch('miracast_client.casting.threading.Thread')
    def test_stop_casting_emits_signal(self, mock_thread_class):
        """Test stop_casting emits the casting-stopped signal."""
        mock_source = MagicMock()
        mock_source.name = "Test Screen"
        mock_device = MagicMock()
        mock_device.name = "Test TV"

        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        with patch('miracast_client.casting.Config'):
            manager = CastManager()
        manager.emit = MagicMock()

        manager.start_casting(mock_source, mock_device)
        stats = manager.stop_casting()

        # Check that casting-stopped was emitted
        calls = [c for c in manager.emit.call_args_list if c[0][0] == "casting-stopped"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][1], stats)


if __name__ == '__main__':
    unittest.main()
