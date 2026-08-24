"""RTSP 1.0 message parser and builder (RFC 2326).

Implements the subset of RTSP required by Wi-Fi Display Technical Specification v2.3.
The WFD protocol uses RTSP 1.0 (NOT RTSP 2.0 / RFC 7826).

Reference: RFC 2326 §6 (Request), §7 (Response), §12 (Header fields)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class RTSPVersion(enum.Enum):
    """RTSP protocol version."""

    RTSP_1_0 = "RTSP/1.0"


class RTSPMethod(enum.Enum):
    """RTSP methods used in Wi-Fi Display session management.

    Reference: WFD Technical Specification v2.3 §4.5, Table 4-5
    """

    OPTIONS = "OPTIONS"
    GET_PARAMETER = "GET_PARAMETER"
    SET_PARAMETER = "SET_PARAMETER"
    SETUP = "SETUP"
    PLAY = "PLAY"
    PAUSE = "PAUSE"
    TEARDOWN = "TEARDOWN"


class RTSPStatusCode(enum.IntEnum):
    """Common RTSP status codes (RFC 2326 §7.1.1)."""

    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    SESSION_NOT_FOUND = 454
    METHOD_NOT_VALID = 455
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    SERVICE_UNAVAILABLE = 503


# Standard reason phrases per RFC 2326
_STATUS_PHRASES: dict[int, str] = {
    200: "OK",
    400: "Bad Request",
    401: "Unauthorized",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    454: "Session Not Found",
    455: "Method Not Valid in This State",
    500: "Internal Server Error",
    501: "Not Implemented",
    503: "Service Unavailable",
}


@dataclass
class RTSPMessage:
    """Base class for RTSP messages.

    Both requests and responses share headers and an optional body.
    """

    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""

    @property
    def cseq(self) -> int | None:
        """Get the CSeq header value."""
        val = self.headers.get("CSeq")
        if val is not None:
            try:
                return int(val)
            except ValueError:
                return None
        return None

    @cseq.setter
    def cseq(self, value: int) -> None:
        """Set the CSeq header value."""
        self.headers["CSeq"] = str(value)

    @property
    def content_length(self) -> int:
        """Get the Content-Length header value."""
        val = self.headers.get("Content-Length")
        if val is not None:
            try:
                return int(val)
            except ValueError:
                return 0
        return 0

    @property
    def session_id(self) -> str | None:
        """Get the Session header value (may include timeout parameter)."""
        val = self.headers.get("Session")
        if val is not None:
            # Session header can be "session-id;timeout=N"
            return val.split(";")[0].strip()
        return None


@dataclass
class RTSPRequest(RTSPMessage):
    """An RTSP request message.

    Format (RFC 2326 §6.1):
        Method SP Request-URI SP RTSP-Version CRLF
        *(general-header | request-header | entity-header) CRLF
        CRLF
        [message-body]
    """

    method: RTSPMethod = RTSPMethod.OPTIONS
    uri: str = "*"
    version: RTSPVersion = RTSPVersion.RTSP_1_0

    def serialize(self) -> bytes:
        """Serialize the request to bytes for transmission."""
        lines: list[str] = []

        # Request line
        lines.append(f"{self.method.value} {self.uri} {self.version.value}")

        # Update Content-Length if body is present
        if self.body:
            self.headers["Content-Length"] = str(len(self.body.encode("utf-8")))
            if "Content-Type" not in self.headers:
                self.headers["Content-Type"] = "text/parameters"

        # Headers
        for key, value in self.headers.items():
            lines.append(f"{key}: {value}")

        # Blank line separator (two empty strings produce \r\n\r\n when joined)
        lines.append("")
        lines.append("")

        result = "\r\n".join(lines)

        # Body (appended after the double CRLF)
        if self.body:
            # Remove the trailing \r\n from the join and add body
            result = result.rstrip("\r\n") + "\r\n\r\n" + self.body

        return result.encode("utf-8")

    @classmethod
    def parse(cls, data: bytes) -> RTSPRequest:
        """Parse raw bytes into an RTSPRequest.

        Args:
            data: Raw bytes received from network.

        Returns:
            Parsed RTSPRequest object.

        Raises:
            ValueError: If the data is not a valid RTSP request.
        """
        text = data.decode("utf-8", errors="replace")
        return cls.parse_text(text)

    @classmethod
    def parse_text(cls, text: str) -> RTSPRequest:
        """Parse a text string into an RTSPRequest.

        Args:
            text: RTSP request as string.

        Returns:
            Parsed RTSPRequest object.

        Raises:
            ValueError: If the text is not a valid RTSP request.
        """
        # Split header section from body
        if "\r\n\r\n" in text:
            header_section, body = text.split("\r\n\r\n", 1)
        elif "\n\n" in text:
            header_section, body = text.split("\n\n", 1)
        else:
            header_section = text
            body = ""

        lines = header_section.replace("\r\n", "\n").split("\n")
        if not lines:
            raise ValueError("Empty RTSP request")

        # Parse request line: "METHOD URI RTSP/1.0"
        request_line = lines[0].strip()
        parts = request_line.split(" ", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid request line: {request_line!r}")

        method_str, uri, version_str = parts

        try:
            method = RTSPMethod(method_str)
        except ValueError:
            raise ValueError(f"Unknown RTSP method: {method_str!r}") from None

        if version_str != "RTSP/1.0":
            raise ValueError(f"Unsupported RTSP version: {version_str!r}")

        # Parse headers
        headers: dict[str, str] = {}
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip()] = value.strip()

        return cls(
            method=method,
            uri=uri,
            version=RTSPVersion.RTSP_1_0,
            headers=headers,
            body=body.strip(),
        )


@dataclass
class RTSPResponse(RTSPMessage):
    """An RTSP response message.

    Format (RFC 2326 §7.1):
        RTSP-Version SP Status-Code SP Reason-Phrase CRLF
        *(general-header | response-header | entity-header) CRLF
        CRLF
        [message-body]
    """

    version: RTSPVersion = RTSPVersion.RTSP_1_0
    status_code: int = 200
    reason: str = "OK"

    def serialize(self) -> bytes:
        """Serialize the response to bytes for transmission."""
        lines: list[str] = []

        # Status line
        lines.append(f"{self.version.value} {self.status_code} {self.reason}")

        # Update Content-Length if body is present
        if self.body:
            self.headers["Content-Length"] = str(len(self.body.encode("utf-8")))
            if "Content-Type" not in self.headers:
                self.headers["Content-Type"] = "text/parameters"

        # Headers
        for key, value in self.headers.items():
            lines.append(f"{key}: {value}")

        # Blank line separator (two empty strings produce \r\n\r\n when joined)
        lines.append("")
        lines.append("")

        result = "\r\n".join(lines)

        # Body (appended after the double CRLF)
        if self.body:
            result = result.rstrip("\r\n") + "\r\n\r\n" + self.body

        return result.encode("utf-8")

    @classmethod
    def parse(cls, data: bytes) -> RTSPResponse:
        """Parse raw bytes into an RTSPResponse.

        Args:
            data: Raw bytes received from network.

        Returns:
            Parsed RTSPResponse object.

        Raises:
            ValueError: If the data is not a valid RTSP response.
        """
        text = data.decode("utf-8", errors="replace")
        return cls.parse_text(text)

    @classmethod
    def parse_text(cls, text: str) -> RTSPResponse:
        """Parse a text string into an RTSPResponse.

        Args:
            text: RTSP response as string.

        Returns:
            Parsed RTSPResponse object.

        Raises:
            ValueError: If the text is not a valid RTSP response.
        """
        # Split header section from body
        if "\r\n\r\n" in text:
            header_section, body = text.split("\r\n\r\n", 1)
        elif "\n\n" in text:
            header_section, body = text.split("\n\n", 1)
        else:
            header_section = text
            body = ""

        lines = header_section.replace("\r\n", "\n").split("\n")
        if not lines:
            raise ValueError("Empty RTSP response")

        # Parse status line: "RTSP/1.0 200 OK"
        status_line = lines[0].strip()
        parts = status_line.split(" ", 2)
        if len(parts) < 2:
            raise ValueError(f"Invalid status line: {status_line!r}")

        version_str = parts[0]
        if version_str != "RTSP/1.0":
            raise ValueError(f"Unsupported RTSP version: {version_str!r}")

        try:
            status_code = int(parts[1])
        except ValueError:
            raise ValueError(f"Invalid status code: {parts[1]!r}") from None

        reason = parts[2] if len(parts) > 2 else _STATUS_PHRASES.get(status_code, "")

        # Parse headers
        headers: dict[str, str] = {}
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip()] = value.strip()

        return cls(
            version=RTSPVersion.RTSP_1_0,
            status_code=status_code,
            reason=reason,
            headers=headers,
            body=body.strip(),
        )

    @classmethod
    def ok(cls, cseq: int, **kwargs) -> RTSPResponse:
        """Create a 200 OK response."""
        resp = cls(status_code=200, reason="OK", **kwargs)
        resp.cseq = cseq
        return resp

    @classmethod
    def error(cls, status_code: int, cseq: int) -> RTSPResponse:
        """Create an error response."""
        reason = _STATUS_PHRASES.get(status_code, "Error")
        resp = cls(status_code=status_code, reason=reason)
        resp.cseq = cseq
        return resp


def parse_rtsp_message(data: bytes) -> RTSPMessage:
    """Parse raw bytes into either an RTSPRequest or RTSPResponse.

    Detects whether the message is a request or response based on the first line.

    Args:
        data: Raw bytes of an RTSP message.

    Returns:
        RTSPRequest or RTSPResponse.

    Raises:
        ValueError: If the data cannot be parsed as a valid RTSP message.
    """
    text = data.decode("utf-8", errors="replace").lstrip()

    if text.startswith("RTSP/"):
        return RTSPResponse.parse_text(text)
    else:
        return RTSPRequest.parse_text(text)
