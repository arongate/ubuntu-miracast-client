"""Wi-Fi Display (WFD) parameter parsing and formatting.

Implements the WFD-specific RTSP parameters used in M3 (GET_PARAMETER) and
M4 (SET_PARAMETER) message exchange.

Reference: Wi-Fi Display Technical Specification v2.3 §4.5, Tables 4-15 through 4-23
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Video Format Tables (WFD Spec §4.5.4, Table 4-18)
# ─────────────────────────────────────────────────────────────

class VideoProfile(enum.IntEnum):
    """H.264 profiles supported by WFD."""

    CONSTRAINED_BASELINE = 0  # CBP — mandatory
    CONSTRAINED_HIGH = 1      # CHP — optional


class VideoLevel(enum.IntEnum):
    """H.264 levels supported by WFD (bitmap positions)."""

    LEVEL_3_1 = 0  # Mandatory
    LEVEL_3_2 = 1
    LEVEL_4_0 = 2
    LEVEL_4_1 = 3
    LEVEL_4_2 = 4


# CEA resolution table (WFD Spec Table 4-17)
# Bitmap position → (width, height, fps, interlaced)
CEA_RESOLUTIONS: dict[int, tuple[int, int, int, bool]] = {
    0: (640, 480, 60, False),
    1: (720, 480, 60, False),
    2: (720, 480, 60, True),
    3: (720, 576, 50, False),
    4: (720, 576, 50, True),
    5: (1280, 720, 30, False),
    6: (1280, 720, 60, False),
    7: (1920, 1080, 30, False),
    8: (1920, 1080, 60, False),
    9: (1920, 1080, 60, True),
    10: (1280, 720, 25, False),
    11: (1280, 720, 50, False),
    12: (1920, 1080, 25, False),
    13: (1920, 1080, 50, False),
    14: (1920, 1080, 50, True),
    15: (1280, 720, 24, False),
    16: (1920, 1080, 24, False),
}

# VESA resolution table (WFD Spec Table 4-18)
VESA_RESOLUTIONS: dict[int, tuple[int, int, int, bool]] = {
    0: (800, 600, 30, False),
    1: (800, 600, 60, False),
    2: (1024, 768, 30, False),
    3: (1024, 768, 60, False),
    4: (1280, 768, 30, False),
    5: (1280, 768, 60, False),
    6: (1280, 800, 30, False),
    7: (1280, 800, 60, False),
    8: (1280, 1024, 30, False),
    9: (1280, 1024, 60, False),
    10: (1400, 1050, 30, False),
    11: (1400, 1050, 60, False),
    12: (1440, 900, 30, False),
    13: (1440, 900, 60, False),
    14: (1600, 900, 30, False),
    15: (1600, 900, 60, False),
    16: (1600, 1200, 30, False),
    17: (1600, 1200, 60, False),
    18: (1680, 1024, 30, False),
    19: (1680, 1024, 60, False),
    20: (1680, 1050, 30, False),
    21: (1680, 1050, 60, False),
    22: (1920, 1200, 30, False),
}

# Handheld (HH) resolution table (WFD Spec Table 4-19)
HH_RESOLUTIONS: dict[int, tuple[int, int, int, bool]] = {
    0: (800, 480, 30, False),
    1: (800, 480, 60, False),
    2: (854, 480, 30, False),
    3: (854, 480, 60, False),
    4: (864, 480, 30, False),
    5: (864, 480, 60, False),
    6: (640, 360, 30, False),
    7: (640, 360, 60, False),
    8: (960, 540, 30, False),
    9: (960, 540, 60, False),
    10: (848, 480, 30, False),
    11: (848, 480, 60, False),
}


@dataclass
class VideoFormat:
    """A specific video format (resolution + profile + level)."""

    width: int
    height: int
    fps: int
    interlaced: bool = False
    profile: VideoProfile = VideoProfile.CONSTRAINED_BASELINE
    level: VideoLevel = VideoLevel.LEVEL_3_1

    @property
    def description(self) -> str:
        """Human-readable description."""
        mode = "i" if self.interlaced else "p"
        return f"{self.width}x{self.height}{mode}{self.fps}"


# ─────────────────────────────────────────────────────────────
# Audio Codec Tables (WFD Spec §4.5.5)
# ─────────────────────────────────────────────────────────────

class AudioCodecType(enum.Enum):
    """Audio codec types supported by WFD."""

    LPCM = "LPCM"    # Linear PCM — mandatory
    AAC = "AAC"      # AAC-LC — optional
    AC3 = "AC3"      # Dolby Digital — optional


@dataclass
class AudioCodec:
    """A supported audio codec configuration."""

    codec: AudioCodecType
    modes: int  # Bitmap of supported modes
    latency: int = 0  # Decoder latency in units of 5ms

    @property
    def sample_rates(self) -> list[int]:
        """Get supported sample rates based on mode bitmap."""
        rates = []
        if self.codec == AudioCodecType.LPCM:
            if self.modes & 0x01:
                rates.append(44100)
            if self.modes & 0x02:
                rates.append(48000)
        elif self.codec == AudioCodecType.AAC:
            if self.modes & 0x01:
                rates.append(48000)  # 2ch
            if self.modes & 0x02:
                rates.append(48000)  # 4ch
            if self.modes & 0x04:
                rates.append(48000)  # 6ch
        return rates

    def format_wfd(self) -> str:
        """Format for WFD parameter string."""
        return f"{self.codec.value} {self.modes:08X} {self.latency:02X}"

    @classmethod
    def parse_wfd(cls, text: str) -> AudioCodec:
        """Parse a single audio codec from WFD parameter string.

        Args:
            text: String like 'LPCM 00000003 00'

        Returns:
            AudioCodec instance.

        Raises:
            ValueError: If the text cannot be parsed.
        """
        parts = text.strip().split()
        if len(parts) != 3:
            raise ValueError(f"Invalid audio codec format: {text!r}")

        try:
            codec = AudioCodecType(parts[0])
        except ValueError:
            raise ValueError(f"Unknown audio codec: {parts[0]!r}") from None

        try:
            modes = int(parts[1], 16)
        except ValueError:
            raise ValueError(f"Invalid modes bitmap: {parts[1]!r}") from None

        try:
            latency = int(parts[2], 16)
        except ValueError:
            raise ValueError(f"Invalid latency value: {parts[2]!r}") from None

        return cls(codec=codec, modes=modes, latency=latency)


# ─────────────────────────────────────────────────────────────
# WFD Video Formats Parameter
# ─────────────────────────────────────────────────────────────

@dataclass
class WFDVideoFormats:
    """WFD video formats parameter (wfd_video_formats).

    Format: <native> <pref_display_mode> <profile> <level> <CEA> <VESA> <HH>
            <latency> <min_slice> <slice_enc> <frame_rate_ctl> [<max_hres> <max_vres>]

    Reference: WFD Spec v2.3 §4.5.4, Table 4-16
    """

    native: int = 0x00          # Native resolution index
    preferred_display: int = 0  # 0=not supported, 1=supported
    profile: int = 0x01         # H.264 profile bitmap (bit0=CBP, bit1=CHP)
    level: int = 0x02           # H.264 level bitmap (bit0=3.1, bit1=3.2, bit2=4.0)
    cea_bitmap: int = 0x000000A1  # CEA resolution bitmap (default: 640x480p60 + 1280x720p30)
    vesa_bitmap: int = 0x00000000  # VESA resolution bitmap
    hh_bitmap: int = 0x00000000    # HH resolution bitmap
    latency: int = 0x00         # Max decoder latency (units of 5ms)
    min_slice_size: int = 0     # Minimum slice size
    slice_enc_params: int = 0   # Slice encoding parameters
    frame_rate_control: int = 0x00  # Frame rate control support

    def get_supported_resolutions(self) -> list[VideoFormat]:
        """Get all supported video formats from the bitmaps."""
        formats: list[VideoFormat] = []

        for bit, res in CEA_RESOLUTIONS.items():
            if self.cea_bitmap & (1 << bit):
                formats.append(VideoFormat(
                    width=res[0], height=res[1], fps=res[2], interlaced=res[3]
                ))

        for bit, res in VESA_RESOLUTIONS.items():
            if self.vesa_bitmap & (1 << bit):
                formats.append(VideoFormat(
                    width=res[0], height=res[1], fps=res[2], interlaced=res[3]
                ))

        for bit, res in HH_RESOLUTIONS.items():
            if self.hh_bitmap & (1 << bit):
                formats.append(VideoFormat(
                    width=res[0], height=res[1], fps=res[2], interlaced=res[3]
                ))

        return formats

    def format_wfd(self) -> str:
        """Format for WFD parameter string."""
        return (
            f"{self.native:02X} {self.preferred_display:02X} "
            f"{self.profile:02X} {self.level:02X} "
            f"{self.cea_bitmap:08X} {self.vesa_bitmap:08X} {self.hh_bitmap:08X} "
            f"{self.latency:02X} {self.min_slice_size:04X} {self.slice_enc_params:04X} "
            f"{self.frame_rate_control:02X} none none"
        )

    @classmethod
    def parse_wfd(cls, text: str) -> WFDVideoFormats:
        """Parse wfd_video_formats parameter value.

        Args:
            text: The value portion of 'wfd_video_formats: <value>'

        Returns:
            WFDVideoFormats instance.

        Raises:
            ValueError: If the text cannot be parsed.
        """
        parts = text.strip().split()
        if len(parts) < 7:
            raise ValueError(
                f"Invalid wfd_video_formats (need at least 7 fields, got {len(parts)}): {text!r}"
            )

        try:
            native = int(parts[0], 16)
            preferred_display = int(parts[1], 16)
            profile = int(parts[2], 16)
            level = int(parts[3], 16)
            cea_bitmap = int(parts[4], 16)
            vesa_bitmap = int(parts[5], 16)
            hh_bitmap = int(parts[6], 16)
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid hex values in wfd_video_formats: {e}") from e

        latency = int(parts[7], 16) if len(parts) > 7 else 0
        min_slice = int(parts[8], 16) if len(parts) > 8 else 0
        slice_enc = int(parts[9], 16) if len(parts) > 9 else 0
        frc = int(parts[10], 16) if len(parts) > 10 else 0

        return cls(
            native=native,
            preferred_display=preferred_display,
            profile=profile,
            level=level,
            cea_bitmap=cea_bitmap,
            vesa_bitmap=vesa_bitmap,
            hh_bitmap=hh_bitmap,
            latency=latency,
            min_slice_size=min_slice,
            slice_enc_params=slice_enc,
            frame_rate_control=frc,
        )


# ─────────────────────────────────────────────────────────────
# WFD Audio Codecs Parameter
# ─────────────────────────────────────────────────────────────

@dataclass
class WFDAudioCodecs:
    """WFD audio codecs parameter (wfd_audio_codecs).

    Format: <codec1> <modes1> <latency1>[, <codec2> <modes2> <latency2>]

    Reference: WFD Spec v2.3 §4.5.5
    """

    codecs: list[AudioCodec] = field(default_factory=list)

    def format_wfd(self) -> str:
        """Format for WFD parameter string."""
        if not self.codecs:
            return "none"
        return ", ".join(c.format_wfd() for c in self.codecs)

    @classmethod
    def parse_wfd(cls, text: str) -> WFDAudioCodecs:
        """Parse wfd_audio_codecs parameter value.

        Args:
            text: Value like 'LPCM 00000003 00, AAC 00000007 00'

        Returns:
            WFDAudioCodecs instance.

        Raises:
            ValueError: If the text cannot be parsed.
        """
        text = text.strip()
        if text.lower() == "none":
            return cls(codecs=[])

        codecs: list[AudioCodec] = []
        for codec_str in text.split(","):
            codec_str = codec_str.strip()
            if codec_str:
                codecs.append(AudioCodec.parse_wfd(codec_str))

        return cls(codecs=codecs)

    @classmethod
    def default_source(cls) -> WFDAudioCodecs:
        """Default audio codecs supported by a WFD source (LPCM mandatory)."""
        return cls(codecs=[
            AudioCodec(codec=AudioCodecType.LPCM, modes=0x03, latency=0),  # 44.1 + 48 kHz
        ])


# ─────────────────────────────────────────────────────────────
# WFD Client RTP Ports
# ─────────────────────────────────────────────────────────────

@dataclass
class WFDClientRTPPorts:
    """WFD client RTP ports parameter (wfd_client_rtp_ports).

    Format: RTP/AVP/UDP;unicast <port0> <port1> mode=play

    Reference: WFD Spec v2.3 §4.5.3
    """

    profile: str = "RTP/AVP/UDP;unicast"
    port0: int = 19000  # Primary RTP port
    port1: int = 0      # Secondary RTP port (0 = not used)
    mode: str = "play"

    def format_wfd(self) -> str:
        """Format for WFD parameter string."""
        return f"{self.profile} {self.port0} {self.port1} mode={self.mode}"

    @classmethod
    def parse_wfd(cls, text: str) -> WFDClientRTPPorts:
        """Parse wfd_client_rtp_ports parameter value.

        Args:
            text: Value like 'RTP/AVP/UDP;unicast 19000 0 mode=play'

        Returns:
            WFDClientRTPPorts instance.

        Raises:
            ValueError: If the text cannot be parsed.
        """
        parts = text.strip().split()
        if len(parts) < 4:
            raise ValueError(
                f"Invalid wfd_client_rtp_ports (need 4 parts, got {len(parts)}): {text!r}"
            )

        profile = parts[0]
        try:
            port0 = int(parts[1])
            port1 = int(parts[2])
        except ValueError as e:
            raise ValueError(f"Invalid port number in wfd_client_rtp_ports: {e}") from e

        # Validate port range
        if not (0 <= port0 <= 65535) or not (0 <= port1 <= 65535):
            raise ValueError(f"Port out of range: port0={port0}, port1={port1}")

        mode = "play"
        if parts[3].startswith("mode="):
            mode = parts[3].split("=", 1)[1]

        return cls(profile=profile, port0=port0, port1=port1, mode=mode)


# ─────────────────────────────────────────────────────────────
# WFD Trigger Method
# ─────────────────────────────────────────────────────────────

class WFDTriggerMethod(enum.Enum):
    """WFD trigger methods sent via SET_PARAMETER (M5, M8, M10, M12)."""

    SETUP = "SETUP"
    TEARDOWN = "TEARDOWN"
    PAUSE = "PAUSE"
    PLAY = "PLAY"


# ─────────────────────────────────────────────────────────────
# Composite WFD Parameters (M3/M4 body)
# ─────────────────────────────────────────────────────────────

# Parameters requested in M3 GET_PARAMETER
WFD_M3_REQUEST_PARAMS = [
    "wfd_video_formats",
    "wfd_audio_codecs",
    "wfd_client_rtp_ports",
    "wfd_content_protection",
]


@dataclass
class WFDParameters:
    """Collection of WFD session parameters exchanged in M3/M4.

    This represents the sink's capabilities (from M3 response) or the
    source's selected session parameters (for M4 request).
    """

    video_formats: WFDVideoFormats | None = None
    audio_codecs: WFDAudioCodecs | None = None
    client_rtp_ports: WFDClientRTPPorts | None = None
    content_protection: str | None = None  # "none" or HDCP spec
    presentation_url: str | None = None
    trigger_method: WFDTriggerMethod | None = None

    def format_body(self) -> str:
        """Format parameters as RTSP message body (for M3 response or M4 request)."""
        lines: list[str] = []

        if self.video_formats is not None:
            lines.append(f"wfd_video_formats: {self.video_formats.format_wfd()}")
        if self.audio_codecs is not None:
            lines.append(f"wfd_audio_codecs: {self.audio_codecs.format_wfd()}")
        if self.client_rtp_ports is not None:
            lines.append(f"wfd_client_rtp_ports: {self.client_rtp_ports.format_wfd()}")
        if self.content_protection is not None:
            lines.append(f"wfd_content_protection: {self.content_protection}")
        if self.presentation_url is not None:
            lines.append(f"wfd_presentation_URL: {self.presentation_url}")
        if self.trigger_method is not None:
            lines.append(f"wfd_trigger_method: {self.trigger_method.value}")

        return "\r\n".join(lines)

    @classmethod
    def parse_body(cls, body: str) -> WFDParameters:
        """Parse WFD parameters from an RTSP message body.

        Args:
            body: Message body containing WFD parameter lines.

        Returns:
            WFDParameters instance with parsed values.
        """
        params = cls()

        for line in body.replace("\r\n", "\n").split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue

            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()

            if key == "wfd_video_formats":
                try:
                    params.video_formats = WFDVideoFormats.parse_wfd(value)
                except ValueError as e:
                    logger.warning(f"Failed to parse wfd_video_formats: {e}")
            elif key == "wfd_audio_codecs":
                try:
                    params.audio_codecs = WFDAudioCodecs.parse_wfd(value)
                except ValueError as e:
                    logger.warning(f"Failed to parse wfd_audio_codecs: {e}")
            elif key == "wfd_client_rtp_ports":
                try:
                    params.client_rtp_ports = WFDClientRTPPorts.parse_wfd(value)
                except ValueError as e:
                    logger.warning(f"Failed to parse wfd_client_rtp_ports: {e}")
            elif key == "wfd_content_protection":
                params.content_protection = value
            elif key == "wfd_presentation_url":
                params.presentation_url = value
            elif key == "wfd_trigger_method":
                try:
                    params.trigger_method = WFDTriggerMethod(value)
                except ValueError:
                    logger.warning(f"Unknown trigger method: {value!r}")

        return params

    @classmethod
    def m3_request_body(cls) -> str:
        """Generate the M3 GET_PARAMETER request body (parameter names only)."""
        return "\r\n".join(WFD_M3_REQUEST_PARAMS)

    @classmethod
    def default_source_capabilities(cls) -> WFDParameters:
        """Default parameters advertised by this source."""
        return cls(
            video_formats=WFDVideoFormats(
                native=0x00,
                preferred_display=0x00,
                profile=0x01,  # CBP only
                level=0x02,    # Level 3.1
                cea_bitmap=0x000000A1,  # 640x480p60 + 720x480p60 + 1280x720p30
                vesa_bitmap=0x00000000,
                hh_bitmap=0x00000000,
            ),
            audio_codecs=WFDAudioCodecs.default_source(),
            content_protection="none",
        )
