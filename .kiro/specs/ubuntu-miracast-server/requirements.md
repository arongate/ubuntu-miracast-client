# Requirements Document

## Introduction

The Ubuntu Miracast Server is a Python 3.12 GTK 4 desktop application that receives incoming Miracast streams over Wi-Fi Direct and renders them in a display window. It serves as the companion receiver (sink) to the existing ubuntu-miracast-client. The server advertises itself as a WFD Primary Sink via wpa_supplicant, accepts incoming P2P connections from Miracast sources, negotiates RTSP/WFD sessions, receives and decodes the MPEG2-TS/RTP video stream with GStreamer, and presents video in a GTK 4 window. It also supports headless service mode for digital signage scenarios.

## Glossary

- **Server**: The Ubuntu Miracast Server application
- **Advertiser**: The component responsible for WFD sink advertisement via wpa_supplicant
- **ConnectionHandler**: The component that accepts and manages incoming Wi-Fi Direct P2P connections
- **Receiver**: The component that handles RTSP negotiation and GStreamer decode/render pipeline
- **HistoryManager**: The component that persists and retrieves session records
- **ConfigManager**: The component that manages application settings
- **ServiceManager**: The component that manages systemd user service for headless operation
- **DisplayView**: The GTK 4 widget that renders video output
- **Source**: A Miracast source device (e.g., phone, laptop) that sends a stream to the Server
- **WFD**: Wi-Fi Display — the Miracast protocol specification
- **P2P**: Peer-to-peer Wi-Fi Direct connection between Source and Server
- **GO**: Group Owner — the device that acts as the access point in a Wi-Fi Direct group
- **RTSP**: Real Time Streaming Protocol — used for session negotiation in Miracast
- **RTP**: Real-time Transport Protocol — carries the MPEG2-TS stream
- **MPEG2-TS**: MPEG-2 Transport Stream — container format for Miracast video/audio
- **Pipeline**: A GStreamer media processing pipeline that decodes and renders the stream
- **SessionRecord**: A persisted record of a completed receiving session

## Requirements

### Requirement 1: WFD Sink Advertisement

**User Story:** As a user, I want the server to advertise itself as a Miracast sink on the local Wi-Fi Direct network, so that Miracast source devices can discover and connect to it.

#### Acceptance Criteria

1. WHEN the user starts advertising, THE Advertiser SHALL enable Wi-Fi Display on the P2P interface and set WFD subelements to identify the device as a WFD Primary Sink with session availability set to available
2. WHEN the user starts advertising, THE Advertiser SHALL configure the RTSP control port (default 7236) in the WFD subelements
3. WHEN advertising is initiated, THE Advertiser SHALL place the P2P interface into listen mode to make the device discoverable
4. IF no P2P interface is specified, THEN THE Advertiser SHALL auto-detect an available P2P-capable Wi-Fi interface; IF a P2P interface IS specified by the user, THEN THE Advertiser SHALL validate that the specified interface exists on the system and supports P2P before proceeding; IF validation fails, THEN THE Advertiser SHALL emit an advertising-error signal indicating the interface does not exist or lacks P2P capability
5. IF the P2P interface cannot be found, THEN THE Advertiser SHALL emit an advertising-error signal with a message indicating no P2P-capable interface was detected
6. IF the p2p_listen command fails, THEN THE Advertiser SHALL emit an advertising-error signal and remain in a non-advertising state; IF the user simultaneously requests stop_advertising during a failed start_advertising attempt, THEN THE Advertiser SHALL emit the advertising-error signal for the failed start and process the stop request separately
7. IF a WFD configuration command fails prior to entering listen mode, THEN THE Advertiser SHALL emit an advertising-error signal indicating which configuration step failed and remain in a non-advertising state
8. WHEN advertising starts successfully (interface validation passed, WFD configuration succeeded, and p2p_listen succeeded), THE Advertiser SHALL emit an advertising-started signal AND set its internal state to ADVERTISING; THE Advertiser SHALL only consider advertising started after all three steps complete without error
9. WHEN the user stops advertising, THE Advertiser SHALL exit P2P listen mode and emit an advertising-stopped signal
10. WHILE already advertising, THE Advertiser SHALL ignore duplicate start_advertising calls

