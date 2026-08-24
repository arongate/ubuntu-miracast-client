"""Comprehensive tests for RTSP/WFD session state machine.

Uses a mock TCP server to simulate a Miracast sink responding to
the source's RTSP M1-M7 session establishment flow.
"""

import contextlib
import socket
import threading

import pytest

from miracast_client.rtsp.messages import (
    RTSPMethod,
    RTSPRequest,
    RTSPResponse,
    parse_rtsp_message,
)
from miracast_client.rtsp.session import (
    RTSPSession,
    SessionConfig,
    SessionState,
)
from miracast_client.rtsp.wfd_params import WFDParameters, WFDVideoFormats

# ─────────────────────────────────────────────────────────────
# Mock Miracast Sink (TCP server simulating M1-M7 flow)
# ─────────────────────────────────────────────────────────────


class MockMiracastSink:
    """A mock Miracast sink that responds to RTSP session establishment.

    Simulates the complete M1-M7 flow from the sink's perspective.
    """

    def __init__(self, port=0):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("127.0.0.1", port))
        self.server_socket.listen(1)
        self.port = self.server_socket.getsockname()[1]
        self._client_socket = None
        self._thread = None
        self._running = False
        self._ready = threading.Event()
        self._cseq = 0
        self.messages_received = []
        self.error = None
        self._m3_body = (
            "wfd_video_formats: 00 00 01 02 000000A1 00000000 00000000 00 0000 0000 00 none none\r\n"
            "wfd_audio_codecs: LPCM 00000003 00\r\n"
            "wfd_client_rtp_ports: RTP/AVP/UDP;unicast 19000 0 mode=play\r\n"
            "wfd_content_protection: none"
        )
        # Control behavior
        self.m1_status = 200
        self.m3_status = 200
        self.m4_status = 200
        self.m5_status = 200
        self.skip_m2 = False
        self.skip_m6 = False
        self.skip_m7 = False
        self.m6_port = 19000

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5.0)

    def stop(self):
        self._running = False
        if self._client_socket:
            with contextlib.suppress(Exception):
                self._client_socket.close()
        with contextlib.suppress(Exception):
            self.server_socket.close()
        if self._thread:
            self._thread.join(timeout=3.0)

    def _run(self):
        try:
            self.server_socket.settimeout(10.0)
            self._ready.set()  # Signal that we're ready to accept
            self._client_socket, _ = self.server_socket.accept()
            self._client_socket.settimeout(5.0)
            self._handle_session()
        except Exception as e:
            if self._running:
                self.error = e

    def _handle_session(self):
        """Handle the M1-M7 session flow."""
        # M1: Receive OPTIONS from source, respond
        msg = self._recv_message()
        self.messages_received.append(msg)
        if not isinstance(msg, RTSPRequest) or msg.method != RTSPMethod.OPTIONS:
            return

        resp = RTSPResponse(status_code=self.m1_status, reason="OK")
        resp.cseq = msg.cseq
        resp.headers["Public"] = (
            "org.wfa.wfd1.0, GET_PARAMETER, SET_PARAMETER, SETUP, PLAY, TEARDOWN"
        )
        self._send(resp.serialize())

        if self.m1_status != 200:
            return

        # M2: Send OPTIONS to source
        if not self.skip_m2:
            self._cseq += 1
            req = RTSPRequest(
                method=RTSPMethod.OPTIONS,
                uri="*",
                headers={"CSeq": str(self._cseq), "Require": "org.wfa.wfd1.0"},
            )
            self._send(req.serialize())

            # Receive 200 OK from source
            msg = self._recv_message()
            self.messages_received.append(msg)

        # M3: Receive GET_PARAMETER from source, respond with capabilities
        msg = self._recv_message()
        self.messages_received.append(msg)
        if not isinstance(msg, RTSPRequest) or msg.method != RTSPMethod.GET_PARAMETER:
            return

        resp = RTSPResponse(status_code=self.m3_status, reason="OK")
        resp.cseq = msg.cseq
        resp.body = self._m3_body
        self._send(resp.serialize())

        if self.m3_status != 200:
            return

        # M4: Receive SET_PARAMETER from source, respond 200 OK
        msg = self._recv_message()
        self.messages_received.append(msg)
        if not isinstance(msg, RTSPRequest) or msg.method != RTSPMethod.SET_PARAMETER:
            return

        resp = RTSPResponse(status_code=self.m4_status, reason="OK")
        resp.cseq = msg.cseq
        self._send(resp.serialize())

        if self.m4_status != 200:
            return

        # M5: Receive SET_PARAMETER (trigger SETUP) from source
        msg = self._recv_message()
        self.messages_received.append(msg)
        if not isinstance(msg, RTSPRequest) or msg.method != RTSPMethod.SET_PARAMETER:
            return

        resp = RTSPResponse(status_code=self.m5_status, reason="OK")
        resp.cseq = msg.cseq
        self._send(resp.serialize())

        if self.m5_status != 200:
            return

        # M6: Sink sends SETUP to source
        if not self.skip_m6:
            self._cseq += 1
            req = RTSPRequest(
                method=RTSPMethod.SETUP,
                uri="rtsp://127.0.0.1/wfd1.0/streamid=0",
                headers={
                    "CSeq": str(self._cseq),
                    "Transport": f"RTP/AVP/UDP;unicast;client_port={self.m6_port}",
                },
            )
            self._send(req.serialize())

            # Receive 200 OK from source
            msg = self._recv_message()
            self.messages_received.append(msg)

        # M7: Sink sends PLAY to source
        if not self.skip_m7:
            self._cseq += 1
            req = RTSPRequest(
                method=RTSPMethod.PLAY,
                uri="rtsp://127.0.0.1/wfd1.0/streamid=0",
                headers={
                    "CSeq": str(self._cseq),
                    "Session": "mock-session-id",
                },
            )
            self._send(req.serialize())

            # Receive 200 OK from source
            msg = self._recv_message()
            self.messages_received.append(msg)

    def _send(self, data: bytes):
        self._client_socket.sendall(data)

    def _recv_message(self):
        """Receive and parse an RTSP message from the source."""
        data = b""
        while True:
            chunk = self._client_socket.recv(4096)
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk

            # Check if we have a complete message
            if b"\r\n\r\n" in data:
                header_end = data.find(b"\r\n\r\n")
                header_text = data[:header_end].decode("utf-8", errors="replace")
                content_length = 0
                for line in header_text.split("\n"):
                    if line.strip().lower().startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())
                        break
                total = header_end + 4 + content_length
                if len(data) >= total:
                    return parse_rtsp_message(data[:total])


