#!/usr/bin/env python3
"""Create GitHub issues from docs/guides/TASKS.md entries.

This utility parses the task list and opens labeled issues on GitHub.
A personal access token is required unless running in --dry-run mode.

Example:
    python tools/issue_migrator.py --repo owner/repo --token $GITHUB_TOKEN \
        --milestone "Backlog" --dry-run
"""
import argparse
import os
import re
from pathlib import Path
from typing import Dict, List

import json
from urllib import request as urlrequest

TASKS_PATH = Path(__file__).parent.parent / "docs/guides/TASKS.md"


def parse_tasks(file_path: Path) -> List[Dict[str, str]]:
    """Parse TASKS.md into a list of issue dictionaries."""
    lines = file_path.read_text().splitlines()
    tasks: List[Dict[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        heading = re.match(r"##\s+\d+\.\s+(.*)", line)
        if heading:
            title = heading.group(1).strip()
            if title == "Feature and UI Enhancements":
                i += 1
                while i < len(lines) and not lines[i].startswith("## "):
                    sub = lines[i].strip()
                    if sub.startswith("- **"):
                        sub_title = re.match(r"- \*\*(.+?)\*\*", sub).group(1)
                        i += 1
                        sub_body: List[str] = []
                        while i < len(lines) and (lines[i].startswith("  -") or not lines[i].strip()):
                            content = lines[i].strip()
                            if content:
                                sub_body.append(content[2:])
                            i += 1
                        tasks.append({"title": sub_title, "body": "\n".join(sub_body).strip()})
                    else:
                        i += 1
            else:
                i += 1
                body: List[str] = []
                while i < len(lines) and not lines[i].startswith("## "):
                    if lines[i].strip():
                        body.append(lines[i].strip())
                    i += 1
                tasks.append({"title": title, "body": "\n".join(body).strip()})
        else:
            i += 1
    return tasks


def create_issue(repo: str, token: str, title: str, body: str,
                 labels: List[str], milestone: int | None, dry_run: bool) -> None:
    """Create a GitHub issue via REST API."""
    if dry_run:
        print(f"[DRY-RUN] {title}\n{body}\n")
        return
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    payload: Dict[str, object] = {"title": title, "body": body, "labels": labels}
    if milestone is not None:
        payload["milestone"] = milestone
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, headers=headers, method="POST")
    with urlrequest.urlopen(req, timeout=10) as resp:
        issue = json.load(resp)
    print(f"Created issue #{issue['number']}: {title}")


def get_milestone_number(repo: str, token: str, milestone: str) -> int | None:
    """Retrieve milestone number by name."""
    url = f"https://api.github.com/repos/{repo}/milestones"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    req = urlrequest.Request(url, headers=headers)
    with urlrequest.urlopen(req, timeout=10) as resp:
        milestones = json.load(resp)
    for ms in milestones:
        if ms["title"] == milestone:
            return ms["number"]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Create GitHub issues from TASKS.md")
    parser.add_argument("--repo", required=True, help="GitHub repo in 'owner/repo' format")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"),
                        help="GitHub personal access token")
    parser.add_argument("--label", action="append", default=["task"],
                        help="Label to apply to created issues")
    parser.add_argument("--milestone", help="Milestone name to assign to issues")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print issues without creating them")
    args = parser.parse_args()

    if not args.token and not args.dry_run:
        parser.error("GitHub token required unless using --dry-run")

    milestone_number = None
    if args.milestone and not args.dry_run:
        milestone_number = get_milestone_number(args.repo, args.token, args.milestone)
        if milestone_number is None:
            parser.error(f"Milestone '{args.milestone}' not found")

    for task in parse_tasks(TASKS_PATH):
        create_issue(
            repo=args.repo,
            token=args.token,
            title=task["title"],
            body=task["body"],
            labels=args.label,
            milestone=milestone_number,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