### Requirement 2: Wi-Fi Direct P2P Connection Acceptance

**User Story:** As a user, I want the server to accept incoming Wi-Fi Direct connections from Miracast sources, so that a streaming session can be established.

#### Acceptance Criteria

1. WHEN a P2P-GO-NEG-REQUEST event is received, IF auto_accept is True, THEN THE ConnectionHandler SHALL invoke p2p_connect with the peer address using PBC method and the configured GO intent value (default 15)
2. WHEN a P2P-GO-NEG-REQUEST event is received, IF auto_accept is False, THEN THE ConnectionHandler SHALL prompt the user for confirmation before invoking p2p_connect
3. WHEN a P2P-GROUP-STARTED event is received, THE ConnectionHandler SHALL extract the group interface name, peer IP, peer MAC address, peer device name, and our IP address on the group interface into an IncomingConnection object with connected_at set to the current timestamp
4. WHEN a P2P-GROUP-STARTED event is received and all IncomingConnection fields are populated with valid values, THE ConnectionHandler SHALL emit a connection-received signal with the IncomingConnection object
5. WHEN a P2P-GROUP-REMOVED event is received, THE ConnectionHandler SHALL emit a connection-lost signal with a reason string indicating the cause of disconnection
6. WHILE a connection is active, IF a new P2P-GO-NEG-REQUEST event is received, THEN THE ConnectionHandler SHALL ignore the request without invoking p2p_connect and SHALL NOT emit any signal
7. IF wpa_supplicant is not running when start_listening is called, THEN THE ConnectionHandler SHALL emit a connection-error signal with an error message indicating that wpa_supplicant is unavailable
8. WHEN the user disconnects a peer, THE ConnectionHandler SHALL remove the P2P group via p2p_group_remove and set the active connection to None
9. IF no P2P-GROUP-STARTED event is received within 30 seconds after p2p_connect is invoked, THEN THE ConnectionHandler SHALL emit a connection-error signal with an error message indicating a connection timeout and cancel the pending connection attempt

### Requirement 3: RTSP Session Negotiation

**User Story:** As a user, I want the server to negotiate codec and transport parameters with the Miracast source, so that the stream can be received with compatible settings.

#### Acceptance Criteria

1. WHEN a connection is established, THE Receiver SHALL bind an RTSP server socket to the P2P group interface IP on the configured RTSP port with a listen backlog of 1
2. WHEN an RTSP OPTIONS request is received, THE Receiver SHALL respond with RTSP 200 OK listing the supported WFD methods: OPTIONS, GET_PARAMETER, SET_PARAMETER, SETUP, PLAY, TEARDOWN
3. WHEN an RTSP GET_PARAMETER request is received, THE Receiver SHALL respond with RTSP 200 OK containing the server WFD capability parameters including supported video codecs (H.264), supported resolutions up to the configured max_resolution, and supported audio formats (AAC) if audio is enabled
4. WHEN an RTSP SET_PARAMETER request is received, THE Receiver SHALL parse and apply the WFD session parameters (resolution, codec, transport port) and respond with RTSP 200 OK
5. WHEN an RTSP SETUP request is received, THE Receiver SHALL allocate an RTP port in the range 1024–65535, configure the decode pipeline for the negotiated codec and resolution, explicitly verify that both port allocation and pipeline configuration succeeded without errors, and respond with RTSP 200 OK including the allocated transport port; IF port allocation fails or pipeline configuration fails, THEN THE Receiver SHALL respond with RTSP 500 Internal Server Error without starting the pipeline
6. WHEN an RTSP PLAY request is received, THE Receiver SHALL start the GStreamer receive pipeline and emit a stream-started signal with the source info
7. WHEN an RTSP TEARDOWN request is received, THE Receiver SHALL stop the pipeline, close the RTSP socket, and emit a stream-stopped signal with final ReceiverStats
8. IF a malformed RTSP request is received (unparseable method, missing CSeq header, or invalid content length), THEN THE Receiver SHALL respond with RTSP 400 Bad Request and log the issue, regardless of the request method — this validation overrides the 200 OK responses specified for well-formed OPTIONS, GET_PARAMETER, SET_PARAMETER, and SETUP requests; WHEN a request has multiple issues, THE Receiver SHALL prioritize the most specific error response based on what can be parsed (e.g., if the method is parseable but CSeq is missing, respond with 400 citing missing CSeq rather than a generic parse failure)
9. IF the source requests an unsupported codec or resolution, THEN THE Receiver SHALL respond with RTSP 406 Not Acceptable
10. IF the source does not initiate RTSP within the connection_timeout period (default 30 seconds), THEN THE Receiver SHALL close the socket, disconnect the P2P group, and emit a stream-error signal
11. THE Receiver SHALL include a matching CSeq header in every RTSP response corresponding to the CSeq value from the request