# ─────────────────────────────────────────────────────────────
# RTSPSession Tests — Full Flow
# ─────────────────────────────────────────────────────────────


class TestRTSPSessionFullFlow:
    """Tests for complete M1-M7 session establishment."""

    def test_full_session_establishment(self):
        """Complete M1-M7 flow succeeds."""
        sink = MockMiracastSink()
        sink.start()

        try:
            config = SessionConfig(
                peer_ip="127.0.0.1",
                control_port=sink.port,
                local_ip="127.0.0.1",
                connect_timeout=5.0,
                response_timeout=5.0,
            )
            session = RTSPSession(config)
            result = session.establish()

            assert result is True
            assert session.state == SessionState.STREAMING
            assert session.is_established
            assert session.negotiated.rtp_port == 19000
            assert session.negotiated.rtsp_session_id != ""
            assert session.negotiated.sink_capabilities is not None

            # Verify sink capabilities were parsed
            caps = session.negotiated.sink_capabilities
            assert caps.video_formats is not None
            assert caps.audio_codecs is not None
            assert caps.client_rtp_ports is not None
            assert caps.client_rtp_ports.port0 == 19000

            session.close()
        finally:
            sink.stop()

    def test_negotiated_video_format(self):
        """Session selects appropriate video format from sink capabilities."""
        sink = MockMiracastSink()
        sink.start()

        try:
            config = SessionConfig(
                peer_ip="127.0.0.1",
                control_port=sink.port,
                local_ip="127.0.0.1",
            )
            session = RTSPSession(config)
            session.establish()

            # Should select 1920x1080p30 (highest in CEA bitmap 0xA1)
            assert session.negotiated.selected_video_width >= 640
            assert session.negotiated.selected_video_height >= 480
            assert session.negotiated.selected_video_fps > 0

            session.close()
        finally:
            sink.stop()

    def test_custom_rtp_port(self):
        """Sink specifies custom RTP port in SETUP."""
        sink = MockMiracastSink()
        sink.m6_port = 5004
        sink.start()

        try:
            config = SessionConfig(
                peer_ip="127.0.0.1",
                control_port=sink.port,
                local_ip="127.0.0.1",
            )
            session = RTSPSession(config)
            session.establish()

            assert session.negotiated.rtp_port == 5004
            session.close()
        finally:
            sink.stop()

    def test_state_transitions(self):
        """Verify correct state transitions during establishment."""
        sink = MockMiracastSink()
        sink.start()

        states = []

        try:
            config = SessionConfig(
                peer_ip="127.0.0.1",
                control_port=sink.port,
                local_ip="127.0.0.1",
            )
            session = RTSPSession(config, on_state_change=states.append)
            session.establish()

            assert SessionState.M1_SENT in states
            assert SessionState.M2_RECEIVED in states
            assert SessionState.M3_SENT in states
            assert SessionState.M4_SENT in states
            assert SessionState.M5_SENT in states
            assert SessionState.M6_RECEIVED in states
            assert SessionState.M7_RECEIVED in states
            assert SessionState.STREAMING in states

            session.close()
        finally:
            sink.stop()


