# ADR-001: Migrate from setup.py to PEP 621 pyproject.toml with hatchling

## Status

**Accepted** — 2026-08-24

## Context

The project uses a legacy `setup.py` + `setup.cfg` build system with `setuptools>=42`. This has several problems:

1. Metadata is split across setup.py, setup.cfg, and pyproject.toml
2. Version is read from a `VERSION` file via fragile Path resolution that breaks in installed packages
3. Dev dependencies use `extras_require` (published to PyPI metadata unnecessarily)
4. No lockfile for reproducible installs
5. Requires `MANIFEST.in` for sdist control
6. Cannot use modern PEP 735 dependency groups

The Python ecosystem has standardized on PEP 621 (project metadata in pyproject.toml) with PEP 517/518 build backends.

## Decision

Migrate to:
- **Build backend:** `hatchling>=1.26` (modern, fast, good plugin ecosystem)
- **Metadata:** Full PEP 621 in `[project]` table
- **Dev dependencies:** PEP 735 `[dependency-groups]` (not published to PyPI)
- **Linting/formatting:** Ruff (replaces black + isort + flake8)
- **Package manager:** `uv` with committed `uv.lock`
- **Version:** Static in `[project]` table initially; migrate to `hatch-vcs` when git tags are consistent

## Consequences

### Positive
- Single source of truth for all configuration
- Proper PyPI metadata and classifiers
- Reproducible installs via uv.lock
- 10-100x faster dependency resolution (uv vs pip)
- Ruff is 10-100x faster than black+flake8 combined
- PEP 735 groups keep dev deps out of published metadata

### Negative
- One-time migration effort (removing setup.py, setup.cfg, .flake8, MANIFEST.in)
- Contributors must install `uv` (or fall back to pip)
- Existing CI workflows need updating (done)

### Removed files
- `setup.py`
- `setup.cfg`
- `.flake8`
- `MANIFEST.in`

## References

- [PEP 621](https://peps.python.org/pep-0621/)
- [PEP 735](https://peps.python.org/pep-0735/)
- [Hatchling docs](https://hatch.pypa.io/latest/)
- [uv docs](https://docs.astral.sh/uv/)
- [Ruff docs](https://docs.astral.sh/ruff/)
