"""Tests for the config module."""

import tempfile
import unittest
from pathlib import Path

from miracast_client.config import Config


class TestConfig(unittest.TestCase):
    """Test cases for the Config class."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test config
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_default_config(self):
        """Test that default configuration is created correctly."""
        config = Config(self.config_path)

        # Check that the config file was created
        self.assertTrue(self.config_path.exists())

        # Check default values
        self.assertEqual(config.get("general", "minimize_to_tray"), True)
        self.assertEqual(config.get("general", "start_minimized"), False)
        self.assertEqual(config.get("general", "log_level"), "INFO")

        self.assertEqual(config.get("streaming", "video_quality"), "High")
        self.assertEqual(config.get("streaming", "frame_rate"), 30)
        self.assertEqual(config.get("streaming", "audio_enabled"), True)

        self.assertEqual(config.get("advanced", "discovery_timeout"), 10)
        self.assertEqual(config.get("advanced", "connection_timeout"), 15)

    def test_set_and_get(self):
        """Test setting and getting configuration values."""
        config = Config(self.config_path)

        # Set some values
        config.set("general", "log_level", "DEBUG")
        config.set("streaming", "video_quality", "Low")
        config.set("advanced", "discovery_timeout", 20)

        # Check that the values were set correctly
        self.assertEqual(config.get("general", "log_level"), "DEBUG")
        self.assertEqual(config.get("streaming", "video_quality"), "Low")
        self.assertEqual(config.get("advanced", "discovery_timeout"), 20)

    def test_save_and_load(self):
        """Test saving and loading configuration."""
        # Create and modify config
        config1 = Config(self.config_path)
        config1.set("general", "log_level", "DEBUG")
        config1.set("streaming", "video_quality", "Low")
        config1.save()

        # Create a new config instance that should load the saved values
        config2 = Config(self.config_path)

        # Check that the values were loaded correctly
        self.assertEqual(config2.get("general", "log_level"), "DEBUG")
        self.assertEqual(config2.get("streaming", "video_quality"), "Low")

    def test_nonexistent_key(self):
        """Test getting a nonexistent key."""
        config = Config(self.config_path)

        # Get a nonexistent key with default value
        self.assertEqual(config.get("general", "nonexistent", "default"), "default")

        # Get a nonexistent key without default value
        self.assertIsNone(config.get("general", "nonexistent"))

    def test_nonexistent_section(self):
        """Test getting a nonexistent section."""
        config = Config(self.config_path)

        # Get a nonexistent section with default value
        self.assertEqual(config.get("nonexistent", "key", "default"), "default")

        # Get a nonexistent section without default value
        self.assertIsNone(config.get("nonexistent", "key"))


if __name__ == "__main__":
    unittest.main()
