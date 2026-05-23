#!/usr/bin/env python3
"""
Deep-scan GitHub Actions logs: for each workflow, analyze at most two runs:
  - Always the latest run on the branch.
  - If that run did not succeed, also the immediately prior run.

Discovery: unique workflow names from recent `gh run list` (time window).

Usage:
  python tools/gha_latest_prior_log_scan.py
  python tools/gha_latest_prior_log_scan.py --shards 2 --shard 0 --out tmp/deep0.md
  python tools/gha_latest_prior_log_scan.py --workflow "Unified Audit Dashboard"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_REPO = "eltonaguiar/findtorontoevents_antigravity.ca"

SIGNAL_LINE = re.compile(
    r"|".join(
        [
            r"##\[error\]",
            r"KeyError",
            r"NameError",
            r"ValueError",
            r"TypeError",
            r"Traceback \(most recent",
            r"Quote not found for symbol",
            r"symbol.*not found",
            r"HTTP Error 404",
            r"HTTP Error 451",
            r"403 Client Error",
            r"fatal:",
            r"unknown switch",
            r"pathspec .* did not match",
            r"merge conflict",
            r"CONFLICT \(",
            r"Could not fetch data for",
            r"All Binance endpoints failed",
            r"CIRCUIT BREAKER",
            r"STALE payload",
            r"Process completed with exit code",
            r"submodule",
            r"No url found for submodule",
        ]
    ),
    re.I,
)


def _run_gh(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def gh_json(args: list[str]) -> list | dict:
    p = _run_gh(args)
    if p.returncode != 0:
        sys.stderr.write(p.stderr or p.stdout or "gh failed\n")
        raise SystemExit(p.returncode or 1)
    if not (p.stdout or "").strip():
        return []
    return json.loads(p.stdout)


def discover_workflows(
    repo: str,
    branch: str,
    hours: int,
    list_limit: int,
) -> list[str]:
    """Ordered-unique workflow names from recent runs on branch."""
    runs = gh_json(
        [
            "run",
            "list",
            "--repo",
            repo,
            "--branch",
            branch,
            "--limit",
            str(list_limit),
            "--json",
            "workflowName,createdAt",
        ]
    )
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    seen: OrderedDict[str, None] = OrderedDict()
    for r in runs:
        try:
            t = datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00"))
        except Exception:
            continue
        if t < cutoff:
            continue
        name = r.get("workflowName") or ""
        if name and name not in seen:
            seen[name] = None
    return list(seen.keys())


def fetch_runs_for_workflow(
    repo: str,
    branch: str,
    workflow: str,
    limit: int,
) -> list[dict]:
    p = _run_gh(
        [
            "run",
            "list",
            "--repo",
            repo,
            "--branch",
            branch,
            "-w",
            workflow,
            "--limit",
            str(limit),
            "--json",
            "databaseId,workflowName,status,conclusion,createdAt,url",
        ]
    )
    if p.returncode != 0:
        return []
    if not (p.stdout or "").strip():
        return []
    return json.loads(p.stdout)


def fetch_log_excerpt(run_id: int, repo: str, max_full_log_lines: int = 120) -> str:
    p = _run_gh(["run", "view", str(run_id), "--repo", repo, "--log-failed"])
    text = (p.stdout or "") + (p.stderr or "")
    if text.strip():
        return text
    p2 = _run_gh(["run", "view", str(run_id), "--repo", repo, "--log"])
    full = (p2.stdout or "") + (p2.stderr or "")
    lines = full.splitlines()
    if len(lines) <= max_full_log_lines:
        return full
    return "\n".join(lines[-max_full_log_lines:])


def extract_signals(log: str, max_lines: int = 60) -> list[str]:
    out: list[str] = []
    for line in log.splitlines():
        if SIGNAL_LINE.search(line):
            s = line.strip()
            if len(s) > 400:
                s = s[:400] + "…"
            out.append(s)
    return out[:max_lines]


def workflow_shard(name: str, shard: int, shards: int) -> bool:
    if shards <= 1:
        return True
    h = int(hashlib.md5(name.encode("utf-8"), usedforsecurity=False).hexdigest(), 16)
    return (h % shards) == shard


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--hours", type=int, default=24, help="Discover workflows touched in this window")
    ap.add_argument("--list-limit", type=int, default=250)
    ap.add_argument("--max-workflows", type=int, default=45, help="Cap workflows scanned (discovery order)")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--workflow", action="append", default=[], help="Only these workflows (repeatable)")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("docs/GHA_DEEP_SCAN_LATEST_PRIOR.md"),
    )
    args = ap.parse_args()

    if args.workflow:
        workflows = args.workflow
    else:
        workflows = discover_workflows(
            args.repo, args.branch, args.hours, args.list_limit
        )
        workflows = [w for w in workflows if workflow_shard(w, args.shard, args.shards)]
        workflows = workflows[: args.max_workflows]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows: list[str] = []
    detail_blocks: list[str] = []

    def esc_cell(s: str) -> str:
        return (s or "").replace("|", "\\|")

    for wf in workflows:
        runs = fetch_runs_for_workflow(args.repo, args.branch, wf, 2)
        if not runs:
            rows.append(f"| {esc_cell(wf)} | *(no runs)* | — | — |")
            continue

        latest = runs[0]
        prior = runs[1] if len(runs) > 1 else None
        want: list[tuple[str, dict]] = [("latest", latest)]
        lc = (latest.get("conclusion") or "").lower()
        st_latest = (latest.get("status") or "").lower()
        if (
            st_latest == "completed"
            and lc not in ("success", "skipped")
            and prior is not None
        ):
            want.append(("prior", prior))

        sig_latest = "—"
        pr_note = "—"
        if len(want) > 1 and prior:
            pc = prior.get("conclusion") or "-"
            pu = prior.get("url") or ""
            pr_note = f"[{pc}]({pu})"

        for label, run in want:
            rid = run["databaseId"]
            log = fetch_log_excerpt(int(rid), args.repo)
            sigs = extract_signals(log)
            url = run.get("url") or ""
            conc = run.get("conclusion") or "-"
            st = run.get("status") or "-"
            detail_blocks.append(
                f"### {esc_cell(wf)} — **{label}** ({conc} / {st}) [run {rid}]({url})\n\n"
                + (
                    "Signal lines:\n\n```text\n" + "\n".join(sigs) + "\n```\n"
                    if sigs
                    else "*No signal regex hits; last 25 log lines:*\n\n```text\n"
                    + "\n".join(log.splitlines()[-25:])
                    + "\n```\n"
                )
            )
            if label == "latest":
                sig_latest = f"{len(sigs)} hit(s)" if sigs else "0 hits"

        lurl = latest.get("url", "")
        lconc = latest.get("conclusion") or "-"
        lst = latest.get("status") or "-"
        rows.append(
            f"| {esc_cell(wf)} | [{lconc} / {lst}]({lurl}) | {pr_note} | {sig_latest} |"
        )

    out_lines: list[str] = [
        "# GitHub Actions deep scan (latest + prior on failure)",
        "",
        f"Generated: **{now}**",
        "",
        "## Method",
        "",
        "- **Repo:** `" + args.repo + "`",
        f"- **Branch:** `{args.branch}`",
        f"- **Discovery:** workflows seen in the last **{args.hours}h** among the **{args.list_limit}** newest runs"
        + (" (or `--workflow` filter)." if args.workflow else "."),
        "- **Runs per workflow:** **latest** always; **if latest is `completed` and not `success`/`skipped`,** also the **previous** run.",
        "- **Logs:** `gh run view --log-failed` first; if empty, tail of full `--log`.",
    ]
    if args.shards > 1:
        out_lines.append(f"- **Shard:** {args.shard + 1}/{args.shards}")
    out_lines.extend(
        [
            "",
            "## Summary table",
            "",
            "| Workflow | Latest | Prior (if scanned) | Signal hits (latest) |",
            "|----------|--------|--------------------|----------------------|",
        ]
        + rows
        + ["", "## Detailed excerpts", ""]
        + detail_blocks
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Wrote {args.out} ({len(workflows)} workflows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
