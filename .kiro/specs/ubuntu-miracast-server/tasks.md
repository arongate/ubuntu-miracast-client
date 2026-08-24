# Implementation Plan: Ubuntu Miracast Server

## Overview

Build the Ubuntu Miracast Server as a Python 3.12 GTK 4 desktop application that receives incoming Miracast streams over Wi-Fi Direct. The implementation follows the modular architecture defined in the design document, mirroring the existing ubuntu-miracast-client patterns. Tasks are ordered by dependency: project scaffolding → data models → core modules (config, history, advertiser, connection, receiver) → UI layer → service mode → packaging → integration testing.

## Tasks

- [x] 1. Project scaffolding and build configuration
  - [x] 1.1 Create project directory structure and build files
    - Create `ubuntu-miracast-server/` directory with `src/miracast_server/`, `tests/`, `debian/` subdirectories
    - Create `pyproject.toml` with build-system, black, isort, mypy, pytest configuration (matching client patterns)
    - Create `setup.cfg` and `setup.py` with package metadata, entry points (`ubuntu-miracast-server` console script pointing to `miracast_server.app:main`)
    - Create `Makefile` with targets: lint, format, test, coverage, install, clean
    - Create `src/miracast_server/__init__.py` with package version
    - Create `src/miracast_server/ui/__init__.py`
    - Create `tests/__init__.py`
    - _Requirements: Design Project Structure_

  - [x] 1.2 Create core utility and shared helpers
    - Create `src/miracast_server/utils.py` with `_find_p2p_interface()` and `_run_wpa_cli()` helper functions (matching client's pattern)
    - Implement parameter validation for wpa_cli arguments (alphanumeric, colons, hyphens, underscores only)
    - Implement list-based subprocess calls (no shell=True)
    - _Requirements: 10.6_

- [x] 2. Data models with validation
  - [x] 2.1 Implement IncomingConnection data model
    - Create `src/miracast_server/models.py`
    - Implement `IncomingConnection` dataclass with fields: peer_address, peer_ip, peer_name, group_interface, our_ip, connected_at, go_role
    - Implement MAC address validation (XX:XX:XX:XX:XX:XX format, case-insensitive hex)
    - Implement IPv4 address validation (dotted-decimal, octets 0-255)
    - Implement group_interface validation (2-16 characters, non-empty)
    - Implement connected_at validation (not in the future)
    - Raise ValueError with field name and reason on validation failure
    - _Requirements: 13.1, 13.2, 13.3, 13.7_

  - [x] 2.2 Implement ReceiverStats and SourceInfo data models
    - Add `ReceiverStats` dataclass with validation: duration >= 0, data_received >= 0, frames_decoded >= frames_dropped >= 0
    - Add `SourceInfo` dataclass with fields: name, address, model, resolution, codec, audio_codec
    - Add `ServerSessionRecord` dataclass with to_dict/from_dict serialization
    - Implement ISO 8601 datetime serialization and None → null handling
    - Implement from_dict error handling: raise exception on missing fields or unparseable values without creating partial objects
    - _Requirements: 13.4, 13.5, 13.6, 13.7, 7.1, 7.2, 7.3, 7.4_

  - [ ]* 2.3 Write property tests for data model validation (Property 17)
    - **Property 17: IncomingConnection Field Validation**
    - Test MAC format acceptance/rejection with hypothesis-generated strings
    - Test IPv4 validation with arbitrary strings and valid/invalid octets
    - Test group_interface length constraints
    - **Validates: Requirements 13.1, 13.2, 13.3, 13.7**

  - [ ]* 2.4 Write property tests for ReceiverStats invariants (Property 18)
    - **Property 18: ReceiverStats Invariants**
    - Test that construction enforces duration >= 0, data_received >= 0, frames_decoded >= frames_dropped >= 0
    - Test that invalid values raise ValueError
    - **Validates: Requirements 13.4, 13.5, 13.6, 13.7**

  - [ ]* 2.5 Write property tests for session record serialization (Property 9, Property 10)
    - **Property 9: Session Record Serialization Round-Trip**
    - Generate arbitrary ServerSessionRecord objects and verify to_dict → from_dict roundtrip equality
    - **Property 10: Session Record Deserialization Error Handling**
    - Generate dictionaries with missing/invalid fields and verify exceptions are raised
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

- [x] 3. Configuration management
  - [x] 3.1 Implement ConfigManager
    - Create `src/miracast_server/config.py`
    - Implement `ServerConfig` class with get/set/save methods
    - Implement default configuration generation with all sections (general, streaming, network, service)
    - Implement JSON file persistence at `~/.config/ubuntu-miracast-server/config.json`
    - Implement file creation with 0600 permissions
    - Implement value validation: rtsp_port 1024-65535, go_intent 0-15, connection_timeout 1-120
    - Handle malformed JSON on load: log warning, use defaults
    - Handle disk write failures: retain in memory, log error
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 10.5_

  - [ ]* 3.2 Write property tests for configuration (Property 14, Property 15)
    - **Property 14: Configuration Round-Trip**
    - Test set then get returns same value for valid key-value pairs
    - Test get with default for missing keys does not modify file
    - **Property 15: Configuration Value Validation**
    - Test rtsp_port, go_intent, connection_timeout boundary rejection/acceptance
    - **Validates: Requirements 8.3, 8.5, 8.6**

- [~] 4. Session history persistence
  - [x] 4.1 Implement ServerSessionHistory
    - Create `src/miracast_server/history.py`
    - Implement `ServerSessionHistory` class with add_session, get_sessions, clear methods
    - Persist to `~/.local/share/ubuntu-miracast-server/history.json` with 0600 permissions
    - Enforce maximum 500 records (discard oldest on overflow)
    - Return sessions sorted by timestamp descending
    - Handle missing/invalid history file: initialize empty list
    - Handle disk write failures: retain in memory, emit persist-error
    - Record sessions from both stream-stopped and stream-error signals
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.10, 10.5_

  - [ ]* 4.2 Write property tests for history (Property 11, Property 12)
    - **Property 11: History Maximum Records Enforcement**
    - Test that adding records beyond 500 discards oldest, resulting in exactly 500
    - **Property 12: History Sort Order**
    - Generate records with distinct timestamps and verify descending sort order
    - **Validates: Requirements 6.3, 6.6**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. WFD Sink Advertiser
  - [x] 6.1 Implement MiracastAdvertiser
    - Create `src/miracast_server/advertiser.py`
    - Implement `MiracastAdvertiser(GObject.Object)` with GObject signals: advertising-started, advertising-stopped, advertising-error
    - Implement start_advertising: find P2P interface, enable wifi_display, set WFD subelements (Primary Sink, RTSP port, session available), set device_name, p2p_listen
    - Implement WFD subelement encoding: device type bits for Primary Sink, hex port encoding
    - Implement stop_advertising: p2p_stop_find, emit advertising-stopped
    - Implement idempotence: ignore duplicate start_advertising calls when already advertising
    - Implement interface auto-detection and user-specified interface validation
    - Handle errors at each step: emit advertising-error with descriptive message
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 12.1, 12.5_

  - [ ]* 6.2 Write property tests for WFD subelement generation (Property 1, Property 2)
    - **Property 1: WFD Subelement Generation**
    - For any valid RTSP port (1024-65535), verify hex encoding at correct offset, device type bits = Primary Sink, session availability = available
    - **Property 2: Advertising Idempotence**
    - Verify that calling start_advertising when already advertising does not change state, emit signals, or issue commands
    - **Validates: Requirements 1.1, 1.2, 1.10**

  - [ ]* 6.3 Write unit tests for Advertiser lifecycle
    - Test start/stop transitions with mocked wpa_cli
    - Test interface detection failure handling
    - Test p2p_listen failure handling
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

- [x] 7. Wi-Fi Direct Connection Handler
  - [x] 7.1 Implement ConnectionHandler
    - Create `src/miracast_server/connection.py`
    - Implement `ConnectionHandler(GObject.Object)` with GObject signals: connection-received, connection-lost, connection-error
    - Implement start_listening: spawn daemon thread running wpa_cli event monitor
    - Implement P2P-GO-NEG-REQUEST handling: auto-accept with PBC + configured go_intent, or prompt user
    - Implement P2P-GROUP-STARTED parsing: extract group_interface, peer_ip, peer_mac, peer_name, our_ip
    - Implement P2P-GROUP-REMOVED handling: emit connection-lost
    - Implement single-connection invariant: ignore new requests while connection is active
    - Implement connection timeout: 30 seconds after p2p_connect, emit connection-error if no group formed
    - Implement disconnect_peer: p2p_group_remove, clear active connection
    - Implement stop_listening: set running flag, join thread within 5 seconds
    - All signal emissions via GLib.idle_add
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 14.1, 14.3, 14.6, 15.2_

  - [ ]* 7.2 Write property tests for P2P event parsing (Property 3, Property 4)
    - **Property 3: P2P Event Parsing**
    - Generate valid P2P-GROUP-STARTED event strings with varying fields and verify correct extraction into IncomingConnection
    - **Property 4: Single Active Session Invariant**
    - Verify that while receiving, additional P2P-GO-NEG-REQUEST events are ignored
    - **Validates: Requirements 2.3, 2.4, 2.6, 16.1, 16.2**

  - [ ]* 7.3 Write unit tests for ConnectionHandler
    - Test auto-accept flow with mocked wpa_cli
    - Test timeout handling
    - Test disconnect_peer cleanup
    - _Requirements: 2.1, 2.7, 2.8, 2.9_

- [x] 8. RTSP Session Handler and Receiver
  - [x] 8.1 Implement RTSP message parsing and generation
    - Create `src/miracast_server/rtsp.py` with RTSP request/response parsing utilities
    - Implement RTSP request parser: method, URI, CSeq, content-length, headers, body
    - Implement RTSP response builder: status code, CSeq echo, headers, body
    - Implement WFD parameter parsing: video codec spec, resolution, RTP transport port
    - Implement request validation: size limits (8192 header, 65536 body), required headers, malformed detection
    - Implement WFD capability response generation (supported codecs, resolutions, audio formats)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.8, 3.9, 3.11, 10.3, 10.7_

  - [x] 8.2 Implement MiracastReceiver core
    - Create `src/miracast_server/receiver.py`
    - Implement `MiracastReceiver(GObject.Object)` with GObject signals: stream-started, stream-stopped, stream-error, stats-updated, resolution-changed
    - Implement start_receiving: bind RTSP socket to P2P interface IP (not 0.0.0.0), start RTSP handler thread
    - Implement RTSP session loop: OPTIONS, GET_PARAMETER, SET_PARAMETER, SETUP, PLAY, TEARDOWN handling
    - Implement connection timeout: close socket if no RTSP within 30 seconds
    - Implement stop_receiving: stop pipeline, close sockets, join threads, return ReceiverStats
    - Implement session teardown: pipeline NULL, socket close, emit stream-stopped
    - All signal emissions via GLib.idle_add
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 10.2, 14.4, 14.6, 15.1, 16.3_

  - [x] 8.3 Implement GStreamer receive pipeline construction
    - Implement pipeline builder: udpsrc (2MB buffer, negotiated port) → rtpmp2tdepay → tsdemux → h264parse → decoder → videoconvert → sink
    - Implement codec whitelist validation: "H264" for video, "AAC" for audio (block pipeline on invalid codec)
    - Implement port validation: integer in range 1024-65535
    - Implement GUI mode sink: gtk4paintablesink
    - Implement headless mode sink: fakesink sync=true
    - Implement hardware decode detection: try vaapidecodebin/nvh264dec, fallback to avdec_h264
    - Implement audio pipeline branch: aacparse → avdec_aac → audioconvert → pulsesink
    - Configure queue bounds: max-size-buffers=200, max-size-bytes=10485760, max-size-time=1000000000
    - Configure low-latency flags on decoder, zero-buffering on demuxer
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.8, 4.9, 10.4, 11.2, 11.3, 11.4_

  - [x] 8.4 Implement stream monitoring and error recovery
    - Implement stream loss detection: no RTP packets for 5 seconds → pipeline NULL, emit stream-error
    - Implement pipeline state transition timeout: 5 seconds to PLAYING or emit error
    - Implement hardware decode fallback: on pipeline error, rebuild with avdec_h264
    - Implement stats collection thread: 1-second interval, query pipeline for resolution/bitrate/frames
    - Implement peak bitrate tracking: update on each stats interval when new max observed
    - Implement frame drop rate monitoring: emit warning when drops > 5% over 10-second window
    - Implement RTSP error recovery: keep connection open 10 seconds for renegotiation
    - _Requirements: 4.6, 4.7, 4.10, 4.11, 6.8, 6.9, 11.1, 11.6, 11.7, 12.2, 12.3, 12.4, 12.6, 14.5, 16.4_

  - [ ]* 8.5 Write property tests for RTSP and pipeline (Property 5, Property 6, Property 7, Property 8)
    - **Property 5: RTSP CSeq Echo**
    - For any CSeq integer (0 to 2^31-1), verify response contains matching CSeq
    - **Property 6: RTSP Malformed Request Rejection**
    - Generate invalid RTSP byte strings and verify appropriate error codes without crash
    - **Property 7: WFD Parameter Parsing**
    - Generate valid WFD SET_PARAMETER bodies and verify correct field extraction
    - **Property 8: GStreamer Pipeline Construction Safety**
    - For any valid port (1024-65535) and whitelisted codec, verify pipeline contains all required elements
    - **Validates: Requirements 3.2, 3.4, 3.8, 3.11, 4.1, 10.3, 10.4, 10.7**

  - [ ]* 8.6 Write property test for peak bitrate tracking (Property 13)
    - **Property 13: Peak Bitrate is Maximum**
    - Generate sequences of bitrate samples and verify peak_bitrate equals the maximum
    - **Validates: Requirement 6.9**

  - [ ]* 8.7 Write unit tests for Receiver lifecycle
    - Test RTSP negotiation flow with mock client
    - Test pipeline construction for various codec/port combinations
    - Test timeout and error scenarios
    - Test stop_receiving cleanup
    - _Requirements: 3.5, 3.6, 3.7, 3.10, 4.10, 15.1_

- [x] 9. Checkpoint - Ensure all core module tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. GTK 4 UI layer
  - [x] 10.1 Implement MainWindow and application entry point
    - Create `src/miracast_server/app.py` with `MiracastServerApp(Adw.Application)` and `main()` function
    - Implement CLI argument parsing: --service, --name, --help
    - Create `src/miracast_server/ui/main_window.py` with `MainWindow(Adw.ApplicationWindow)`
    - Implement HeaderBar with title, status indicator, and menu button (Settings, About)
    - Implement Gtk.Stack navigation: Display, Sessions, Settings pages
    - Implement bottom bar with status label and navigation buttons
    - Wire up core components: Advertiser, ConnectionHandler, Receiver, History, Config
    - Connect GObject signals between components
    - _Requirements: 5.1_

  - [x] 10.2 Implement DisplayView
    - Create `src/miracast_server/ui/display_view.py`
    - Implement idle state: centered icon + "Waiting for Miracast source..." text + device name
    - Implement connected state: "Source connected, waiting for stream..." with source name
    - Implement receiving state: Gtk.Picture bound to gtk4paintablesink paintable
    - Implement fullscreen management: auto-fullscreen on stream start (configurable), F11/double-click toggle, Escape exit
    - Implement floating overlay controls in fullscreen: pause, disconnect, fullscreen toggle (show on mouse move, auto-hide after 3 seconds)
    - Implement return to idle on stream stop or error (exit fullscreen if active)
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 11.5_

  - [x] 10.3 Implement SessionsView
    - Create `src/miracast_server/ui/sessions_view.py`
    - Display history of past sessions: source name, date, duration, resolution, data received
    - Implement clear history button with confirmation
    - Bind to ServerSessionHistory for data
    - _Requirements: 6.1, 6.6, 6.7_

  - [x] 10.4 Implement SettingsView
    - Create `src/miracast_server/ui/settings_view.py`
    - Implement settings groups: General (device_name, start_minimized, fullscreen_on_stream, log_level), Streaming (rtsp_port, audio_enabled, max_resolution, preferred_codec), Network (go_intent, connection_timeout, auto_accept), Service (enabled, virtual_display, idle_timeout)
    - Bind to ServerConfig for persistence
    - Implement input validation feedback (reject invalid values per requirement 8.6)
    - _Requirements: 8.1, 8.2, 8.3, 8.6_

- [x] 11. Systemd service mode
  - [x] 11.1 Implement ServerServiceManager and headless mode
    - Create `src/miracast_server/service.py`
    - Implement `ServerServiceManager` class: enable/disable/start/stop service
    - Implement service file generation: install to ~/.config/systemd/user/, daemon-reload
    - Implement rollback on failure: no inconsistent state (file without reload, or reload without file)
    - Implement `run_as_service()`: GLib main loop with Advertiser + ConnectionHandler, no GTK, fakesink video
    - Implement idle_timeout: exit with code 0 after configured inactivity (range 1-86400, 0 = disabled)
    - Implement sync configuration for fakesink in service mode (sync=true default, sync=false with high_throughput_mode)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

  - [ ]* 11.2 Write unit tests for ServiceManager
    - Test service file generation and installation
    - Test enable/disable lifecycle with mocked systemctl
    - Test rollback on failure
    - Test idle timeout behavior
    - _Requirements: 9.4, 9.5, 9.6, 9.7, 9.8_

- [x] 12. Application lifecycle and signal shutdown
  - [x] 12.1 Implement graceful shutdown and resource cleanup
    - Implement SIGTERM/SIGINT handling: stop Receiver → ConnectionHandler → Advertiser (initiation order)
    - Implement window close handler: same shutdown sequence
    - Set running flags before joining threads; join with 5-second timeouts
    - Log failures on thread join timeout, continue shutdown
    - Implement session recording on stream-error (partial stats)
    - Implement automatic return to advertising/listening after stream ends
    - _Requirements: 14.6, 14.7, 15.1, 15.2, 15.3, 15.4, 15.5, 12.2, 12.3, 16.3, 16.4_

  - [ ]* 12.2 Write unit tests for shutdown and cleanup
    - Test orderly shutdown sequence with mocked components
    - Test thread join timeout handling
    - Test session recording on error
    - _Requirements: 15.4, 15.5_

- [x] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. wpa_cli parameter security and validation
  - [x] 14.1 Implement security validation in utils
    - Implement wpa_cli parameter allowlist validation in `utils.py` (alphanumeric, colons, hyphens, underscores)
    - Implement codec whitelist check for pipeline construction ("H264", "AAC")
    - Implement RTSP request size limit enforcement (8192 bytes header, 65536 bytes body)
    - Ensure all subprocess calls use list format (no shell=True)
    - _Requirements: 10.1, 10.3, 10.4, 10.6, 10.7_

  - [ ]* 14.2 Write property test for wpa_cli parameter validation (Property 16)
    - **Property 16: wpa_cli Parameter Validation**
    - Generate arbitrary strings and verify acceptance iff all characters are alphanumeric, colon, hyphen, or underscore
    - **Validates: Requirement 10.6**

- [x] 15. Debian packaging
  - [x] 15.1 Create Debian packaging files
    - Create `debian/control` with package metadata, dependencies (python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1, gir1.2-gst-plugins-base-1.0, gstreamer1.0-plugins-good, gstreamer1.0-plugins-bad, wpa-supplicant)
    - Create `debian/rules` with dh_python3 build
    - Create `debian/changelog`, `debian/copyright`
    - Create `debian/ubuntu-miracast-server.desktop` desktop entry
    - Create `debian/ubuntu-miracast-server.install` file mapping
    - _Requirements: Design Dependencies_

- [x] 16. Integration wiring and end-to-end flow
  - [x] 16.1 Wire all components together in app.py
    - Connect Advertiser signals to UI status updates
    - Connect ConnectionHandler.connection-received → Receiver.start_receiving
    - Connect Receiver.stream-started → DisplayView transition to receiving state
    - Connect Receiver.stream-stopped → History.add_session + return to idle
    - Connect Receiver.stream-error → History.add_session (partial) + return to advertising
    - Connect stats-updated → UI stats display
    - Implement single-session invariant: reject connections while streaming (GO negotiation rejection with reason)
    - _Requirements: 16.1, 16.2, 16.3, 12.3, 14.1_

  - [ ]* 16.2 Write integration tests
    - Test full flow: advertiser → connection → RTSP negotiation → pipeline start → teardown (with mocked wpa_supplicant and test video source)
    - Test error recovery flow: stream loss → history record → return to advertising
    - Test service mode startup and idle timeout
    - _Requirements: 12.2, 12.3, 16.3, 16.4_

- [x] 17. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties defined in the design document (18 properties)
- Unit tests validate specific examples and edge cases
- The implementation language is Python 3.12 as specified in the design document
- The project mirrors the existing ubuntu-miracast-client architecture and conventions
- All GObject signal emissions must use GLib.idle_add for thread safety
- All wpa_cli subprocess calls must use list format (no shell=True)
- Configuration and history files use 0600 permissions

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1"] },
    { "id": 3, "tasks": ["2.3", "2.4", "2.5", "3.2", "4.1"] },
    { "id": 4, "tasks": ["4.2", "6.1"] },
    { "id": 5, "tasks": ["6.2", "6.3", "7.1"] },
    { "id": 6, "tasks": ["7.2", "7.3", "8.1"] },
    { "id": 7, "tasks": ["8.2", "8.3"] },
    { "id": 8, "tasks": ["8.4", "8.5", "8.6", "8.7"] },
    { "id": 9, "tasks": ["10.1", "14.1"] },
    { "id": 10, "tasks": ["10.2", "10.3", "10.4", "11.1", "14.2"] },
    { "id": 11, "tasks": ["11.2", "12.1", "15.1"] },
    { "id": 12, "tasks": ["12.2", "16.1"] },
    { "id": 13, "tasks": ["16.2"] }
  ]
}
```
