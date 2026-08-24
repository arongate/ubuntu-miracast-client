"""RTSP/WFD session state machine for Miracast source role.

Implements the WFD session establishment flow (M1-M7) and session management
(M8-M9 teardown, M14 keep-alive) per Wi-Fi Display Technical Specification v2.3 §4.5.

The source initiates a TCP connection to the sink's control port (default 7236)
and drives the session through the following states:

    INIT → M1_SENT → M2_RECEIVED → M3_SENT → M4_SENT → M5_SENT →
    M6_RECEIVED → M7_RECEIVED → STREAMING → TEARDOWN → DONE

Reference: WFD Spec v2.3 Table 4-5 (RTSP Messages)
"""

from __future__ import annotations

import contextlib
import enum
import logging
import socket
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from miracast_client.rtsp.messages import (
    RTSPMethod,
    RTSPRequest,
    RTSPResponse,
    parse_rtsp_message,
)
from miracast_client.rtsp.wfd_params import (
    WFDClientRTPPorts,
    WFDParameters,
    WFDTriggerMethod,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# Default WFD control port (TCP)
WFD_DEFAULT_CONTROL_PORT = 7236

# Session timeout in seconds (WFD spec default: 30s)
WFD_SESSION_TIMEOUT = 30

# Keep-alive interval (must be less than session timeout)
WFD_KEEPALIVE_INTERVAL = 15

# Socket receive buffer size
RECV_BUFFER_SIZE = 4096

# Maximum receive buffer size (prevent unbounded memory growth from malicious peers)
MAX_RECV_BUFFER_SIZE = 65536

# Maximum Content-Length we'll accept (prevent memory exhaustion)
MAX_CONTENT_LENGTH = 16384

# Connection and response timeouts
CONNECT_TIMEOUT = 10
RESPONSE_TIMEOUT = 10


class SessionState(enum.Enum):
    """WFD RTSP session states."""

    INIT = "init"
    M1_SENT = "m1_sent"           # OPTIONS sent to sink
    M2_RECEIVED = "m2_received"   # OPTIONS received from sink (responded)
    M3_SENT = "m3_sent"           # GET_PARAMETER sent
    M4_SENT = "m4_sent"           # SET_PARAMETER sent
    M5_SENT = "m5_sent"           # Trigger SETUP sent
    M6_RECEIVED = "m6_received"   # SETUP received from sink (responded)
    M7_RECEIVED = "m7_received"   # PLAY received from sink (responded)
    STREAMING = "streaming"       # Active media streaming
    TEARDOWN = "teardown"         # Teardown in progress
    DONE = "done"                 # Session ended
    ERROR = "error"               # Unrecoverable error


@dataclass
class SessionConfig:
    """Configuration for an RTSP/WFD session."""

    peer_ip: str = ""
    control_port: int = WFD_DEFAULT_CONTROL_PORT
    local_ip: str = ""
    presentation_url: str = ""  # Set during session setup
    connect_timeout: float = CONNECT_TIMEOUT
    response_timeout: float = RESPONSE_TIMEOUT


@dataclass
class NegotiatedParams:
    """Parameters negotiated during session establishment."""

    # Sink capabilities (from M3 response)
    sink_capabilities: WFDParameters | None = None

    # Selected streaming parameters (sent in M4)
    selected_video_width: int = 1280
    selected_video_height: int = 720
    selected_video_fps: int = 30
    selected_video_profile: str = "baseline"
    selected_audio_codec: str = "LPCM"

    # Transport (from M6 SETUP)
    rtp_port: int = 0           # UDP port to stream to
    rtsp_session_id: str = ""   # RTSP session identifier


class RTSPSession:
    """Manages an RTSP/WFD session with a Miracast sink.

    This implements the source-side of the WFD session negotiation.
    The session drives the M1-M7 handshake, then enters STREAMING state
    where the caller can begin sending RTP media.

    Usage:
        session = RTSPSession(config)
        session.establish()  # Blocks until STREAMING or ERROR
        # ... stream media to session.negotiated.rtp_port ...
        session.teardown()
    """

    def __init__(
        self,
        config: SessionConfig,
        on_state_change: Callable[[SessionState], None] | None = None,
    ):
        """Initialize an RTSP session.

        Args:
            config: Session configuration (peer IP, port, etc.)
            on_state_change: Optional callback invoked on state transitions.
        """
        self.config = config
        self._state = SessionState.INIT
        self._cseq = 0
        self._socket: socket.socket | None = None
        self._recv_buffer = b""
        self._on_state_change = on_state_change
        self._keepalive_thread: threading.Thread | None = None
        self._keepalive_stop = threading.Event()
        self._lock = threading.Lock()

        # Negotiated session parameters
        self.negotiated = NegotiatedParams()

        # Source capabilities (what we offer)
        self._source_params = WFDParameters.default_source_capabilities()

    @property
    def state(self) -> SessionState:
        """Current session state."""
        return self._state

    @property
    def is_established(self) -> bool:
        """Whether the session is in STREAMING state."""
        return self._state == SessionState.STREAMING

    def _set_state(self, new_state: SessionState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        logger.info(f"RTSP session state: {old_state.value} → {new_state.value}")
        if self._on_state_change:
            self._on_state_change(new_state)

    def _next_cseq(self) -> int:
        """Get the next CSeq number."""
        self._cseq += 1
        return self._cseq

    # ─────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────

    def establish(self) -> bool:
        """Establish the RTSP/WFD session (M1-M7).

        This blocks until the session reaches STREAMING state or fails.

        Returns:
            True if session established successfully, False otherwise.

        Raises:
            ConnectionError: If TCP connection to sink fails.
            TimeoutError: If a response is not received within timeout.
            RuntimeError: If session negotiation fails.
        """
        try:
            self._connect()
            self._do_m1_options()
            self._handle_m2_options()
            self._do_m3_get_parameter()
            self._do_m4_set_parameter()
            self._do_m5_trigger_setup()
            self._handle_m6_setup()
            self._handle_m7_play()
            self._set_state(SessionState.STREAMING)
            self._start_keepalive()
            return True
        except Exception as e:
            logger.error(f"Session establishment failed: {e}")
            self._set_state(SessionState.ERROR)
            self._cleanup()
            raise

    def teardown(self) -> None:
        """Tear down the session (M8-M9).

        Sends trigger TEARDOWN and waits for the sink's TEARDOWN request.
        """
        if self._state not in (SessionState.STREAMING, SessionState.M7_RECEIVED):
            logger.warning(f"Cannot teardown from state {self._state.value}")
            return

        self._stop_keepalive()
        self._set_state(SessionState.TEARDOWN)

        try:
            # M8: Source sends SET_PARAMETER with trigger TEARDOWN
            cseq = self._next_cseq()
            params = WFDParameters(trigger_method=WFDTriggerMethod.TEARDOWN)
            request = RTSPRequest(
                method=RTSPMethod.SET_PARAMETER,
                uri=self.config.presentation_url or "*",
                headers={
                    "CSeq": str(cseq),
                    "Session": self.negotiated.rtsp_session_id,
                },
                body=params.format_body(),
            )
            self._send(request.serialize())
            response = self._recv_response()
            if response.status_code != 200:
                logger.warning(f"Trigger TEARDOWN got {response.status_code}")

            # M9: Expect TEARDOWN request from sink
            try:
                teardown_req = self._recv_request(timeout=5.0)
                if teardown_req.method == RTSPMethod.TEARDOWN:
                    # Send 200 OK
                    resp = RTSPResponse.ok(teardown_req.cseq or 0)
                    self._send(resp.serialize())
            except TimeoutError:
                logger.debug("No TEARDOWN request received from sink (timeout)")

        except Exception as e:
            logger.warning(f"Error during teardown: {e}")
        finally:
            self._set_state(SessionState.DONE)
            self._cleanup()

    def close(self) -> None:
        """Force-close the session without graceful teardown."""
        self._stop_keepalive()
        self._set_state(SessionState.DONE)
        self._cleanup()

    # ─────────────────────────────────────────────────────────
    # Session establishment steps
    # ─────────────────────────────────────────────────────────

    def _connect(self) -> None:
        """Establish TCP connection to sink's RTSP control port."""
        logger.info(
            f"Connecting to {self.config.peer_ip}:{self.config.control_port}"
        )
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(self.config.connect_timeout)
        try:
            self._socket.connect((self.config.peer_ip, self.config.control_port))
        except (TimeoutError, OSError) as e:
            raise ConnectionError(
                f"Failed to connect to {self.config.peer_ip}:{self.config.control_port}: {e}"
            ) from e
        logger.info("TCP connection established")

    def _do_m1_options(self) -> None:
        """M1: Source → Sink: OPTIONS (query sink capabilities)."""
        cseq = self._next_cseq()
        request = RTSPRequest(
            method=RTSPMethod.OPTIONS,
            uri="*",
            headers={
                "CSeq": str(cseq),
                "Require": "org.wfa.wfd1.0",
            },
        )
        self._send(request.serialize())
        self._set_state(SessionState.M1_SENT)

        response = self._recv_response()
        if response.status_code != 200:
            raise RuntimeError(f"M1 OPTIONS failed: {response.status_code} {response.reason}")

        # Parse the Public header for supported methods
        public = response.headers.get("Public", "")
        logger.info(f"M1: Sink supports methods: {public}")

    def _handle_m2_options(self) -> None:
        """M2: Sink → Source: OPTIONS (sink queries our capabilities).

        We respond with our supported methods.
        """
        request = self._recv_request()
        if request.method != RTSPMethod.OPTIONS:
            raise RuntimeError(f"Expected M2 OPTIONS, got {request.method.value}")

        # Respond with our supported methods
        supported_methods = "org.wfa.wfd1.0, GET_PARAMETER, SET_PARAMETER"
        response = RTSPResponse.ok(request.cseq or 0)
        response.headers["Public"] = supported_methods
        self._send(response.serialize())
        self._set_state(SessionState.M2_RECEIVED)
        logger.info("M2: Responded to sink OPTIONS")

    def _do_m3_get_parameter(self) -> None:
        """M3: Source → Sink: GET_PARAMETER (query sink WFD capabilities)."""
        cseq = self._next_cseq()
        request = RTSPRequest(
            method=RTSPMethod.GET_PARAMETER,
            uri="rtsp://localhost/wfd1.0",
            headers={"CSeq": str(cseq)},
            body=WFDParameters.m3_request_body(),
        )
        self._send(request.serialize())
        self._set_state(SessionState.M3_SENT)

        response = self._recv_response()
        if response.status_code != 200:
            raise RuntimeError(f"M3 GET_PARAMETER failed: {response.status_code}")

        # Parse sink capabilities from response body
        sink_params = WFDParameters.parse_body(response.body)
        self.negotiated.sink_capabilities = sink_params
        logger.info(f"M3: Sink capabilities received (RTP port: "
                    f"{sink_params.client_rtp_ports.port0 if sink_params.client_rtp_ports else 'unknown'})")

    def _do_m4_set_parameter(self) -> None:
        """M4: Source → Sink: SET_PARAMETER (set session parameters)."""
        sink_caps = self.negotiated.sink_capabilities

        # Determine RTP port from sink capabilities
        rtp_port = 19000  # Default
        if sink_caps and sink_caps.client_rtp_ports:
            rtp_port = sink_caps.client_rtp_ports.port0

        # Build presentation URL
        presentation_url = f"rtsp://{self.config.local_ip}/wfd1.0/streamid=0"
        self.config.presentation_url = presentation_url

        # Select best compatible video format
        selected_video = self._select_video_format(sink_caps)
        self.negotiated.selected_video_width = selected_video[0]
        self.negotiated.selected_video_height = selected_video[1]
        self.negotiated.selected_video_fps = selected_video[2]

        # Build M4 parameters
        params = WFDParameters(
            video_formats=self._source_params.video_formats,
            audio_codecs=self._source_params.audio_codecs,
            client_rtp_ports=WFDClientRTPPorts(port0=rtp_port, port1=0),
            presentation_url=f"{presentation_url} none",
        )

        cseq = self._next_cseq()
        request = RTSPRequest(
            method=RTSPMethod.SET_PARAMETER,
            uri="rtsp://localhost/wfd1.0",
            headers={"CSeq": str(cseq)},
            body=params.format_body(),
        )
        self._send(request.serialize())
        self._set_state(SessionState.M4_SENT)

        response = self._recv_response()
        if response.status_code != 200:
            raise RuntimeError(f"M4 SET_PARAMETER failed: {response.status_code}")
        logger.info("M4: Session parameters accepted by sink")

    def _do_m5_trigger_setup(self) -> None:
        """M5: Source → Sink: SET_PARAMETER with wfd_trigger_method: SETUP."""
        cseq = self._next_cseq()
        params = WFDParameters(trigger_method=WFDTriggerMethod.SETUP)
        request = RTSPRequest(
            method=RTSPMethod.SET_PARAMETER,
            uri="rtsp://localhost/wfd1.0",
            headers={"CSeq": str(cseq)},
            body=params.format_body(),
        )
        self._send(request.serialize())
        self._set_state(SessionState.M5_SENT)

        response = self._recv_response()
        if response.status_code != 200:
            raise RuntimeError(f"M5 trigger SETUP failed: {response.status_code}")
        logger.info("M5: Trigger SETUP accepted")

    def _handle_m6_setup(self) -> None:
        """M6: Sink → Source: SETUP (transport parameters)."""
        request = self._recv_request()
        if request.method != RTSPMethod.SETUP:
            raise RuntimeError(f"Expected M6 SETUP, got {request.method.value}")

        # Parse transport header: "RTP/AVP/UDP;unicast;client_port=19000"
        transport = request.headers.get("Transport", "")
        rtp_port = self._parse_transport_port(transport)
        self.negotiated.rtp_port = rtp_port

        # Generate session ID
        import uuid
        session_id = uuid.uuid4().hex[:16]
        self.negotiated.rtsp_session_id = session_id

        # Respond with 200 OK including session and transport
        response = RTSPResponse.ok(request.cseq or 0)
        response.headers["Session"] = f"{session_id};timeout={WFD_SESSION_TIMEOUT}"
        response.headers["Transport"] = (
            f"RTP/AVP/UDP;unicast;client_port={rtp_port};"
            f"server_port={rtp_port}"
        )
        self._send(response.serialize())
        self._set_state(SessionState.M6_RECEIVED)
        logger.info(f"M6: SETUP complete, RTP port={rtp_port}, session={session_id}")

    def _handle_m7_play(self) -> None:
        """M7: Sink → Source: PLAY (start streaming)."""
        request = self._recv_request()
        if request.method != RTSPMethod.PLAY:
            raise RuntimeError(f"Expected M7 PLAY, got {request.method.value}")

        # Respond with 200 OK
        response = RTSPResponse.ok(request.cseq or 0)
        response.headers["Session"] = self.negotiated.rtsp_session_id
        self._send(response.serialize())
        self._set_state(SessionState.M7_RECEIVED)
        logger.info("M7: PLAY received, ready to stream")

    # ─────────────────────────────────────────────────────────
    # Keep-alive (M14)
    # ─────────────────────────────────────────────────────────

    def _start_keepalive(self) -> None:
        """Start the keep-alive thread (M14: GET_PARAMETER every 15s)."""
        self._keepalive_stop.clear()
        self._keepalive_thread = threading.Thread(
            target=self._keepalive_loop, daemon=True
        )
        self._keepalive_thread.start()

    def _stop_keepalive(self) -> None:
        """Stop the keep-alive thread."""
        self._keepalive_stop.set()
        if self._keepalive_thread:
            self._keepalive_thread.join(timeout=3.0)
            self._keepalive_thread = None

    def _keepalive_loop(self) -> None:
        """Send periodic keep-alive messages."""
        while not self._keepalive_stop.wait(timeout=WFD_KEEPALIVE_INTERVAL):
            if self._state != SessionState.STREAMING:
                break
            try:
                with self._lock:
                    cseq = self._next_cseq()
                    request = RTSPRequest(
                        method=RTSPMethod.GET_PARAMETER,
                        uri=self.config.presentation_url or "*",
                        headers={
                            "CSeq": str(cseq),
                            "Session": self.negotiated.rtsp_session_id,
                        },
                    )
                    self._send(request.serialize())
                    response = self._recv_response()
                    if response.status_code != 200:
                        logger.warning(f"Keep-alive failed: {response.status_code}")
            except Exception as e:
                logger.warning(f"Keep-alive error: {e}")
                break

    # ─────────────────────────────────────────────────────────
    # Network I/O
    # ─────────────────────────────────────────────────────────

    def _send(self, data: bytes) -> None:
        """Send data over the TCP socket."""
        if not self._socket:
            raise RuntimeError("Not connected")
        try:
            self._socket.sendall(data)
        except OSError as e:
            raise ConnectionError(f"Send failed: {e}") from e

    def _recv_response(self, timeout: float | None = None) -> RTSPResponse:
        """Receive and parse an RTSP response from the sink.

        Args:
            timeout: Override default response timeout.

        Returns:
            Parsed RTSPResponse.

        Raises:
            TimeoutError: If no response received within timeout.
            RuntimeError: If received message is not a response.
        """
        msg = self._recv_message(timeout or self.config.response_timeout)
        if not isinstance(msg, RTSPResponse):
            raise RuntimeError(f"Expected response, got request: {msg}")
        return msg

    def _recv_request(self, timeout: float | None = None) -> RTSPRequest:
        """Receive and parse an RTSP request from the sink.

        Args:
            timeout: Override default response timeout.

        Returns:
            Parsed RTSPRequest.

        Raises:
            TimeoutError: If no request received within timeout.
            RuntimeError: If received message is not a request.
        """
        msg = self._recv_message(timeout or self.config.response_timeout)
        if not isinstance(msg, RTSPRequest):
            raise RuntimeError(f"Expected request, got response: {msg}")
        return msg

    def _recv_message(self, timeout: float):
        """Receive a complete RTSP message from the socket.

        Reads until we have a complete message (headers + body based on Content-Length).
        """
        if not self._socket:
            raise RuntimeError("Not connected")

        self._socket.settimeout(timeout)
        deadline = time.monotonic() + timeout

        while True:
            # Check if we already have a complete message in the buffer
            message = self._try_parse_buffer()
            if message is not None:
                return message

            # Read more data
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for RTSP message") from None

            self._socket.settimeout(remaining)
            try:
                chunk = self._socket.recv(RECV_BUFFER_SIZE)
            except TimeoutError:
                raise TimeoutError("Timed out waiting for RTSP message") from None

            if not chunk:
                raise ConnectionError("Connection closed by peer")

            self._recv_buffer += chunk

            # Prevent unbounded buffer growth (DoS protection)
            if len(self._recv_buffer) > MAX_RECV_BUFFER_SIZE:
                raise RuntimeError(
                    f"Receive buffer exceeded {MAX_RECV_BUFFER_SIZE} bytes "
                    f"without a complete message — possible attack or malformed peer"
                )

    def _try_parse_buffer(self):
        """Try to parse a complete RTSP message from the receive buffer.

        Returns None if the buffer doesn't contain a complete message yet.
        """
        # Need at least the header section (ends with \r\n\r\n)
        header_end = self._recv_buffer.find(b"\r\n\r\n")
        if header_end == -1:
            # Try with just \n\n as well
            header_end = self._recv_buffer.find(b"\n\n")
            if header_end == -1:
                return None
            separator_len = 2
        else:
            separator_len = 4

        # Parse headers to find Content-Length
        header_data = self._recv_buffer[:header_end].decode("utf-8", errors="replace")
        content_length = 0
        for line in header_data.split("\n"):
            if line.strip().lower().startswith("content-length:"):
                with contextlib.suppress(ValueError):
                    content_length = int(line.split(":", 1)[1].strip())
                break

        # Reject absurdly large Content-Length (DoS protection)
        if content_length > MAX_CONTENT_LENGTH:
            self._recv_buffer = b""
            raise RuntimeError(
                f"Content-Length {content_length} exceeds maximum "
                f"{MAX_CONTENT_LENGTH} — rejecting message"
            )

        # Check if we have the full message (headers + separator + body)
        total_length = header_end + separator_len + content_length
        if len(self._recv_buffer) < total_length:
            return None

        # Extract the complete message and remove from buffer
        message_data = self._recv_buffer[:total_length]
        self._recv_buffer = self._recv_buffer[total_length:]

        return parse_rtsp_message(message_data)

    # ─────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────

    def _select_video_format(
        self, sink_caps: WFDParameters | None
    ) -> tuple[int, int, int]:
        """Select the best video format compatible with the sink.

        Returns (width, height, fps) tuple.
        """
        # Default: 1280x720p30 (mandatory WFD resolution)
        default = (1280, 720, 30)

        if not sink_caps or not sink_caps.video_formats:
            return default

        formats = sink_caps.video_formats.get_supported_resolutions()
        if not formats:
            return default

        # Prefer highest resolution that's <= 1080p30
        best = default
        for fmt in formats:
            if fmt.interlaced:
                continue
            pixels = fmt.width * fmt.height
            if pixels >= best[0] * best[1] and fmt.fps >= best[2] and pixels <= 1920 * 1080 and fmt.fps <= 60:
                    best = (fmt.width, fmt.height, fmt.fps)

        return best

    @staticmethod
    def _parse_transport_port(transport: str) -> int:
        """Parse client_port from RTSP Transport header.

        Args:
            transport: Transport header value like
                      'RTP/AVP/UDP;unicast;client_port=19000'

        Returns:
            Client RTP port number.
        """
        for param in transport.split(";"):
            param = param.strip()
            if param.startswith("client_port="):
                port_str = param.split("=", 1)[1]
                # May be "port" or "port-port" range
                port_str = port_str.split("-")[0]
                try:
                    port = int(port_str)
                    if 1 <= port <= 65535:
                        return port
                except ValueError:
                    pass

        # Fallback to default
        return 19000

    def _cleanup(self) -> None:
        """Clean up socket and threads."""
        self._stop_keepalive()
        if self._socket:
            with contextlib.suppress(Exception):
                self._socket.close()
            self._socket = None
        self._recv_buffer = b""
