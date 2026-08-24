# Architecture — Ubuntu Miracast Client

> **Purpose:** This document captures the system architecture, design decisions, and implementation roadmap for AI agents and human contributors to build upon.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Ubuntu Miracast Client                         │
├─────────────────────────────────────────────────────────────────┤
│  UI Layer (GTK4 + libadwaita)                                    │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ MainWindow   │ │ DeviceSelect │ │ SourceSel  │ │ Settings │ │
│  └──────────────┘ └──────────────┘ └────────────┘ └──────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Application Layer                                               │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ App          │ │ CastManager  │ │ Discovery  │ │ Config   │ │
│  │ (Adw.App)    │ │              │ │            │ │          │ │
│  └──────────────┘ └──────────────┘ └────────────┘ └──────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Protocol Layer (TODO: RTSP + WFD negotiation)                   │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐              │
│  │ RTSP Server  │ │ WFD Session  │ │ Codec Neg  │              │
│  │ (M1-M16)     │ │ Manager      │ │            │              │
│  └──────────────┘ └──────────────┘ └────────────┘              │
├─────────────────────────────────────────────────────────────────┤
│  Transport Layer                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐              │
│  │ Wi-Fi Direct │ │ GStreamer    │ │ MPEG-TS/   │              │
│  │ (P2P via NM) │ │ Pipeline    │ │ RTP Stream │              │
│  └──────────────┘ └──────────────┘ └────────────┘              │
├─────────────────────────────────────────────────────────────────┤
│  System Layer                                                    │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐              │
│  │ NetworkMgr   │ │ wpa_suppl.   │ │ systemd    │              │
│  │ D-Bus API    │ │ (P2P)       │ │ (service)  │              │
│  └──────────────┘ └──────────────┘ └────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Module Responsibilities

| Module | File | Role | Dependencies |
|--------|------|------|--------------|
| **App** | `app.py` | Adw.Application lifecycle, component wiring | All modules |
| **Discovery** | `discovery.py` | P2P device scanning, WFD IE parsing | wpa_cli (subprocess) |
| **Capture** | `capture.py` | Screen/window enumeration via X11 | xprop, Gdk |
| **Casting** | `casting.py` | P2P connection + GStreamer streaming | gst-launch-1.0 (subprocess) |
| **Config** | `config.py` | JSON config in XDG_CONFIG_HOME | pathlib, json |
| **History** | `history.py` | Session records in XDG_DATA_HOME | pathlib, json |
| **Service** | `service.py` | systemd user service management | systemctl (subprocess) |
| **UI** | `ui/` | GTK4/libadwaita views | Gtk, Adw via PyGObject |

## Data Flow: Casting Session

```
1. User clicks "Cast"
   ↓
2. CastManager.start_casting(source, device)
   ↓
3. WifiDirectConnection.connect()
   → wpa_cli p2p_connect <addr> pbc go_intent=0
   → Wait for group interface (p2p-wlo1-N)
   → Get peer IP (ARP / DHCP)
   ↓
4. [MISSING] RTSP session setup (M1-M7)
   → Should: TCP connect to port 7236, negotiate codecs, get UDP port
   → Currently: Skipped entirely
   ↓
5. GStreamer pipeline (subprocess: gst-launch-1.0)
   → ximagesrc/pipewiresrc → x264enc → mpegtsmux → rtpmp2tpay → udpsink
   ↓
6. Stream sent directly to device IP (no RTSP negotiation)
   ↓
7. User clicks "Stop" → terminate GStreamer, p2p_group_remove
```

## Protocol Conformance Status

| WFD Requirement | Status | Notes |
|-----------------|--------|-------|
| Wi-Fi Direct P2P discovery | ✅ Implemented | Via wpa_cli p2p_find |
| WFD IE advertisement | ✅ Implemented | Sets wifi_display=1, wfd_subelem_set |
| WFD subelement parsing | ⚠️ Partial | Basic ID=0 parsing, no multi-subelement |
| P2P connection (GO negotiation) | ✅ Implemented | PBC mode, go_intent=0 |
| RTSP M1 (OPTIONS src→sink) | ❌ Missing | Critical gap |
| RTSP M2 (OPTIONS sink→src) | ❌ Missing | Critical gap |
| RTSP M3 (GET_PARAMETER) | ❌ Missing | Capability negotiation |
| RTSP M4 (SET_PARAMETER) | ❌ Missing | Session parameters |
| RTSP M5 (Trigger SETUP) | ❌ Missing | |
| RTSP M6 (SETUP) | ❌ Missing | Transport negotiation |
| RTSP M7 (PLAY) | ❌ Missing | Stream start |
| H.264 CBP encoding | ✅ Implemented | x264enc profile=baseline |
| MPEG-TS muxing | ✅ Implemented | mpegtsmux |
| RTP packetization | ✅ Implemented | rtpmp2tpay |
| LPCM audio | ❌ Missing | Mandatory per spec |
| Session teardown (M8-M9) | ❌ Missing | Just kills process |
| Keep-alive (M14) | ❌ Missing | Session will timeout |
| HDCP content protection | ❌ Not planned | Optional for source |
| UIBC | ❌ Not planned | Optional |

## Key Design Decisions

### Current (inherited/vibe-coded):

