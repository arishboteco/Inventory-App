#!/usr/bin/env python3
"""
Changelog maintenance utility for Inventory Pro development.

Usage:
    python tools/changelog.py add "feat: new feature description"
    python tools/changelog.py release "2.2.0"
    python tools/changelog.py unreleased
"""

import argparse
import datetime
from pathlib import Path

CHANGELOG_PATH = Path(__file__).parent.parent / "CHANGELOG.md"


def add_entry(entry_type, description):
    """Add a new entry to the Unreleased section."""
    content = CHANGELOG_PATH.read_text()
    lines = content.split("\n")

    # Find the [Unreleased] section
    unreleased_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "## [Unreleased]":
            unreleased_idx = i
            break

    if unreleased_idx is None:
        print("Could not find [Unreleased] section in CHANGELOG.md")
        return

    # Determine section based on entry type
    section_map = {
        "feat": "Added",
        "fix": "Fixed",
        "docs": "Changed",
        "perf": "Performance",
        "test": "Changed",
        "refactor": "Changed",
        "style": "Changed",
        "chore": "Changed",
    }

    entry_type_clean = entry_type.split(":")[0] if ":" in entry_type else entry_type
    section = section_map.get(entry_type_clean, "Changed")

    # Find or create the section
    section_idx = None
    for i in range(unreleased_idx, len(lines)):
        if lines[i].strip() == f"### {section}":
            section_idx = i
            break
        elif lines[i].strip().startswith("## [") and i > unreleased_idx:
            # Hit the next version section, need to add our section
            break

    if section_idx is None:
        # Add new section
        insert_idx = unreleased_idx + 1
        while insert_idx < len(lines) and not lines[insert_idx].strip().startswith(
            "## ["
        ):
            if lines[insert_idx].strip().startswith("### "):
                break
            insert_idx += 1

        lines.insert(insert_idx, "")
        lines.insert(insert_idx + 1, f"### {section}")
        lines.insert(insert_idx + 2, f"- {description}")
        section_idx = insert_idx + 1
    else:
        # Add to existing section
        insert_idx = section_idx + 1
        while (
            insert_idx < len(lines)
            and lines[insert_idx].strip()
            and not lines[insert_idx].strip().startswith("### ")
        ):
            insert_idx += 1
        lines.insert(insert_idx, f"- {description}")

    CHANGELOG_PATH.write_text("\n".join(lines))
    print(f"Added to {section}: {description}")


def create_release(version):
    """Move Unreleased items to a new version section."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    content = CHANGELOG_PATH.read_text()

    # Replace [Unreleased] with the new version
    content = content.replace(
        "## [Unreleased]", f"## [Unreleased]\n\n## [{version}] - {today}"
    )

    CHANGELOG_PATH.write_text(content)
    print(f"Created release [{version}] - {today}")


def show_unreleased():
    """Show current unreleased changes."""
    content = CHANGELOG_PATH.read_text()
    lines = content.split("\n")

    unreleased_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "## [Unreleased]":
            unreleased_idx = i
            break

    if unreleased_idx is None:
        print("No unreleased section found")
        return

    print("Current unreleased changes:")
    print("=" * 40)

    for i in range(unreleased_idx, len(lines)):
        line = lines[i]
        if line.strip().startswith("## [") and i > unreleased_idx:
            break
        if line.strip():
            print(line)


def main():
    parser = argparse.ArgumentParser(description="Maintain CHANGELOG.md")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add entry command
    add_parser = subparsers.add_parser("add", help="Add new changelog entry")
    add_parser.add_argument("description", help="Description of the change")
    add_parser.add_argument(
        "--type", default="feat", help="Type of change (feat, fix, docs, etc.)"
    )

    # Release command
    release_parser = subparsers.add_parser("release", help="Create new release section")
    release_parser.add_argument("version", help="Version number (e.g., 2.2.0)")

    # Show unreleased command
    subparsers.add_parser("unreleased", help="Show unreleased changes")

    args = parser.parse_args()

    if args.command == "add":
        add_entry(args.type, args.description)
    elif args.command == "release":
        create_release(args.version)
    elif args.command == "unreleased":
        show_unreleased()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
