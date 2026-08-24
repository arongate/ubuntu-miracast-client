"""Comprehensive tests for WFD parameters parsing and formatting."""

import pytest

from miracast_client.rtsp.wfd_params import (
    CEA_RESOLUTIONS,
    HH_RESOLUTIONS,
    VESA_RESOLUTIONS,
    AudioCodec,
    AudioCodecType,
    VideoFormat,
    VideoLevel,
    VideoProfile,
    WFDAudioCodecs,
    WFDClientRTPPorts,
    WFDParameters,
    WFDTriggerMethod,
    WFDVideoFormats,
)

# ─────────────────────────────────────────────────────────────
# VideoFormat Tests
# ─────────────────────────────────────────────────────────────


class TestVideoFormat:
    """Tests for VideoFormat dataclass."""

    def test_basic_format(self):
        """Create a basic video format."""
        fmt = VideoFormat(width=1920, height=1080, fps=30)
        assert fmt.width == 1920
        assert fmt.height == 1080
        assert fmt.fps == 30
        assert fmt.interlaced is False
        assert fmt.profile == VideoProfile.CONSTRAINED_BASELINE
        assert fmt.level == VideoLevel.LEVEL_3_1

    def test_description_progressive(self):
        """Description for progressive format."""
        fmt = VideoFormat(width=1280, height=720, fps=60)
        assert fmt.description == "1280x720p60"

    def test_description_interlaced(self):
        """Description for interlaced format."""
        fmt = VideoFormat(width=1920, height=1080, fps=60, interlaced=True)
        assert fmt.description == "1920x1080i60"

    def test_resolution_tables_not_empty(self):
        """All resolution tables have entries."""
        assert len(CEA_RESOLUTIONS) > 0
        assert len(VESA_RESOLUTIONS) > 0
        assert len(HH_RESOLUTIONS) > 0

    def test_cea_mandatory_resolution(self):
        """CEA table contains mandatory 1280x720p30."""
        found = False
        for _bit, res in CEA_RESOLUTIONS.items():
            if res == (1280, 720, 30, False):
                found = True
                break
        assert found, "Mandatory 1280x720p30 not found in CEA table"

    def test_cea_640x480p60(self):
        """CEA bit 0 is 640x480p60."""
        assert CEA_RESOLUTIONS[0] == (640, 480, 60, False)

    def test_vesa_800x600p30(self):
        """VESA bit 0 is 800x600p30."""
        assert VESA_RESOLUTIONS[0] == (800, 600, 30, False)


# ─────────────────────────────────────────────────────────────
# WFDVideoFormats Tests
# ─────────────────────────────────────────────────────────────


class TestWFDVideoFormats:
    """Tests for WFD video formats parsing and formatting."""

    def test_parse_minimal(self):
        """Parse minimal video formats (7 fields)."""
        text = "00 00 01 02 000000A1 00000000 00000000"
        vf = WFDVideoFormats.parse_wfd(text)
        assert vf.native == 0x00
        assert vf.preferred_display == 0x00
        assert vf.profile == 0x01  # CBP
        assert vf.level == 0x02    # Level 3.1
        assert vf.cea_bitmap == 0x000000A1
        assert vf.vesa_bitmap == 0x00000000
        assert vf.hh_bitmap == 0x00000000

    def test_parse_full(self):
        """Parse full video formats with all fields."""
        text = "00 00 02 02 0000FFFF 0FFFFFFF 00000FFF 00 0000 0000 01 none none"
        vf = WFDVideoFormats.parse_wfd(text)
        assert vf.profile == 0x02
        assert vf.cea_bitmap == 0x0000FFFF
        assert vf.vesa_bitmap == 0x0FFFFFFF
        assert vf.hh_bitmap == 0x00000FFF
        assert vf.frame_rate_control == 0x01

    def test_parse_invalid_too_few_fields(self):
        """Parse with too few fields raises ValueError."""
        with pytest.raises(ValueError, match="at least 7 fields"):
            WFDVideoFormats.parse_wfd("00 00 01")

    def test_parse_invalid_hex(self):
        """Invalid hex values raise ValueError."""
        with pytest.raises(ValueError, match="Invalid hex"):
            WFDVideoFormats.parse_wfd("ZZ 00 01 02 000000A1 00000000 00000000")

    def test_get_supported_resolutions_cea(self):
        """Get resolutions from CEA bitmap."""
        # Bit 0 (640x480p60) + Bit 5 (1280x720p30) + Bit 7 (1920x1080p30)
        vf = WFDVideoFormats(cea_bitmap=0x000000A1)
        resolutions = vf.get_supported_resolutions()
        widths = [(r.width, r.height, r.fps) for r in resolutions]
        assert (640, 480, 60) in widths
        assert (1280, 720, 30) in widths
        assert (1920, 1080, 30) in widths

    def test_get_supported_resolutions_vesa(self):
        """Get resolutions from VESA bitmap."""
        vf = WFDVideoFormats(cea_bitmap=0, vesa_bitmap=0x01)  # Bit 0 = 800x600p30
        resolutions = vf.get_supported_resolutions()
        assert len(resolutions) == 1
        assert resolutions[0].width == 800
        assert resolutions[0].height == 600

    def test_get_supported_resolutions_empty(self):
        """Empty bitmaps return no resolutions."""
        vf = WFDVideoFormats(cea_bitmap=0, vesa_bitmap=0, hh_bitmap=0)
        assert vf.get_supported_resolutions() == []

    def test_format_wfd_roundtrip(self):
        """format_wfd() output can be parsed back."""
        original = WFDVideoFormats(
            native=0x00, preferred_display=0x00, profile=0x01, level=0x02,
            cea_bitmap=0x000000A1, vesa_bitmap=0x00000000, hh_bitmap=0x00000000,
        )
        text = original.format_wfd()
        parsed = WFDVideoFormats.parse_wfd(text)
        assert parsed.profile == original.profile
        assert parsed.cea_bitmap == original.cea_bitmap


