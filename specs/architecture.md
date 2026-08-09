# Architecture & Design Specification

## Ubuntu Miracast Client v1.0.0

**Document Version:** 1.0  
**Date:** 2026-08-09  
**Status:** Final

---

## 1. Overview

The Ubuntu Miracast Client is a Python-based GTK 4 desktop application that enables wireless screen/window casting to Miracast-compatible displays. The architecture follows a layered, modular design with clear separation between UI, core logic, and system integration.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                           │
│            app.py — MiracastClientApp (Adw.Application)         │
├─────────────────────────────────────────────────────────────────┤
│                         UI Layer                                 │
│  MainWindow │ SourceSelector │ DeviceSelector │ HistoryView     │
│             │ SettingsView                                       │
├─────────────────────────────────────────────────────────────────┤
│                        Core Layer                                │
│  Discovery │ Capture │ Casting │ History │ Config               │
├─────────────────────────────────────────────────────────────────┤
│                  System Integration Layer                        │
│  ServiceManager (systemd) │ wpa_supplicant │ GStreamer          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Design

### 3.1 Application Entry Point (`app.py`)

**Class:** `MiracastClientApp(Adw.Application)`

**Responsibilities:**
- Bootstrap the GTK/Adw application
- Instantiate all core components (Config, Discovery, CastManager, History, ServiceManager)
- Create the main window on activation
- Route `--service` CLI flag to service mode

**Design Decisions:**
- Uses `Adw.Application` for native GNOME integration and single-instance enforcement
- All core components are instantiated at startup and injected into the UI

### 3.2 Discovery Module (`discovery.py`)

**Classes:**
- `MiracastDevice` — data class representing a discovered device
- `MiracastDiscovery(GObject.Object)` — discovery service with signal-based event emission

**Design Pattern:** Observer (via GObject signals)

**Signals:**

| Signal | Parameters | Description |
|--------|-----------|-------------|
| `device-found` | `(object,)` | Emitted when a device is found or updated |
| `device-lost` | `(str,)` | Emitted with device ID when a device disappears |
| `discovery-started` | `()` | Emitted when discovery begins |
| `discovery-stopped` | `()` | Emitted when discovery ends |
| `discovery-error` | `(str,)` | Emitted with error message |

**Threading Model:**
- Discovery runs on a daemon background thread
- Thread-safe device map protected by `threading.Lock`
- UI updates dispatched via `GLib.idle_add()` to the main thread

### 3.3 Capture Module (`capture.py`)

**Classes:**
- `CaptureSource` — base dataclass (id, name, description, icon)
- `ScreenSource(CaptureSource)` — monitor capture with Gdk.Monitor
- `WindowSource(CaptureSource)` — window capture with window ID

**Functions:**
- `get_available_sources(screen_only, windows_only)` — enumerates capture sources

**Design Decisions:**
- Each source generates its own GStreamer pipeline string via `start_capture()`
- Uses Gdk.Display/Gdk.Monitor for screen enumeration
- Window enumeration designed for future Wnck or XDG desktop portal integration

### 3.4 Casting Module (`casting.py`)

**Classes:**
- `CastingStats` — session statistics dataclass
- `CastManager(GObject.Object)` — manages the streaming session lifecycle

**Signals:**

| Signal | Parameters | Description |
|--------|-----------|-------------|
| `casting-started` | `(object, object)` | Source and device |
| `casting-stopped` | `(object,)` | CastingStats |
| `casting-error` | `(str,)` | Error message |
| `stats-updated` | `(object,)` | Updated CastingStats |

**State Machine:**
```
[Idle] --start_casting(source, device)--> [Casting] --stop_casting()--> [Idle]
                                              |
                                       casting-error → [Error]
```

**Quality Profiles:**

| Quality | Bitrate |
|---------|---------|
| Low | 2 Mbps |
| Medium | 5 Mbps |
| High | 10 Mbps |
| Very High | 20 Mbps |

### 3.5 History Module (`history.py`)

**Classes:**
- `SessionRecord` — composite dataclass holding source, device, stats, and timestamp
- `SessionHistory` — manages persistence of session records

**Storage:**
- Location: `~/.local/share/ubuntu-miracast-client/history.json`
- Format: JSON array of serialized `SessionRecord` objects
- Read on init, written on every add/clear operation

**Serialization:** Custom `to_dict()` / `from_dict()` methods handle datetime ISO format and nested dataclass conversion.

### 3.6 Config Module (`config.py`)

