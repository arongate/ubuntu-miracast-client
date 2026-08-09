# API & Module Specification

## Ubuntu Miracast Client v1.0.0

**Document Version:** 1.0  
**Date:** 2026-08-09  
**Status:** Final

---

## 1. Module Overview

| Module | File | Purpose |
|--------|------|---------|
| `miracast_client` | `__init__.py` | Package root, version declaration |
| `miracast_client.app` | `app.py` | Application entry point and GTK app class |
| `miracast_client.discovery` | `discovery.py` | Wi-Fi Direct device discovery |
| `miracast_client.capture` | `capture.py` | Screen/window capture sources |
| `miracast_client.casting` | `casting.py` | Streaming session management |
| `miracast_client.history` | `history.py` | Session history persistence |
| `miracast_client.config` | `config.py` | Configuration management |
| `miracast_client.service` | `service.py` | Systemd service management |
| `miracast_client.ui.main_window` | `ui/main_window.py` | Main application window |
| `miracast_client.ui.source_selector` | `ui/source_selector.py` | Source selection widget |
| `miracast_client.ui.device_selector` | `ui/device_selector.py` | Device selection widget |
| `miracast_client.ui.history_view` | `ui/history_view.py` | History display widget |
| `miracast_client.ui.settings_view` | `ui/settings_view.py` | Settings widget |

---

## 2. Core Module APIs

### 2.1 `miracast_client.discovery`

#### Class: `MiracastDevice`

```python
@dataclass
class MiracastDevice:
    id: str                # Unique device identifier (P2P address)
    name: str              # Human-readable device name
    address: str           # Network address (MAC format)
    model: str             # Device model/type
    signal_strength: int   # Signal strength (0-100)
```

**Class Methods:**

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `from_wpa_supplicant_p2p_device` | `device_info: dict` | `MiracastDevice` | Factory from wpa_supplicant P2P data |

**Expected `device_info` keys:**
- `p2p_dev_addr` — P2P device address (fallback: UUID)
- `device_name` — Device name (fallback: "Unknown Device")
- `primary_dev_type` — Device model (fallback: "Unknown")
- `signal_level` — Signal strength as string (fallback: "0")

#### Class: `MiracastDiscovery(GObject.Object)`

**Constructor:** `MiracastDiscovery()`

**Public Methods:**

| Method | Parameters | Returns | Raises | Description |
|--------|-----------|---------|--------|-------------|
| `start_discovery()` | — | `None` | — | Start background P2P scan. No-op if already running. |
| `stop_discovery()` | — | `None` | — | Stop background scan and join thread. No-op if not running. |
| `get_devices()` | — | `List[MiracastDevice]` | — | Thread-safe snapshot of discovered devices. |

**GObject Signals:**

| Signal | Signature | Emission |
|--------|-----------|----------|
| `device-found` | `(MiracastDevice,)` | On main thread via idle_add |
| `device-lost` | `(str,)` | On main thread via idle_add |
| `discovery-started` | `()` | Synchronous from caller thread |
| `discovery-stopped` | `()` | Synchronous from caller thread |
| `discovery-error` | `(str,)` | On main thread via idle_add |

---

### 2.2 `miracast_client.capture`

#### Class: `CaptureSource`

```python
@dataclass
class CaptureSource:
    id: str           # Unique source identifier
    name: str         # Display name
    description: str  # Additional details
    icon: str         # Icon name (default: "video-display")
```

#### Class: `ScreenSource(CaptureSource)`

**Constructor:** `ScreenSource(monitor_num: int, display: Gdk.Display, monitor: Gdk.Monitor)`

**Properties:**
- `monitor_num: int` — Monitor index
- `display: Gdk.Display` — Display reference
- `monitor: Gdk.Monitor` — Monitor reference
- `width: int` — Screen width in pixels
- `height: int` — Screen height in pixels

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `start_capture()` | `str` | GStreamer pipeline: `ximagesrc display-name=... show-pointer=true ! video/x-raw,framerate=30/1 ! videoconvert ! queue` |

#### Class: `WindowSource(CaptureSource)`

**Constructor:** `WindowSource(window_id: int, title: str, app_name: str, icon_name: str = None)`

**Properties:**
- `window_id: int` — X11 window ID
- `app_name: str` — Application name

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `start_capture()` | `str` | GStreamer pipeline: `ximagesrc xid=... ! video/x-raw,framerate=30/1 ! videoconvert ! queue` |

#### Function: `get_available_sources`

