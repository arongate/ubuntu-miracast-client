"""Comprehensive tests for RTSP 1.0 message parser/builder (RFC 2326)."""

import pytest

from miracast_client.rtsp.messages import (
    RTSPMethod,
    RTSPRequest,
    RTSPResponse,
    RTSPStatusCode,
    RTSPVersion,
    parse_rtsp_message,
)

# ─────────────────────────────────────────────────────────────
# RTSPRequest Tests
# ─────────────────────────────────────────────────────────────


class TestRTSPRequestParsing:
    """Tests for parsing RTSP requests."""

    def test_parse_options_request(self):
        """Parse a standard M1 OPTIONS request."""
        raw = b"OPTIONS * RTSP/1.0\r\nCSeq: 1\r\nRequire: org.wfa.wfd1.0\r\n\r\n"
        req = RTSPRequest.parse(raw)
        assert req.method == RTSPMethod.OPTIONS
        assert req.uri == "*"
        assert req.version == RTSPVersion.RTSP_1_0
        assert req.cseq == 1
        assert req.headers["Require"] == "org.wfa.wfd1.0"
        assert req.body == ""

    def test_parse_get_parameter_with_body(self):
        """Parse M3 GET_PARAMETER request with body."""
        raw = (
            b"GET_PARAMETER rtsp://localhost/wfd1.0 RTSP/1.0\r\n"
            b"CSeq: 3\r\n"
            b"Content-Type: text/parameters\r\n"
            b"Content-Length: 77\r\n"
            b"\r\n"
            b"wfd_video_formats\r\n"
            b"wfd_audio_codecs\r\n"
            b"wfd_client_rtp_ports\r\n"
            b"wfd_content_protection"
        )
        req = RTSPRequest.parse(raw)
        assert req.method == RTSPMethod.GET_PARAMETER
        assert req.uri == "rtsp://localhost/wfd1.0"
        assert req.cseq == 3
        assert "wfd_video_formats" in req.body
        assert "wfd_content_protection" in req.body

    def test_parse_set_parameter_wfd_trigger(self):
        """Parse M5 SET_PARAMETER with trigger method."""
        raw = (
            b"SET_PARAMETER rtsp://localhost/wfd1.0 RTSP/1.0\r\n"
            b"CSeq: 5\r\n"
            b"Content-Type: text/parameters\r\n"
            b"Content-Length: 24\r\n"
            b"\r\n"
            b"wfd_trigger_method: SETUP"
        )
        req = RTSPRequest.parse(raw)
        assert req.method == RTSPMethod.SET_PARAMETER
        assert req.cseq == 5
        assert "wfd_trigger_method: SETUP" in req.body

    def test_parse_setup_request(self):
        """Parse M6 SETUP request from sink."""
        raw = (
            b"SETUP rtsp://192.168.49.1/wfd1.0/streamid=0 RTSP/1.0\r\n"
            b"CSeq: 3\r\n"
            b"Transport: RTP/AVP/UDP;unicast;client_port=19000\r\n"
            b"\r\n"
        )
        req = RTSPRequest.parse(raw)
        assert req.method == RTSPMethod.SETUP
        assert "streamid=0" in req.uri
        assert req.headers["Transport"] == "RTP/AVP/UDP;unicast;client_port=19000"

    def test_parse_play_request(self):
        """Parse M7 PLAY request from sink."""
        raw = (
            b"PLAY rtsp://192.168.49.1/wfd1.0/streamid=0 RTSP/1.0\r\n"
            b"CSeq: 4\r\n"
            b"Session: abc123\r\n"
            b"\r\n"
        )
        req = RTSPRequest.parse(raw)
        assert req.method == RTSPMethod.PLAY
        assert req.session_id == "abc123"

    def test_parse_teardown_request(self):
        """Parse M9 TEARDOWN request from sink."""
        raw = (
            b"TEARDOWN rtsp://192.168.49.1/wfd1.0/streamid=0 RTSP/1.0\r\n"
            b"CSeq: 5\r\n"
            b"Session: abc123\r\n"
            b"\r\n"
        )
        req = RTSPRequest.parse(raw)
        assert req.method == RTSPMethod.TEARDOWN
        assert req.cseq == 5

    def test_parse_with_newline_only(self):
        """Parse request using \\n instead of \\r\\n."""
        raw = b"OPTIONS * RTSP/1.0\nCSeq: 1\n\n"
        req = RTSPRequest.parse(raw)
        assert req.method == RTSPMethod.OPTIONS
        assert req.cseq == 1

    def test_parse_invalid_method_raises(self):
        """Unknown method raises ValueError."""
        raw = b"INVALID * RTSP/1.0\r\nCSeq: 1\r\n\r\n"
        with pytest.raises(ValueError, match="Unknown RTSP method"):
            RTSPRequest.parse(raw)

    def test_parse_invalid_version_raises(self):
        """Wrong RTSP version raises ValueError."""
        raw = b"OPTIONS * RTSP/2.0\r\nCSeq: 1\r\n\r\n"
        with pytest.raises(ValueError, match="Unsupported RTSP version"):
            RTSPRequest.parse(raw)

    def test_parse_malformed_request_line(self):
        """Malformed request line raises ValueError."""
        raw = b"OPTIONS *\r\nCSeq: 1\r\n\r\n"
        with pytest.raises(ValueError, match="Invalid request line"):
            RTSPRequest.parse(raw)

    def test_parse_empty_raises(self):
        """Empty input raises ValueError."""
        with pytest.raises(ValueError):
            RTSPRequest.parse(b"")

    def test_session_id_with_timeout(self):
        """Session header with timeout parameter."""
        raw = b"PLAY rtsp://x/wfd1.0 RTSP/1.0\r\nCSeq: 1\r\nSession: deadbeef;timeout=30\r\n\r\n"
        req = RTSPRequest.parse(raw)
        assert req.session_id == "deadbeef"


