"""Miracast device discovery module using real wpa_supplicant P2P."""

import logging
import subprocess
import threading
import time
import uuid

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib, GObject

logger = logging.getLogger(__name__)

# Wi-Fi Display device types (from WFD subelems device info bits 0-1)
WFD_SOURCE = 0
WFD_PRIMARY_SINK = 1
WFD_SECONDARY_SINK = 2
WFD_DUAL = 3


def _find_p2p_interface():
    """Find the P2P device interface name.

    Returns:
        Tuple of (p2p_interface, wifi_interface) or (None, None) if not found.
    """
    try:
        result = subprocess.run(
            ["sudo", "wpa_cli", "interface"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None, None

        lines = result.stdout.strip().split("\n")
        p2p_iface = None
        wifi_iface = None
        for line in lines:
            line = line.strip()
            if line.startswith("p2p-dev-"):
                p2p_iface = line
                wifi_iface = line.replace("p2p-dev-", "")
            elif line.startswith("wl") and not wifi_iface:
                wifi_iface = line

        return p2p_iface, wifi_iface
    except Exception as e:
        logger.error(f"Failed to find P2P interface: {e}")
        return None, None


def _parse_wfd_subelems(wfd_hex):
    """Parse WFD subelements to determine device type.

    Args:
        wfd_hex: Hex string of WFD subelements (e.g., '000006001100000032')

    Returns:
        Tuple of (device_type, rtsp_port) where device_type is WFD_SOURCE/SINK/DUAL
    """
    try:
        if not wfd_hex or len(wfd_hex) < 12:
            return None, 0

        # WFD subelement format:
        # ID(2) + Length(4) + DeviceInfo(4) + ControlPort(4) + MaxThroughput(4)
        # First subelement starts at index 0
        # ID = wfd_hex[0:2], Length = wfd_hex[2:6], DeviceInfo = wfd_hex[6:10]
        device_info = int(wfd_hex[6:10], 16)
        device_type = device_info & 0x03
        rtsp_port = int(wfd_hex[10:14], 16) if len(wfd_hex) >= 14 else 7236

        return device_type, rtsp_port
    except (ValueError, IndexError) as e:
        logger.debug(f"Failed to parse WFD subelems '{wfd_hex}': {e}")
        return None, 0


class MiracastDevice(GObject.Object):
    """Represents a discovered Miracast device."""

    def __init__(self, id, name, address, model, signal_strength,
                 manufacturer="", wfd_type=None, rtsp_port=7236, p2p_interface=None):
        super().__init__()
        self.id = id
        self.name = name
        self.address = address
        self.model = model
        self.signal_strength = signal_strength
        self.manufacturer = manufacturer
        self.wfd_type = wfd_type  # WFD_SOURCE, WFD_PRIMARY_SINK, etc.
        self.rtsp_port = rtsp_port
        self.p2p_interface = p2p_interface
        self.ip_address = None  # Set after connection

    @classmethod
    def from_wpa_supplicant_p2p_device(cls, device_info):
        """Create a MiracastDevice from wpa_supplicant P2P device info.

        Args:
            device_info: Dict with keys from 'wpa_cli p2p_peer <addr>' output.
        """
        # Parse WFD subelements for device type and RTSP port
        wfd_type = None
        rtsp_port = 7236
        wfd_subelems = device_info.get("wfd_subelems", "")
        if wfd_subelems:
            wfd_type, rtsp_port = _parse_wfd_subelems(wfd_subelems)

        # Signal level from wpa_supplicant is in dBm (negative), normalize to 0-100
        raw_level = int(device_info.get("level", "-100"))
        # Map -100 dBm (worst) to 0, -30 dBm (best) to 100
        signal_strength = max(0, min(100, int((raw_level + 100) * 100 / 70)))

        return cls(
            id=device_info.get("p2p_dev_addr", str(uuid.uuid4())),
            name=device_info.get("device_name", "Unknown Device"),
            address=device_info.get("p2p_dev_addr", "00:00:00:00:00:00"),
            model=device_info.get("model_name", "").strip() or device_info.get(
                "pri_dev_type", "Unknown"
            ),
            signal_strength=signal_strength,
            manufacturer=device_info.get("manufacturer", "").strip(),
            wfd_type=wfd_type,
            rtsp_port=rtsp_port,
        )

    @property
    def is_sink(self):
        """Check if this device can receive a Miracast stream."""
        return self.wfd_type in (WFD_PRIMARY_SINK, WFD_SECONDARY_SINK, WFD_DUAL)

    @property
    def type_description(self):
        """Human-readable device type."""
        types = {
            WFD_SOURCE: "Source",
            WFD_PRIMARY_SINK: "Sink",
            WFD_SECONDARY_SINK: "Secondary Sink",
            WFD_DUAL: "Source + Sink",
        }
        return types.get(self.wfd_type, "Unknown")


class MiracastDiscovery(GObject.Object):
    """Discovers Miracast devices on the network using wpa_supplicant P2P."""

    __gsignals__ = {
        "device-found": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "device-lost": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "discovery-started": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "discovery-stopped": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "discovery-error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, timeout=None, p2p_interface=None):
        """Initialize the discovery service.

        Args:
            timeout: Discovery timeout in seconds. If None, reads from config.
                     Set to 0 to disable timeout (discover indefinitely).
            p2p_interface: Override the P2P interface name (auto-detected if None).
        """
        super().__init__()
        self._running = False
        self._thread = None
        self._devices = {}  # Map of device ID to device object
        self._lock = threading.Lock()

        # Auto-detect P2P interface
        if p2p_interface:
            self._p2p_interface = p2p_interface
        else:
            self._p2p_interface, self._wifi_interface = _find_p2p_interface()

        # Load timeout from config if not provided
        if timeout is None:
            from miracast_client.config import Config

            config = Config()
            self._timeout = config.get("advanced", "discovery_timeout", 10)
        else:
            self._timeout = timeout

    def start_discovery(self):
        """Start discovering Miracast devices via Wi-Fi Direct P2P."""
        if self._running:
            logger.warning("Discovery already running")
            return

        if not self._p2p_interface:
            error_msg = "No P2P interface found. Ensure wpa_supplicant is running with P2P support."
            logger.error(error_msg)
            self.emit("discovery-error", error_msg)
            return

        self._running = True
        self._thread = threading.Thread(target=self._discovery_thread, daemon=True)
        self._thread.start()

        self.emit("discovery-started")
        logger.info(f"Miracast device discovery started on {self._p2p_interface}")

    def stop_discovery(self):
        """Stop discovering Miracast devices."""
        if not self._running:
            logger.warning("Discovery not running")
            return

        self._running = False

        # Stop the P2P find on wpa_supplicant
        try:
            subprocess.run(
                ["sudo", "wpa_cli", "-i", self._p2p_interface, "p2p_stop_find"],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except Exception as e:
            logger.debug(f"Error stopping p2p_find: {e}")

        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

        self.emit("discovery-stopped")
        logger.info("Miracast device discovery stopped")

    def get_devices(self):
        """Get the list of discovered devices (sinks only).

        Returns:
            List of MiracastDevice objects that are Miracast sinks.
        """
        with self._lock:
            return [d for d in self._devices.values() if d.is_sink]

    def get_all_devices(self):
        """Get all discovered P2P devices regardless of type.

        Returns:
            List of all MiracastDevice objects.
        """
        with self._lock:
            return list(self._devices.values())

    def _discovery_thread(self):
        """Background thread for real P2P device discovery."""
        try:
            self._run_p2p_discovery()
        except Exception as e:
            logger.error(f"Discovery error: {e}")
            GLib.idle_add(self.emit, "discovery-error", str(e))

    def _run_p2p_discovery(self):
        """Run actual wpa_supplicant P2P discovery."""
        iface = self._p2p_interface

        # Enable WFD (Wi-Fi Display) subelements so we advertise ourselves as WFD source
        # This helps sinks respond to our probe requests
        self._set_wfd_subelements()

        # Start P2P find
        result = subprocess.run(
            ["sudo", "wpa_cli", "-i", iface, "p2p_find"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 or "OK" not in result.stdout:
            error_msg = f"Failed to start P2P find: {result.stdout.strip()} {result.stderr.strip()}"
            logger.error(error_msg)
            GLib.idle_add(self.emit, "discovery-error", error_msg)
            return

        logger.info("P2P find started, polling for peers...")

        start_time = time.time()
        known_peers = set()

        while self._running:
            # Check timeout
            if self._timeout > 0 and (time.time() - start_time) >= self._timeout:
                logger.info(f"Discovery timeout reached ({self._timeout}s)")
                GLib.idle_add(self._auto_stop_discovery)
                return

            # Get list of discovered peers
            result = subprocess.run(
                ["sudo", "wpa_cli", "-i", iface, "p2p_peers"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                time.sleep(1)
                continue

            current_peers = set()
            for line in result.stdout.strip().split("\n"):
                addr = line.strip()
                if addr and len(addr) == 17 and ":" in addr:  # MAC address format
                    current_peers.add(addr)

            # Query details for each new or updated peer
            for addr in current_peers:
                if not self._running:
                    break
                self._query_peer(iface, addr)

            # Detect lost devices
            lost_peers = known_peers - current_peers
            for addr in lost_peers:
                with self._lock:
                    if addr in self._devices:
                        del self._devices[addr]
                GLib.idle_add(self.emit, "device-lost", addr)
                logger.info(f"Device lost: {addr}")

            known_peers = current_peers

            # Poll interval
            time.sleep(2)

    def _query_peer(self, iface, addr):
        """Query details of a specific P2P peer and emit device-found if it's new/updated."""
        try:
            result = subprocess.run(
                ["sudo", "wpa_cli", "-i", iface, "p2p_peer", addr],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return

            # Parse the peer info
            device_info = {"p2p_dev_addr": addr}
            for line in result.stdout.strip().split("\n"):
                if "=" in line:
                    key, _, value = line.partition("=")
                    device_info[key.strip()] = value.strip()

            # Create device object
            device = MiracastDevice.from_wpa_supplicant_p2p_device(device_info)
            device.p2p_interface = iface

            # Check if this is a new device or an update
            with self._lock:
                existing = self._devices.get(addr)
                self._devices[addr] = device

            # Emit signal if new or signal strength changed
            if existing is None or existing.signal_strength != device.signal_strength:
                GLib.idle_add(self.emit, "device-found", device)
                if existing is None:
                    logger.info(
                        f"Found device: {device.name} ({addr}) "
                        f"type={device.type_description} signal={device.signal_strength}%"
                    )

        except subprocess.TimeoutExpired:
            logger.debug(f"Timeout querying peer {addr}")
        except Exception as e:
            logger.debug(f"Error querying peer {addr}: {e}")

    def _set_wfd_subelements(self):
        """Set WFD subelements to advertise as a WFD source."""
        # WFD Device Information subelement:
        # Type=0x00, Length=0x0006
        # Device Info: 0x0010 (WFD source, session available, WSD supported)
        # Control Port: 7236 (0x1C44)
        # Max Throughput: 50 Mbps (0x0032)
        wfd_subelems = "000600101C440032"

        try:
            result = subprocess.run(
                ["sudo", "wpa_cli", "-i", self._p2p_interface, "set", "wifi_display", "1"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            logger.debug(f"Set wifi_display=1: {result.stdout.strip()}")

            result = subprocess.run(
                [
                    "sudo", "wpa_cli", "-i", self._p2p_interface,
                    "wfd_subelem_set", "0", wfd_subelems,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            logger.debug(f"Set WFD subelems: {result.stdout.strip()}")
        except Exception as e:
            logger.warning(f"Failed to set WFD subelements: {e}")

    def _auto_stop_discovery(self):
        """Auto-stop discovery after timeout (called on main thread via idle_add)."""
        if self._running:
            self._running = False
            try:
                subprocess.run(
                    ["sudo", "wpa_cli", "-i", self._p2p_interface, "p2p_stop_find"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            except Exception:
                pass
            self.emit("discovery-stopped")
            logger.info("Discovery auto-stopped after timeout")