```python
def get_available_sources(screen_only: bool = False, windows_only: bool = False) -> List[CaptureSource]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `screen_only` | `bool` | `False` | Only return screen sources |
| `windows_only` | `bool` | `False` | Only return window sources |

**Returns:** List of `CaptureSource` (mixed `ScreenSource` and `WindowSource`)

---

### 2.3 `miracast_client.casting`

#### Class: `CastingStats`

```python
@dataclass
class CastingStats:
    start_time: datetime       # Session start timestamp
    end_time: datetime = None  # Session end timestamp (None while active)
    duration: int = 0          # Duration in seconds
    data_transferred: int = 0  # Bytes transferred
    average_bitrate: float = 0 # Average bitrate in bps
    peak_bitrate: float = 0    # Peak bitrate in bps
    dropped_frames: int = 0    # Number of dropped frames
    errors: int = 0            # Number of errors
```

#### Class: `CastManager(GObject.Object)`

**Constructor:** `CastManager()`

**Public Methods:**

| Method | Parameters | Returns | Raises | Description |
|--------|-----------|---------|--------|-------------|
| `is_casting()` | — | `bool` | — | Check if a session is active |
| `start_casting(source, device)` | `source: CaptureSource, device: MiracastDevice` | `bool` | `RuntimeError` if already casting, `ValueError` if source/device is None | Start streaming session |
| `stop_casting()` | — | `CastingStats` | `RuntimeError` if not casting | Stop session and return final stats |

**GObject Signals:**

| Signal | Signature | Description |
|--------|-----------|-------------|
| `casting-started` | `(CaptureSource, MiracastDevice)` | Session started |
| `casting-stopped` | `(CastingStats,)` | Session stopped with final stats |
| `casting-error` | `(str,)` | Error occurred during session |
| `stats-updated` | `(CastingStats,)` | Stats updated (every ~1 second) |

---

### 2.4 `miracast_client.history`

#### Class: `SessionRecord`

```python
@dataclass
class SessionRecord:
    source: CaptureSource      # Casting source used
    device: MiracastDevice     # Target device
    stats: CastingStats        # Session statistics
    timestamp: datetime        # When session was recorded
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `dict` | Serialize to JSON-compatible dict |
| `from_dict(data)` | `SessionRecord` | Class method to deserialize from dict |

#### Class: `SessionHistory`

**Constructor:** `SessionHistory(history_path: str = None)`

- Default path: `~/.local/share/ubuntu-miracast-client/history.json`
- Creates parent directories on init
- Loads existing history from disk

**Public Methods:**

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `add_session(source, device, stats)` | `source: CaptureSource, device: MiracastDevice, stats: CastingStats` | `SessionRecord` | Add and persist a new session |
| `get_sessions()` | — | `List[SessionRecord]` | Get all session records |
| `clear()` | — | `None` | Clear all records and persist |

---

### 2.5 `miracast_client.config`

#### Class: `Config`

**Constructor:** `Config(config_path: str = None)`

- Default path: `~/.config/ubuntu-miracast-client/config.json`
- Creates parent directories on init
- Loads existing config or creates default

**Public Methods:**

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get(section, key, default)` | `section: str, key: str, default: Any = None` | `Any` | Get config value or default |
| `set(section, key, value)` | `section: str, key: str, value: Any` | `None` | Set config value (creates section if needed) |
| `save(config)` | `config: dict = None` | `None` | Save current config (or provided dict) to disk |

**Default Configuration Sections:**

- `general` — minimize_to_tray, start_minimized, log_level
- `streaming` — video_quality, frame_rate, audio_enabled
- `advanced` — discovery_timeout, connection_timeout

---

### 2.6 `miracast_client.service`

#### Class: `ServiceManager`

**Constants:**
- `SERVICE_NAME = "ubuntu-miracast-client"`
- `SERVICE_FILE = "ubuntu-miracast-client.service"`

**Constructor:** `ServiceManager()`

**Public Methods:**

| Method | Parameters | Returns | Raises | Description |
|--------|-----------|---------|--------|-------------|
| `is_service_enabled()` | — | `bool` | — | Check if service is enabled via systemctl |
| `is_service_running()` | — | `bool` | — | Check if service is active via systemctl |
| `enable_service()` | — | `None` | `RuntimeError` | Create service file, reload daemon, enable |
| `disable_service()` | — | `None` | `RuntimeError` | Stop, disable, remove file, reload |
| `start_service()` | — | `None` | `RuntimeError` | Start service (enables if needed) |
| `stop_service()` | — | `None` | `RuntimeError` | Stop service |

#### Function: `run_as_service()`

```python
def run_as_service() -> int
```

Runs the application in headless service mode with a GLib.MainLoop. Starts discovery automatically. Returns 0 on clean exit.

---

## 3. UI Module APIs

### 3.1 `miracast_client.ui.main_window`

#### Class: `MainWindow(Adw.ApplicationWindow)`

**Constructor:** `MainWindow(application, discovery, cast_manager, session_history)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `application` | `Adw.Application` | Parent application |
| `discovery` | `MiracastDiscovery` | Discovery service instance |
| `cast_manager` | `CastManager` | Cast manager instance |
| `session_history` | `SessionHistory` | History manager instance |

**Public Methods:**