### Requirement 4: GStreamer Stream Receiving and Decoding

**User Story:** As a user, I want the server to decode incoming Miracast video and audio streams in real time, so that I can view the source device screen on my display.

#### Acceptance Criteria

1. WHEN RTSP PLAY is received, THE Receiver SHALL construct a GStreamer pipeline with udpsrc bound to the RTP port negotiated during RTSP SETUP, rtpmp2tdepay, tsdemux, h264parse, avdec_h264, and videoconvert as core decode elements, with the video sink determined by mode (see AC 4.2 and 4.3)
2. WHILE in GUI mode, THE Receiver SHALL use gtk4paintablesink as the video sink element regardless of whether the video widget reference has been bound at pipeline construction time; IF hardware decode failure or configuration error necessitates a different sink, THEN THE Receiver MAY override this choice with an alternative video sink
3. WHEN no video widget is set (headless mode), THE Receiver SHALL use fakesink with sync=true as the video sink element
4. WHEN audio is enabled in configuration and the source provides an audio stream as negotiated during RTSP SET_PARAMETER, THE Receiver SHALL decode the audio via aacparse, avdec_aac, audioconvert, and render to pulsesink
5. IF hardware-accelerated decode is available (vaapi or nvdec), THEN THE Receiver SHALL insert the hardware decoder element in place of avdec_h264 in the pipeline
6. IF hardware decode fails during pipeline state transition or produces a GStreamer error, THEN THE Receiver SHALL rebuild the pipeline using avdec_h264 as the software decoder
7. IF no RTP packets are received for 5 seconds after the pipeline has entered PLAYING state, THEN THE Receiver SHALL detect stream loss, set the pipeline state to NULL, and emit a stream-error signal; IF the pipeline leaves PLAYING state during the 5-second timeout window, THEN THE Receiver SHALL cancel the stream loss detection timer
8. THE Receiver SHALL configure the UDP receive buffer to 2MB to handle burst traffic without packet loss
9. THE Receiver SHALL configure GStreamer queues with max-size-buffers=200, max-size-bytes=10485760 (10MB), and max-size-time=1000000000 (1 second) to prevent unbounded memory growth
10. IF the GStreamer pipeline fails to transition to PLAYING state within 5 seconds of construction, THEN THE Receiver SHALL set the pipeline state to NULL, release all pipeline resources, and emit a stream-error signal indicating pipeline initialization failure
11. THE Receiver SHALL achieve an end-to-end decode latency of no more than 100 milliseconds from RTP packet receipt to frame delivery at the video sink under normal operating conditions

### Requirement 5: GTK 4 Display Rendering

**User Story:** As a user, I want to view the incoming Miracast stream in a desktop window with the option to go fullscreen, so that I can use the server as a wireless display.

#### Acceptance Criteria