# ─────────────────────────────────────────────────────────────
# RTSPSession Tests — Error Handling
# ─────────────────────────────────────────────────────────────


class TestRTSPSessionErrors:
    """Tests for session error handling."""

    def test_connection_refused(self):
        """ConnectionError when sink is unreachable."""
        config = SessionConfig(
            peer_ip="127.0.0.1",
            control_port=59999,  # Nothing listening here
            connect_timeout=1.0,
            response_timeout=1.0,
        )
        session = RTSPSession(config)
        with pytest.raises(ConnectionError):
            session.establish()
        assert session.state == SessionState.ERROR

    def test_m1_rejected(self):
        """RuntimeError when sink rejects M1 OPTIONS."""
        sink = MockMiracastSink()
        sink.m1_status = 501  # Not Implemented
        sink.start()

        try:
            config = SessionConfig(
                peer_ip="127.0.0.1",
                control_port=sink.port,
                local_ip="127.0.0.1",
            )
            session = RTSPSession(config)
            with pytest.raises(RuntimeError, match="M1 OPTIONS failed"):
                session.establish()
            assert session.state == SessionState.ERROR
        finally:
            sink.stop()

    def test_m3_rejected(self):
        """RuntimeError when sink rejects M3 GET_PARAMETER."""
        sink = MockMiracastSink()
        sink.m3_status = 406
        sink.start()

        try:
            config = SessionConfig(
                peer_ip="127.0.0.1",
                control_port=sink.port,
                local_ip="127.0.0.1",
            )
            session = RTSPSession(config)
            with pytest.raises(RuntimeError, match="M3 GET_PARAMETER failed"):
                session.establish()
            assert session.state == SessionState.ERROR
        finally:
            sink.stop()

    def test_m4_rejected(self):
        """RuntimeError when sink rejects M4 SET_PARAMETER."""
        sink = MockMiracastSink()
        sink.m4_status = 406
        sink.start()

        try:
            config = SessionConfig(
                peer_ip="127.0.0.1",
                control_port=sink.port,
                local_ip="127.0.0.1",
            )
            session = RTSPSession(config)
            with pytest.raises(RuntimeError, match="M4 SET_PARAMETER failed"):
                session.establish()
            assert session.state == SessionState.ERROR
        finally:
            sink.stop()

    def test_m5_rejected(self):
        """RuntimeError when sink rejects M5 trigger SETUP."""
        sink = MockMiracastSink()
        sink.m5_status = 455
        sink.start()

        try:
            config = SessionConfig(
                peer_ip="127.0.0.1",
                control_port=sink.port,
                local_ip="127.0.0.1",
            )
            session = RTSPSession(config)
            with pytest.raises(RuntimeError, match="M5 trigger SETUP failed"):
                session.establish()
            assert session.state == SessionState.ERROR
        finally:
            sink.stop()


