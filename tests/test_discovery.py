"""Tests for the discovery module."""

import unittest
from unittest.mock import MagicMock, patch

from miracast_client.discovery import MiracastDevice, MiracastDiscovery


class TestMiracastDevice(unittest.TestCase):
    """Test cases for the MiracastDevice class."""

    def test_from_wpa_supplicant_p2p_device(self):
        """Test creating a MiracastDevice from wpa_supplicant P2P device info."""
        device_info = {
            "p2p_dev_addr": "aa:bb:cc:dd:ee:ff",
            "device_name": "Test Device",
            "primary_dev_type": "Test Model",
            "signal_level": "75",
        }

        device = MiracastDevice.from_wpa_supplicant_p2p_device(device_info)

        self.assertEqual(device.id, "aa:bb:cc:dd:ee:ff")
        self.assertEqual(device.name, "Test Device")
        self.assertEqual(device.address, "aa:bb:cc:dd:ee:ff")
        self.assertEqual(device.model, "Test Model")
        self.assertEqual(device.signal_strength, 75)

    def test_from_wpa_supplicant_p2p_device_missing_fields(self):
        """Test creating a MiracastDevice with missing fields."""
        device_info = {}

        device = MiracastDevice.from_wpa_supplicant_p2p_device(device_info)

        # ID should be a UUID if p2p_dev_addr is missing
        self.assertIsNotNone(device.id)
        self.assertEqual(device.name, "Unknown Device")
        self.assertEqual(device.address, "00:00:00:00:00:00")
        self.assertEqual(device.model, "Unknown")
        self.assertEqual(device.signal_strength, 0)


class TestMiracastDiscovery(unittest.TestCase):
    """Test cases for the MiracastDiscovery class."""

    def setUp(self):
        """Set up test environment."""
        # Create a MiracastDiscovery instance without patching threading
        # (patching the whole module breaks GObject initialization)
        self.discovery = MiracastDiscovery()

    @patch("miracast_client.discovery.threading.Thread")
    def test_start_discovery(self, mock_thread_class):
        """Test starting discovery."""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Connect to the discovery-started signal
        self.discovery.connect("discovery-started", self._on_discovery_started)
        self.signal_received = False

        # Start discovery
        self.discovery.start_discovery()

        # Check that discovery is running
        self.assertTrue(self.discovery._running)

        # Check that the thread was started
        mock_thread.start.assert_called_once()

        # Check that the signal was emitted
        self.assertTrue(self.signal_received)

        # Clean up
        self.discovery._running = False

    def test_stop_discovery(self):
        """Test stopping discovery."""
        # Set up running discovery
        self.discovery._running = True
        mock_thread = MagicMock()
        self.discovery._thread = mock_thread

        # Connect to the discovery-stopped signal
        self.discovery.connect("discovery-stopped", self._on_discovery_stopped)
        self.signal_received = False

        # Stop discovery
        self.discovery.stop_discovery()

        # Check that discovery is not running
        self.assertFalse(self.discovery._running)

        # Check that the thread was joined (use our reference since stop sets _thread to None)
        mock_thread.join.assert_called_once()

        # Check that the signal was emitted
        self.assertTrue(self.signal_received)

    def test_get_devices(self):
        """Test getting discovered devices."""
        # Add some test devices
        test_devices = {
            "device1": MiracastDevice("device1", "Device 1", "addr1", "model1", 80),
            "device2": MiracastDevice("device2", "Device 2", "addr2", "model2", 70),
        }
        self.discovery._devices = test_devices

        # Get devices
        devices = self.discovery.get_devices()

        # Check that the correct devices were returned
        self.assertEqual(len(devices), 2)
        self.assertIn(test_devices["device1"], devices)
        self.assertIn(test_devices["device2"], devices)

    def _on_discovery_started(self, discovery):
        """Handler for discovery-started signal."""
        self.signal_received = True

    def _on_discovery_stopped(self, discovery):
        """Handler for discovery-stopped signal."""
        self.signal_received = True


if __name__ == "__main__":
    unittest.main()
