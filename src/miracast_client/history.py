"""Session history management for Ubuntu Miracast Client."""

import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List

from miracast_client.capture import CaptureSource
from miracast_client.discovery import MiracastDevice
from miracast_client.casting import CastingStats

logger = logging.getLogger(__name__)


@dataclass
class SessionRecord:
    """Record of a casting session."""
    
    source: CaptureSource
    device: MiracastDevice
    stats: CastingStats
    timestamp: datetime
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            "source": {
                "id": self.source.id,
                "name": self.source.name,
                "description": self.source.description,
                "icon": self.source.icon
            },
            "device": {
                "id": self.device.id,
                "name": self.device.name,
                "address": self.device.address,
                "model": self.device.model,
                "signal_strength": self.device.signal_strength
            },
            "stats": {
                "start_time": self.stats.start_time.isoformat(),
                "end_time": self.stats.end_time.isoformat() if self.stats.end_time else None,
                "duration": self.stats.duration,
                "data_transferred": self.stats.data_transferred,
                "average_bitrate": self.stats.average_bitrate,
                "peak_bitrate": self.stats.peak_bitrate,
                "dropped_frames": self.stats.dropped_frames,
                "errors": self.stats.errors
            },
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary."""
        source = CaptureSource(
            id=data["source"]["id"],
            name=data["source"]["name"],
            description=data["source"]["description"],
            icon=data["source"].get("icon", "video-display")
        )
        
        device = MiracastDevice(
            id=data["device"]["id"],
            name=data["device"]["name"],
            address=data["device"]["address"],
            model=data["device"]["model"],
            signal_strength=data["device"]["signal_strength"]
        )
        
        stats = CastingStats(
            start_time=datetime.fromisoformat(data["stats"]["start_time"]),
            end_time=datetime.fromisoformat(data["stats"]["end_time"]) if data["stats"]["end_time"] else None,
            duration=data["stats"]["duration"],
            data_transferred=data["stats"]["data_transferred"],
            average_bitrate=data["stats"]["average_bitrate"],
            peak_bitrate=data["stats"]["peak_bitrate"],
            dropped_frames=data["stats"]["dropped_frames"],
            errors=data["stats"]["errors"]
        )
        
        return cls(
            source=source,
            device=device,
            stats=stats,
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


class SessionHistory:
    """Manages casting session history."""
    
    def __init__(self, history_path=None):
        """Initialize the session history manager.
        
        Args:
            history_path: Optional path to the history file. If not provided,
                         the default location will be used.
        """
        if history_path:
            self.history_path = Path(history_path)
        else:
            # Use XDG data directory
            self.history_path = Path.home() / ".local" / "share" / "ubuntu-miracast-client" / "history.json"
        
        # Create directory if it doesn't exist
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load history
        self.sessions = self._load_history()
    
    def _load_history(self):
        """Load session history from file.
        
        Returns:
            List of SessionRecord objects
        """
        if not self.history_path.exists():
            return []
        
        try:
            with open(self.history_path, 'r') as f:
                data = json.load(f)
            
            sessions = []
            for session_data in data:
                try:
                    session = SessionRecord.from_dict(session_data)
                    sessions.append(session)
                except Exception as e:
                    logger.error(f"Failed to load session record: {e}")
            
            logger.info(f"Loaded {len(sessions)} session records")
            return sessions
        except Exception as e:
            logger.error(f"Failed to load session history: {e}")
            return []
    
    def _save_history(self):
        """Save session history to file."""
        try:
            data = [session.to_dict() for session in self.sessions]
            with open(self.history_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("Session history saved")
        except Exception as e:
            logger.error(f"Failed to save session history: {e}")
    
    def add_session(self, source, device, stats):
        """Add a new session record.
        
        Args:
            source: CaptureSource object
            device: MiracastDevice object
            stats: CastingStats object
        """
        session = SessionRecord(
            source=source,
            device=device,
            stats=stats,
            timestamp=datetime.now()
        )
        
        self.sessions.append(session)
        self._save_history()
        
        logger.info(f"Added session record: {source.name} → {device.name}")
        return session
    
    def get_sessions(self):
        """Get all session records.
        
        Returns:
            List of SessionRecord objects
        """
        return self.sessions
    
    def clear(self):
        """Clear all session records."""
        self.sessions = []
        self._save_history()
        logger.info("Session history cleared")