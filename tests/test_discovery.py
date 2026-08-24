"""Tests for the discovery module."""

from unittest.mock import MagicMock, patch

from miracast_client.discovery import (
    WFD_DUAL,
    WFD_PRIMARY_SINK,
    WFD_SOURCE,
    MiracastDevice,
    MiracastDiscovery,
    _find_p2p_interface,
    _parse_wfd_subelems,
)


class TestParseWfdSubelems:
    """Tests for WFD subelement parsing."""

    def test_primary_sink(self):
        # TuTuLink: 000006001100000032
        device_type, port = _parse_wfd_subelems("000006001100000032")
        assert device_type == WFD_PRIMARY_SINK
        assert port == 7236  # port field is 0000, defaults to WFD standard port 7236

    def test_dual_device(self):
        # Samsung TV: 00000601131c440036
        device_type, port = _parse_wfd_subelems("00000601131c440036")
        assert device_type == WFD_DUAL
        assert port == 0x1C44  # 7236

    def test_source_device(self):
        # Source: device info bits 0-1 = 00
        device_type, _port = _parse_wfd_subelems("000006001000001032")
        assert device_type == WFD_SOURCE

    def test_empty_string(self):
        device_type, port = _parse_wfd_subelems("")
        assert device_type is None
        assert port == 0

    def test_none_value(self):
        device_type, port = _parse_wfd_subelems(None)
        assert device_type is None
        assert port == 0

    def test_short_string(self):
        device_type, port = _parse_wfd_subelems("0000")
        assert device_type is None
        assert port == 0


class TestMiracastDevice:
    """Tests for MiracastDevice class."""

    def test_from_wpa_supplicant_p2p_device(self):
        device_info = {
            "p2p_dev_addr": "d6:9d:c0:93:af:c8",
            "device_name": "[TV] Samsung Q70 Series (65)",
            "manufacturer": "SAMSUNG_ELECTRONICS",
            "model_name": "QE65Q70RATXXC",
            "pri_dev_type": "7-0050F204-1",
            "level": "-83",
            "wfd_subelems": "00000601131c440036",
        }

        device = MiracastDevice.from_wpa_supplicant_p2p_device(device_info)

        assert device.id == "d6:9d:c0:93:af:c8"
        assert device.name == "[TV] Samsung Q70 Series (65)"
        assert device.address == "d6:9d:c0:93:af:c8"
        assert device.model == "QE65Q70RATXXC"
        assert device.manufacturer == "SAMSUNG_ELECTRONICS"
        assert device.wfd_type == WFD_DUAL
        assert device.rtsp_port == 7236
        assert device.is_sink is True
        assert device.signal_strength >= 0
        assert device.signal_strength <= 100

    def test_from_wpa_supplicant_p2p_device_missing_fields(self):
        device_info = {}

        device = MiracastDevice.from_wpa_supplicant_p2p_device(device_info)

        assert device.name == "Unknown Device"
        assert device.address == "00:00:00:00:00:00"
        assert device.signal_strength == 0

    def test_is_sink_for_primary_sink(self):
        device_info = {
            "p2p_dev_addr": "56:ae:bc:d7:ce:96",
            "device_name": "TuTuLink BCD7CE96",
            "level": "-61",
            "wfd_subelems": "000006001100000032",
        }
        device = MiracastDevice.from_wpa_supplicant_p2p_device(device_info)
        assert device.is_sink is True
        assert device.wfd_type == WFD_PRIMARY_SINK

    def test_is_sink_false_for_source(self):
        device_info = {
            "p2p_dev_addr": "aa:bb:cc:dd:ee:ff",
            "device_name": "Phone",
            "level": "-50",
            "wfd_subelems": "000006001000001032",  # source only
        }
        device = MiracastDevice.from_wpa_supplicant_p2p_device(device_info)
        assert device.is_sink is False
        assert device.wfd_type == WFD_SOURCE

    def test_signal_strength_conversion(self):
        """Signal level -30 dBm should be ~100%, -100 dBm should be 0%."""
        device_info = {"p2p_dev_addr": "aa:bb:cc:dd:ee:ff", "level": "-30"}
        device = MiracastDevice.from_wpa_supplicant_p2p_device(device_info)
        assert device.signal_strength == 100

        device_info["level"] = "-100"
        device = MiracastDevice.from_wpa_supplicant_p2p_device(device_info)
        assert device.signal_strength == 0

    def test_type_description(self):
        device = MiracastDevice(
            id="test",
            name="Test",
            address="aa:bb:cc:dd:ee:ff",
            model="Model",
            signal_strength=50,
            wfd_type=WFD_PRIMARY_SINK,
        )
        assert device.type_description == "Sink"