| Method | Parameters | Description |
|--------|-----------|-------------|
| `show_page(page)` | `page: Page` | Navigate to specified page |

**Page Enum:**
- `SOURCE_SELECTION` — Source selection view
- `DEVICE_SELECTION` — Device discovery/selection view
- `CASTING` — Active casting view
- `HISTORY` — Session history view
- `SETTINGS` — Settings view

**Actions (Gio.SimpleAction):**
- `settings` — Navigate to settings page
- `about` — Show about dialog
- `new-cast` — Start new casting flow
- `stop-cast` — Stop active casting session

---

### 3.2 `miracast_client.ui.source_selector`

#### Class: `SourceSelector(Gtk.Box)`

**Constructor:** `SourceSelector()`

**GObject Signals:**

| Signal | Signature | Description |
|--------|-----------|-------------|
| `source-selected` | `(CaptureSource,)` | Emitted when user selects a source and clicks Select |

**Behavior:**
- Displays radio buttons for "Entire Screen" / "Application Window"
- Lists available sources based on selected type
- Uses `Gtk.ListView` with factory pattern
- Select button enabled only when an item is selected

---

### 3.3 `miracast_client.ui.device_selector`

#### Class: `DeviceSelector(Gtk.Box)`

**Constructor:** `DeviceSelector(discovery: MiracastDiscovery)`

**GObject Signals:**

| Signal | Signature | Description |
|--------|-----------|-------------|
| `device-selected` | `(MiracastDevice,)` | Emitted when user connects to a device |

**Public Methods:**

| Method | Description |
|--------|-------------|
| `start_discovery()` | Clear list, start spinner, begin discovery |
| `stop_discovery()` | Stop spinner, halt discovery |

**Behavior:**
- Displays spinner and status label during discovery
- Shows device name, model, signal strength in list
- Refresh button restarts discovery
- Connect button enabled only when device is selected

---

### 3.4 `miracast_client.ui.history_view`

#### Class: `HistoryView(Gtk.Box)`

**Constructor:** `HistoryView(session_history: SessionHistory)`

**GObject Signals:**

| Signal | Signature | Description |
|--------|-----------|-------------|
| `new-cast` | `()` | Emitted when user clicks "New Cast" button |

**Public Methods:**

| Method | Description |
|--------|-------------|
| `refresh()` | Reload session list from history (newest first) |

**Behavior:**
- Shows session list with source→device, duration, data, timestamp
- Shows detail panel when session selected (source, destination, start time, duration, data transferred, average bitrate)
- "New Cast" button emits signal to start a new session

---

### 3.5 `miracast_client.ui.settings_view`

#### Class: `SettingsView(Gtk.Box)`

**Constructor:** `SettingsView()`

**Settings Groups:**

| Group | Controls |
|-------|----------|
| General | Minimize to tray (switch), Start minimized (switch), Log level (dropdown) |
| Streaming | Video quality (dropdown), Frame rate (dropdown), Audio enabled (switch) |
| Service | Run as service (switch), Status label, Start/Stop buttons |
| Advanced | Discovery timeout (spin), Connection timeout (spin), Clear history button |

**Behavior:**
- Reads current values from `Config` and `ServiceManager` on init
- Save button writes all values to Config and calls `config.save()`
- Service switch toggles enable/disable with error handling
- Clear history shows confirmation dialog before clearing

---

## 4. Application Entry Point

### 4.1 `miracast_client.app`

#### Class: `MiracastClientApp(Adw.Application)`

**Application ID:** `com.ubuntu.miracast-client`

**Constructor:** `MiracastClientApp()`

Instantiates: Config, MiracastDiscovery, CastManager, SessionHistory, ServiceManager

**Signals:**
- `activate` → Creates and presents MainWindow

#### Function: `main()`

```python
def main() -> int
```

- If `sys.argv[1] == "--service"` → calls `run_as_service()`
- Otherwise → creates `MiracastClientApp()` and runs GTK main loop
- Returns exit code

**Console Script Entry Point:** `ubuntu-miracast-client = miracast_client.app:main`

---

## 5. Inter-Module Dependencies

```
app.py
├── config.Config
├── discovery.MiracastDiscovery
├── casting.CastManager
├── history.SessionHistory
├── service.ServiceManager
└── ui.main_window.MainWindow
    ├── ui.source_selector.SourceSelector
    │   └── capture.get_available_sources
    ├── ui.device_selector.DeviceSelector
    │   └── discovery.MiracastDiscovery
    ├── ui.history_view.HistoryView
    │   └── history.SessionHistory
    └── ui.settings_view.SettingsView
        ├── config.Config
        └── service.ServiceManager
```

---

## 6. Logging

All modules use `logging.getLogger(__name__)` with the following configuration:

- **Format:** `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Handlers:** FileHandler (to `~/.local/share/ubuntu-miracast-client/logs/`) + StreamHandler (stderr)
- **Default Level:** INFO (configurable via settings)