class TestRTSPRequestSerialization:
    """Tests for serializing RTSP requests."""

    def test_serialize_options(self):
        """Serialize a simple OPTIONS request."""
        req = RTSPRequest(
            method=RTSPMethod.OPTIONS,
            uri="*",
            headers={"CSeq": "1", "Require": "org.wfa.wfd1.0"},
        )
        data = req.serialize()
        text = data.decode("utf-8")
        assert text.startswith("OPTIONS * RTSP/1.0\r\n")
        assert "CSeq: 1\r\n" in text
        assert "Require: org.wfa.wfd1.0\r\n" in text

    def test_serialize_with_body(self):
        """Serialize request with body adds Content-Length."""
        req = RTSPRequest(
            method=RTSPMethod.SET_PARAMETER,
            uri="rtsp://localhost/wfd1.0",
            headers={"CSeq": "5"},
            body="wfd_trigger_method: SETUP",
        )
        data = req.serialize()
        text = data.decode("utf-8")
        assert "Content-Length: 25" in text
        assert "Content-Type: text/parameters" in text
        assert text.endswith("wfd_trigger_method: SETUP")

    def test_roundtrip_request(self):
        """Serialize then parse should produce equivalent request."""
        original = RTSPRequest(
            method=RTSPMethod.GET_PARAMETER,
            uri="rtsp://192.168.49.1/wfd1.0",
            headers={"CSeq": "3"},
            body="wfd_video_formats\r\nwfd_audio_codecs",
        )
        data = original.serialize()
        parsed = RTSPRequest.parse(data)
        assert parsed.method == original.method
        assert parsed.uri == original.uri
        assert parsed.cseq == 3
        assert "wfd_video_formats" in parsed.body


# ─────────────────────────────────────────────────────────────
# RTSPResponse Tests
# ─────────────────────────────────────────────────────────────


