# Getting Started with Ubuntu Miracast Client

This guide covers installation, first-time setup, and your first casting session.

## Prerequisites

- Ubuntu 24.04 LTS (or compatible)
- Wi-Fi adapter with P2P support (check: `iw phy | grep P2P`)
- A Miracast-compatible receiver (smart TV, wireless display adapter, or phone with a Miracast sink app)
- X11 display server (Wayland is not yet supported)

## Installation

### From Debian Package

1. Download the latest `.deb` from the [releases page](https://github.com/yourusername/ubuntu-miracast-client/releases).

2. Install:
   ```bash
   sudo apt install ./ubuntu-miracast-client_0.0.1_amd64.deb
   ```

### From Source (using uv)

1. Install system dependencies:
   ```bash
   sudo apt install python3-gi python3-cairo python3-gst-1.0 \
       gir1.2-gtk-4.0 gir1.2-adw-1 \
       gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 \
       gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly \
       wpasupplicant x11-utils
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
   sudo ubuntu-miracast-client
   ```

## Running the Application

The application requires **root privileges** for Wi-Fi Direct P2P operations (device discovery and connection use `wpa_cli`):

```bash
sudo ubuntu-miracast-client
```

> **Why sudo?** Wi-Fi Direct P2P find/connect operations require access to the
> wpa_supplicant control interface, which is restricted to root. A future release
> will support polkit rules for passwordless access.

## First-Time Setup

1. Launch the application with `sudo ubuntu-miracast-client`.
2. Click the menu button (top-right) → **Settings**.
3. Configure your preferences:
   - **Streaming**: Video quality (Low 2 Mbps / Medium 5 Mbps / High 10 Mbps / Very High 20 Mbps), frame rate (15/24/30/60 fps)
   - **Advanced**: Discovery timeout (how long to scan for devices, default 10s)
4. Click **Save Settings**.

## Casting Your Screen

### Step 1: Select a Source

1. On the main screen, choose:
   - **Entire Screen** — cast your full display (uses `ximagesrc`)
   - **Application Window** — cast a specific window (lists real open windows)
2. Select the source from the list.
3. Click **Select**.

### Step 2: Select a Device

1. The app performs a real Wi-Fi Direct P2P scan using wpa_supplicant.
2. Miracast sinks (TVs, displays, receiver apps) appear in the list with signal strength.
3. Select your target device.
4. Click **Connect**.

### Step 3: Casting

1. A Wi-Fi Direct P2P connection is established to the receiver.
2. GStreamer captures your screen/window and streams H.264 video over UDP.
3. The app window minimizes while casting.
4. To stop: re-open the app and click **Stop Casting**.
5. After stopping, session statistics are recorded to history.

## Testing with a Phone (e.g., Samsung Galaxy S23 Ultra)

To use your phone as a Miracast receiver:

1. Install a Miracast sink app on your phone (e.g., "WiFi Display" from F-Droid or Play Store).
2. Open the app and put it in **receive/sink mode** — it should say "Waiting for connection".
3. On your Ubuntu machine, run `sudo ubuntu-miracast-client`.
4. Select a source → the device discovery page should find your phone.
5. Select the phone and click **Connect**.

> **Note:** Your phone's standard "Smart View" / "Screen Mirror" feature makes the
> phone a *source* (it casts FROM the phone). To receive a cast FROM your PC, the
> phone must be running a sink app.

## Service Mode

Run Ubuntu Miracast Client as a background service:

1. **Via Settings**: Go to Settings → Service → toggle "Run as System Service"
2. **Via CLI**: `sudo ubuntu-miracast-client --service`
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

1. **Receiver in sink mode?** Ensure the Miracast receiver is powered on and waiting for connections.
2. **Wi-Fi Direct supported?** Check with:
   ```bash
   iw phy | grep P2P
   ```
   You need `P2P-client`, `P2P-GO`, and `P2P-device` in the output.
3. **wpa_supplicant running?**
   ```bash
   systemctl status wpa_supplicant
   ```
4. **P2P interface exists?**
   ```bash
   sudo wpa_cli interface
   ```
   Should show `p2p-dev-<your_wifi_interface>`.
5. **Increase timeout**: Go to Settings → Advanced → set Discovery Timeout to 20-30s.
6. **Manual test**:
   ```bash
   sudo wpa_cli -i p2p-dev-wlo1 p2p_find
   sleep 5
   sudo wpa_cli -i p2p-dev-wlo1 p2p_peers
   ```

### Connection Fails

- Ensure the receiver isn't already connected to another device.
- Move closer to the receiver for better signal strength.
- Some sinks require PBC (Push Button) confirmation — check the receiver's screen.
- Check the log file: `~/.local/share/ubuntu-miracast-client/logs/miracast-client.log`

### No Video on Receiver

- The receiver may expect full Miracast RTSP/WFD session negotiation. Some sinks (especially smart TVs) need more than raw UDP streaming.
- Try a dedicated Miracast sink app (TuTuLink, WiFi Display) which tend to be more compatible with direct streaming.
- Check that `gst-launch-1.0` is installed: `which gst-launch-1.0`

### Poor Streaming Quality

- Lower the quality in Settings → Streaming → Video Quality.
- Use a 5 GHz Wi-Fi network (less interference).
- Reduce frame rate to 15 or 24 fps.
- Close bandwidth-heavy applications.

### Logs

Application logs are at:
- App mode: `~/.local/share/ubuntu-miracast-client/logs/miracast-client.log`
- Service mode: `~/.local/share/ubuntu-miracast-client/logs/miracast-service.log`

## How It Works (Technical Overview)

```
[Your Screen/Window]
        │
        ▼ (ximagesrc)
[GStreamer Capture] → x264enc (H.264, ultrafast) → mpegtsmux → rtpmp2tpay → UDP
        │
        ▼ (Wi-Fi Direct P2P)
[Miracast Sink/TV]
```

1. **Discovery**: `wpa_cli p2p_find` scans for P2P peers with WFD (Wi-Fi Display) capabilities
2. **Connection**: `wpa_cli p2p_connect <addr> pbc` establishes a Wi-Fi Direct link
3. **Streaming**: GStreamer captures, encodes H.264, wraps in MPEG-TS/RTP, sends via UDP

## Next Steps

- [Usage Scenarios](usage-scenarios.md) — real-world use cases and tips
- [Architecture documentation](architecture.md) — internal design details
- [Miracast Protocol](miracast-protocol.md) — the underlying protocol
- [Contributing](../CONTRIBUTING.md) — development setup and workflow
