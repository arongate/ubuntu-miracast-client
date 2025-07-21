# Miracast Protocol: Technical Overview

## Introduction

Miracast is a wireless display standard developed by the Wi-Fi Alliance. It allows users to mirror their device's screen to another display wirelessly, without requiring a physical HDMI connection. Miracast is based on Wi-Fi Direct technology, which enables devices to connect directly without requiring a wireless access point or router.

## Protocol Architecture

Miracast operates on a three-layer architecture:

1. **Connectivity Layer**: Based on Wi-Fi Direct (P2P)
2. **Session Management Layer**: RTSP (Real Time Streaming Protocol)
3. **Audio/Video Streaming Layer**: H.264 video encoding and AAC audio encoding

### Connectivity Layer (Wi-Fi Direct)

Wi-Fi Direct allows devices to connect directly without an intermediate access point. The protocol establishes a secure connection between the source device (the one sharing content) and the sink device (the display receiving content).

Key aspects:
- Operates on 2.4GHz or 5GHz bands (5GHz preferred for better performance)
- Uses WPA2 for security
- Supports discovery and service advertisement
- Negotiates roles (Group Owner and Client)

### Session Management Layer (RTSP)

The Real Time Streaming Protocol (RTSP) is used to establish and control the media session between devices:

1. **Discovery**: Source device discovers sink devices
2. **Capability Negotiation**: Devices exchange information about supported resolutions, codecs, etc.
3. **Session Establishment**: RTSP SETUP messages configure the session parameters
4. **Session Control**: PLAY, PAUSE, TEARDOWN commands manage the session

### Audio/Video Streaming Layer

Once the session is established, the actual content is streamed:

- **Video**: H.264/AVC encoding (mandatory)
- **Audio**: AAC encoding (mandatory)
- **Transport**: RTP (Real-time Transport Protocol) over UDP or TCP

## Miracast Session Establishment

The following steps occur when establishing a Miracast session:

1. **Device Discovery**:
   - Source device sends probe requests
   - Sink devices respond with probe responses containing Miracast capability information
   - User selects a sink device from the discovered list

2. **Wi-Fi Direct Connection**:
   - Devices perform Wi-Fi Protected Setup (WPS) for secure pairing
   - Group formation (one device becomes Group Owner)
   - IP address assignment via DHCP

3. **RTSP Session Setup**:
   - Source device sends RTSP OPTIONS request to discover sink capabilities
   - Source sends RTSP SETUP request with proposed parameters
   - Sink responds with accepted parameters
   - Source sends RTSP PLAY request to start the streaming session

4. **Media Streaming**:
   - Source captures screen/application content
   - Content is encoded using H.264/AVC for video and AAC for audio
   - Encoded streams are packetized into RTP packets
   - RTP packets are transmitted over the Wi-Fi Direct connection

5. **Session Termination**:
   - Source sends RTSP TEARDOWN request
   - Wi-Fi Direct connection is terminated

## Implementation Challenges

### Screen Capture

Capturing screen content efficiently requires:
- Low-latency frame grabbing
- Hardware-accelerated encoding when possible
- Handling of different resolutions and aspect ratios
- Managing frame rate to balance quality and performance

### Network Performance

Miracast requires significant bandwidth:
- 1080p streaming can require 5-10 Mbps
- Latency must be minimized for interactive use
- Packet loss must be handled gracefully

### Audio Synchronization

Keeping audio and video in sync is critical:
- RTP timestamps must be properly managed
- Buffer management to handle network jitter
- Adaptive timing to maintain synchronization

## Limitations of Miracast

1. **Bandwidth Constraints**:
   - High-resolution streaming requires substantial bandwidth
   - Performance degrades in congested Wi-Fi environments
   - Distance between devices affects quality

2. **Latency Issues**:
   - Noticeable delay can occur (typically 50-150ms)
   - Makes interactive applications challenging
   - Gaming may experience significant input lag

3. **Compatibility Problems**:
   - Inconsistent implementation across different manufacturers
   - Some devices implement proprietary extensions
   - Certification doesn't guarantee interoperability

4. **Security Concerns**:
   - Wi-Fi Direct security depends on proper WPS implementation
   - Potential for man-in-the-middle attacks during discovery
   - No content protection for streamed media

5. **Linux Support Limitations**:
   - Limited native support in Linux distributions
   - Requires specific hardware support for optimal performance
   - May need proprietary drivers for full functionality

## Ubuntu-Specific Implementation

For Ubuntu 24.04 LTS, our implementation addresses these challenges by:

1. **Screen Capture**: Using GStreamer with hardware acceleration when available
2. **Network Discovery**: Implementing WPA Supplicant integration for Wi-Fi Direct
3. **Protocol Stack**: Using existing libraries for RTSP and RTP handling
4. **Performance Optimization**: Adaptive quality based on network conditions
5. **Security**: Implementing proper WPA2 security and certificate validation

## References

1. Wi-Fi Alliance Miracast Specification
2. RTSP RFC 2326
3. H.264/AVC Standard (ITU-T H.264)
4. Wi-Fi Direct Specification
5. RTP RFC 3550