class TestRTSPResponseParsing:
    """Tests for parsing RTSP responses."""

    def test_parse_200_ok(self):
        """Parse a 200 OK response."""
        raw = (
            b"RTSP/1.0 200 OK\r\n"
            b"CSeq: 1\r\n"
            b"Public: org.wfa.wfd1.0, GET_PARAMETER, SET_PARAMETER\r\n"
            b"\r\n"
        )
        resp = RTSPResponse.parse(raw)
        assert resp.status_code == 200
        assert resp.reason == "OK"
        assert resp.cseq == 1
        assert "GET_PARAMETER" in resp.headers["Public"]

    def test_parse_200_with_body(self):
        """Parse M3 response with WFD parameters body."""
        raw = (
            b"RTSP/1.0 200 OK\r\n"
            b"CSeq: 3\r\n"
            b"Content-Type: text/parameters\r\n"
            b"Content-Length: 120\r\n"
            b"\r\n"
            b"wfd_video_formats: 00 00 01 02 000000A1 00000000 00000000 00 0000 0000 00 none none\r\n"
            b"wfd_audio_codecs: LPCM 00000003 00\r\n"
            b"wfd_client_rtp_ports: RTP/AVP/UDP;unicast 19000 0 mode=play"
        )
        resp = RTSPResponse.parse(raw)
        assert resp.status_code == 200
        assert "wfd_video_formats" in resp.body
        assert "wfd_audio_codecs" in resp.body
        assert "wfd_client_rtp_ports" in resp.body

    def test_parse_error_response(self):
        """Parse a 406 Not Acceptable response."""
        raw = b"RTSP/1.0 406 Not Acceptable\r\nCSeq: 4\r\n\r\n"
        resp = RTSPResponse.parse(raw)
        assert resp.status_code == 406
        assert resp.reason == "Not Acceptable"

    def test_parse_status_without_reason(self):
        """Parse response with status code but no reason phrase."""
        raw = b"RTSP/1.0 200\r\nCSeq: 1\r\n\r\n"
        resp = RTSPResponse.parse(raw)
        assert resp.status_code == 200
        # Should get default reason from lookup
        assert resp.reason == "OK"

    def test_parse_invalid_status_code(self):
        """Non-integer status code raises ValueError."""
        raw = b"RTSP/1.0 abc OK\r\nCSeq: 1\r\n\r\n"
        with pytest.raises(ValueError, match="Invalid status code"):
            RTSPResponse.parse(raw)

    def test_parse_invalid_version(self):
        """Wrong version raises ValueError."""
        raw = b"RTSP/2.0 200 OK\r\nCSeq: 1\r\n\r\n"
        with pytest.raises(ValueError, match="Unsupported RTSP version"):
            RTSPResponse.parse(raw)

    def test_parse_malformed_status_line(self):
        """Incomplete status line raises ValueError."""
        raw = b"RTSP/1.0\r\nCSeq: 1\r\n\r\n"
        with pytest.raises(ValueError, match="Invalid status line"):
            RTSPResponse.parse(raw)


class TestRTSPResponseSerialization:
    """Tests for serializing RTSP responses."""

    def test_serialize_200_ok(self):
        """Serialize a 200 OK response."""
        resp = RTSPResponse.ok(cseq=1)
        resp.headers["Public"] = "GET_PARAMETER, SET_PARAMETER"
        data = resp.serialize()
        text = data.decode("utf-8")
        assert text.startswith("RTSP/1.0 200 OK\r\n")
        assert "CSeq: 1\r\n" in text

    def test_serialize_with_body(self):
        """Serialize response with body."""
        resp = RTSPResponse.ok(cseq=3)
        resp.body = (
            "wfd_video_formats: 00 00 01 02 000000A1 00000000 00000000 00 0000 0000 00 none none"
        )
        data = resp.serialize()
        text = data.decode("utf-8")
        assert "Content-Length:" in text
        assert "wfd_video_formats" in text

    def test_error_factory(self):
        """RTSPResponse.error creates proper error response."""
        resp = RTSPResponse.error(454, cseq=7)
        assert resp.status_code == 454
        assert resp.reason == "Session Not Found"
        assert resp.cseq == 7

    def test_roundtrip_response(self):
        """Serialize then parse should produce equivalent response."""
        original = RTSPResponse.ok(cseq=5)
        original.headers["Session"] = "abc123;timeout=30"
        original.body = "wfd_trigger_method: SETUP"
        data = original.serialize()
        parsed = RTSPResponse.parse(data)
        assert parsed.status_code == 200
        assert parsed.cseq == 5
        assert parsed.session_id == "abc123"
        assert "SETUP" in parsed.body


