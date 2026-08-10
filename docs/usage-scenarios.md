# Usage Scenarios — Ubuntu Miracast Client

This document describes real-world scenarios for using Ubuntu Miracast Client, explaining **what** you can do, **why** you would do it, and **how** to accomplish it.

## Overview

Ubuntu Miracast Client is a desktop application that wirelessly casts your screen or application windows to Miracast-compatible receivers (smart TVs, wireless displays, projectors) over Wi-Fi Direct. It is designed for Ubuntu 24.04 LTS with the GNOME desktop.

---

## Scenario 1: Presenting Slides in a Meeting Room

### Why

You're in a meeting room with a Miracast-capable smart TV or wireless display adapter. You need to present your LibreOffice Impress slides without plugging in any cables.

### How

1. **Launch** the application from the Activities menu or run `ubuntu-miracast-client`.
2. On the **Source Selection** page, select **"Application Window"**.
3. Choose your LibreOffice Impress window from the list.
4. Click **Select** → you'll move to the Device Selection page.
5. Wait for the meeting room display to appear in the device list (scanning takes up to 10 seconds by default).
6. Select the display and click **Connect**.
7. Your presentation window is now cast to the screen. The app minimizes automatically.
8. When done, re-open the app and click **Stop Casting** (or use the `stop-cast` action).

### Tips

- Set Video Quality to **High** or **Very High** in Settings for crisp text.
- If the device doesn't appear, click **Refresh** or increase the discovery timeout in Settings → Advanced.

---

## Scenario 2: Casting Your Entire Desktop for a Demo

### Why

You want to show a live coding demo, terminal commands, or multi-application workflow on a large display — sharing everything visible on your screen.

### How

1. Launch `ubuntu-miracast-client`.
2. On the Source Selection page, select **"Entire Screen"**.
3. If you have multiple monitors, select the one you want to cast.
4. Click **Select** → proceed to Device Selection.
5. Select your Miracast receiver and click **Connect**.
6. Your full desktop is now mirrored on the external display.

### Tips

- Close sensitive applications (email, chat) before casting your entire screen.
- Frame rate of **30 fps** (default) is sufficient for demos; use **60 fps** for smoother animation at the cost of higher bandwidth.

---

## Scenario 3: Streaming a Video to Your Living Room TV

### Why

You have a video file or browser stream on your laptop and want to watch it on your smart TV without HDMI cables.

### How

1. Start playing the video in your preferred player or browser.
2. Launch `ubuntu-miracast-client`.
3. Choose **"Application Window"** and select the video player window.
4. Alternatively, choose **"Entire Screen"** if the video is fullscreen.
5. In Settings, ensure **Audio Enabled** is turned on.
6. Select your TV from the device list and connect.
7. The video (with audio) streams to your TV.

### Tips

- Use **Medium** or **High** quality to balance visual fidelity and network bandwidth.
- Ensure your Wi-Fi uses 5 GHz for reduced latency and better throughput.

---

## Scenario 4: Running as a Background Service

### Why

You want the application to be always available for quick casting without manually launching it each time you log in — useful in a classroom or conference setup where screens are cast frequently.

### How

1. Launch the app and go to **Settings → Service**.
2. Toggle **"Run as System Service"** on.
3. The app now runs as a systemd user service that starts on login.
4. Alternatively, enable it from the CLI:
   ```bash
   ubuntu-miracast-client --service
   ```
   Or via systemd:
   ```bash
   systemctl --user enable --now ubuntu-miracast-client
   ```
5. To stop the service:
   ```bash
   systemctl --user stop ubuntu-miracast-client
   ```

### Tips

- The service restarts automatically on failure (after 5 seconds).
- Service logs are at `~/.local/share/ubuntu-miracast-client/logs/miracast-service.log`.

---

## Scenario 5: Reviewing Past Casting Sessions

### Why

You want to check how much data was transferred during your last presentation, or verify that a casting session completed successfully.

### How

1. Open the app and navigate to the **History** page (accessible after any completed session, or via the navigation).
2. Sessions are listed in reverse chronological order (newest first).
3. Click on a session to see details:
   - Source and destination device
   - Start time and duration
   - Data transferred and average bitrate
4. Use this information to estimate bandwidth needs for future sessions.

### Tips

- Clear history from **Settings → Advanced → Clear History** if needed.
- History is stored at `~/.local/share/ubuntu-miracast-client/history.json`.

---

## Scenario 6: Optimizing for Slow Networks

### Why

You're on a congested Wi-Fi network (hotel, conference) and casting quality is poor with dropped frames.

### How

1. Open **Settings → Streaming**.
2. Lower **Video Quality** to **Low** (2 Mbps) or **Medium** (5 Mbps).
3. Set **Frame Rate** to **15 fps** or **24 fps**.
4. Disable **Audio** if not needed (saves 128 kbps).
5. Save settings and restart your cast.

### Quality Profiles

| Quality | Bitrate | Best for |
|---------|---------|----------|
| Low | 2 Mbps | Slow networks, basic slides |
| Medium | 5 Mbps | Standard presentations |
| High | 10 Mbps | Video content, demos |
| Very High | 20 Mbps | High-resolution video, fast Wi-Fi |

---

## Scenario 7: Troubleshooting — No Devices Found

### Why

The device list remains empty after scanning.

### Checklist

1. **Receiver powered on?** Ensure the Miracast receiver/TV is on and in discovery mode.
2. **Wi-Fi Direct supported?** Check with:
   ```bash
   iw phy | grep P2P
   ```
   If no output, your adapter doesn't support Wi-Fi Direct.
3. **wpa_supplicant running?**
   ```bash
   systemctl status wpa_supplicant
   ```
4. **Increase timeout:** Go to Settings → Advanced and increase Discovery Timeout to 30 seconds.
5. **Network interference:** Move closer to the receiver or switch to 5 GHz band.
6. **Check logs:**
   ```bash
   cat ~/.local/share/ubuntu-miracast-client/logs/miracast-client.log
   ```

---

## When to Use This Application

| Use case | Recommended? | Notes |
|----------|:---:|-------|
| Wireless presentations | ✅ | Primary use case — works with real Miracast TVs |
| Screen sharing in meetings | ✅ | Choose window or full screen |
| Casual video streaming to TV | ✅ | Enable audio, use Medium+ quality |
| Gaming / low-latency needs | ⚠️ | Miracast adds ~100-150ms latency |
| Multi-display casting | ❌ | Not supported in v0.0.1 |
| Remote (internet) casting | ❌ | Wi-Fi Direct is local-only |

---

## Current Limitations (v0.0.1)

This is an early release. Known limitations:

- **Requires sudo**: P2P discovery and connection use `wpa_cli` which requires root privileges. Run the application with `sudo` or configure polkit rules for passwordless access.
- **X11 only**: Screen/window capture uses `ximagesrc`. Wayland support (via PipeWire/XDG portal) is planned for a future release.
- **No RTSP negotiation**: The current implementation streams directly via UDP to the sink's RTSP port. Full Miracast RTSP/WFD session negotiation (SETUP/PLAY/TEARDOWN) is planned.
- **No multi-display casting**: Only one session at a time.
- **PBC connection only**: Uses Push Button Configuration for P2P pairing. PIN-based WPS is not yet supported.
- **One-way streaming**: Audio streaming pipeline is configured but may not work with all sinks without full WFD negotiation.

These limitations reflect the 0.x unstable status. The core functionality (discover real devices, capture real screens/windows, stream real video over Wi-Fi Direct) is fully operational.