# ─────────────────────────────────────────────────────────────
# AudioCodec Tests
# ─────────────────────────────────────────────────────────────


class TestAudioCodec:
    """Tests for AudioCodec parsing and formatting."""

    def test_parse_lpcm(self):
        """Parse LPCM audio codec."""
        codec = AudioCodec.parse_wfd("LPCM 00000003 00")
        assert codec.codec == AudioCodecType.LPCM
        assert codec.modes == 0x03
        assert codec.latency == 0

    def test_parse_aac(self):
        """Parse AAC audio codec."""
        codec = AudioCodec.parse_wfd("AAC 00000007 00")
        assert codec.codec == AudioCodecType.AAC
        assert codec.modes == 0x07
        assert codec.latency == 0

    def test_parse_ac3(self):
        """Parse AC3 audio codec."""
        codec = AudioCodec.parse_wfd("AC3 00000001 02")
        assert codec.codec == AudioCodecType.AC3
        assert codec.modes == 0x01
        assert codec.latency == 0x02

    def test_parse_invalid_codec_name(self):
        """Unknown codec name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown audio codec"):
            AudioCodec.parse_wfd("MP3 00000001 00")

    def test_parse_invalid_format(self):
        """Wrong number of parts raises ValueError."""
        with pytest.raises(ValueError, match="Invalid audio codec format"):
            AudioCodec.parse_wfd("LPCM 00000003")

    def test_parse_invalid_hex(self):
        """Invalid hex in modes raises ValueError."""
        with pytest.raises(ValueError, match="Invalid modes bitmap"):
            AudioCodec.parse_wfd("LPCM ZZZZZZZZ 00")

    def test_format_wfd(self):
        """Format back to WFD string."""
        codec = AudioCodec(codec=AudioCodecType.LPCM, modes=0x03, latency=0)
        assert codec.format_wfd() == "LPCM 00000003 00"

    def test_sample_rates_lpcm(self):
        """LPCM sample rates from mode bitmap."""
        codec = AudioCodec(codec=AudioCodecType.LPCM, modes=0x03)
        rates = codec.sample_rates
        assert 44100 in rates
        assert 48000 in rates

    def test_sample_rates_lpcm_48k_only(self):
        """LPCM with only 48kHz."""
        codec = AudioCodec(codec=AudioCodecType.LPCM, modes=0x02)
        rates = codec.sample_rates
        assert 48000 in rates
        assert 44100 not in rates

    def test_sample_rates_aac(self):
        """AAC sample rates from mode bitmap."""
        codec = AudioCodec(codec=AudioCodecType.AAC, modes=0x07)
        rates = codec.sample_rates
        assert 48000 in rates


# ─────────────────────────────────────────────────────────────
# WFDAudioCodecs Tests
# ─────────────────────────────────────────────────────────────


class TestWFDAudioCodecs:
    """Tests for WFDAudioCodecs parsing and formatting."""

    def test_parse_single_codec(self):
        """Parse single codec."""
        ac = WFDAudioCodecs.parse_wfd("LPCM 00000003 00")
        assert len(ac.codecs) == 1
        assert ac.codecs[0].codec == AudioCodecType.LPCM

    def test_parse_multiple_codecs(self):
        """Parse multiple codecs separated by comma."""
        ac = WFDAudioCodecs.parse_wfd("LPCM 00000003 00, AAC 00000007 00")
        assert len(ac.codecs) == 2
        assert ac.codecs[0].codec == AudioCodecType.LPCM
        assert ac.codecs[1].codec == AudioCodecType.AAC

    def test_parse_none(self):
        """Parse 'none' value."""
        ac = WFDAudioCodecs.parse_wfd("none")
        assert ac.codecs == []

    def test_format_wfd_none(self):
        """Format empty codecs as 'none'."""
        ac = WFDAudioCodecs(codecs=[])
        assert ac.format_wfd() == "none"

    def test_format_wfd_multiple(self):
        """Format multiple codecs."""
        ac = WFDAudioCodecs(codecs=[
            AudioCodec(codec=AudioCodecType.LPCM, modes=0x03, latency=0),
            AudioCodec(codec=AudioCodecType.AAC, modes=0x01, latency=0),
        ])
        result = ac.format_wfd()
        assert "LPCM 00000003 00" in result
        assert "AAC 00000001 00" in result
        assert ", " in result

    def test_default_source(self):
        """Default source capabilities include LPCM."""
        ac = WFDAudioCodecs.default_source()
        assert len(ac.codecs) == 1
        assert ac.codecs[0].codec == AudioCodecType.LPCM


# ─────────────────────────────────────────────────────────────
# WFDClientRTPPorts Tests
# ─────────────────────────────────────────────────────────────


class TestWFDClientRTPPorts:
    """Tests for WFDClientRTPPorts parsing and formatting."""

    def test_parse_standard(self):
        """Parse standard RTP ports."""
        ports = WFDClientRTPPorts.parse_wfd("RTP/AVP/UDP;unicast 19000 0 mode=play")
        assert ports.profile == "RTP/AVP/UDP;unicast"
        assert ports.port0 == 19000
        assert ports.port1 == 0
        assert ports.mode == "play"

    def test_parse_custom_port(self):
        """Parse with custom port number."""
        ports = WFDClientRTPPorts.parse_wfd("RTP/AVP/UDP;unicast 5004 5005 mode=play")
        assert ports.port0 == 5004
        assert ports.port1 == 5005

    def test_parse_invalid_too_few_parts(self):
        """Too few parts raises ValueError."""
        with pytest.raises(ValueError, match="need 4 parts"):
            WFDClientRTPPorts.parse_wfd("RTP/AVP/UDP;unicast 19000")

    def test_parse_invalid_port(self):
        """Non-numeric port raises ValueError."""
        with pytest.raises(ValueError, match="Invalid port"):
            WFDClientRTPPorts.parse_wfd("RTP/AVP/UDP;unicast abc 0 mode=play")

    def test_parse_port_out_of_range(self):
        """Port > 65535 raises ValueError."""
        with pytest.raises(ValueError, match="Port out of range"):
            WFDClientRTPPorts.parse_wfd("RTP/AVP/UDP;unicast 70000 0 mode=play")

    def test_format_wfd(self):
        """Format to WFD string."""
        ports = WFDClientRTPPorts(port0=19000, port1=0)
        result = ports.format_wfd()
        assert "RTP/AVP/UDP;unicast" in result
        assert "19000" in result
        assert "mode=play" in result

    def test_format_roundtrip(self):
        """Format and parse roundtrip."""
        original = WFDClientRTPPorts(port0=19990, port1=0, mode="play")
        text = original.format_wfd()
        parsed = WFDClientRTPPorts.parse_wfd(text)
        assert parsed.port0 == original.port0
        assert parsed.port1 == original.port1


# ─────────────────────────────────────────────────────────────
# WFDParameters Tests
# ─────────────────────────────────────────────────────────────


class TestWFDParameters:
    """Tests for composite WFD parameters."""

    def test_parse_m3_response_body(self):
        """Parse a complete M3 response body."""
        body = (
            "wfd_video_formats: 00 00 01 02 000000A1 00000000 00000000 00 0000 0000 00 none none\r\n"
            "wfd_audio_codecs: LPCM 00000003 00, AAC 00000007 00\r\n"
            "wfd_client_rtp_ports: RTP/AVP/UDP;unicast 19000 0 mode=play\r\n"
            "wfd_content_protection: none"
        )
        params = WFDParameters.parse_body(body)
        assert params.video_formats is not None
        assert params.video_formats.profile == 0x01
        assert params.audio_codecs is not None
        assert len(params.audio_codecs.codecs) == 2
        assert params.client_rtp_ports is not None
        assert params.client_rtp_ports.port0 == 19000
        assert params.content_protection == "none"

    def test_parse_body_with_trigger(self):
        """Parse body with wfd_trigger_method."""
        body = "wfd_trigger_method: SETUP"
        params = WFDParameters.parse_body(body)
        assert params.trigger_method == WFDTriggerMethod.SETUP

    def test_parse_body_teardown_trigger(self):
        """Parse TEARDOWN trigger."""
        body = "wfd_trigger_method: TEARDOWN"
        params = WFDParameters.parse_body(body)
        assert params.trigger_method == WFDTriggerMethod.TEARDOWN

    def test_parse_body_empty(self):
        """Parse empty body returns empty params."""
        params = WFDParameters.parse_body("")
        assert params.video_formats is None
        assert params.audio_codecs is None

    def test_parse_body_with_presentation_url(self):
        """Parse presentation URL."""
        body = "wfd_presentation_URL: rtsp://192.168.49.1/wfd1.0/streamid=0 none"
        params = WFDParameters.parse_body(body)
        assert "192.168.49.1" in params.presentation_url

    def test_parse_body_invalid_video_formats_graceful(self):
        """Invalid video formats logged but doesn't crash."""
        body = "wfd_video_formats: INVALID"
        params = WFDParameters.parse_body(body)
        assert params.video_formats is None  # Failed to parse, set to None

    def test_format_body_full(self):
        """Format full parameter set."""
        params = WFDParameters(
            video_formats=WFDVideoFormats(profile=0x01, level=0x02, cea_bitmap=0xA1),
            audio_codecs=WFDAudioCodecs(codecs=[
                AudioCodec(codec=AudioCodecType.LPCM, modes=0x03, latency=0)
            ]),
            client_rtp_ports=WFDClientRTPPorts(port0=19000),
            content_protection="none",
        )
        body = params.format_body()
        assert "wfd_video_formats:" in body
        assert "wfd_audio_codecs:" in body
        assert "wfd_client_rtp_ports:" in body
        assert "wfd_content_protection: none" in body

    def test_format_body_trigger_only(self):
        """Format trigger-only parameter."""
        params = WFDParameters(trigger_method=WFDTriggerMethod.SETUP)
        body = params.format_body()
        assert body == "wfd_trigger_method: SETUP"

    def test_m3_request_body(self):
        """M3 request body contains parameter names."""
        body = WFDParameters.m3_request_body()
        assert "wfd_video_formats" in body
        assert "wfd_audio_codecs" in body
        assert "wfd_client_rtp_ports" in body
        assert "wfd_content_protection" in body
        # Should NOT contain values, just names
        assert ":" not in body

    def test_default_source_capabilities(self):
        """Default source capabilities are valid."""
        caps = WFDParameters.default_source_capabilities()
        assert caps.video_formats is not None
        assert caps.video_formats.profile == 0x01  # CBP
        assert caps.audio_codecs is not None
        assert len(caps.audio_codecs.codecs) >= 1
        assert caps.content_protection == "none"

    def test_format_body_roundtrip(self):
        """Format then parse roundtrip preserves key fields."""
        original = WFDParameters.default_source_capabilities()
        original.client_rtp_ports = WFDClientRTPPorts(port0=19000)
        body = original.format_body()
        parsed = WFDParameters.parse_body(body)
        assert parsed.video_formats is not None
        assert parsed.audio_codecs is not None
        assert parsed.client_rtp_ports.port0 == 19000


# ─────────────────────────────────────────────────────────────
# WFDTriggerMethod Tests
# ─────────────────────────────────────────────────────────────


class TestWFDTriggerMethod:
    """Tests for trigger method enum."""

    def test_all_trigger_methods(self):
        """All WFD trigger methods are defined."""
        assert WFDTriggerMethod.SETUP.value == "SETUP"
        assert WFDTriggerMethod.TEARDOWN.value == "TEARDOWN"
        assert WFDTriggerMethod.PAUSE.value == "PAUSE"
        assert WFDTriggerMethod.PLAY.value == "PLAY"

    def test_trigger_from_string(self):
        """Create trigger method from string."""
        assert WFDTriggerMethod("SETUP") == WFDTriggerMethod.SETUP

    def test_invalid_trigger_raises(self):
        """Invalid trigger method raises ValueError."""
        with pytest.raises(ValueError):
            WFDTriggerMethod("INVALID")
