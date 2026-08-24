# Engineering Analysis — Ubuntu Miracast Client

**Date:** 2026-08-24
**Version Analyzed:** 0.0.1
**Analyst:** AI Engineering Agent (Kiro)

## Executive Summary

This document analyzes the ubuntu-miracast-client project against current best practices from:
- **Wi-Fi Alliance** Wi-Fi Display Technical Specification v2.3 (2024)
- **Python Packaging Authority** (PyPA) — PEP 621, PEP 735, PEP 517/518
- **OpenSSF** Scorecard & SLSA v1.0
- **Freedesktop.org** XDG, D-Bus, Desktop Entry specifications
- **GNOME** Human Interface Guidelines (GTK4/libadwaita)
- **systemd** service hardening best practices

The project is in early development (0.x) with solid foundational architecture but significant gaps in packaging, security hardening, CI/CD maturity, and protocol conformance.

---

## 1. Protocol Conformance

### 1.1 Critical Gap: No RTSP Session Negotiation

**Spec requirement (WFD v2.3 §4.5):** Miracast sources MUST implement RTSP 1.0 (RFC 2326) session establishment via M1–M7 message exchange before streaming begins.

**Current state:** The project skips RTSP entirely — it establishes a Wi-Fi Direct P2P connection and immediately starts UDP streaming via GStreamer. This means:
- No capability negotiation (M3 GET_PARAMETER)
- No codec/resolution agreement (M4 SET_PARAMETER)
- No transport parameter exchange (M6 SETUP)
- No session management (PAUSE/TEARDOWN)

**Impact:** Won't interoperate with any spec-compliant Miracast sink (TVs, dongles, etc.). The sink expects an RTSP server; it receives raw MPEG-TS/RTP.

**Recommendation (P1):** Implement RTSP 1.0 session manager with M1–M7 flow. Reference: gnome-network-displays and Intel WDS (Wysiwidi) implementations.

### 1.2 WFD Subelement Parsing

**Current state:** Basic parsing exists but:
- No bounds-checking on hex string length before slicing
- No validation that subelement ID matches expected (0x00)
- Doesn't parse multiple subelements (only reads first one)
- Hardcodes wfd_subelems for advertisement without negotiation

**Recommendation (P2):** Add robust parser with length validation, multi-subelement support, and unit tests for malformed inputs.

### 1.3 Transport

**Current state:** Streams directly to `rtsp_port` via UDP without RTSP handshake.
**Spec requirement:** Port 7236 is the TCP control port for RTSP, NOT the UDP streaming port. The UDP port is negotiated in M6 SETUP (`client_port=NNNNN`).

**Recommendation (P1):** Separate control (TCP:7236) and streaming (UDP:negotiated) channels.

---

## 2. Build System & Packaging

### 2.1 Legacy setup.py (Critical)

| Current | Best Practice |
|---------|--------------|
| `setup.py` + `setup.cfg` + `VERSION` file | `pyproject.toml` with PEP 621 metadata |
| `setuptools>=42` build-backend | `hatchling>=1.26` or `setuptools>=77` |
| `extras_require` for dev deps | PEP 735 `[dependency-groups]` |
| Manual version reading from file | `hatch-vcs` or explicit in `[project]` |
| `MANIFEST.in` for sdist | Hatchling auto-includes or explicit config |

**Impact:** Poor metadata on PyPI, no lockfile support, fragile version resolution.

**Recommendation (P1):** Migrate to full PEP 621 pyproject.toml with hatchling backend.

### 2.2 Development Tooling

| Current | Best Practice |
|---------|--------------|
| black + isort + flake8 + mypy | Ruff (replaces all linting/formatting) + mypy |
| `.flake8` config file | All config in `pyproject.toml` |
| No lockfile | `uv.lock` committed to VCS |
| pip for package management | `uv` (10-100x faster, lockfiles, PEP 735) |

**Recommendation (P2):** Replace black/isort/flake8 with Ruff. Adopt uv as package manager.

### 2.3 Version Management

**Current:** `VERSION` file read at runtime via `Path(__file__).parent.parent.parent / "VERSION"`.
**Problems:**
- Fragile path resolution (breaks in installed packages)
- Not PEP 517 compliant (version not in sdist metadata)
- Build artifacts show incorrect version (dist has `1.0.0` while VERSION says `0.0.1`)