1. WHEN the application starts in GUI mode, THE Server SHALL display a main window with a HeaderBar, status indicator, and navigation between Display, Sessions, and Settings views
2. WHILE no stream is active and no connection is established, THE DisplayView SHALL show a centered idle state with an icon and "Waiting for Miracast source..." text
3. WHEN a connection is received but the stream has not started, THE DisplayView SHALL show a connected state displaying the source device name from the peer connection information
4. IF fullscreen_on_stream is True in configuration, THEN WHEN a stream starts, THE DisplayView SHALL enter fullscreen mode automatically
5. WHILE receiving a stream, THE DisplayView SHALL render video frames from the GStreamer pipeline via the gtk4paintablesink paintable bound to a Gtk.Picture widget
6. WHILE receiving a stream in fullscreen, THE DisplayView SHALL show floating overlay controls (pause, disconnect, and fullscreen toggle) that appear on pointer movement and auto-hide after 3 seconds of inactivity
7. WHEN the stream stops, THE DisplayView SHALL return to the idle state and exit fullscreen mode if currently fullscreen
8. WHEN the user presses F11 or double-clicks the video area while receiving a stream, THE DisplayView SHALL toggle fullscreen mode; WHEN the user presses Escape while in fullscreen, THE DisplayView SHALL exit fullscreen mode
9. IF a GStreamer pipeline error occurs while receiving a stream, THEN THE DisplayView SHALL stop rendering, return to the idle state, and display an error indication describing the failure reason

### Requirement 6: Session History and Statistics

**User Story:** As a user, I want to view a history of past receiving sessions with statistics, so that I can track usage and diagnose streaming quality issues.

#### Acceptance Criteria

1. WHEN a stream stops via the stream-stopped signal, THE HistoryManager SHALL create a ServerSessionRecord containing the source info and receiver statistics
2. IF a stream ends due to a stream-error signal, THEN THE HistoryManager SHALL create a ServerSessionRecord containing the source info and the statistics collected up to the point of failure
3. WHEN a session record is created, THE HistoryManager SHALL persist the record to the history JSON file at ~/.local/share/ubuntu-miracast-server/history.json, retaining a maximum of 500 records and discarding the oldest record when the limit is exceeded; IF disk persistence fails, THE HistoryManager SHALL still retain the record in memory (record creation succeeds regardless of persistence outcome)
4. WHEN the application starts and the history file exists and contains valid JSON, THE HistoryManager SHALL load existing session records from the history file
5. IF the history file does not exist or contains invalid JSON when the application starts, THEN THE HistoryManager SHALL initialize with an empty session list and continue without error
6. THE HistoryManager SHALL provide access to the complete list of past session records sorted by timestamp in descending order
7. WHEN the user clears history, THE HistoryManager SHALL remove all session records from memory and delete the contents of the history file, resulting in an empty JSON array persisted to disk; IF the clear operation fails, THEN THE HistoryManager SHALL emit a persist-error signal indicating the failure reason and leave the history state unchanged
8. WHILE a stream is active, THE Receiver SHALL emit stats-updated signals at an interval of 1000 milliseconds with a tolerance of ±200 milliseconds, with current ReceiverStats (duration, data received, bitrate, frames decoded, frames dropped, resolution, codec); WHEN a stream-error signal is emitted, THE Receiver SHALL continue emitting stats-updated signals until the pipeline transitions to NULL state
9. THE Receiver SHALL record peak bitrate as the highest observed bitrate sample across all stats-updated intervals during a session; WHEN a new bitrate sample exceeds the current peak_bitrate value, THE Receiver SHALL update the peak_bitrate field and emit a stats-updated signal reflecting the new peak
10. IF persisting a session record to disk fails, THEN THE HistoryManager SHALL always retain the record in memory regardless of whether a partial write occurred, and SHALL emit a persist-error signal indicating the failure reason; IF memory retention itself fails due to resource constraints, THEN THE HistoryManager SHALL emit an additional error signal indicating memory retention failure

### Requirement 7: Session Record Serialization

**User Story:** As a developer, I want session records to serialize and deserialize reliably, so that history is preserved across application restarts.

#### Acceptance Criteria