# ─────────────────────────────────────────────────────────────
# RTSPSession Tests — Teardown
# ─────────────────────────────────────────────────────────────


class TestRTSPSessionTeardown:
    """Tests for session teardown."""

    def test_teardown_from_streaming(self):
        """Graceful teardown from STREAMING state."""
        sink = MockMiracastSink()
        sink.start()

        try:
            config = SessionConfig(
                peer_ip="127.0.0.1",
                control_port=sink.port,
                local_ip="127.0.0.1",
            )
            session = RTSPSession(config)
            session.establish()
            assert session.state == SessionState.STREAMING

            # Teardown — sink may not respond to M8, that's ok
            session.teardown()
            assert session.state == SessionState.DONE
        finally:
            sink.stop()

    def test_teardown_from_init_is_noop(self):
        """Teardown from INIT state does nothing."""
        config = SessionConfig(peer_ip="127.0.0.1", control_port=12345)
        session = RTSPSession(config)
        session.teardown()  # Should not raise
        assert session.state == SessionState.INIT

    def test_close_from_any_state(self):
        """close() works from any state without error."""
        config = SessionConfig(peer_ip="127.0.0.1", control_port=12345)
        session = RTSPSession(config)
        session.close()
        assert session.state == SessionState.DONE


# ─────────────────────────────────────────────────────────────
# RTSPSession Tests — Helpers
# ─────────────────────────────────────────────────────────────


class TestRTSPSessionHelpers:
    """Tests for session helper methods."""

    def test_parse_transport_port_standard(self):
        """Parse standard transport header."""
        port = RTSPSession._parse_transport_port(
            "RTP/AVP/UDP;unicast;client_port=19000"
        )
        assert port == 19000

    def test_parse_transport_port_range(self):
        """Parse transport header with port range."""
        port = RTSPSession._parse_transport_port(
            "RTP/AVP/UDP;unicast;client_port=5004-5005"
        )
        assert port == 5004

    def test_parse_transport_port_missing(self):
        """Missing client_port returns default."""
        port = RTSPSession._parse_transport_port("RTP/AVP/UDP;unicast")
        assert port == 19000  # Default fallback

    def test_parse_transport_port_invalid(self):
        """Invalid port value returns default."""
        port = RTSPSession._parse_transport_port(
            "RTP/AVP/UDP;unicast;client_port=abc"
        )
        assert port == 19000

    def test_select_video_format_with_caps(self):
        """Select best video format from sink capabilities."""
        config = SessionConfig(peer_ip="127.0.0.1", control_port=7236)
        session = RTSPSession(config)

        # Sink supports 640x480p60 + 1280x720p30 + 1920x1080p30 (CEA 0xA1)
        caps = WFDParameters.parse_body(
            "wfd_video_formats: 00 00 01 02 000000A1 00000000 00000000 00 0000 0000 00 none none"
        )
        result = session._select_video_format(caps)
        # Should select 1920x1080p30 (highest)
        assert result == (1920, 1080, 30)

    def test_select_video_format_no_caps(self):
        """Default format when no sink caps available."""
        config = SessionConfig(peer_ip="127.0.0.1", control_port=7236)
        session = RTSPSession(config)
        result = session._select_video_format(None)
        assert result == (1280, 720, 30)

    def test_select_video_format_empty_caps(self):
        """Default format when caps have no resolutions."""
        config = SessionConfig(peer_ip="127.0.0.1", control_port=7236)
        session = RTSPSession(config)
        caps = WFDParameters(video_formats=WFDVideoFormats(cea_bitmap=0))
        result = session._select_video_format(caps)
        assert result == (1280, 720, 30)
