# Getting Started with Ubuntu Miracast Client

This guide covers installation, first-time setup, and your first casting session.

## Installation

### From Debian Package

1. Download the latest `.deb` from the [releases page](https://github.com/yourusername/ubuntu-miracast-client/releases).

2. Install:
   ```bash
   sudo apt install ./ubuntu-miracast-client_1.0.0_amd64.deb
   ```

3. Launch from your applications menu or terminal:
   ```bash
   ubuntu-miracast-client
   ```

### From Source (using uv)

1. Install system dependencies:
   ```bash
   sudo apt install python3-gi python3-cairo python3-gst-1.0 \
       gir1.2-gtk-4.0 gir1.2-adw-1 \
       gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 \
       wpasupplicant
   ```

2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. Clone and set up:
   ```bash
   git clone https://github.com/yourusername/ubuntu-miracast-client.git
   cd ubuntu-miracast-client

   # Create venv with system GTK/GStreamer access
   uv venv .venv --python /usr/bin/python3 --system-site-packages
   source .venv/bin/activate

   # Install dev tools and the project
   uv pip install pytest pytest-cov black isort flake8 mypy
   uv pip install -e . --no-deps
   ```

4. Run:
   ```bash
   ubuntu-miracast-client
   ```

## First-Time Setup

1. Launch the application.
2. Click the menu button (top-right) → **Settings**.
3. Configure your preferences:
   - **General**: Minimize to tray, start minimized, log level
   - **Streaming**: Video quality (Low/Medium/High/Very High), frame rate (15/24/30/60 fps), audio on/off
   - **Advanced**: Discovery timeout, connection timeout
4. Click **Save Settings**.

## Casting Your Screen

### Step 1: Select a Source

1. On the main screen, choose:
   - **Entire Screen** — cast your full display
   - **Application Window** — cast a specific window
2. Select the source from the list.
3. Click **Select**.

### Step 2: Select a Device

1. The app searches for Miracast receivers on your network.
2. Wait for devices to appear (spinner indicates scanning).
3. Select your target device.
4. Click **Connect**.

### Step 3: Casting

1. The window minimizes while casting.
2. To stop: re-open the app and click **Stop Casting**.
3. After stopping, you'll see session statistics (duration, data transferred, bitrate).

## Service Mode

Run Ubuntu Miracast Client as a background service:

1. **Via Settings**: Go to Settings → Service → toggle "Run as System Service"
2. **Via CLI**: `ubuntu-miracast-client --service`
3. **Via systemctl**: 
   ```bash
   systemctl --user enable ubuntu-miracast-client
   systemctl --user start ubuntu-miracast-client
   ```

## Configuration

Settings are stored at `~/.config/ubuntu-miracast-client/config.json`:

```json
{
  "general": {
    "minimize_to_tray": true,
    "start_minimized": false,
    "log_level": "INFO"
  },
  "streaming": {
    "video_quality": "High",
    "frame_rate": 30,
    "audio_enabled": true
  },
  "advanced": {
    "discovery_timeout": 10,
    "connection_timeout": 15
  }
}
```

## Troubleshooting

### No Devices Found

- Ensure your Miracast receiver is powered on and discoverable.
- Verify your Wi-Fi adapter supports Wi-Fi Direct: `iw phy | grep P2P`
- Try clicking **Refresh** to restart discovery.
- Check that wpa_supplicant is running: `systemctl status wpa_supplicant`

### Connection Fails

- Ensure the receiver isn't already connected to another device.
- Move closer to the receiver for better signal.
- Check the log file: `~/.local/share/ubuntu-miracast-client/logs/miracast-client.log`

### Poor Streaming Quality

- Lower the quality in Settings → Streaming → Video Quality.
- Use a 5GHz Wi-Fi connection if available.
- Close bandwidth-heavy applications.
- Check for network congestion.

### Logs

Application logs are at:
- App mode: `~/.local/share/ubuntu-miracast-client/logs/miracast-client.log`
- Service mode: `~/.local/share/ubuntu-miracast-client/logs/miracast-service.log`

## Next Steps

- [Architecture documentation](architecture.md) — understand how the app works internally
- [Miracast Protocol](miracast-protocol.md) — learn about the underlying protocol
- [Contributing](../CONTRIBUTING.md) — set up a development environment and contribute