1. WHEN a ServerSessionRecord is serialized via to_dict, THE HistoryManager SHALL produce a JSON-compatible dictionary containing source_info (with name, address, model, resolution, codec, audio_codec), stats (with start_time, end_time, duration, data_received, average_bitrate, peak_bitrate, frames_decoded, frames_dropped, errors, resolution, codec), and timestamp, with all datetime values formatted as ISO 8601 strings and None values represented as JSON null
2. WHEN a dictionary containing all required fields is deserialized via from_dict, THE HistoryManager SHALL reconstruct a ServerSessionRecord object whose fields are equal in value and type to the original, including nested SourceInfo and ReceiverStats objects
3. FOR ALL valid ServerSessionRecord objects, serializing via to_dict then deserializing via from_dict SHALL produce an object where every field (source_info, stats, timestamp) is equal to the corresponding field of the original object
4. IF a dictionary passed to from_dict is missing required fields or contains values that cannot be parsed, THEN THE HistoryManager SHALL raise an exception without creating a partial ServerSessionRecord object

### Requirement 8: Configuration Management

**User Story:** As a user, I want to configure server settings such as device name, RTSP port, resolution limits, and auto-accept behavior, so that I can customize the server for my environment.

#### Acceptance Criteria

1. WHEN no configuration file exists, THE ConfigManager SHALL generate a default configuration file in JSON format with sections for general, streaming, network, and service, and SHALL write it to disk before returning
2. THE ConfigManager SHALL support the following default values: device_name "Ubuntu Miracast Server", rtsp_port 7236, audio_enabled true, max_resolution "1920x1080", go_intent 15, connection_timeout 30, auto_accept true
3. WHEN the user modifies a setting via the set method, THE ConfigManager SHALL write the updated configuration to disk within 1 second of the modification
4. WHEN the application starts and the configuration file exists, THE ConfigManager SHALL load configuration from the file; IF the configuration file contains malformed JSON, THEN THE ConfigManager SHALL log a warning, discard the corrupted file content, and load all default values
5. WHEN a configuration key is not present in the loaded configuration, THE ConfigManager SHALL return the specified default value without modifying the persisted file
6. IF the user attempts to set rtsp_port to a value outside the range 1024 to 65535, or go_intent to a value outside the range 0 to 15, or connection_timeout to a value less than 1 or greater than 120 seconds, THEN THE ConfigManager SHALL reject the change and retain the previous value
7. IF a disk write fails when persisting configuration, THEN THE ConfigManager SHALL retain the updated values in memory and log an error message indicating the write failure

### Requirement 9: Systemd Service Mode

**User Story:** As a system administrator, I want to run the Miracast server as a headless systemd user service, so that I can use it for digital signage without a logged-in desktop session.

#### Acceptance Criteria

1. WHEN the server is launched with the --service flag, THE Server SHALL run in headless mode using a GLib main loop without creating a GTK window or requiring a display server connection
2. WHILE in service mode, THE Server SHALL start the Advertiser and ConnectionHandler without instantiating any UI widgets; previously created UI widgets SHALL NOT prevent service operations from functioning
3. WHILE in service mode, THE Receiver SHALL use fakesink as the video sink element with sync configurable (sync=true by default; sync=false when high_throughput_mode is enabled in configuration); IF sync=true is explicitly configured in the configuration file, THEN that explicit value SHALL override the high_throughput_mode default of sync=false
4. WHEN the ServiceManager enables the service, THE ServiceManager SHALL generate a systemd user service file invoking the server with the --service flag, install it to ~/.config/systemd/user/, and run daemon-reload; daemon-reload SHALL only execute after successful service file installation
5. WHEN the ServiceManager disables the service, THE ServiceManager SHALL stop the service unit if running, remove the systemd user service file from ~/.config/systemd/user/, and run daemon-reload
6. IF idle_timeout is configured to a value greater than 0 (in seconds, range 1 to 86400) and no stream is active for the configured duration, THEN THE Server SHALL exit the service process with exit code 0
7. IF idle_timeout is configured to 0, THEN THE Server SHALL treat idle timeout as disabled and remain running indefinitely until explicitly stopped
8. IF the ServiceManager fails to install or remove the service file or run daemon-reload, or IF any operation results in an inconsistent service state (e.g., service file present without daemon-reload, or daemon-reload completed without service file), THEN THE ServiceManager SHALL validate the complete service configuration after each operation and raise an error indicating the failure reason without leaving the service in an inconsistent state; WHILE handling errors, THE ServiceManager SHALL never leave the service in a transiently inconsistent state and SHALL roll back partial changes before raising the error

