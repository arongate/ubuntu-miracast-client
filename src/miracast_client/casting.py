"""Miracast casting functionality."""

import gi
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime

gi.require_version('GLib', '2.0')
from gi.repository import GObject, GLib

from miracast_client.config import Config

logger = logging.getLogger(__name__)


@dataclass
class CastingStats:
    """Statistics for a casting session."""
    
    start_time: datetime
    end_time: datetime = None
    duration: int = 0  # in seconds
    data_transferred: int = 0  # in bytes
    average_bitrate: float = 0  # in bps
    peak_bitrate: float = 0  # in bps
    dropped_frames: int = 0
    errors: int = 0


class CastManager(GObject.Object):
    """Manages Miracast casting sessions."""
    
    __gsignals__ = {
        'casting-started': (GObject.SignalFlags.RUN_FIRST, None, (object, object)),
        'casting-stopped': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'casting-error': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'stats-updated': (GObject.SignalFlags.RUN_FIRST, None, (object,))
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
            Exception: If casting fails to start
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
            self._thread = threading.Thread(target=self._casting_thread)
            self._thread.daemon = True
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
        
        # Wait for thread to finish
        if self._thread:
            self._thread.join(timeout=2.0)
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
            # In a real implementation, this would:
            # 1. Establish Wi-Fi Direct connection with the device
            # 2. Set up RTSP session
            # 3. Start streaming using GStreamer
            
            # For this example, we'll simulate the casting process
            self._simulate_casting()
        except Exception as e:
            logger.error(f"Casting error: {e}")
            GLib.idle_add(self.emit, "casting-error", str(e))
            self._casting = False
    
    def _simulate_casting(self):
        """Simulate casting for demonstration purposes."""
        # Get quality settings
        quality = self.config.get("streaming", "video_quality", "High")
        frame_rate = self.config.get("streaming", "frame_rate", 30)
        audio_enabled = self.config.get("streaming", "audio_enabled", True)
        
        # Calculate simulated bitrate based on quality
        bitrates = {
            "Low": 2_000_000,      # 2 Mbps
            "Medium": 5_000_000,   # 5 Mbps
            "High": 10_000_000,    # 10 Mbps
            "Very High": 20_000_000  # 20 Mbps
        }
        
        base_bitrate = bitrates.get(quality, 5_000_000)
        
        # Simulate streaming
        start_time = time.time()
        last_update = start_time
        last_bytes = 0
        
        while not self._stop_event.is_set():
            # Simulate 100ms of streaming
            time.sleep(0.1)
            
            # Calculate elapsed time
            now = time.time()
            elapsed = now - start_time
            
            # Simulate data transfer (bitrate with some variation)
            variation = (hash(str(now)) % 20) / 100  # -10% to +10%
            current_bitrate = base_bitrate * (1 + variation)
            
            # Add audio bitrate if enabled
            if audio_enabled:
                current_bitrate += 128_000  # 128 kbps for audio
            
            # Calculate bytes transferred in this interval
            interval = now - last_update
            bytes_in_interval = int(current_bitrate * interval / 8)
            
            # Update statistics
            self._stats.data_transferred += bytes_in_interval
            self._stats.duration = int(elapsed)
            
            # Update peak bitrate
            if current_bitrate > self._stats.peak_bitrate:
                self._stats.peak_bitrate = current_bitrate
            
            # Calculate current average bitrate
            self._stats.average_bitrate = (self._stats.data_transferred * 8) / elapsed
            
            # Occasionally simulate dropped frames
            if hash(str(now)) % 100 < 5:  # 5% chance
                self._stats.dropped_frames += 1
            
            # Update stats every second
            if now - last_update >= 1.0:
                # Calculate instantaneous bitrate for logging
                instant_bitrate = (self._stats.data_transferred - last_bytes) * 8 / (now - last_update)
                last_bytes = self._stats.data_transferred
                last_update = now
                
                # Log statistics
                logger.debug(f"Casting stats: {instant_bitrate/1_000_000:.2f} Mbps, "
                            f"{self._stats.data_transferred/1_000_000:.2f} MB transferred, "
                            f"{self._stats.dropped_frames} dropped frames")
                
                # Emit stats update signal
                GLib.idle_add(self.emit, "stats-updated", self._stats)
        
        logger.info("Casting thread stopped")