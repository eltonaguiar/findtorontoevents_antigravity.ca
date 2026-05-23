#!/usr/bin/env python3
"""List repo workflows whose latest run is missing or older than N days."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_owner_repo() -> str:
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "eltonaguiar/findtorontoevents_antigravity.ca"
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    return m.group(1) if m else "eltonaguiar/findtorontoevents_antigravity.ca"


def gh_api_json(repo: str, api_path: str) -> dict:
    r = subprocess.run(
        ["gh", "api", f"repos/{repo}{api_path}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(r.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "min_days",
        nargs="?",
        type=float,
        default=30.0,
        help="Flag workflows whose latest run is this many days old (default: 30)",
    )
    parser.add_argument(
        "--repo",
        help="owner/name override (default: parse from git remote origin)",
    )
    parser.add_argument(
        "--summary-file",
        help="Append the text report to this file (e.g. $GITHUB_STEP_SUMMARY)",
    )
    args = parser.parse_args()

    repo = args.repo or get_owner_repo()
    min_days = args.min_days
    now = datetime.now(timezone.utc)
    workflows: list[dict] = []
    page = 1
    while True:
        data = gh_api_json(
            repo,
            f"/actions/workflows?per_page=100&page={page}",
        )
        batch = data.get("workflows") or []
        workflows.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    stale = []
    never = []
    for w in workflows:
        wid = w["id"]
        path = w.get("path", "")
        state = w.get("state", "")
        name = w.get("name", path)
        try:
            runs = gh_api_json(
                repo,
                f"/actions/workflows/{wid}/runs?per_page=1",
            )
        except subprocess.CalledProcessError as e:
            stale.append((name, path, state, f"api_error: {e.stderr[:200]}"))
            continue
        items = runs.get("workflow_runs") or []
        if not items:
            never.append((name, path, state))
            continue
        created = items[0].get("created_at", "")
        conc = items[0].get("conclusion") or ""
        status = items[0].get("status") or ""
        try:
            t = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            continue
        days = (now - t).total_seconds() / 86400
        if days >= min_days:
            stale.append(
                (name, path, state, f"{days:.1f}d ago", conc, status, created[:10])
            )

    never.sort(key=lambda x: x[1])
    stale.sort(key=lambda x: str(x[3]))

    lines: list[str] = []
    lines.append(f"Repo: {repo}")
    lines.append(f"Total workflows on GitHub: {len(workflows)}")
    lines.append(f"Never run: {len(never)}")
    lines.append(f"Latest run >= {min_days} days ago: {len(stale)}")
    lines.append("")
    if never:
        lines.append("=== Never run ===")
        for row in never[:80]:
            lines.append(f"  {row[2]:8} {row[1]}")
        if len(never) > 80:
            lines.append(f"  ... and {len(never) - 80} more")
        lines.append("")
    if stale:
        lines.append(f"=== Stale (>={min_days}d) ===")
        for row in stale[:80]:
            lines.append("  " + "\t".join(str(x) for x in row))
        if len(stale) > 80:
            lines.append(f"  ... and {len(stale) - 80} more")

    report = "\n".join(lines)
    print(report)
    if args.summary_file:
        Path(args.summary_file).open("a", encoding="utf-8").write(
            "## Stale / never-run workflows\n\n```\n" + report + "\n```\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