### Requirement 10: Security

**User Story:** As a user, I want the server to enforce secure communication and safe resource handling, so that my system is protected from unauthorized access and malicious input.

#### Acceptance Criteria

1. THE Server SHALL enforce WPA2 security on all Wi-Fi Direct P2P connections (via wpa_supplicant group formation)
2. THE Receiver SHALL bind the RTSP server socket only to the P2P group interface IP address, not to 0.0.0.0
3. THE Receiver SHALL validate all RTSP headers and WFD parameters before processing, rejecting malformed requests with RTSP 400 Bad Request for syntax errors (including invalid header values even when the overall request structure appears valid), 404 Not Found for invalid URIs, 455 Method Not Valid in This State for out-of-sequence methods, and 500 Internal Server Error for processing failures
4. THE Server SHALL construct GStreamer pipeline strings from validated parameters only — port numbers validated as integers in the range 1024 to 65535, codec names matched against a whitelist of "H264" for video and "AAC" for audio — and never interpolate user-supplied strings into pipeline descriptions; pipeline construction SHALL proceed when the codec name passes whitelist validation, independent of other non-codec validation steps; IF the codec name does NOT pass whitelist validation, THEN pipeline construction SHALL be blocked regardless of other parameter validation results
5. THE ConfigManager SHALL create configuration and history files with 0600 permissions (user-only read/write)
6. THE Server SHALL use list-based subprocess calls for all wpa_cli commands (no shell=True) with each parameter validated against an allowlist of expected characters (alphanumeric, colons, hyphens, and underscores)
7. THE Receiver SHALL follow standard RTSP connection management practices (keep-alive) for all responses, keeping connections open after successful responses and error responses that allow continued negotiation; IF an RTSP request exceeds 8192 bytes in header size or 65536 bytes in body size, THEN THE Receiver SHALL check header size first and body size second, rejecting the request with RTSP 413 Request Entity Too Large at the first violation encountered, send the RTSP 413 error response, and then close the connection

### Requirement 11: Performance

**User Story:** As a user, I want the server to decode and display the stream with minimal latency and without dropped frames, so that the wireless display experience is smooth and responsive.

#### Acceptance Criteria

1. WHILE receiving a stream under steady-state conditions, THE Receiver SHALL maintain less than 100ms end-to-end latency from RTP packet receipt to pixel display for at least 95% of frames measured over any 10-second window
2. THE Receiver SHALL configure GStreamer decode elements with low-latency flags and zero-buffering on the demuxer (max-size-time=0)
3. THE Receiver SHALL limit the GStreamer queue to at most 30 frames to bound memory usage
4. THE Receiver SHALL set the UDP source buffer size to 2097152 bytes (2MB)
5. WHILE in fullscreen mode, THE DisplayView SHALL use the GTK4 GPU rendering path for video frame composition; WHILE in windowed mode, THE DisplayView SHALL allow GPU rendering but SHALL NOT require it; IF the GPU is unavailable or drivers are missing, THEN THE DisplayView SHALL fall back to software rendering rather than refusing to display
6. WHILE receiving a stream, THE Receiver SHALL maintain a frame drop rate of no more than 1% of total frames decoded over any 30-second measurement window, calculated using a maintained rolling metric updated on each stats interval rather than recalculated from raw frame counts
7. IF the Receiver detects that frame drops exceed 5% of frames over a 10-second window, THEN THE Receiver SHALL emit a stats-updated signal reporting the current frames_dropped count; the reported frames_dropped count SHALL reflect the actual number of dropped frames detected at the time of the threshold trigger (not zero or a stale value)

### Requirement 12: Error Handling and Fault Tolerance

**User Story:** As a user, I want the server to handle errors gracefully and recover automatically where possible, so that I do not need to manually restart the application after transient failures.

#### Acceptance Criteria