**Recommendation (P2):** Use `hatch-vcs` with git tags, or declare version statically in `[project]`.

---

## 3. CI/CD Pipeline

### 3.1 Security Hardening (Critical)

| Gap | Risk | Fix |
|-----|------|-----|
| Actions pinned to tags (`@v4`, `@v5`) | Supply-chain attack (tj-actions, trivy incidents) | Pin to full SHA |
| No `permissions:` block | Overprivileged GITHUB_TOKEN | Add `permissions: read-all` at workflow level |
| No concurrency control | Wasted CI minutes, race conditions | Add `concurrency:` with cancel-in-progress |
| No dependency review | Malicious deps merge unnoticed | Add `actions/dependency-review-action` |
| No SAST | Security bugs in source | Add CodeQL + Bandit |
| No secret scanning | Credentials in code | Enable GitHub secret scanning |

### 3.2 Missing OpenSSF Scorecard Checks

Current estimated score: **~3/10**

| Check | Status | Fix |
|-------|--------|-----|
| Token-Permissions | ❌ | Add explicit permissions |
| Pinned-Dependencies | ❌ | SHA-pin all actions |
| Branch-Protection | ❌ | Configure branch rules |
| Security-Policy | ❌ | Add SECURITY.md |
| Dependency-Update-Tool | ❌ | Add dependabot.yml |
| SAST | ❌ | Add CodeQL workflow |
| Code-Review | ❌ | Require PR reviews |
| Signed-Releases | ✅ (partial) | attest-build-provenance exists |
| Vulnerabilities | ⚠️ | Need pip-audit in CI |

### 3.3 Release Pipeline

**Current strengths:** Has build provenance attestation, PyPI trusted publishing, Debian package build, conventional commits.

**Gaps:**
- No SBOM generation
- No Sigstore signing of release artifacts
- No environment protection rules for PyPI publish
- Snapshot builds create too many pre-release tags (tag pollution)

**Recommendation (P1):** Rewrite CI/CD to best-in-class. See implementation below.

---

## 4. Security

### 4.1 Privilege Escalation (Critical)

**Current:** All wpa_cli commands run with `sudo` — requires the entire application to run as root or the user to have passwordless sudo for wpa_cli.

**Best practice (Freedesktop/GNOME):**
1. Main app runs unprivileged as the user
2. Privileged operations delegated to a small helper
3. Helper authorized via polkit policy
4. Or: Use NetworkManager D-Bus API (already polkit-mediated)

**Recommendation (P1):** Create polkit policy + helper binary pattern. Medium-term: migrate to NetworkManager D-Bus API.

### 4.2 Systemd Service Hardening

**Current service file:**
```ini
[Service]
ExecStart=...
Restart=on-failure
RestartSec=5s
Environment=DISPLAY=:0
```

**Missing directives (all should be added):**
- `NoNewPrivileges=true`
- `ProtectSystem=strict`
- `ProtectHome=read-only`
- `PrivateTmp=true`
- `PrivateDevices=true`
- `ProtectKernelTunables=true`
- `ProtectKernelModules=true`
- `ProtectControlGroups=true`
- `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK`
- `RestrictNamespaces=true`
- `MemoryDenyWriteExecute=true`
- `SystemCallFilter=@system-service`
- `MemoryMax=512M`
- `CPUQuota=80%`

### 4.3 Input Validation

**WFD subelement parsing** has no bounds checking:
```python
device_info = int(wfd_hex[6:10], 16)  # Can crash on short strings
rtsp_port = int(wfd_hex[10:14], 16)   # No validation port is valid (1-65535)
```

**Recommendation (P2):** Add defensive parsing with explicit length checks and value range validation.

### 4.4 Missing Security Infrastructure

- No `SECURITY.md` (vulnerability reporting process)
- No AppArmor profile
- No Linux capabilities usage (CAP_NET_ADMIN instead of full root)
- No input sanitization on subprocess arguments (shell injection risk if device names contain special characters)

---

## 5. Application Architecture

### 5.1 D-Bus Application ID

**Current:** `com.ubuntu.miracast-client`
**Issue:** Hyphens in D-Bus bus names are deprecated (spec v0.32+). Also, `com.ubuntu` namespace should only be used by Canonical.

