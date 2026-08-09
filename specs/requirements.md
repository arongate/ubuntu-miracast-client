# Requirements Specification

## Ubuntu Miracast Client v1.0.0

**Document Version:** 1.0  
**Date:** 2026-08-09  
**Status:** Final

---

## 1. Introduction

### 1.1 Purpose

This document specifies the functional and non-functional requirements for the Ubuntu Miracast Client application, a desktop tool enabling Ubuntu 24.04 LTS users to wirelessly cast their screen or application windows to Miracast-compatible receivers.

### 1.2 Scope

The application provides screen and window casting over the Miracast protocol using Wi-Fi Direct, with a modern GTK 4 user interface and optional system service mode.

### 1.3 Target Platform

- Ubuntu 24.04 LTS
- Python 3.10+ (recommended 3.12)
- GNOME desktop environment (primary), other GTK-compatible desktops (secondary)

---

## 2. Functional Requirements

### 2.1 Device Discovery

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-D01 | The system SHALL discover Miracast-compatible devices on the local network using Wi-Fi Direct P2P via wpa_supplicant | Must |
| FR-D02 | The system SHALL emit events when devices are found or lost | Must |
| FR-D03 | The system SHALL display device name, model, and signal strength for each discovered device | Must |
| FR-D04 | The system SHALL run discovery in a background thread to avoid blocking the UI | Must |
| FR-D05 | The system SHALL support starting and stopping discovery on demand | Must |
| FR-D06 | The system SHALL update device signal strength in real-time during discovery | Should |
| FR-D07 | The system SHALL apply a configurable discovery timeout (default: 10 seconds) | Should |

### 2.2 Screen/Window Capture

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-C01 | The system SHALL enumerate available screens/monitors for capture | Must |
| FR-C02 | The system SHALL enumerate open application windows for capture | Must |
| FR-C03 | The system SHALL display screen resolution and manufacturer information | Must |
| FR-C04 | The system SHALL display window title and application name | Must |
| FR-C05 | The system SHALL generate GStreamer pipeline strings for screen capture (ximagesrc) | Must |
| FR-C06 | The system SHALL generate GStreamer pipeline strings for window capture (ximagesrc with xid) | Must |
| FR-C07 | The system SHALL support 30 fps default frame rate for capture | Must |

### 2.3 Casting/Streaming

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-S01 | The system SHALL start a casting session from a selected source to a selected device | Must |
| FR-S02 | The system SHALL stop the current casting session on demand | Must |
| FR-S03 | The system SHALL collect real-time session statistics (duration, data transferred, bitrate, dropped frames, errors) | Must |
| FR-S04 | The system SHALL emit events for casting start, stop, error, and stats updates | Must |
| FR-S05 | The system SHALL prevent starting a new session while one is already active | Must |
| FR-S06 | The system SHALL validate that both source and device are provided before casting | Must |
| FR-S07 | The system SHALL support configurable video quality (Low: 2 Mbps, Medium: 5 Mbps, High: 10 Mbps, Very High: 20 Mbps) | Must |
| FR-S08 | The system SHALL support configurable frame rates (15, 24, 30, 60 fps) | Should |
| FR-S09 | The system SHALL support optional audio streaming (128 kbps AAC) | Should |

### 2.4 Session History

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-H01 | The system SHALL record each completed casting session (source, device, statistics, timestamp) | Must |
| FR-H02 | The system SHALL persist session history to disk in JSON format | Must |
| FR-H03 | The system SHALL load session history from disk on startup | Must |
| FR-H04 | The system SHALL provide an interface to retrieve all session records | Must |
| FR-H05 | The system SHALL provide an interface to clear all session history | Must |
| FR-H06 | The system SHALL display sessions in reverse chronological order | Should |

### 2.5 Configuration

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-CF01 | The system SHALL persist configuration in JSON format at `~/.config/ubuntu-miracast-client/config.json` | Must |
| FR-CF02 | The system SHALL create default configuration if none exists | Must |
| FR-CF03 | The system SHALL support sections: general, streaming, advanced | Must |
| FR-CF04 | The system SHALL provide get/set interface for configuration values | Must |
| FR-CF05 | The system SHALL support configurable log level (DEBUG, INFO, WARNING, ERROR) | Should |
| FR-CF06 | The system SHALL support minimize-to-tray and start-minimized options | Should |

### 2.6 System Service

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-SV01 | The system SHALL support running as a systemd user service | Should |
| FR-SV02 | The system SHALL provide enable/disable/start/stop service controls | Should |
| FR-SV03 | The system SHALL auto-generate the systemd service file | Should |
| FR-SV04 | The system SHALL check service status (enabled/running) | Should |
| FR-SV05 | The system SHALL support `--service` CLI flag to run in service mode | Should |

