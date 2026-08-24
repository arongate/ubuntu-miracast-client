# ADR-004: CI/CD Security Strategy — OpenSSF Scorecard Compliance

## Status

**Accepted** — 2026-08-24

## Context

The project's CI/CD pipeline had multiple security gaps:
- GitHub Actions pinned to mutable tags (vulnerable to supply-chain attacks like tj-actions March 2025)
- No permissions restrictions (GITHUB_TOKEN has broad access)
- No SAST/SCA scanning
- No dependency update automation
- No SLSA provenance for releases
- No release signing

The OpenSSF Scorecard estimated score was ~3/10.

## Decision

Implement a defense-in-depth CI/CD pipeline targeting OpenSSF Scorecard 8+/10:

### Security Controls Implemented

| Control | Implementation |
|---------|---------------|
| SHA-pinned actions | All actions pinned to full commit SHA with version comment |
| Minimal permissions | `permissions: read-all` at workflow level, explicit per-job |
| Concurrency control | Cancel redundant runs, prevent race conditions |
| SAST | CodeQL (semantic analysis) + Bandit (Python-specific) |
| SCA | `uv audit` for dependency vulnerabilities |
| Dependency updates | Dependabot for Actions (SHA), Python deps, Docker |
| Dependency review | `actions/dependency-review-action` on PRs |
| SLSA provenance | `actions/attest-build-provenance` (Build L2) |
| Release signing | Sigstore (`gh-action-sigstore-python`) |
| SBOM | CycloneDX JSON generation |
| Trusted publishing | PyPI OIDC (no stored API tokens) |
| Environment protection | GitHub Environments with required reviewers |
| Branch protection | Required status checks, signed commits, linear history |
| Security policy | SECURITY.md with responsible disclosure process |
| Code ownership | CODEOWNERS for review requirements |

### Workflow Architecture

```
┌─────────────┐
│  ci.yml     │ ── Every push/PR to main
├─────────────┤
│ • lint      │    Ruff check + format
│ • typecheck │    mypy strict mode
│ • test      │    pytest matrix (3.10, 3.11, 3.12)
│ • codeql    │    SAST (Python)
│ • bandit    │    Python security linting
│ • audit     │    uv audit (SCA)
│ • dep-review│    PR-only dependency gating
│ • ci-pass   │    Gate job for branch protection
└─────────────┘

┌──────────────┐
│ release.yml  │ ── Manual dispatch (workflow_dispatch)
├──────────────┤
│ • prepare    │    Version from conventional commits
│ • test       │    Full test suite
│ • build      │    Python wheel + sdist + deb + SBOM
│ • publish    │    Tag → Attest → Sign → PyPI → GH Release
└──────────────┘

┌──────────────┐
│ snapshot.yml │ ── Push to main (source changes only)
├──────────────┤
│ • test+build │    Quick build + attest + upload artifact
└──────────────┘
```

### SHA Pins Used (verified 2026-08)

| Action | SHA | Tag |
|--------|-----|-----|
| actions/checkout | `11bd71901bbe5b1630ceea73d27597364c9af683` | v4.2.2 |
| actions/setup-python | `a26af69be951a213d495a4c3e4e4022e16d87065` | v5.6.0 |
| actions/upload-artifact | `ea165f8d65b6e75b540449e92b4886f43607fa02` | v4.6.2 |
| actions/download-artifact | `d3f86a106a0bac45b974a628896c90dbdf5c8093` | v4.3.0 |
| actions/attest-build-provenance | `db473fddc028af60658334401dc6fa3ffd8669fd` | v2.3.0 |
| actions/dependency-review-action | `da24556b548a50705dd671f47852072ea4c105d9` | v4.7.0 |
| astral-sh/setup-uv | `6b9c6063abd6010835644d4c2e1bef4cf5cd0fca` | v6.0.0 |
| dorny/paths-filter | `de90cc6fb38fc0963ad72b210f1f284cd68cea36` | v3.0.2 |
| sigstore/gh-action-sigstore-python | `f514d46b907ebcd5bedc05145c03b69c1edd8b46` | v3.0.0 |
| pypa/gh-action-pypi-publish | `76f52bc884231f62b9a034ebfe128415bbaabdfc` | release/v1 |
| softprops/action-gh-release | `01570a1f39cb168c169c802c3bceb9e93fb10974` | v2.3.0 |

## Consequences

### Positive
- OpenSSF Scorecard target: 8+/10 (up from ~3)
- Protected against supply-chain attacks on GitHub Actions
- Vulnerabilities caught before merge (CodeQL, Bandit, dependency review)
- Cryptographic proof of build provenance (SLSA L2)
- Users can verify package authenticity (Sigstore)
- No stored secrets for PyPI publishing (OIDC)
- Automated dependency updates with grouped PRs

### Negative
- SHA pins require manual updates (mitigated by Dependabot)
- CI runs are slightly longer (security scanning adds ~2-3 min)
- Contributors must be aware of commit signing requirement
- Environment protection adds friction to releases (intentional)

## References

- [OpenSSF Scorecard](https://github.com/ossf/scorecard)
- [SLSA v1.0 Specification](https://slsa.dev/spec/v1.0/)
- [tj-actions supply chain attack (2025)](https://blog.stepsecurity.io/tj-actions-changed-files-incident/)
- [GitHub Artifact Attestations](https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations)
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