**Recommendation:** Use `io.github.<username>.MiracastClient` or similar reverse-DNS without hyphens.

### 5.2 GStreamer Pipeline

**Current:** Launches `gst-launch-1.0` as a subprocess.
**Best practice:** Use GStreamer Python bindings (Gst module via PyGObject) for:
- Proper error handling via bus messages
- Dynamic pipeline modification
- Accurate stats (QoS messages, buffer levels)
- No subprocess overhead

**Recommendation (P3):** Migrate to in-process GStreamer pipeline.

### 5.3 XDG Compliance

**Current:** Partially compliant
- ✅ Config in `~/.config/ubuntu-miracast-client/`
- ✅ Logs in `~/.local/share/ubuntu-miracast-client/logs/`
- ❌ Should use `$XDG_CONFIG_HOME` env var (not hardcoded `~/.config`)
- ❌ History should be in `$XDG_STATE_HOME` (not data)
- ❌ Missing `$XDG_CACHE_HOME` usage

### 5.4 Error Handling

**Current:** Broad `except Exception` blocks everywhere.
**Recommendation (P3):** Define specific exception hierarchy, handle expected errors (NetworkError, TimeoutError, DeviceNotFoundError, etc.).

---

## 6. Testing

### 6.1 Current State (Good Foundation)

- 100 tests across 7 modules
- Unit tests with mocking for subprocess calls
- Integration tests for cross-module interactions
- Coverage reporting

### 6.2 Gaps

- No property-based testing (Hypothesis) for WFD parsing
- No fuzz testing for protocol parsers
- No end-to-end tests with mock RTSP server
- No performance/benchmark tests
- Tests don't run in CI with proper system dependencies (GStreamer/GTK stubs)

---

## 7. Priority Matrix

| Priority | Area | Issue | Effort |
|----------|------|-------|--------|
| **P0** | CI/CD | SHA-pin actions, add permissions, concurrency | Small |
| **P0** | Security | Add SECURITY.md | Small |
| **P0** | Packaging | Migrate to PEP 621 pyproject.toml | Medium |
| **P1** | CI/CD | Add CodeQL, dependency review, Dependabot | Medium |
| **P1** | Protocol | Implement RTSP session negotiation | Large |
| **P1** | Security | Polkit policy + privileged helper | Medium |
| **P1** | CI/CD | Add SBOM, Sigstore signing | Small |
| **P2** | Tooling | Replace black/isort/flake8 with Ruff | Small |
| **P2** | Tooling | Adopt uv + uv.lock | Small |
| **P2** | Security | Systemd service hardening | Small |
| **P2** | Security | Input validation on WFD parsing | Small |
| **P2** | App | Fix D-Bus application ID (no hyphens) | Small |
| **P3** | Architecture | Migrate to NetworkManager D-Bus API | Large |
| **P3** | Architecture | In-process GStreamer (not subprocess) | Medium |
| **P3** | App | Full XDG compliance with env vars | Small |
| **P3** | Testing | Add property-based + fuzz tests | Medium |

---

## 8. Immediate Actions (This Session)

1. ✅ Create this engineering analysis document
2. Create best-in-class CI/CD pipelines (SHA-pinned, permissions, security scanning)
3. Create SECURITY.md, CODEOWNERS, dependabot.yml
4. Modernize pyproject.toml (PEP 621, Ruff, dependency groups)
5. Create ARCHITECTURE.md for agent follow-up context
6. Create ADR (Architecture Decision Records) for key decisions

---

## References

- [Wi-Fi Display Technical Specification v2.3](https://www.wi-fi.org/) (Wi-Fi Alliance, 2024)
- [OpenSSF Scorecard](https://github.com/ossf/scorecard)
- [SLSA v1.0 Specification](https://slsa.dev/spec/v1.0/)
- [PEP 621 — Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)
- [PEP 735 — Dependency Groups](https://peps.python.org/pep-0735/)
- [D-Bus Specification v0.43](https://dbus.freedesktop.org/doc/dbus-specification.html)
- [systemd.exec — Service Hardening](https://www.freedesktop.org/software/systemd/man/systemd.exec.html)
- [GNOME Network Displays](https://gitlab.gnome.org/GNOME/gnome-network-displays) (Reference Miracast implementation)