### 2.7 User Interface

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-UI01 | The system SHALL provide a GTK 4 / libadwaita interface | Must |
| FR-UI02 | The system SHALL provide a source selection page with screen/window radio toggle | Must |
| FR-UI03 | The system SHALL provide a device discovery/selection page with spinner and device list | Must |
| FR-UI04 | The system SHALL provide a session history page with detail view | Must |
| FR-UI05 | The system SHALL provide a settings page with all configurable options | Must |
| FR-UI06 | The system SHALL use stack-based navigation with slide transitions | Must |
| FR-UI07 | The system SHALL provide a menu with Settings and About options | Should |
| FR-UI08 | The system SHALL minimize window when casting starts | Should |
| FR-UI09 | The system SHALL display a status bar showing current state | Should |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-P01 | Device discovery SHALL complete initial scan within the configured timeout (default 10s) | Must |
| NFR-P02 | The UI SHALL remain responsive during background operations (discovery, casting) | Must |
| NFR-P03 | Statistics SHALL update at least once per second during casting | Should |
| NFR-P04 | Streaming latency SHOULD be below 150ms for local network conditions | Should |

### 3.2 Reliability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-R01 | The system SHALL handle connection failures gracefully without crashing | Must |
| NFR-R02 | The system SHALL recover from streaming errors (dropped frames, network interruptions) | Must |
| NFR-R03 | The system SHALL validate inputs before operations (source, device not null) | Must |
| NFR-R04 | The system SHALL log errors with full context for debugging | Must |
| NFR-R05 | The service mode SHALL restart on failure (RestartSec=5s) | Should |

### 3.3 Security

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-S01 | Wi-Fi Direct connections SHALL use WPA2 security | Must |
| NFR-S02 | Configuration files SHALL be stored with user-only read/write permissions | Should |
| NFR-S03 | The system SHALL validate all input data before processing | Must |

### 3.4 Usability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-U01 | The application SHALL follow GNOME Human Interface Guidelines | Should |
| NFR-U02 | The UI SHALL provide clear feedback for all user actions (spinners, status messages) | Must |
| NFR-U03 | Error messages SHALL be user-friendly and actionable | Must |

### 3.5 Maintainability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-M01 | The codebase SHALL follow modular architecture with clear separation of concerns | Must |
| NFR-M02 | The code SHALL be formatted with Black (line-length=100) and isort | Should |
| NFR-M03 | The code SHALL pass flake8 linting | Should |
| NFR-M04 | Test coverage SHALL be maintained with pytest | Must |

### 3.6 Portability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-PT01 | The application SHALL be installable via Debian package (.deb) | Must |
| NFR-PT02 | The application SHALL be installable via pip (Python package) | Must |
| NFR-PT03 | The application SHALL support Python 3.10, 3.11, and 3.12 | Must |

---

## 4. Constraints

| ID | Constraint |
|----|-----------|
| C01 | Target platform is Ubuntu 24.04 LTS only |
| C02 | Requires network connection (5GHz Wi-Fi preferred for optimal performance) |
| C03 | Depends on system-level wpa_supplicant for Wi-Fi Direct P2P |
| C04 | Requires GStreamer runtime for media capture and encoding |
| C05 | GTK 4 and libadwaita must be available on the system |
| C06 | Hardware-accelerated encoding availability depends on GPU drivers |

---

## 5. Dependencies

### 5.1 Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyGObject | >=3.42.0 | GTK 4 / GLib Python bindings |
| pycairo | >=1.20.0 | Cairo rendering support |
| gstreamer-python | >=1.0.0 | GStreamer pipeline control |
| GTK 4 | System | UI framework |
| libadwaita | System | GNOME design patterns |
| GStreamer | System | Media capture and encoding |
| wpa_supplicant | System | Wi-Fi Direct P2P discovery |

### 5.2 Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=7.0.0 | Test framework |
| pytest-cov | >=4.0.0 | Coverage reporting |
| black | >=23.0.0 | Code formatting |
| isort | >=5.12.0 | Import sorting |
| flake8 | >=6.0.0 | Linting |
| mypy | >=1.0.0 | Type checking |

---

## 6. Future Enhancements (Out of Scope for v1.0)

- Support for additional protocols (AirPlay, Chromecast)
- Advanced encoding profiles and custom encoding options
- Multi-display simultaneous casting
- Remote control via mobile devices
- Deeper GNOME desktop integration
