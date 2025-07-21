# Getting Started with Ubuntu Miracast Client

This guide will help you get started with Ubuntu Miracast Client, from installation to your first casting session.

## Installation

### From Debian Package

1. Download the latest `.deb` package from the [releases page](https://github.com/yourusername/ubuntu-miracast-client/releases).

2. Install the package:
   ```bash
   sudo apt install ./ubuntu-miracast-client_1.0.0_amd64.deb
   ```

3. The application will be available in your applications menu or can be launched from the terminal:
   ```bash
   ubuntu-miracast-client
   ```

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ubuntu-miracast-client.git
   cd ubuntu-miracast-client
   ```

2. Install dependencies:
   ```bash
   sudo apt install python3-gi python3-cairo python3-gst-1.0 gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 wpasupplicant
   ```

3. Install the package:
   ```bash
   pip install -e .
   ```

4. Run the application:
   ```bash
   ubuntu-miracast-client
   ```

## First-Time Setup

When you first launch Ubuntu Miracast Client, you may want to configure some settings:

1. Click on the menu button in the top-right corner and select "Settings".

2. In the Settings view, you can configure:
   - General settings (minimize to system tray, start minimized)
   - Streaming quality and frame rate
   - Service mode options
   - Advanced settings

3. Click "Save Settings" to apply your changes.

## Casting Your Screen

### Step 1: Select a Source

1. Launch Ubuntu Miracast Client.

2. On the "Select What to Cast" screen, choose either:
   - "Entire Screen" to cast your whole display
   - "Application Window" to cast a specific application

3. Select the specific screen or window from the list.

4. Click "Select" to proceed.

### Step 2: Select a Device

1. The application will search for Miracast-compatible devices on your network.

2. Wait for the discovery process to complete.

3. Select your target device from the list.

4. Click "Connect" to start casting.

### Step 3: Manage Your Casting Session

1. The application will minimize to the system tray while casting.

2. To stop casting, click on the system tray icon to restore the window, then click "Stop Casting".

3. After stopping, you'll see statistics about your casting session.

## Using Service Mode

Service mode allows Ubuntu Miracast Client to run in the background:

1. Go to Settings > Service.

2. Toggle "Run as System Service" to enable service mode.

3. Use the "Start Service" and "Stop Service" buttons to control the service.

4. When running as a service, the application will automatically start when you log in.

## Troubleshooting

### No Devices Found

- Make sure your Miracast receiver is powered on and connected to the network.
- Check that your Wi-Fi adapter supports Wi-Fi Direct.
- Try restarting the discovery process by clicking "Refresh".

### Connection Issues

- Ensure your Miracast receiver is not already connected to another device.
- Check that your Wi-Fi signal is strong enough.
- Try moving your computer closer to the Miracast receiver.

### Performance Issues

- Lower the streaming quality in Settings > Streaming.
- Close other applications that may be using network bandwidth.
- Use a 5GHz Wi-Fi connection if available for better performance.

### Logs

If you encounter issues, check the log files:

- Application log: `~/.local/share/ubuntu-miracast-client/logs/miracast-client.log`
- Service log: `~/.local/share/ubuntu-miracast-client/logs/miracast-service.log`

## Next Steps

- Check out the [Miracast Protocol](miracast-protocol.md) document to learn more about how Miracast works.
- Visit our [GitHub repository](https://github.com/yourusername/ubuntu-miracast-client) for updates and to report issues.