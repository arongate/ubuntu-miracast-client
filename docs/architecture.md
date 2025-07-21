# Ubuntu Miracast Client Architecture

## Overview

The Ubuntu Miracast Client follows a modular architecture with clear separation of concerns between UI components, core functionality, and system integration.

## Architecture Layers

### UI Layer

- **Main Window**: Central UI component that manages navigation between different views
- **Source Selector**: UI for selecting a casting source (screen or window)
- **Device Selector**: UI for discovering and selecting Miracast devices
- **History View**: UI for viewing casting session history and statistics
- **Settings View**: UI for configuring application settings

### Core Components

- **Discovery Module**: Discovers Miracast-compatible devices on the network
- **Capture Module**: Manages screen and window capture sources
- **Casting Module**: Handles the Miracast streaming session
- **History Module**: Tracks and stores casting session history
- **Config Module**: Manages application configuration
- **Service Module**: Manages the optional system service mode

### System Integration

- **Systemd Service**: Integration with systemd for service mode
- **Logging**: Comprehensive logging for debugging and auditing

## Data Flow

1. **Source Selection**:
   - User selects a source (screen or window) via the Source Selector
   - Source information is passed to the Capture Module

2. **Device Discovery**:
   - Discovery Module finds Miracast devices on the network
   - Device Selector displays available devices to the user

3. **Casting Session**:
   - User selects a target device
   - Casting Module establishes connection with the device
   - Capture Module provides screen/window content
   - Content is streamed to the target device

4. **Session Management**:
   - Casting statistics are collected during the session
   - When the session ends, statistics are saved to the History Module
   - History View displays session history and statistics

## Technology Stack

- **UI Framework**: GTK 4 with libadwaita
- **Streaming**: GStreamer
- **Network Discovery**: Wi-Fi Direct via wpa_supplicant
- **Configuration**: JSON-based configuration
- **Logging**: Python logging module

## Security Considerations

- WPA2 security for Wi-Fi Direct connections
- Proper error handling and input validation
- Secure storage of configuration data

## Fault Tolerance

- Graceful handling of connection failures
- Recovery from streaming errors
- Comprehensive logging for debugging