class TestMiracastDiscovery:
    """Tests for MiracastDiscovery class."""

    @patch("miracast_client.discovery.subprocess.run")
    def test_start_discovery(self, mock_run):
        """Test that start_discovery starts the thread and emits signal."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK\n")

        discovery = MiracastDiscovery(timeout=1, p2p_interface="p2p-dev-test")

        signals_emitted = []
        discovery.connect("discovery-started", lambda d: signals_emitted.append("started"))

        discovery.start_discovery()
        assert discovery._running is True
        assert "started" in signals_emitted

        # Clean up
        discovery.stop_discovery()

    @patch("miracast_client.discovery.subprocess.run")
    def test_stop_discovery(self, mock_run):
        """Test that stop_discovery stops the thread and emits signal."""
        mock_run.return_value = MagicMock(returncode=0, stdout="OK\n")

        discovery = MiracastDiscovery(timeout=1, p2p_interface="p2p-dev-test")

        signals_emitted = []
        discovery.connect("discovery-stopped", lambda d: signals_emitted.append("stopped"))

        discovery.start_discovery()
        discovery.stop_discovery()

        assert discovery._running is False
        assert "stopped" in signals_emitted

    def test_start_discovery_no_interface(self):
        """Test that missing P2P interface emits error."""
        discovery = MiracastDiscovery(timeout=1, p2p_interface=None)
        discovery._p2p_interface = None

        errors = []
        discovery.connect("discovery-error", lambda d, msg: errors.append(msg))
        discovery.start_discovery()

        assert len(errors) == 1
        assert "No P2P interface" in errors[0]

    def test_get_devices_returns_sinks_only(self):
        """Test that get_devices() only returns sink devices."""
        discovery = MiracastDiscovery(timeout=1, p2p_interface="p2p-dev-test")

        sink_device = MiracastDevice(
            id="sink1",
            name="TV",
            address="aa:bb:cc:dd:ee:01",
            model="TV",
            signal_strength=80,
            wfd_type=WFD_PRIMARY_SINK,
        )
        source_device = MiracastDevice(
            id="source1",
            name="Phone",
            address="aa:bb:cc:dd:ee:02",
            model="Phone",
            signal_strength=70,
            wfd_type=WFD_SOURCE,
        )

        discovery._devices = {"sink1": sink_device, "source1": source_device}

        devices = discovery.get_devices()
        assert len(devices) == 1
        assert devices[0].name == "TV"

    def test_get_all_devices(self):
        """Test that get_all_devices() returns all devices."""
        discovery = MiracastDiscovery(timeout=1, p2p_interface="p2p-dev-test")

        sink_device = MiracastDevice(
            id="sink1",
            name="TV",
            address="aa:bb:cc:dd:ee:01",
            model="TV",
            signal_strength=80,
            wfd_type=WFD_PRIMARY_SINK,
        )
        source_device = MiracastDevice(
            id="source1",
            name="Phone",
            address="aa:bb:cc:dd:ee:02",
            model="Phone",
            signal_strength=70,
            wfd_type=WFD_SOURCE,
        )

        discovery._devices = {"sink1": sink_device, "source1": source_device}

        devices = discovery.get_all_devices()
        assert len(devices) == 2


class TestFindP2pInterface:
    """Tests for _find_p2p_interface."""

    @patch("miracast_client.discovery.subprocess.run")
    def test_finds_p2p_interface(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Selected interface 'wlo1'\nAvailable interfaces:\np2p-dev-wlo1\nwlo1\n",
        )
        p2p, wifi = _find_p2p_interface()
        assert p2p == "p2p-dev-wlo1"
        assert wifi == "wlo1"

    @patch("miracast_client.discovery.subprocess.run")
    def test_no_p2p_interface(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Selected interface 'wlan0'\nAvailable interfaces:\nwlan0\n",
        )
        p2p, wifi = _find_p2p_interface()
        assert p2p is None
        assert wifi == "wlan0"

    @patch("miracast_client.discovery.subprocess.run")
    def test_command_fails(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        p2p, wifi = _find_p2p_interface()
        assert p2p is None
        assert wifi is None
