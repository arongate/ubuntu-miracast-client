# ADR-003: Privilege Escalation Strategy — Polkit + NetworkManager D-Bus

## Status

**Proposed** — 2026-08-24

## Context

The application currently requires `sudo` for all wpa_supplicant operations (P2P discovery, connection, group management). This means:
- The entire application must run as root
- Users must type their password or configure passwordless sudo
- No granular access control
- Violates principle of least privilege
- systemd service hardening is undermined by running as root

## Decision

Implement a two-phase migration:

### Phase 1 (Short-term): Polkit + Privileged Helper

```
┌──────────────────────┐        ┌─────────────────────────┐
│  Main App (user)     │───────▶│  miracast-helper (root)  │
│  Unprivileged        │ D-Bus  │  /usr/libexec/           │
│  GTK4 UI             │◀───────│  Minimal helper binary   │
└──────────────────────┘        └─────────────────────────┘
         │                                   │
         │ polkit authorization              │ wpa_cli commands
         ▼                                   ▼
┌──────────────────────┐        ┌─────────────────────────┐
│  polkit agent (GUI)  │        │  wpa_supplicant          │
│  Auth dialog shown   │        │  (P2P operations)        │
└──────────────────────┘        └─────────────────────────┘
```

Files to create:
- `data/com.ubuntu.MiracastClient.policy` — Polkit policy file
- `src/miracast_client/helper.py` — Privileged helper (D-Bus service)
- `data/com.ubuntu.MiracastClient.Helper.service` — D-Bus service file

### Phase 2 (Medium-term): NetworkManager D-Bus API

NetworkManager already manages wpa_supplicant and exposes P2P operations via D-Bus with polkit authorization built-in.

```python
# Using NetworkManager D-Bus API (no root needed)
import dbus

bus = dbus.SystemBus()
nm = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager")

# Get Wi-Fi device
devices = nm.GetDevices(dbus_interface="org.freedesktop.NetworkManager")
for dev_path in devices:
    dev = bus.get_object("org.freedesktop.NetworkManager", dev_path)
    if dev.Get("org.freedesktop.NetworkManager.Device", "DeviceType") == 2:  # Wi-Fi
        wifi_p2p = dbus.Interface(dev, "org.freedesktop.NetworkManager.Device.WifiP2P")
        wifi_p2p.StartFind({})  # Polkit handles authorization
```

**Key NM interfaces for P2P:**
- `org.freedesktop.NetworkManager.Device.WifiP2P.StartFind()`
- `org.freedesktop.NetworkManager.Device.WifiP2P.StopFind()`
- `org.freedesktop.NetworkManager.Device.WifiP2P.Peers` (property)
- `org.freedesktop.NetworkManager.WifiP2PPeer.Name`
- `org.freedesktop.NetworkManager.WifiP2PPeer.WfdIEs`

## Alternatives Considered

1. **Keep sudo approach:** Simple but insecure, poor UX, fails OpenSSF security checks.

2. **Linux capabilities only (CAP_NET_ADMIN):** Works for the binary but `wpa_cli` still needs root to connect to the wpa_supplicant control socket.

3. **Add user to `netdev` group + polkit rule:** Works on some systems but not universally portable.

4. **Flatpak/Snap confinement:** Handles privilege automatically via portal APIs, but the app currently targets native Debian packaging.

## Consequences

### Phase 1 Positive
- Main app runs unprivileged
- Polkit gives users a standard auth prompt
- Helper is minimal (small attack surface)
- Can be audited independently
- Works with systemd hardening (NoNewPrivileges on main app)

### Phase 1 Negative
- Extra D-Bus service to maintain
- Helper must be installed system-wide (/usr/libexec)
- Adds dependency on polkit runtime

### Phase 2 Positive
- No custom helper needed
- NetworkManager handles all coordination with wpa_supplicant
- Already polkit-mediated (users in `netdev` group get auto-approval)
- Better integration with GNOME desktop (network indicator shows P2P status)
- Handles interface conflicts automatically

### Phase 2 Negative
- NetworkManager P2P support may not cover all WFD-specific operations
- Requires NM >= 1.16 (available on Ubuntu 20.04+)
- May need to fall back to direct wpa_supplicant for some operations

## References

- Polkit documentation: https://www.freedesktop.org/software/polkit/docs/latest/
- NetworkManager D-Bus API: https://networkmanager.dev/docs/api/latest/
- gnome-network-displays: Uses NM D-Bus for all P2P operations
- GNOME Settings > Wi-Fi: Shows how NM handles P2P groups
