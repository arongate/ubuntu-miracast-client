# Ubuntu Miracast Client Architecture

## Overview

The Ubuntu Miracast Client follows a modular architecture with clear separation of concerns between UI components, core functionality, and system integration. All modules use real system calls — no simulated or mocked behavior at runtime.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                           │
│            app.py — MiracastClientApp (Adw.Application)         │
├─────────────────────────────────────────────────────────────────┤
│                         UI Layer (GTK 4)                         │
│  MainWindow │ SourceSelector │ DeviceSelector │ HistoryView     │
│             │ SettingsView                                       │
├─────────────────────────────────────────────────────────────────┤
│                        Core Layer                                │
│  Discovery │ Capture │ Casting │ History │ Config               │
├─────────────────────────────────────────────────────────────────┤
│                  System Integration Layer                        │
│  wpa_cli (P2P) │ GStreamer (gst-launch-1.0) │ xprop (X11)     │
│  systemd (service) │ ip (networking)                            │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### Discovery Module (`discovery.py`)

Discovers Miracast-compatible devices using real wpa_supplicant P2P:

- **Interface detection**: Auto-detects `p2p-dev-*` interface via `wpa_cli interface`
- **WFD advertisement**: Sets Wi-Fi Display subelements to identify as WFD source
- **P2P scanning**: `wpa_cli p2p_find` → polls `p2p_peers` → queries `p2p_peer <addr>`
- **WFD parsing**: Decodes WFD subelement bitmaps to identify sinks vs sources
- **Signal mapping**: Converts dBm values to 0-100% scale
- **Filtering**: `get_devices()` returns only castable sinks

### Capture Module (`capture.py`)

Enumerates real screens and windows:

- **Screens**: Via `Gdk.Display.get_monitors()` (GTK 4) or `xrandr` fallback
- **Windows**: Via `xprop -root _NET_CLIENT_LIST` + per-window `WM_NAME`/`WM_CLASS` queries
- **Pipeline generation**: Each source produces a GStreamer `ximagesrc` pipeline string

### Casting Module (`casting.py`)

Manages the full streaming lifecycle:

- **Wi-Fi Direct connection** (`WifiDirectConnection`):
  - `wpa_cli p2p_connect <addr> pbc go_intent=0`
  - Monitors `ip link show` for P2P group interface creation
  - Resolves peer IP via `ip addr show` + `ip neigh show`

- **GStreamer streaming**:
  - Launches `gst-launch-1.0` as subprocess
  - Pipeline: `ximagesrc → videoconvert → x264enc (ultrafast/zerolatency) → mpegtsmux → rtpmp2tpay → udpsink`
  - Monitors process health, collects stats

- **Cleanup**: Terminates GStreamer, disconnects P2P group on stop/error

### History Module (`history.py`)

Persists session records to JSON at `~/.local/share/ubuntu-miracast-client/history.json`.

### Config Module (`config.py`)

XDG-compliant JSON config at `~/.config/ubuntu-miracast-client/config.json`.

### Service Module (`service.py`)

Manages systemd user service lifecycle via `systemctl --user` commands.

## Data Flow

```
[User selects source] → SourceSelector emits "source-selected"
        │
        ▼
[User selects device] → DeviceSelector emits "device-selected"
        │
        ▼
[CastManager.start_casting(source, device)]
        │
        ├─► WifiDirectConnection.connect()  [wpa_cli p2p_connect]
        │       │
        │       ▼ (P2P group formed, IP assigned)
        │
        ├─► source.start_capture()  [generates GStreamer pipeline]
        │
        └─► subprocess.Popen(gst-launch-1.0 ...)  [real streaming]
                │
                ▼ (UDP packets → Miracast sink)
```

## Threading Model

| Operation | Thread | IPC Mechanism |
|-----------|--------|---------------|
| UI rendering | Main (GTK) | — |
| P2P discovery | Daemon thread | `GLib.idle_add()` for signals |
| Casting session | Daemon thread | `threading.Event` for stop, `GLib.idle_add()` for signals |
| GStreamer streaming | Subprocess (separate process) | `Popen.poll()` for health check |
| Config/History I/O | Main thread | Synchronous file I/O |

## System Dependencies

| Tool | Used for | Package |
|------|----------|---------|
| `wpa_cli` | P2P discovery and connection | `wpasupplicant` |
| `gst-launch-1.0` | Video capture and streaming | `gstreamer1.0-tools` |
| `xprop` | X11 window enumeration | `x11-utils` |
| `ip` | Network interface/neighbor queries | `iproute2` (preinstalled) |

## Security Considerations

- Wi-Fi Direct P2P connections use WPA2 (enforced by wpa_supplicant)
- Application requires root for `wpa_cli` access (P2P operations)
- Config files stored with default user permissions
- GStreamer runs as subprocess (inherits root context when run with sudo)

## Fault Tolerance

- **Discovery errors**: Emitted as `discovery-error` signal, UI shows error
- **Connection timeout**: Configurable (default 30s), raises RuntimeError
- **GStreamer crash**: Detected via `poll()`, emits `casting-error` signal
- **P2P disconnection**: Cleaned up in `stop_casting()` and on error paths
- **Service mode**: systemd `Restart=on-failure` with 5s delay
