"""Miracast casting functionality with real GStreamer streaming."""

import logging
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib, GObject

from miracast_client.config import Config

logger = logging.getLogger(__name__)


# Quality presets: name -> bitrate in bps
QUALITY_BITRATES = {
    "Low": 2_000_000,
    "Medium": 5_000_000,
    "High": 10_000_000,
    "Very High": 20_000_000,
}


@dataclass
class CastingStats:
    """Statistics for a casting session."""

    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: int = 0  # in seconds
    data_transferred: int = 0  # in bytes
    average_bitrate: float = 0  # in bps
    peak_bitrate: float = 0  # in bps
    dropped_frames: int = 0
    errors: int = 0


class WifiDirectConnection:
    """Manages a Wi-Fi Direct P2P connection to a Miracast sink."""

    def __init__(self, device):
        """Initialize connection to a device.

        Args:
            device: MiracastDevice instance.
        """
        self.device = device
        self.p2p_interface = device.p2p_interface
        self.group_interface = None  # e.g., p2p-wlo1-0
        self.peer_ip = None
        self.our_ip = None
        self._connected = False

    def connect(self, timeout=30):
        """Establish Wi-Fi Direct P2P connection.

        Args:
            timeout: Connection timeout in seconds.

        Returns:
            True if connected successfully.

        Raises:
            RuntimeError: If connection fails.
        """
        addr = self.device.address
        iface = self.p2p_interface
        logger.info(f"Connecting to {self.device.name} ({addr}) via P2P...")

        # Initiate P2P connection using PBC (Push Button Configuration)
        result = subprocess.run(
            [
                "sudo", "wpa_cli", "-i", iface, "p2p_connect",
                addr, "pbc", "go_intent=0",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0 or "FAIL" in result.stdout:
            raise RuntimeError(
                f"P2P connect failed: {result.stdout.strip()} {result.stderr.strip()}"
            )

        logger.info(f"P2P connect initiated: {result.stdout.strip()}")

        # Wait for group formation and IP assignment
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(1)

            # Check if a P2P group interface has been created
            group_iface = self._find_group_interface()
            if group_iface:
                self.group_interface = group_iface
                logger.info(f"P2P group interface: {group_iface}")

                # Wait for DHCP / IP assignment
                peer_ip = self._get_peer_ip(group_iface)
                if peer_ip:
                    self.peer_ip = peer_ip
                    self._connected = True
                    logger.info(f"Connected! Peer IP: {peer_ip}")
                    return True

        raise RuntimeError(
            f"Connection timeout after {timeout}s - no group formed or no IP assigned"
        )

    def disconnect(self):
        """Disconnect the P2P connection."""
        if not self._connected:
            return

        try:
            if self.group_interface:
                subprocess.run(
                    ["sudo", "wpa_cli", "-i", self.group_interface, "disconnect"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

            # Remove the P2P group
            subprocess.run(
                ["sudo", "wpa_cli", "-i", self.p2p_interface, "p2p_group_remove",
                 self.group_interface or ""],
                capture_output=True,
                text=True,
                timeout=5,
            )
            logger.info("P2P connection disconnected")
        except Exception as e:
            logger.warning(f"Error during disconnect: {e}")
        finally:
            self._connected = False

    @property
    def is_connected(self):
        return self._connected

    def _find_group_interface(self):
        """Find the P2P group interface (e.g., p2p-wlo1-0)."""
        try:
            result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.split("\n"):
                # Look for p2p- interfaces that aren't the p2p-dev-
                if "p2p-" in line and "p2p-dev-" not in line:
                    # Extract interface name: "5: p2p-wlo1-0: <..."
                    parts = line.split(":")
                    if len(parts) >= 2:
                        iface_name = parts[1].strip()
                        return iface_name
        except Exception as e:
            logger.debug(f"Error finding group interface: {e}")
        return None

    def _get_peer_ip(self, group_iface):
        """Get the peer's IP address after P2P group formation.

        Tries multiple methods: ARP table, DHCP leases, and wpa_cli info.
        """
        # Method 1: Check our own IP on the group interface
        try:
            result = subprocess.run(
                ["ip", "addr", "show", group_iface],
                capture_output=True,
                text=True,
                timeout=5,
            )
            import re
            ip_match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/", result.stdout)
            if ip_match:
                our_ip = ip_match.group(1)
                self.our_ip = our_ip
                logger.debug(f"Our IP on {group_iface}: {our_ip}")

                # The peer is typically .1 if we're client, or .x if we're GO
                # Check ARP for the peer
                arp_result = subprocess.run(
                    ["ip", "neigh", "show", "dev", group_iface],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in arp_result.stdout.split("\n"):
                    if line.strip():
                        peer_ip = line.split()[0]
                        if peer_ip != our_ip:
                            return peer_ip

                # If we're client (typically get 192.168.49.x), GO is at .1
                if "192.168.49." in our_ip:
                    return "192.168.49.1"

        except Exception as e:
            logger.debug(f"Error getting peer IP: {e}")

        return None


class CastManager(GObject.Object):
    """Manages Miracast casting sessions with real GStreamer streaming."""

    __gsignals__ = {
        "casting-started": (GObject.SignalFlags.RUN_FIRST, None, (object, object)),
        "casting-stopped": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "casting-error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "stats-updated": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self):
        """Initialize the cast manager."""
        super().__init__()
        self.config = Config()
        self._casting = False
        self._source = None
        self._device = None
        self._stats = None
        self._thread = None
        self._stop_event = threading.Event()
        self._gst_process = None
        self._connection = None

    def is_casting(self):
        """Check if casting is active.

        Returns:
            True if casting is active, False otherwise
        """
        return self._casting

    def start_casting(self, source, device):
        """Start a casting session.

        Args:
            source: CaptureSource object
            device: MiracastDevice object

        Raises:
            RuntimeError: If casting is already active
            ValueError: If source or device is invalid
        """
        if self._casting:
            raise RuntimeError("Casting is already active")

        if not source:
            raise ValueError("No source specified")

        if not device:
            raise ValueError("No device specified")

        logger.info(f"Starting casting from {source.name} to {device.name}")

        try:
            # Initialize statistics
            self._stats = CastingStats(start_time=datetime.now())

            # Store source and device
            self._source = source
            self._device = device

            # Start casting thread
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._casting_thread, daemon=True)
            self._thread.start()

            self._casting = True
            self.emit("casting-started", source, device)

            return True
        except Exception as e:
            logger.error(f"Failed to start casting: {e}")
            self.emit("casting-error", str(e))
            raise

    def stop_casting(self):
        """Stop the current casting session.

        Returns:
            CastingStats object with session statistics

        Raises:
            RuntimeError: If no casting is active
        """
        if not self._casting:
            raise RuntimeError("No active casting session")

        logger.info("Stopping casting")

        # Signal thread to stop
        self._stop_event.set()

        # Kill the GStreamer process if running
        if self._gst_process:
            try:
                self._gst_process.terminate()
                self._gst_process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error stopping GStreamer process: {e}")
                try:
                    self._gst_process.kill()
                except Exception:
                    pass
            self._gst_process = None

        # Disconnect Wi-Fi Direct
        if self._connection:
            self._connection.disconnect()
            self._connection = None

        # Wait for thread to finish
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

        # Update statistics
        self._stats.end_time = datetime.now()
        self._stats.duration = int((self._stats.end_time - self._stats.start_time).total_seconds())

        # Calculate average bitrate
        if self._stats.duration > 0:
            self._stats.average_bitrate = (self._stats.data_transferred * 8) / self._stats.duration

        # Reset state
        self._casting = False

        # Emit signal
        self.emit("casting-stopped", self._stats)

        # Return statistics
        return self._stats

    def _casting_thread(self):
        """Background thread for managing the casting session."""
        try:
            # Step 1: Establish Wi-Fi Direct connection
            self._connection = WifiDirectConnection(self._device)
            self._connection.connect(timeout=30)

            if self._stop_event.is_set():
                return

            # Step 2: Start GStreamer streaming pipeline
            self._start_gstreamer_pipeline()

        except Exception as e:
            logger.error(f"Casting error: {e}")
            GLib.idle_add(self.emit, "casting-error", str(e))
            self._casting = False

            # Clean up on error
            if self._connection:
                self._connection.disconnect()
                self._connection = None

    def _start_gstreamer_pipeline(self):
        """Start the real GStreamer streaming pipeline."""
        # Get quality settings from config
        quality = self.config.get("streaming", "video_quality", "High")
        frame_rate = self.config.get("streaming", "frame_rate", 30)
        audio_enabled = self.config.get("streaming", "audio_enabled", True)  # noqa: F841

        bitrate = QUALITY_BITRATES.get(quality, 10_000_000)
        bitrate_kbps = bitrate // 1000

        # Determine target IP and port
        target_ip = self._connection.peer_ip
        target_port = self._device.rtsp_port or 7236

        logger.info(
            f"Starting GStreamer pipeline: {quality} ({bitrate_kbps} kbps) "
            f"@ {frame_rate} fps → {target_ip}:{target_port}"
        )

        # Get the capture pipeline from the source
        capture_pipeline = self._source.start_capture(framerate=frame_rate)

        # Build the full GStreamer pipeline
        # Video: capture → encode H264 → MPEG-TS mux → RTP → UDP
        pipeline = (
            f"{capture_pipeline}"
            f" ! x264enc tune=zerolatency bitrate={bitrate_kbps}"
            f" speed-preset=ultrafast key-int-max={frame_rate * 2}"
            f" ! video/x-h264,profile=baseline"
            f" ! mpegtsmux"
            f" ! rtpmp2tpay"
            f" ! udpsink host={target_ip} port={target_port} sync=false"
        )

        logger.info(f"GStreamer pipeline: gst-launch-1.0 {pipeline}")

        # Launch GStreamer as subprocess
        cmd = ["gst-launch-1.0", "-e"] + pipeline.split()

        try:
            self._gst_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            logger.info(f"GStreamer process started (PID: {self._gst_process.pid})")

            # Monitor the streaming process
            self._monitor_streaming()

        except FileNotFoundError:
            raise RuntimeError(
                "gst-launch-1.0 not found. Install gstreamer1.0-tools: "
                "sudo apt install gstreamer1.0-tools"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start GStreamer: {e}")

    def _monitor_streaming(self):
        """Monitor the GStreamer process and collect stats."""
        start_time = time.time()
        last_update = start_time
        estimated_bytes_per_second = 0

        # Get configured bitrate for estimation
        quality = self.config.get("streaming", "video_quality", "High")
        bitrate = QUALITY_BITRATES.get(quality, 10_000_000)
        estimated_bytes_per_second = bitrate // 8

        while not self._stop_event.is_set():
            # Check if GStreamer process is still running
            if self._gst_process and self._gst_process.poll() is not None:
                # Process exited
                returncode = self._gst_process.returncode
                stderr_output = ""
                try:
                    stderr_output = self._gst_process.stderr.read().decode(
                        "utf-8", errors="replace"
                    )
                except Exception:
                    pass

                if returncode != 0 and not self._stop_event.is_set():
                    error_msg = f"GStreamer exited with code {returncode}"
                    if stderr_output:
                        # Get last meaningful line
                        err_lines = [
                            x for x in stderr_output.strip().split("\n")
                            if x.strip()
                        ]
                        if err_lines:
                            error_msg += f": {err_lines[-1]}"
                    logger.error(error_msg)
                    self._stats.errors += 1
                    GLib.idle_add(self.emit, "casting-error", error_msg)
                    self._casting = False
                    return

                logger.info("GStreamer process ended normally")
                return

            # Update stats every second
            now = time.time()
            if now - last_update >= 1.0:
                elapsed = now - start_time
                self._stats.duration = int(elapsed)

                # Estimate data transferred from bitrate
                self._stats.data_transferred = int(estimated_bytes_per_second * elapsed)

                # Calculate current average bitrate
                if elapsed > 0:
                    self._stats.average_bitrate = (self._stats.data_transferred * 8) / elapsed
                self._stats.peak_bitrate = max(self._stats.peak_bitrate, bitrate)

                last_update = now

                # Emit stats update
                GLib.idle_add(self.emit, "stats-updated", self._stats)

                logger.debug(
                    f"Streaming: {elapsed:.0f}s, "
                    f"{self._stats.data_transferred / 1_000_000:.1f} MB, "
                    f"{self._stats.average_bitrate / 1_000_000:.1f} Mbps"
                )

            time.sleep(0.5)
