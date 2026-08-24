# ADR-002: Implement RTSP 1.0 Session Negotiation for WFD Compliance

## Status

**Proposed** — 2026-08-24

## Context

The Wi-Fi Display Technical Specification v2.3 requires RTSP 1.0 (RFC 2326) session establishment between source and sink before any media streaming can begin. The current implementation skips this entirely — it establishes a P2P connection and immediately streams RTP/MPEG-TS to the peer's RTSP control port (7236), which is incorrect.

**Why this matters:**
- No real Miracast sink (TV, dongle, etc.) will display our stream without RTSP handshake
- We're sending to port 7236 (TCP control port) via UDP (should be a negotiated UDP port)
- No codec capability negotiation — we might send H.264 settings the sink can't decode
- No session lifecycle management (pause, resume, teardown, keep-alive)

## Decision

Implement a minimal RTSP 1.0 session manager supporting the WFD M1-M7 flow (mandatory) and M8-M14 (session management).

### Module structure:
```
src/miracast_client/rtsp/
├── __init__.py
├── messages.py      # RTSP message parser/builder (RFC 2326)
├── wfd_params.py    # WFD-specific parameter parsing/formatting
├── session.py       # State machine for M1-M16 message flow
└── server.py        # TCP server on port 7236 (source role)
```

### Message flow to implement:

**Session establishment (required):**
1. Source opens TCP:7236 on sink (after P2P connection)
2. M1: Source → Sink: OPTIONS (query methods)
3. M2: Sink → Source: OPTIONS (query methods)
4. M3: Source → Sink: GET_PARAMETER (get audio/video/RTP port capabilities)
5. M4: Source → Sink: SET_PARAMETER (set chosen video format, audio codec, presentation URL)
6. M5: Source → Sink: SET_PARAMETER (trigger: SETUP)
7. M6: Sink → Source: SETUP (transport parameters, client_port)
8. M7: Sink → Source: PLAY
9. Begin RTP/UDP streaming to negotiated port

**Session management:**
- M8-M9: TEARDOWN
- M14: Keep-alive (GET_PARAMETER every <30s)
- M13: IDR request from sink

### Key parameters in M3/M4:
```
wfd_video_formats: <native> <pref> <profile> <level> <CEA> <VESA> <HH> <latency> <min_slice> <slice_enc> <frame_rate_control> <max_hres> <max_vres>
wfd_audio_codecs: LPCM <modes> <latency>, AAC <modes> <latency>
wfd_client_rtp_ports: RTP/AVP/UDP;unicast <port> 0 mode=play
wfd_content_protection: none
```

## Alternatives Considered

1. **Use existing RTSP library (e.g., python-rtsp-client):** These implement RTSP 2.0 or are client-only. WFD uses RTSP 1.0 with custom parameters. No library matches.

2. **Port gnome-network-displays RTSP code:** Written in C (GLib/GStreamer RTSP). Could serve as reference but can't be directly reused.

3. **Port Intel WDS (Wysiwidi) RTSP parser:** C++ library. Good reference for message formatting but needs full rewrite in Python.

4. **Skip RTSP, document as "direct streaming only":** Defeats the purpose of Miracast compatibility.

## Consequences

### Positive
- Interoperability with all certified Miracast sinks
- Proper codec negotiation (won't send unsupported formats)
- Session lifecycle management (pause, resume, teardown)
- Accurate streaming stats (from RTSP feedback)
- Keep-alive prevents session timeout

### Negative
- Significant implementation effort (~8 hours)
- Increases complexity (state machine with multiple message types)
- Need to handle RTSP parsing edge cases (malformed responses from cheap sinks)
- Need test infrastructure (mock RTSP sink for testing)

## References

- Wi-Fi Display Technical Specification v2.3, §4.5 (Session Management)
- RFC 2326: Real Time Streaming Protocol (RTSP) 1.0
- gnome-network-displays source: `src/wfd/` directory
- Intel WDS: `libwds/rtsp/` directory