1. IF the P2P interface is unavailable at startup, THEN THE Advertiser SHALL emit an advertising-error signal indicating the missing interface and THE UI SHALL display an error state showing the interface name and instructions to enable Wi-Fi or check hardware
2. IF the source disconnects unexpectedly (whether or not a proper RTSP TEARDOWN was previously sent), THEN THE Receiver SHALL detect stream loss within a configurable timeout (default 5 seconds), stop the GStreamer pipeline, close the RTSP socket, and emit a stream-error signal; THE Server SHALL allow configuration of different timeouts based on disconnection type (e.g., longer timeout for brief Wi-Fi drops that may self-recover); IF detection takes longer than the configured timeout due to network conditions or system load, THEN THE Receiver SHALL still proceed with error handling when detection eventually occurs without considering the delay a failure
3. WHEN stream-error is emitted, THE Server SHALL record the session in history with the stats accumulated up to the point of failure and return to the advertising/listening state within 3 seconds
4. IF a GStreamer pipeline error occurs, THEN THE Receiver SHALL always attempt one fallback to software decoding by reconstructing the pipeline with a software decoder element (the attempt itself determines availability — no precheck for software decoder presence); IF the software fallback pipeline also fails, THEN THE Receiver SHALL attempt RTSP renegotiation requesting an alternative codec from the source, and IF renegotiation fails or is unsupported, THEN THE Receiver SHALL emit a stream-error signal indicating decode failure
5. IF the application lacks permission to execute wpa_cli commands, THEN THE Advertiser SHALL emit an advertising-error signal indicating insufficient permissions and the required privilege level
6. WHEN an error occurs during RTSP negotiation, THE Receiver SHALL send the corresponding RTSP error response and keep the connection open for up to 10 seconds to allow the source to renegotiate, and IF no valid RTSP request is received within that period, THEN THE Receiver SHALL close the connection and emit a stream-error signal

### Requirement 13: Data Model Validation

**User Story:** As a developer, I want data model objects to enforce validation rules, so that invalid state cannot propagate through the system.

#### Acceptance Criteria

1. THE IncomingConnection model SHALL validate that peer_address matches the MAC format XX:XX:XX:XX:XX:XX where each X is a case-insensitive hexadecimal digit (0-9, A-F, a-f)
2. THE IncomingConnection model SHALL validate that peer_ip is a valid IPv4 address in dotted-decimal notation with each octet in the range 0-255
3. THE IncomingConnection model SHALL validate that group_interface is a string of 2 to 16 characters
4. THE ReceiverStats model SHALL ensure that duration is a non-negative integer
5. THE ReceiverStats model SHALL ensure that data_received is a non-negative integer
6. THE ReceiverStats model SHALL ensure that frames_decoded is greater than or equal to frames_dropped; both frames_decoded=0 and frames_dropped=0 simultaneously is a valid state representing no processing having occurred
7. IF any validation rule is violated during model construction or when the invalid field is first accessed, THEN THE model SHALL raise a ValueError indicating which field failed validation and why

### Requirement 14: Concurrency and Thread Safety

**User Story:** As a developer, I want all inter-thread communication to be safe and predictable, so that the application does not exhibit race conditions or UI corruption.

#### Acceptance Criteria

