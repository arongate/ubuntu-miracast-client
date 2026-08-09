"""Tests for the service module."""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from miracast_client.service import ServiceManager


class TestServiceManager(unittest.TestCase):
    """Test cases for the ServiceManager class."""

    def setUp(self):
        """Set up test environment."""
        self.manager = ServiceManager()

    def test_service_file_path(self):
        """Test service file path is correct."""
        expected_path = Path.home() / ".config" / "systemd" / "user" / "ubuntu-miracast-client.service"
        self.assertEqual(self.manager.service_file_path, expected_path)

    def test_service_name(self):
        """Test service name is correct."""
        self.assertEqual(self.manager.SERVICE_NAME, "ubuntu-miracast-client")

    @patch('miracast_client.service.subprocess.run')
    def test_is_service_enabled_true(self, mock_run):
        """Test is_service_enabled returns True when service is enabled."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "enabled\n"
        mock_run.return_value = mock_result

        # Mock the path exists check
        with patch.object(Path, 'exists', return_value=True):
            result = self.manager.is_service_enabled()

        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["systemctl", "--user", "is-enabled", "ubuntu-miracast-client"],
            capture_output=True,
            text=True,
            check=False
        )

    @patch('miracast_client.service.subprocess.run')
    def test_is_service_enabled_false(self, mock_run):
        """Test is_service_enabled returns False when service is disabled."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "disabled\n"
        mock_run.return_value = mock_result

        with patch.object(Path, 'exists', return_value=True):
            result = self.manager.is_service_enabled()

        self.assertFalse(result)

    @patch('miracast_client.service.subprocess.run')
    def test_is_service_enabled_no_service_file(self, mock_run):
        """Test is_service_enabled returns False when service file doesn't exist."""
        with patch.object(Path, 'exists', return_value=False):
            result = self.manager.is_service_enabled()

        self.assertFalse(result)
        mock_run.assert_not_called()

    @patch('miracast_client.service.subprocess.run')
    def test_is_service_running_true(self, mock_run):
        """Test is_service_running returns True when service is active."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "active\n"
        mock_run.return_value = mock_result

        result = self.manager.is_service_running()

        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["systemctl", "--user", "is-active", "ubuntu-miracast-client"],
            capture_output=True,
            text=True,
            check=False
        )

    @patch('miracast_client.service.subprocess.run')
    def test_is_service_running_false(self, mock_run):
        """Test is_service_running returns False when service is inactive."""
        mock_result = MagicMock()
        mock_result.returncode = 3
        mock_result.stdout = "inactive\n"
        mock_run.return_value = mock_result

        result = self.manager.is_service_running()

        self.assertFalse(result)

    @patch('miracast_client.service.subprocess.run')
    def test_enable_service_calls_correct_commands(self, mock_run):
        """Test enable_service calls correct subprocess commands."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(Path, 'mkdir'), \
             patch.object(self.manager, '_create_service_file'):
            self.manager.enable_service()

        # Should call daemon-reload and enable
        expected_calls = [
            call(["systemctl", "--user", "daemon-reload"], check=True),
            call(["systemctl", "--user", "enable", "ubuntu-miracast-client"], check=True),
        ]
        mock_run.assert_has_calls(expected_calls, any_order=False)

    @patch('miracast_client.service.subprocess.run')
    def test_disable_service_calls_correct_commands(self, mock_run):
        """Test disable_service calls correct subprocess commands."""
        mock_run.return_value = MagicMock(returncode=0)

        # Mock is_service_running to return False (not running)
        with patch.object(self.manager, 'is_service_running', return_value=False), \
             patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'unlink'):
            self.manager.disable_service()

        # Should call disable and daemon-reload
        calls = mock_run.call_args_list
        cmd_args = [c[0][0] for c in calls]
        self.assertIn(["systemctl", "--user", "disable", "ubuntu-miracast-client"], cmd_args)
        self.assertIn(["systemctl", "--user", "daemon-reload"], cmd_args)

    @patch('miracast_client.service.subprocess.run')
    def test_start_service_calls_correct_commands(self, mock_run):
        """Test start_service calls correct subprocess commands."""
        mock_run.return_value = MagicMock(returncode=0)

        # Mock is_service_enabled to return True
        with patch.object(self.manager, 'is_service_enabled', return_value=True):
            self.manager.start_service()

        mock_run.assert_called_with(
            ["systemctl", "--user", "start", "ubuntu-miracast-client"],
            check=True
        )

    @patch('miracast_client.service.subprocess.run')
    def test_stop_service_calls_correct_commands(self, mock_run):
        """Test stop_service calls correct subprocess commands."""
        mock_run.return_value = MagicMock(returncode=0)

        self.manager.stop_service()

        mock_run.assert_called_once_with(
            ["systemctl", "--user", "stop", "ubuntu-miracast-client"],
            check=True
        )

    @patch('miracast_client.service.subprocess.run')
    def test_enable_service_raises_runtime_error_on_failure(self, mock_run):
        """Test enable_service raises RuntimeError on failure."""
        mock_run.side_effect = Exception("Permission denied")

        with patch.object(Path, 'mkdir'), \
             patch.object(self.manager, '_create_service_file'):
            with self.assertRaises(RuntimeError) as ctx:
                self.manager.enable_service()

        self.assertIn("Failed to enable service", str(ctx.exception))

    @patch('miracast_client.service.subprocess.run')
    def test_stop_service_raises_runtime_error_on_failure(self, mock_run):
        """Test stop_service raises RuntimeError on failure."""
        mock_run.side_effect = Exception("Service not found")

        with self.assertRaises(RuntimeError) as ctx:
            self.manager.stop_service()

        self.assertIn("Failed to stop service", str(ctx.exception))

    @patch('miracast_client.service.subprocess.run')
    def test_start_service_enables_if_not_enabled(self, mock_run):
        """Test start_service enables the service first if not enabled."""
        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(self.manager, 'is_service_enabled', return_value=False), \
             patch.object(self.manager, 'enable_service') as mock_enable:
            self.manager.start_service()

        mock_enable.assert_called_once()


if __name__ == '__main__':
    unittest.main()