1. **Direct wpa_cli subprocess** — Simple but requires root, conflicts with NetworkManager
2. **GStreamer via gst-launch-1.0 subprocess** — Quick but no error handling, no dynamic control
3. **No RTSP** — Streams directly, breaking interop with real sinks
4. **sudo for privilege** — No polkit, no capability-based access
5. **setup.py packaging** — Legacy, should be pyproject.toml

### Target Architecture (see ADRs):

1. **NetworkManager D-Bus API** for P2P (polkit-mediated, no root needed)
2. **In-process GStreamer** via Gst Python bindings (proper bus messages, QoS)
3. **RTSP 1.0 session manager** implementing M1-M16 message flow
4. **Polkit + privileged helper** for operations NM can't handle
5. **PEP 621 pyproject.toml** with hatchling, Ruff, uv

## File Layout

```
ubuntu-miracast-client/
├── pyproject.toml              # PEP 621 metadata, all tool config
├── uv.lock                     # Lockfile (to be generated)
├── VERSION                     # Current version (to be replaced by hatch-vcs)
├── src/miracast_client/
│   ├── __init__.py             # Package root, version
│   ├── py.typed                # PEP 561 marker (to be added)
│   ├── app.py                  # Adw.Application entry point
│   ├── discovery.py            # Wi-Fi Direct P2P discovery
│   ├── capture.py              # Screen/window capture sources
│   ├── casting.py              # GStreamer streaming + P2P connection
│   ├── config.py               # Configuration (JSON, XDG)
│   ├── history.py              # Session history persistence
│   ├── service.py              # systemd user service
│   └── ui/                     # GTK4/libadwaita views
│       ├── main_window.py
│       ├── source_selector.py
│       ├── device_selector.py
│       ├── history_view.py
│       └── settings_view.py
├── tests/                      # pytest test suite
├── data/                       # Desktop/icon/service files
├── debian/                     # Debian packaging
├── docs/                       # Documentation
│   ├── ENGINEERING_ANALYSIS.md
│   ├── ARCHITECTURE.md         # This file
│   └── adr/                    # Architecture Decision Records
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # CI pipeline
│   │   ├── release.yml         # Release with SLSA/Sigstore
│   │   └── snapshot.yml        # Dev builds
│   ├── dependabot.yml
│   └── CODEOWNERS
├── SECURITY.md
├── CONTRIBUTING.md
└── CHANGELOG.md
```

## Agent Implementation Roadmap

### Phase 1: Packaging & Tooling (P0, ~2 hours)
- [ ] Migrate pyproject.toml to PEP 621 + hatchling
- [ ] Replace black/isort/flake8 with Ruff config
- [ ] Add PEP 735 dependency groups
- [ ] Generate uv.lock
- [ ] Remove setup.py, setup.cfg, .flake8, MANIFEST.in
- [ ] Add py.typed marker

### Phase 2: RTSP Protocol Layer (P1, ~8 hours)
- [ ] Create `src/miracast_client/rtsp/` module
- [ ] Implement RTSP 1.0 message parser (RFC 2326)
- [ ] Implement WFD-specific parameters
- [ ] M1-M2: OPTIONS exchange
- [ ] M3: GET_PARAMETER (capability query)
- [ ] M4: SET_PARAMETER (session config)
- [ ] M5-M7: SETUP/PLAY trigger flow
- [ ] M8-M9: TEARDOWN
- [ ] M14: Keep-alive
- [ ] Integration with CastManager

### Phase 3: Security Hardening (P1, ~4 hours)
- [ ] Create polkit policy file (`data/com.ubuntu.MiracastClient.policy`)
- [ ] Create privileged helper script
- [ ] Add input validation to WFD subelement parser
- [ ] Harden systemd service file
- [ ] Add AppArmor profile

### Phase 4: Architecture Migration (P3, ~12 hours)
- [ ] Migrate from wpa_cli subprocess to NetworkManager D-Bus API
- [ ] Migrate from gst-launch-1.0 subprocess to in-process GStreamer
- [ ] Fix D-Bus application ID (remove hyphens)
- [ ] Full XDG compliance with env var support
- [ ] Proper error hierarchy and handling

## Configuration Schema

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

**Location:** `$XDG_CONFIG_HOME/ubuntu-miracast-client/config.json` (default: `~/.config/ubuntu-miracast-client/config.json`)

## External Dependencies

| Dependency | Type | Purpose | Required |
|-----------|------|---------|----------|
| GTK 4 | System (GI) | UI framework | Yes |
| libadwaita | System (GI) | GNOME design patterns | Yes |
| GStreamer 1.0 | System (GI + CLI) | Video encoding/streaming | Yes |
| wpa_supplicant | System service | Wi-Fi Direct P2P | Yes |
| NetworkManager | System service | Network management (future) | Recommended |
| x264 | GStreamer plugin | H.264 encoding | Yes |
| x11-utils | System package | xprop for window enumeration | Yes (X11) |
| PipeWire | System service | Screen capture (Wayland) | Future |

## Testing Strategy

- **Unit tests:** Mock subprocess calls, test WFD parsing, config handling
- **Integration tests:** Cross-module (discovery → casting flow)
- **Protocol tests (TODO):** Mock RTSP server, test M1-M16 flow
- **Property-based tests (TODO):** Hypothesis for WFD hex parsing
- **E2E tests (TODO):** Full stack with mock sink device
