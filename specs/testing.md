# Testing Specification

## Ubuntu Miracast Client v1.0.0

**Document Version:** 1.0  
**Date:** 2026-08-09  
**Status:** Final

---

## 1. Test Strategy

### 1.1 Overview

The testing strategy employs a layered approach: unit tests for individual modules, integration tests for component interactions, and manual tests for UI/hardware-dependent functionality.

### 1.2 Test Framework & Tools

| Tool | Version | Purpose |
|------|---------|---------|
| pytest | >=7.0.0 | Test runner and assertions |
| pytest-cov | >=4.0.0 | Code coverage measurement |
| unittest.mock | stdlib | Mocking external dependencies |
| flake8 | >=6.0.0 | Static analysis (lint) |
| mypy | >=1.0.0 | Type checking |
| black | >=23.0.0 | Code formatting verification |

### 1.3 Test Execution

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=miracast_client --cov-report=html

# Run specific module tests
pytest tests/test_discovery.py
pytest tests/test_config.py

# Lint checks
flake8 src/
mypy src/
black --check src/
```

### 1.4 CI Integration

Tests run automatically via GitHub Actions on:
- Every push to any branch
- Every pull request

CI workflow (`.github/workflows/ci.yml`) runs:
1. `make lint` — flake8 + black check
2. `make test` — pytest with coverage

---

## 2. Test Categories

### 2.1 Unit Tests

Isolated tests for individual classes and functions with all external dependencies mocked.

### 2.2 Integration Tests

Tests verifying correct interaction between two or more modules (e.g., CastManager + SessionHistory).

### 2.3 Manual Tests

Tests requiring physical hardware or desktop environment that cannot be automated.

---

## 3. Unit Test Specifications

### 3.1 Discovery Module (`tests/test_discovery.py`)

#### TestMiracastDevice

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TD-01 | `test_from_wpa_supplicant_p2p_device` | Factory creates device with correct fields from complete dict |
| TD-02 | `test_from_wpa_supplicant_p2p_device_missing_fields` | Factory handles missing fields with appropriate defaults (UUID for id, "Unknown Device", "00:00:00:00:00:00", "Unknown", 0) |
| TD-03 | `test_device_equality` | Two devices with same fields are equal (dataclass) |
| TD-04 | `test_signal_strength_conversion` | Signal level string correctly converted to int |

#### TestMiracastDiscovery

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TD-05 | `test_start_discovery` | Sets `_running=True`, starts thread, emits `discovery-started` signal |
| TD-06 | `test_start_discovery_already_running` | No-op when discovery is already running (no duplicate threads) |
| TD-07 | `test_stop_discovery` | Sets `_running=False`, joins thread, emits `discovery-stopped` signal |
| TD-08 | `test_stop_discovery_not_running` | No-op when discovery is not running |
| TD-09 | `test_get_devices` | Returns current snapshot of device map as list |
| TD-10 | `test_get_devices_thread_safe` | Concurrent access to `get_devices()` doesn't corrupt data |
| TD-11 | `test_discovery_error_handling` | Thread exceptions emit `discovery-error` signal |

---

### 3.2 Config Module (`tests/test_config.py`)

#### TestConfig

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TC-01 | `test_default_config` | Default config created with correct structure and values when no file exists |
| TC-02 | `test_set_and_get` | Values set via `set()` are retrievable via `get()` |
| TC-03 | `test_save_and_load` | Config persists correctly through save/reload cycle |
| TC-04 | `test_nonexistent_key` | `get()` returns default for missing key |
| TC-05 | `test_nonexistent_section` | `get()` returns default for missing section |
| TC-06 | `test_create_new_section` | `set()` creates section that doesn't exist |
| TC-07 | `test_config_file_created` | Config file is created on disk after init |
| TC-08 | `test_corrupted_config_fallback` | Corrupted JSON file results in default config (graceful recovery) |

---

### 3.3 Capture Module (`tests/test_capture.py`)

#### TestCaptureSource

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TCA-01 | `test_capture_source_creation` | Base CaptureSource fields populated correctly |
| TCA-02 | `test_capture_source_default_icon` | Default icon is "video-display" |

#### TestScreenSource

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TCA-03 | `test_screen_source_creation` | ID format is "screen-{n}", name is "Screen {n+1}" |
| TCA-04 | `test_screen_source_description` | Description includes resolution and manufacturer |
| TCA-05 | `test_screen_source_start_capture` | Returns valid GStreamer pipeline string with display-name |

#### TestWindowSource

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TCA-06 | `test_window_source_creation` | ID format is "window-{id}", name is window title |
| TCA-07 | `test_window_source_start_capture` | Returns valid GStreamer pipeline string with xid |
| TCA-08 | `test_window_source_default_icon` | Default icon when none specified |

#### TestGetAvailableSources

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TCA-09 | `test_get_all_sources` | Returns both screen and window sources |
| TCA-10 | `test_get_screen_only` | `screen_only=True` returns only ScreenSource instances |
| TCA-11 | `test_get_windows_only` | `windows_only=True` returns only WindowSource instances |
| TCA-12 | `test_display_unavailable` | Graceful empty list when no display available |

---

### 3.4 Casting Module (`tests/test_casting.py`)

#### TestCastingStats

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TS-01 | `test_stats_defaults` | Default values: duration=0, data_transferred=0, etc. |
| TS-02 | `test_stats_start_time` | start_time correctly set on creation |

#### TestCastManager

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TS-03 | `test_start_casting_success` | Sets casting=True, emits `casting-started`, starts thread |
| TS-04 | `test_start_casting_already_active` | Raises `RuntimeError` when already casting |
| TS-05 | `test_start_casting_no_source` | Raises `ValueError` with None source |
| TS-06 | `test_start_casting_no_device` | Raises `ValueError` with None device |
| TS-07 | `test_stop_casting_success` | Returns `CastingStats`, emits `casting-stopped`, resets state |
| TS-08 | `test_stop_casting_not_active` | Raises `RuntimeError` when not casting |
| TS-09 | `test_is_casting_true` | Returns True while session is active |
| TS-10 | `test_is_casting_false` | Returns False when idle |
| TS-11 | `test_stats_updated_signal` | `stats-updated` signal emitted during casting |
| TS-12 | `test_casting_error_signal` | `casting-error` emitted on thread exception |
| TS-13 | `test_stop_updates_end_time` | `end_time` and `duration` populated after stop |

---

### 3.5 History Module (`tests/test_history.py`)

#### TestSessionRecord

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TH-01 | `test_to_dict` | Serializes all fields including nested objects and datetime |
| TH-02 | `test_from_dict` | Deserializes correctly from dict |
| TH-03 | `test_roundtrip` | `from_dict(to_dict())` produces equivalent object |
| TH-04 | `test_none_end_time` | Handles None end_time in serialization |

#### TestSessionHistory

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TH-05 | `test_empty_history` | New history returns empty list |
| TH-06 | `test_add_session` | Session added and retrievable |
| TH-07 | `test_persistence` | Sessions survive reload from disk |
| TH-08 | `test_clear` | All sessions removed, file updated |
| TH-09 | `test_multiple_sessions` | Multiple sessions stored in order |
| TH-10 | `test_corrupted_record_skipped` | Malformed records don't crash loading |
| TH-11 | `test_missing_history_file` | Returns empty list for new install |

---

### 3.6 Service Module (`tests/test_service.py`)

#### TestServiceManager

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TSV-01 | `test_is_service_enabled_true` | Returns True when systemctl reports "enabled" |
| TSV-02 | `test_is_service_enabled_false` | Returns False when file doesn't exist |
| TSV-03 | `test_is_service_running_true` | Returns True when systemctl reports "active" |
| TSV-04 | `test_is_service_running_false` | Returns False when not active |
| TSV-05 | `test_enable_service` | Creates file, reloads daemon, enables via systemctl |
| TSV-06 | `test_disable_service` | Stops, disables, removes file, reloads |
| TSV-07 | `test_start_service` | Calls systemctl start (enables first if needed) |
| TSV-08 | `test_stop_service` | Calls systemctl stop |
| TSV-09 | `test_enable_service_failure` | Raises RuntimeError on subprocess failure |
| TSV-10 | `test_service_file_content` | Generated .service file has correct format |

---

## 4. Integration Test Specifications

### 4.1 Casting + History Integration (`tests/test_integration.py`)

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TI-01 | `test_session_recorded_after_stop` | Stopping a cast session adds record to history |
| TI-02 | `test_stats_match_history_record` | Stats from stop_casting() match what's in history |

### 4.2 Config + Casting Integration

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TI-03 | `test_quality_config_affects_bitrate` | Changing video_quality config affects casting bitrate |
| TI-04 | `test_audio_config_affects_stream` | audio_enabled config toggles audio bitrate addition |

### 4.3 Discovery + DeviceSelector Integration

| Test ID | Test Case | Validates |
|---------|-----------|-----------|
| TI-05 | `test_device_found_appears_in_list` | device-found signal populates device list model |
| TI-06 | `test_device_lost_removes_from_list` | device-lost signal removes device from list model |

---

## 5. Manual Test Procedures

### 5.1 End-to-End Casting

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Launch application | Main window appears with source selection |
| 2 | Select "Entire Screen" | Screen sources listed |
| 3 | Select a screen, click "Select" | Navigate to device selection page |
| 4 | Wait for device discovery | Spinner shows, devices appear in list |
| 5 | Select a device, click "Connect" | Casting starts, window minimizes |
| 6 | Verify content on target device | Screen content visible on receiver |
| 7 | Re-open app, stop casting | Session stats displayed in history |

### 5.2 Service Mode

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open Settings → Service | Service status shown |
| 2 | Toggle "Run as System Service" on | Service enabled, status shows "Running" |
| 3 | Run `systemctl --user status ubuntu-miracast-client` | Service is active |
| 4 | Toggle service off | Service stopped and disabled |

### 5.3 Settings Persistence

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Open Settings | Current values displayed |
| 2 | Change video quality to "Low" | Dropdown updated |
| 3 | Click "Save Settings" | Success dialog shown |
| 4 | Close and reopen app | "Low" quality persisted |

---

## 6. Test Coverage Targets

| Module | Target Coverage | Critical Paths |
|--------|----------------|----------------|
| `discovery.py` | ≥80% | Device creation, start/stop lifecycle |
| `capture.py` | ≥80% | Source enumeration, pipeline generation |
| `casting.py` | ≥85% | Start/stop lifecycle, validation, stats |
| `history.py` | ≥90% | Serialization roundtrip, persistence |
| `config.py` | ≥90% | Load/save, defaults, get/set |
| `service.py` | ≥75% | Enable/disable, status checks |
| **Overall** | **≥80%** | — |

---

## 7. Mocking Strategy

| External Dependency | Mock Approach |
|--------------------|---------------|
| `threading.Thread` | Patch to prevent actual thread creation in unit tests |
| `GLib.idle_add` | Patch to capture signal emissions |
| `Gdk.Display` | Mock return values for monitor enumeration |
| `subprocess.run` | Patch for all systemctl calls |
| File I/O | Use `tempfile.TemporaryDirectory` for config/history tests |
| `time.sleep` | Patch to avoid delays in tests |

---

## 8. Test Data

### 8.1 Sample Device Info (wpa_supplicant format)

```python
{
    "p2p_dev_addr": "aa:bb:cc:dd:ee:ff",
    "device_name": "Test TV",
    "primary_dev_type": "Samsung Smart TV",
    "signal_level": "85"
}
```

### 8.2 Sample Config (for test fixtures)

```python
{
    "general": {"minimize_to_tray": True, "start_minimized": False, "log_level": "INFO"},
    "streaming": {"video_quality": "High", "frame_rate": 30, "audio_enabled": True},
    "advanced": {"discovery_timeout": 10, "connection_timeout": 15}
}
```

---

## 9. Known Test Limitations

| Limitation | Reason | Mitigation |
|-----------|--------|------------|
| No actual Wi-Fi Direct testing | Requires compatible hardware | Simulated discovery with sample data |
| No real GStreamer pipeline testing | Requires display server and media devices | Pipeline string validation only |
| GTK widget tests limited | Requires running display server | Test logic separately from GTK widgets |
| Service tests use mocked systemctl | Requires systemd user session | Verify subprocess call arguments |