# ─────────────────────────────────────────────────────────────
# parse_rtsp_message Tests
# ─────────────────────────────────────────────────────────────


class TestParseRTSPMessage:
    """Tests for the generic parse_rtsp_message function."""

    def test_detects_request(self):
        """Correctly identifies and parses a request."""
        raw = b"OPTIONS * RTSP/1.0\r\nCSeq: 1\r\n\r\n"
        msg = parse_rtsp_message(raw)
        assert isinstance(msg, RTSPRequest)
        assert msg.method == RTSPMethod.OPTIONS

    def test_detects_response(self):
        """Correctly identifies and parses a response."""
        raw = b"RTSP/1.0 200 OK\r\nCSeq: 1\r\n\r\n"
        msg = parse_rtsp_message(raw)
        assert isinstance(msg, RTSPResponse)
        assert msg.status_code == 200

    def test_leading_whitespace(self):
        """Handles leading whitespace in message."""
        raw = b"  \r\n  RTSP/1.0 200 OK\r\nCSeq: 1\r\n\r\n"
        msg = parse_rtsp_message(raw)
        assert isinstance(msg, RTSPResponse)


# ─────────────────────────────────────────────────────────────
# Edge Cases and Properties
# ─────────────────────────────────────────────────────────────


class TestRTSPMessageProperties:
    """Tests for message property accessors."""

    def test_cseq_getter_none(self):
        """CSeq is None when header not present."""
        msg = RTSPRequest(method=RTSPMethod.OPTIONS)
        assert msg.cseq is None

    def test_cseq_getter_invalid(self):
        """CSeq is None when header is not a valid integer."""
        msg = RTSPRequest(method=RTSPMethod.OPTIONS, headers={"CSeq": "abc"})
        assert msg.cseq is None

    def test_cseq_setter(self):
        """CSeq setter updates the header."""
        msg = RTSPRequest(method=RTSPMethod.OPTIONS)
        msg.cseq = 42
        assert msg.headers["CSeq"] == "42"
        assert msg.cseq == 42

    def test_content_length_default(self):
        """Content-Length is 0 when not present."""
        msg = RTSPRequest(method=RTSPMethod.OPTIONS)
        assert msg.content_length == 0

    def test_content_length_from_header(self):
        """Content-Length parsed from header."""
        msg = RTSPRequest(headers={"Content-Length": "128"})
        assert msg.content_length == 128

    def test_session_id_none(self):
        """Session ID is None when header not present."""
        msg = RTSPRequest(method=RTSPMethod.OPTIONS)
        assert msg.session_id is None

    def test_status_codes_enum(self):
        """RTSPStatusCode enum has expected values."""
        assert RTSPStatusCode.OK == 200
        assert RTSPStatusCode.NOT_FOUND == 404
        assert RTSPStatusCode.SESSION_NOT_FOUND == 454

    def test_rtsp_method_values(self):
        """All expected RTSP methods are defined."""
        assert RTSPMethod.OPTIONS.value == "OPTIONS"
        assert RTSPMethod.GET_PARAMETER.value == "GET_PARAMETER"
        assert RTSPMethod.SET_PARAMETER.value == "SET_PARAMETER"
        assert RTSPMethod.SETUP.value == "SETUP"
        assert RTSPMethod.PLAY.value == "PLAY"
        assert RTSPMethod.PAUSE.value == "PAUSE"
        assert RTSPMethod.TEARDOWN.value == "TEARDOWN"