**Class:** `Config`

**Storage:**
- Location: `~/.config/ubuntu-miracast-client/config.json` (XDG compliant)
- Format: Nested JSON object with sections

**Configuration Schema:**
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

### 3.7 Service Module (`service.py`)

**Classes:**
- `ServiceManager` — manages systemd user service lifecycle

**Function:**
- `run_as_service()` — standalone service main loop

**Service File Location:** `~/.config/systemd/user/ubuntu-miracast-client.service`

**Service Lifecycle:**
```
enable_service() → daemon-reload → systemctl enable
start_service()  → systemctl start
stop_service()   → systemctl stop
disable_service() → stop → systemctl disable → remove file → daemon-reload
```

---

## 4. UI Architecture

### 4.1 Window Structure

```
MainWindow (Adw.ApplicationWindow)
├── HeaderBar (Adw.HeaderBar)
│   └── MenuButton → Settings, About
├── Stack (Gtk.Stack) [slide-left-right transition]
│   ├── SourceSelector (page: "source")
│   ├── DeviceSelector (page: "device")
│   ├── HistoryView (page: "history")
│   └── SettingsView (page: "settings")
└── StatusBar (Gtk.Label)
```

### 4.2 Navigation Flow

```
[Source Selection] → source-selected → [Device Selection] → device-selected → [Casting]
                                                                                   |
                                                                           stop-casting
                                                                                   v
                                                                           [History View]
```

### 4.3 UI Component Pattern

Each UI component is a self-contained `Gtk.Box` subclass that:
- Defines custom GObject signals for upward communication
- Receives dependencies via constructor injection
- Manages its own internal state and widget tree
- Uses `Gtk.ListView` with `Gio.ListStore` and `Gtk.SignalListItemFactory` for lists

---

## 5. Data Flow

### 5.1 Casting Session Flow

1. User selects source (SourceSelector → source-selected signal)
2. MainWindow stores source, navigates to DeviceSelector
3. DeviceSelector starts MiracastDiscovery in background
4. User selects device (DeviceSelector → device-selected signal)
5. MainWindow calls CastManager.start_casting(source, device)
6. CastManager creates background thread, emits casting-started
7. During session: stats-updated signals emitted every 1s
8. User stops casting → CastManager.stop_casting()
9. CastManager emits casting-stopped with final CastingStats
10. MainWindow calls SessionHistory.add_session()
11. MainWindow navigates to HistoryView

---

## 6. Concurrency Model

| Operation | Thread | Sync Mechanism |
|-----------|--------|---------------|
| UI rendering | Main (GTK) | — |
| Device discovery | Daemon thread | `threading.Lock` for device map, `GLib.idle_add` for signals |
| Casting session | Daemon thread | `threading.Event` for stop, `GLib.idle_add` for signals |
| Config/History I/O | Main thread | Synchronous file I/O |

**Key Invariant:** All GObject signal emissions and GTK widget updates happen on the main thread via `GLib.idle_add()`.

---

## 7. File System Layout

```
~/.config/ubuntu-miracast-client/
├── config.json                              # Application settings
└── systemd/user/
    └── ubuntu-miracast-client.service       # Systemd service file

~/.local/share/ubuntu-miracast-client/
├── history.json                             # Session history
└── logs/
    ├── miracast-client.log                  # Application log
    └── miracast-service.log                 # Service mode log
```

---

## 8. Error Handling Strategy

| Layer | Strategy |
|-------|----------|
| Discovery | Errors caught in thread, emitted as `discovery-error` signal, logged |
| Casting | Errors caught in thread, emitted as `casting-error` signal, state reset |
| Config | Errors logged, fallback to default config on load failure |
| History | Malformed records skipped during load, logged |
| UI | Error dialogs shown to user via `Adw.MessageDialog` |
| Service | systemd `Restart=on-failure` with 5s delay |

---

## 9. Technology Rationale

| Choice | Rationale |
|--------|-----------|
| Python 3.12 | Rapid development, good GTK bindings, Ubuntu default |
| GTK 4 + libadwaita | Native GNOME look, modern widget toolkit |
| GStreamer | Industry-standard multimedia framework, hardware acceleration |
| GObject signals | Native integration with GTK event loop, type-safe |
| JSON config/history | Simple, human-readable, no database dependency |
| Systemd user service | Standard Linux service management, auto-restart |
| Wi-Fi Direct / wpa_supplicant | Standard Miracast connectivity layer |
