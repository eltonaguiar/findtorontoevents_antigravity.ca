#!/usr/bin/env python3
"""Non-main branch run audit: duplicates, redundancy, feeds, branch necessity.

Answers three questions with evidence instead of inference:
  1. What runs on non-main branches, and are those runs duplicates/redundant?
  2. What do non-main runs feed (main pushes, FTP, artifacts, Pages, PR checks)?
  3. Which branches are still needed (compare against main + open PRs)?

Writes reports/gha_nonmain_audit.json and reports/gha_nonmain_audit.md.
Read-only: GET requests only.

    python3 tools/gha_nonmain_audit.py --pages 12 --compare
    python3 tools/gha_nonmain_audit.py --no-compare        # cheaper, runs only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://api.github.com"
REPO = os.getenv("GHA_REPO", "eltonaguiar/findtorontoevents_antigravity.ca")
DEFAULT_BRANCH = os.getenv("GHA_DEFAULT_BRANCH", "main")
WF_DIR = Path(".github/workflows")
REPORTS = Path("reports")

SESSION = requests.Session()


def token() -> str:
    tok = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if tok:
        return tok
    out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if out.returncode != 0 or not out.stdout.strip():
        sys.exit("no GitHub token: set GITHUB_TOKEN or run `gh auth login`")
    return out.stdout.strip()


SESSION.headers.update(
    {
        "Authorization": f"Bearer {token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gha-nonmain-audit/1.0",
    }
)


def get(path: str, **params):
    resp = SESSION.get(f"{API}{path}", params=params, timeout=40)
    if resp.status_code == 404:
        return None
    if resp.status_code == 403:
        print(f"::warning::rate limited on {path}")
        return None
    resp.raise_for_status()
    return resp.json()


def fetch_runs(pages: int) -> list[dict]:
    runs: list[dict] = []
    for page in range(1, pages + 1):
        data = get(f"/repos/{REPO}/actions/runs", per_page=100, page=page)
        if not data:
            break
        chunk = data.get("workflow_runs", [])
        if not chunk:
            break
        runs.extend(chunk)
        if len(chunk) < 100:
            break
    return runs


def minutes(run: dict) -> float:
    def parse(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    start, end = parse(run.get("run_started_at")), parse(run.get("updated_at"))
    if raise_ := (start and end):
        return (end - start).total_seconds() / 60.0
    return 0.0


def feed_profile(path: str) -> dict:
    """Static profile of what a workflow does, from the checked-out file."""
    name = Path(path).name
    file = WF_DIR / name
    if not file.is_file():
        return {"file": name, "local": False}
    text = file.read_text(encoding="utf-8", errors="replace")
    return {
        "file": name,
        "local": True,
        "push_trigger": bool(re.search(r"^\s{2}push:", text, re.M)),
        "pull_request_trigger": bool(re.search(r"^\s{2}pull_request:", text, re.M)),
        "branches_filter": bool(re.search(r"^\s{4}branches(-ignore)?:", text, re.M)),
        "writes_main": bool(
            re.search(r"HEAD:main|push origin main|safe_commit_push\.sh|safe_push\.sh", text)
        ),
        "ftp_deploy": "ftp" in text.lower(),
        "artifacts": "upload-artifact" in text,
        "contents_write": bool(re.search(r"contents:\s*write", text)),
        "event_guard": bool(re.search(r"github\.event_name\s*!=", text)),
    }


def compare_branch(branch: str) -> dict:
    data = get(f"/repos/{REPO}/compare/{DEFAULT_BRANCH}...{branch}")
    if not data:
        return {"branch": branch, "status": "unknown", "ahead_by": None, "behind_by": None}
    return {
        "branch": branch,
        "status": data.get("status"),
        "ahead_by": data.get("ahead_by"),
        "behind_by": data.get("behind_by"),
        "total_commits": data.get("total_commits"),
    }


def list_branches() -> list[str]:
    out: list[str] = []
    page = 1
    while True:
        data = get(f"/repos/{REPO}/branches", per_page=100, page=page)
        if not data:
            break
        out.extend(b["name"] for b in data)
        if len(data) < 100:
            break
        page += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=12, help="100-run pages to scan")
    ap.add_argument("--compare", dest="compare", action="store_true", default=True)
    ap.add_argument("--no-compare", dest="compare", action="store_false")
    args = ap.parse_args()

    runs = fetch_runs(args.pages)
    nonmain = [r for r in runs if r.get("head_branch") != DEFAULT_BRANCH]

    # --- duplicates: same workflow + same commit, more than one run ---
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in nonmain:
        groups[(r.get("path"), r.get("head_sha"))].append(r)
    dup_groups = [
        {
            "workflow": path,
            "sha": sha[:10],
            "branch": items[0].get("head_branch"),
            "runs": len(items),
            "conclusions": dict(Counter(i.get("conclusion") for i in items)),
            "wasted_minutes": round(
                sum(minutes(i) for i in sorted(items, key=lambda x: x.get("created_at", ""))[1:]),
                1,
            ),
        }
        for (path, sha), items in groups.items()
        if len(items) > 1
    ]
    dup_groups.sort(key=lambda x: -x["runs"])

    per_branch: dict[str, dict] = {}
    for r in nonmain:
        b = r.get("head_branch") or "?"
        row = per_branch.setdefault(
            b,
            {
                "runs": 0,
                "workflows": Counter(),
                "events": Counter(),
                "conclusions": Counter(),
                "first": r.get("created_at"),
                "last": r.get("created_at"),
            },
        )
        row["runs"] += 1
        row["workflows"][r.get("path")] += 1
        row["events"][r.get("event")] += 1
        row["conclusions"][str(r.get("conclusion"))] += 1
        row["first"] = min(row["first"], r.get("created_at") or row["first"])
        row["last"] = max(row["last"], r.get("created_at") or row["last"])

    per_workflow: dict[str, dict] = {}
    for r in nonmain:
        path = r.get("path") or "?"
        row = per_workflow.setdefault(
            path, {"runs": 0, "branches": Counter(), "conclusions": Counter(), "durations": []}
        )
        row["runs"] += 1
        row["branches"][r.get("head_branch")] += 1
        row["conclusions"][str(r.get("conclusion"))] += 1
        row["durations"].append(minutes(r))

    feed = {p: feed_profile(p) for p in per_workflow}

    # --- hazard: any-branch push trigger that can write to main ---
    hazard = []
    for file in sorted(WF_DIR.glob("*.yml")):
        text = file.read_text(encoding="utf-8", errors="replace")
        has_push = bool(re.search(r"^\s{2}push:", text, re.M))
        branches = bool(re.search(r"^\s{4}branches(-ignore)?:", text, re.M))
        writes = bool(
            re.search(r"HEAD:main|push origin main|safe_commit_push\.sh|safe_push\.sh", text)
        )
        if has_push and writes and not branches:
            hazard.append({"file": file.name, "why": "push on any branch + writes to main"})

    # --- branch necessity ---
    branches: list[str] = []
    compares: list[dict] = []
    prs: list[dict] = []
    if args.compare:
        branches = list_branches()
        with ThreadPoolExecutor(max_workers=8) as pool:
            compares = list(pool.map(compare_branch, branches))
        pr_data = get(f"/repos/{REPO}/pulls", state="open", per_page=100) or []
        prs = [
            {
                "number": p.get("number"),
                "head": (p.get("head") or {}).get("ref"),
                "title": p.get("title"),
                "updated_at": p.get("updated_at"),
            }
            for p in pr_data
        ]

    pr_heads = {p["head"] for p in prs}
    for row in compares:
        row["has_open_pr"] = row["branch"] in pr_heads
        if row["status"] == "identical" or row.get("ahead_by") == 0:
            row["verdict"] = "merged_or_identical"
        elif row.get("ahead_by") and row["branch"] in pr_heads:
            row["verdict"] = "active_pr"
        elif row.get("ahead_by"):
            row["verdict"] = "unmerged_work"
        else:
            row["verdict"] = "unknown"

    by_verdict = Counter(r["verdict"] for r in compares)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": REPO,
        "default_branch": DEFAULT_BRANCH,
        "runs_scanned": len(runs),
        "window": {
            "newest": max((r.get("created_at") or "" for r in runs), default=None),
            "oldest": min((r.get("created_at") or "" for r in runs), default=None),
        },
        "nonmain_runs": len(nonmain),
        "nonmain_events": dict(Counter(r.get("event") for r in nonmain)),
        "nonmain_conclusions": dict(Counter(str(r.get("conclusion")) for r in nonmain)),
        "duplicate_groups": dup_groups,
        "duplicate_runs": sum(g["runs"] - 1 for g in dup_groups),
        "duplicate_wasted_minutes": round(sum(g["wasted_minutes"] for g in dup_groups), 1),
        "per_branch": {k: {**v, "workflows": dict(v["workflows"]), "events": dict(v["events"]),
                           "conclusions": dict(v["conclusions"])} for k, v in per_branch.items()},
        "per_workflow": {
            k: {"runs": v["runs"], "branches": dict(v["branches"]),
                "conclusions": dict(v["conclusions"])}
            for k, v in per_workflow.items()
        },
        "feed_profiles": feed,
        "hazards": hazard,
        "branches": {
            "total": len(branches),
            "verdicts": dict(by_verdict),
            "rows": sorted(compares, key=lambda r: (r["verdict"], r["branch"])),
            "open_prs": prs,
        },
    }

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "gha_nonmain_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Non-main branch run audit",
        "",
        f"- Runs scanned: **{len(runs)}** ({report['window']['oldest']} → {report['window']['newest']})",
        f"- Non-main runs: **{len(nonmain)}** ({len(nonmain)/len(runs)*100:.1f}%)",
        f"- Events: `{report['nonmain_events']}`",
        f"- Conclusions: `{report['nonmain_conclusions']}`",
        f"- Duplicate groups (same workflow+commit run >1x): **{len(dup_groups)}**, extra runs "
        f"**{report['duplicate_runs']}**, wasted **{report['duplicate_wasted_minutes']} min**",
        "",
        "## Non-main workflows",
        "",
        "| workflow | runs | conclusions | feed |",
        "|---|---|---|---|",
    ]
    for path, row in sorted(per_workflow.items(), key=lambda kv: -kv[1]["runs"]):
        f = feed.get(path, {})
        tags = []
        if f.get("pull_request_trigger"):
            tags.append("PR gate")
        if f.get("writes_main"):
            tags.append("writes main")
        if f.get("ftp_deploy"):
            tags.append("FTP")
        if f.get("artifacts"):
            tags.append("artifact")
        if not f.get("local"):
            tags.append("built-in/no local file")
        lines.append(
            f"| `{Path(path).name}` | {row['runs']} | `{row['conclusions']}` | {', '.join(tags) or '—'} |"
        )

    lines += ["", "## Branches by verdict", "", "| verdict | count |", "|---|---|"]
    for verdict, count in by_verdict.most_common():
        lines.append(f"| {verdict} | {count} |")

    if dup_groups:
        lines += ["", "## Duplicate runs (same commit re-run)", "",
                  "| workflow | branch | sha | runs | wasted min |", "|---|---|---|---|---|"]
        for g in dup_groups[:25]:
            lines.append(
                f"| `{Path(g['workflow']).name}` | {g['branch']} | `{g['sha']}` | {g['runs']} | {g['wasted_minutes']} |"
            )

    if hazard:
        lines += ["", "## Hazard: push on any branch + writes to main", ""]
        for h in hazard:
            lines.append(f"- `{h['file']}` — {h['why']}")

    (REPORTS / "gha_nonmain_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"runs={len(runs)} nonmain={len(nonmain)} dup_groups={len(dup_groups)} "
          f"dup_runs={report['duplicate_runs']} hazards={len(hazard)} "
          f"branches={len(branches)} verdicts={dict(by_verdict)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
