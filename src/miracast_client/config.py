"""Configuration management for Ubuntu Miracast Client."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the application."""

    def __init__(self, config_path=None):
        """Initialize the configuration manager.

        Args:
            config_path: Optional path to the config file. If not provided,
                         the default location will be used.
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Use XDG config directory
            self.config_path = Path.home() / ".config" / "ubuntu-miracast-client" / "config.json"

        # Create directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create config
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()

    def _create_default_config(self):
        """Create default configuration."""
        default_config = {
            "general": {"minimize_to_tray": True, "start_minimized": False, "log_level": "INFO"},
            "streaming": {"video_quality": "High", "frame_rate": 30, "audio_enabled": True},
            "advanced": {"discovery_timeout": 10, "connection_timeout": 15},
        }

        # Save default config
        try:
            self.save(default_config)
        except Exception as e:
            logger.error(f"Failed to save default config: {e}")

        return default_config

    def save(self, config=None):
        """Save configuration to file.

        Args:
            config: Configuration to save. If not provided, the current
                   configuration will be saved.
        """
        if config is None:
            config = self.config

        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.debug("Configuration saved")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise

    def get(self, section, key, default=None):
        """Get a configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if the key doesn't exist

        Returns:
            The configuration value or the default value
        """
        try:
            return self.config[section][key]
        except KeyError:
            return default

    def set(self, section, key, value):
        """Set a configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
        """
        # Create section if it doesn't exist
        if section not in self.config:
            self.config[section] = {}

        self.config[section][key] = value
