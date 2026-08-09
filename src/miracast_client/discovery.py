"""Miracast device discovery module."""

import logging
import threading
import time
import uuid

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib, GObject

logger = logging.getLogger(__name__)


class MiracastDevice(GObject.Object):
    """Represents a discovered Miracast device."""

    def __init__(self, id, name, address, model, signal_strength):
        super().__init__()
        self.id = id
        self.name = name
        self.address = address
        self.model = model
        self.signal_strength = signal_strength

    @classmethod
    def from_wpa_supplicant_p2p_device(cls, device_info):
        """Create a MiracastDevice from wpa_supplicant P2P device info."""
        # This is a simplified example. In a real implementation,
        # we would parse the actual wpa_supplicant output.
        return cls(
            id=device_info.get("p2p_dev_addr", str(uuid.uuid4())),
            name=device_info.get("device_name", "Unknown Device"),
            address=device_info.get("p2p_dev_addr", "00:00:00:00:00:00"),
            model=device_info.get("primary_dev_type", "Unknown"),
            signal_strength=int(device_info.get("signal_level", 0)),
        )


class MiracastDiscovery(GObject.Object):
    """Discovers Miracast devices on the network."""

    __gsignals__ = {
        "device-found": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "device-lost": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "discovery-started": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "discovery-stopped": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "discovery-error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self):
        """Initialize the discovery service."""
        super().__init__()
        self._running = False
        self._thread = None
        self._devices = {}  # Map of device ID to device object
        self._lock = threading.Lock()

    def start_discovery(self):
        """Start discovering Miracast devices."""
        if self._running:
            logger.warning("Discovery already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._discovery_thread)
        self._thread.daemon = True
        self._thread.start()

        self.emit("discovery-started")
        logger.info("Miracast device discovery started")

    def stop_discovery(self):
        """Stop discovering Miracast devices."""
        if not self._running:
            logger.warning("Discovery not running")
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

        self.emit("discovery-stopped")
        logger.info("Miracast device discovery stopped")

    def get_devices(self):
        """Get the list of discovered devices.

        Returns:
            List of MiracastDevice objects
        """
        with self._lock:
            return list(self._devices.values())

    def _discovery_thread(self):
        """Background thread for device discovery."""
        try:
            # In a real implementation, we would use wpa_supplicant's P2P functionality
            # to discover Miracast devices. For this example, we'll simulate discovery.
            self._simulate_discovery()
        except Exception as e:
            logger.error(f"Discovery error: {e}")
            GLib.idle_add(self.emit, "discovery-error", str(e))

    def _simulate_discovery(self):
        """Simulate device discovery for demonstration purposes."""
        # In a real implementation, this would use wpa_supplicant's P2P functionality
        # to discover actual Miracast devices on the network.

        # Simulate finding some devices
        sample_devices = [
            {
                "p2p_dev_addr": "aa:bb:cc:dd:ee:01",
                "device_name": "Living Room TV",
                "primary_dev_type": "Samsung Smart TV",
                "signal_level": "85",
            },
            {
                "p2p_dev_addr": "aa:bb:cc:dd:ee:02",
                "device_name": "Office Monitor",
                "primary_dev_type": "LG Display",
                "signal_level": "70",
            },
            {
                "p2p_dev_addr": "aa:bb:cc:dd:ee:03",
                "device_name": "Bedroom TV",
                "primary_dev_type": "Sony Bravia",
                "signal_level": "60",
            },
        ]

        # Add devices with some delay to simulate discovery
        for device_info in sample_devices:
            if not self._running:
                break

            device = MiracastDevice.from_wpa_supplicant_p2p_device(device_info)

            with self._lock:
                self._devices[device.id] = device

            GLib.idle_add(self.emit, "device-found", device)
            logger.debug(f"Found device: {device.name} ({device.id})")

            # Simulate delay between discoveries
            time.sleep(1.5)

        # Keep checking for devices until stopped
        counter = 0
        while self._running:
            time.sleep(1.0)
            counter += 1

            # Simulate signal strength changes
            if counter % 3 == 0 and self._devices:
                device_id = list(self._devices.keys())[counter % len(self._devices)]
                device = self._devices[device_id]

                # Update signal strength
                new_strength = max(20, min(95, device.signal_strength + (counter % 3 - 1) * 5))
                device.signal_strength = new_strength

                GLib.idle_add(self.emit, "device-found", device)

            # Simulate a new device appearing occasionally
            if counter == 10:
                new_device_info = {
                    "p2p_dev_addr": "aa:bb:cc:dd:ee:04",
                    "device_name": "Portable Projector",
                    "primary_dev_type": "Epson Projector",
                    "signal_level": "55",
                }

                new_device = MiracastDevice.from_wpa_supplicant_p2p_device(new_device_info)

                with self._lock:
                    self._devices[new_device.id] = new_device

                GLib.idle_add(self.emit, "device-found", new_device)
                logger.debug(f"Found device: {new_device.name} ({new_device.id})")

            # Simulate a device disappearing occasionally
            if counter == 15 and len(self._devices) > 1:
                device_id = list(self._devices.keys())[0]

                with self._lock:
                    del self._devices[device_id]

                GLib.idle_add(self.emit, "device-lost", device_id)
                logger.debug(f"Lost device: {device_id}")

                # Reset counter to simulate more events
                counter = 0