1. THE Server SHALL emit all GObject signals (advertising-started, advertising-stopped, advertising-error, connection-received, connection-lost, connection-error, stream-started, stream-stopped, stream-error, stats-updated, resolution-changed) on the main GTK thread via GLib.idle_add
2. THE Server SHALL never access GTK widgets from background threads; this prohibition applies to all access including read-only access to widget properties, and admits no exceptions for debugging or logging purposes
3. WHILE wpa_supplicant event monitoring is active, THE ConnectionHandler SHALL run event parsing in a daemon thread and dispatch connection-received, connection-lost, and connection-error signals to the main thread via GLib.idle_add; the GLib.idle_add constraint applies at signal dispatch time and does not restrict the monitoring thread while idle between events
4. WHILE the RTSP session is active, THE Receiver SHALL run RTSP handling in a daemon thread and SHALL continuously ensure that stream-started, stream-stopped, stream-error, and resolution-changed signals are dispatched to the main thread via GLib.idle_add for the entire duration the daemon thread runs
5. WHILE the stats monitor is active, THE Receiver SHALL continuously enforce that stats collection runs in a daemon thread and stats-updated signals are dispatched to the main thread via GLib.idle_add at an interval of 1 second for the entire duration the monitor is active; stats-updated signal dispatch is permitted even when stats collection is temporarily inactive between collection cycles, provided the monitor itself remains active
6. WHEN a component's stop method is called (stop_listening, stop_receiving, stop_advertising), THE Server SHALL set the running flag to False regardless of whether thread joining succeeds or fails, and SHALL attempt to join all associated daemon threads within 5 seconds before returning
7. IF a daemon thread encounters an unhandled exception, THEN THE owning component SHALL dispatch the corresponding error signal (advertising-error, connection-error, or stream-error) to the main thread via GLib.idle_add with an error message indicating the failure reason; this applies whether or not the exception terminates the thread — IF the thread recovers and continues after an exception, an error signal SHALL still be dispatched

### Requirement 15: Resource Cleanup

**User Story:** As a developer, I want all system resources to be released when components are stopped, so that the application does not leak threads, sockets, or GStreamer pipelines.

#### Acceptance Criteria

1. WHEN stop_receiving is called, THE Receiver SHALL set the GStreamer pipeline state to NULL and free the pipeline, close all RTSP sockets, and join background threads within 5 seconds; IF any individual cleanup step fails, THEN THE Receiver SHALL attempt to log the partial failure on a best-effort basis and continue with remaining cleanup steps regardless of whether logging succeeds
2. WHEN stop_listening is called, THE ConnectionHandler SHALL terminate the wpa_cli event process and join the monitoring thread, both within a combined 5-second deadline; IF either process termination or thread joining fails within the deadline, THEN THE ConnectionHandler SHALL consider the cleanup failed and log an error
3. WHEN stop_advertising is called, THE Advertiser SHALL issue p2p_stop_find via wpa_cli to exit P2P listen mode so the device is no longer discoverable
4. WHEN the application receives SIGTERM or SIGINT or the user closes the window, THE Server SHALL initiate stops of all active components simultaneously in the order Receiver then ConnectionHandler then Advertiser (initiation order, not sequential wait), starting all stops within 10 seconds; individual cleanup tasks that cannot complete within the deadline SHALL continue asynchronously without blocking application exit
5. IF a background thread does not join within its timeout, THEN THE component SHALL log the failure and continue shutdown of remaining resources without blocking indefinitely

### Requirement 16: Single Active Session Invariant

**User Story:** As a user, I want the server to handle one incoming stream at a time, so that resource contention and ambiguity are avoided.

#### Acceptance Criteria

1. WHILE the Receiver is receiving a stream, THE ConnectionHandler SHALL report an active connection via get_active_connection() returning a non-None IncomingConnection
2. WHILE the Receiver is actively receiving a stream, WHEN an additional P2P connection request is received, THE Server SHALL send a proper GO negotiation rejection response indicating the reason (active session in progress) and then decline the GO negotiation so that the requesting source understands why the connection was refused; WHILE a connection is established but the Receiver is not actively streaming, THE Server SHALL allow new P2P connection requests to proceed normally
3. WHEN the source sends an RTSP TEARDOWN, THE Server SHALL stop the GStreamer pipeline, close the RTSP socket, and return to the advertising/listening state; all cleanup steps SHALL complete within 5 seconds before the state transition occurs; this criterion applies exclusively to explicit RTSP TEARDOWN requests — unexpected socket closure without TEARDOWN is handled by stream loss detection (Requirement 12), not by this criterion; the same teardown actions apply to other session-ending conditions such as RTP timeouts (AC 16.4) and connection failures (Requirement 12)
4. IF the RTP stream is not received for 30 seconds or the P2P group is removed, THEN THE Server SHALL treat the stream as ended, stop the pipeline, and return to the advertising/listening state; cleanup SHOULD complete within 5 seconds but MAY exceed this target if proper resource cleanup requires additional time
