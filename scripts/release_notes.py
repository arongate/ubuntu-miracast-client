#!/usr/bin/env python3
"""Generate release notes and determine version bump from Conventional Commits."""

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

COMMIT_PATTERN = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore)"
    r"(?P<breaking>!)?(?:\((?P<scope>[^)]+)\))?:\s*(?P<description>.+)$"
)

SECTION_TITLES = {
    "feat": "🚀 Features",
    "fix": "🐛 Bug Fixes",
    "perf": "⚡ Performance",
    "docs": "📚 Documentation",
    "refactor": "♻️ Refactoring",
    "test": "✅ Tests",
    "build": "🏗️ Build",
    "ci": "👷 CI/CD",
    "style": "💄 Style",
    "chore": "🔧 Chores",
}

BUMP_MAJOR = {"feat!", "fix!", "breaking"}
BUMP_MINOR = {"feat"}
BUMP_PATCH = {"fix", "perf"}


def get_commits_since_tag(tag=None):
    """Get commits since the given tag (or all commits if no tag)."""
    if tag:
        cmd = ["git", "log", f"{tag}..HEAD", "--pretty=format:%H|%s|%b---END---"]
    else:
        cmd = ["git", "log", "--pretty=format:%H|%s|%b---END---"]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    if not result.stdout.strip():
        return []

    commits = []
    for entry in result.stdout.split("---END---"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("|", 2)
        if len(parts) >= 2:
            sha = parts[0]
            subject = parts[1]
            body = parts[2] if len(parts) > 2 else ""
            commits.append({"sha": sha[:7], "subject": subject, "body": body})
    return commits


def get_previous_tag():
    """Get the most recent tag."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def parse_commits(commits):
    """Parse conventional commits and categorize them."""
    sections = defaultdict(list)
    breaking_changes = []
    bump = "patch"  # default bump

    for commit in commits:
        subject = commit["subject"]
        body = commit["body"]
        sha = commit["sha"]

        match = COMMIT_PATTERN.match(subject)
        if not match:
            # Non-conventional commit goes to "chore"
            sections["chore"].append({"description": subject, "sha": sha})
            continue

        commit_type = match.group("type")
        is_breaking = match.group("breaking") == "!"
        description = match.group("description")
        scope = match.group("scope")

        # Check for BREAKING CHANGE in body
        if "BREAKING CHANGE:" in body or "BREAKING-CHANGE:" in body:
            is_breaking = True

        # Format entry
        entry = {"description": description, "sha": sha, "scope": scope}
        sections[commit_type].append(entry)

        # Determine bump level
        if is_breaking:
            breaking_changes.append(
                {"description": description, "sha": sha, "scope": scope}
            )
            bump = "major"
        elif commit_type in BUMP_MINOR and bump != "major":
            bump = "minor"
        elif commit_type in BUMP_PATCH and bump not in ("major", "minor"):
            bump = "patch"

    return sections, breaking_changes, bump


def bump_version(current_version, bump_type):
    """Bump version according to SemVer. During 0.x, major bumps become minor."""
    parts = current_version.split(".")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    # During unstable phase (0.x.y), breaking changes bump minor, not major
    if major == 0 and bump_type == "major":
        bump_type = "minor"

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1

    return f"{major}.{minor}.{patch}"


def generate_release_notes(sections, breaking_changes):
    """Generate markdown release notes."""
    lines = []

    # Breaking changes first
    if breaking_changes:
        lines.append("## ⚠️ Breaking Changes\n")
        for change in breaking_changes:
            scope = f"**{change['scope']}:** " if change.get("scope") else ""
            lines.append(f"- {scope}{change['description']} ({change['sha']})")
        lines.append("")

    # Sections in order of importance
    section_order = ["feat", "fix", "perf", "refactor", "docs", "test", "build", "ci", "chore"]
    for section_type in section_order:
        entries = sections.get(section_type, [])
        if not entries:
            continue
        title = SECTION_TITLES.get(section_type, section_type.title())
        lines.append(f"## {title}\n")
        for entry in entries:
            scope = f"**{entry['scope']}:** " if entry.get("scope") else ""
            lines.append(f"- {scope}{entry['description']} ({entry['sha']})")
        lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    action = sys.argv[1] if len(sys.argv) > 1 else "notes"

    previous_tag = get_previous_tag()
    commits = get_commits_since_tag(previous_tag)

    if not commits:
        print("No commits found since last tag.", file=sys.stderr)
        if action == "bump":
            version_file = Path("VERSION")
            print(version_file.read_text().strip())
        elif action == "notes":
            print("No changes.")
        sys.exit(0)

    sections, breaking_changes, bump_type = parse_commits(commits)

    if action == "bump":
        current = Path("VERSION").read_text().strip()
        new_version = bump_version(current, bump_type)
        print(new_version)
    elif action == "bump-type":
        print(bump_type)
    elif action == "notes":
        notes = generate_release_notes(sections, breaking_changes)
        print(notes)
    elif action == "next-dev":
        # Generate next dev version for snapshots
        current = Path("VERSION").read_text().strip()
        next_version = bump_version(current, bump_type)
        # Count commits since last tag for dev iteration
        dev_count = len(commits)
        print(f"{next_version}-dev.{dev_count}")
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
