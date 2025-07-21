"""Service management for Ubuntu Miracast Client."""

import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages the system service for Ubuntu Miracast Client."""
    
    SERVICE_NAME = "ubuntu-miracast-client"
    SERVICE_FILE = f"{SERVICE_NAME}.service"
    
    def __init__(self):
        """Initialize the service manager."""
        self.systemd_user_dir = Path.home() / ".config" / "systemd" / "user"
        self.systemd_system_dir = Path("/etc/systemd/system")
        self.service_file_path = self.systemd_user_dir / self.SERVICE_FILE
    
    def is_service_enabled(self):
        """Check if the service is enabled.
        
        Returns:
            True if the service is enabled, False otherwise
        """
        try:
            # Check if service file exists
            if not self.service_file_path.exists():
                return False
            
            # Check if service is enabled
            result = subprocess.run(
                ["systemctl", "--user", "is-enabled", self.SERVICE_NAME],
                capture_output=True,
                text=True,
                check=False
            )
            
            return result.returncode == 0 and result.stdout.strip() == "enabled"
        except Exception as e:
            logger.error(f"Failed to check if service is enabled: {e}")
            return False
    
    def is_service_running(self):
        """Check if the service is running.
        
        Returns:
            True if the service is running, False otherwise
        """
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", self.SERVICE_NAME],
                capture_output=True,
                text=True,
                check=False
            )
            
            return result.returncode == 0 and result.stdout.strip() == "active"
        except Exception as e:
            logger.error(f"Failed to check if service is running: {e}")
            return False
    
    def enable_service(self):
        """Enable the service.
        
        Raises:
            RuntimeError: If the service cannot be enabled
        """
        try:
            # Create systemd user directory if it doesn't exist
            self.systemd_user_dir.mkdir(parents=True, exist_ok=True)
            
            # Create service file
            self._create_service_file()
            
            # Reload systemd
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True
            )
            
            # Enable service
            subprocess.run(
                ["systemctl", "--user", "enable", self.SERVICE_NAME],
                check=True
            )
            
            logger.info(f"Service {self.SERVICE_NAME} enabled")
        except Exception as e:
            logger.error(f"Failed to enable service: {e}")
            raise RuntimeError(f"Failed to enable service: {e}")
    
    def disable_service(self):
        """Disable the service.
        
        Raises:
            RuntimeError: If the service cannot be disabled
        """
        try:
            # Stop service if running
            if self.is_service_running():
                self.stop_service()
            
            # Disable service
            subprocess.run(
                ["systemctl", "--user", "disable", self.SERVICE_NAME],
                check=True
            )
            
            # Remove service file
            if self.service_file_path.exists():
                self.service_file_path.unlink()
            
            # Reload systemd
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True
            )
            
            logger.info(f"Service {self.SERVICE_NAME} disabled")
        except Exception as e:
            logger.error(f"Failed to disable service: {e}")
            raise RuntimeError(f"Failed to disable service: {e}")
    
    def start_service(self):
        """Start the service.
        
        Raises:
            RuntimeError: If the service cannot be started
        """
        try:
            # Check if service is enabled
            if not self.is_service_enabled():
                self.enable_service()
            
            # Start service
            subprocess.run(
                ["systemctl", "--user", "start", self.SERVICE_NAME],
                check=True
            )
            
            logger.info(f"Service {self.SERVICE_NAME} started")
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            raise RuntimeError(f"Failed to start service: {e}")
    
    def stop_service(self):
        """Stop the service.
        
        Raises:
            RuntimeError: If the service cannot be stopped
        """
        try:
            # Stop service
            subprocess.run(
                ["systemctl", "--user", "stop", self.SERVICE_NAME],
                check=True
            )
            
            logger.info(f"Service {self.SERVICE_NAME} stopped")
        except Exception as e:
            logger.error(f"Failed to stop service: {e}")
            raise RuntimeError(f"Failed to stop service: {e}")
    
    def _create_service_file(self):
        """Create the systemd service file."""
        # Find the executable path
        executable_path = sys.argv[0]
        if not os.path.isabs(executable_path):
            executable_path = os.path.abspath(executable_path)
        
        # Create service file content
        service_content = f"""[Unit]
Description=Ubuntu Miracast Client Service
After=network.target

[Service]
ExecStart={executable_path} --service
Restart=on-failure
RestartSec=5s
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
"""
        
        # Write service file
        with open(self.service_file_path, 'w') as f:
            f.write(service_content)
        
        logger.debug(f"Created service file at {self.service_file_path}")


def run_as_service():
    """Run the application as a service."""
    import gi
    import time
    
    gi.require_version('GLib', '2.0')
    from gi.repository import GLib
    
    from miracast_client.discovery import MiracastDiscovery
    from miracast_client.casting import CastManager
    
    # Configure logging
    log_dir = Path.home() / ".local" / "share" / "ubuntu-miracast-client" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "miracast-service.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("service")
    logger.info("Starting Ubuntu Miracast Client service")
    
    # Create main loop
    loop = GLib.MainLoop()
    
    # Initialize components
    discovery = MiracastDiscovery()
    cast_manager = CastManager()
    
    # Start discovery
    discovery.start_discovery()
    
    try:
        # Run main loop
        logger.info("Service main loop started")
        loop.run()
    except KeyboardInterrupt:
        logger.info("Service interrupted")
    finally:
        # Clean up
        discovery.stop_discovery()
        if cast_manager.is_casting():
            cast_manager.stop_casting()
        
        logger.info("Service stopped")
    
    return 0