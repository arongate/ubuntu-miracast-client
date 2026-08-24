# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.x (latest) | ✅ Security fixes |
| < latest 0.x | ❌ Upgrade to latest |

> This project is in initial development (0.x). Only the latest release receives security patches.

## Reporting a Vulnerability

**Please do NOT open a public issue for security vulnerabilities.**

### Preferred Method: GitHub Security Advisories

Report vulnerabilities via GitHub's private reporting mechanism:

1. Go to https://github.com/arongate/ubuntu-miracast-client/security/advisories/new
2. Fill in the vulnerability details
3. Submit the advisory

### Alternative: Email

If you cannot use GitHub Security Advisories, email: **security@example.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

### Response Timeline

| Action | Timeline |
|--------|----------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 7 days |
| Fix development | Within 30 days (critical), 90 days (other) |
| Public disclosure | After fix is released |

### Scope

The following are in scope for security reports:

- Authentication/authorization bypass
- Remote code execution
- Privilege escalation (especially wpa_supplicant/root access)
- Information disclosure (config, credentials, session data)
- Denial of service via malformed WFD/RTSP messages
- Supply chain issues (compromised dependencies)
- Insecure defaults

### Out of Scope

- Issues requiring physical access to the device
- Social engineering attacks
- Vulnerabilities in upstream dependencies (report to upstream, but notify us)
- Issues in unsupported versions

## Security Design Principles

This project follows these security principles:

1. **Least privilege**: Minimize use of root/sudo; prefer polkit + capability-based access
2. **Defense in depth**: AppArmor profile, systemd hardening, input validation
3. **Secure defaults**: Restrictive configuration out of the box
4. **Dependency hygiene**: Pinned versions, lockfiles, regular auditing
5. **Supply chain security**: SLSA provenance, Sigstore signatures, SHA-pinned CI actions

## Acknowledgments

We appreciate responsible disclosure and will credit security researchers (unless they prefer anonymity) in our release notes.
