#!/usr/bin/env python3
"""Check the health of critical GitHub Actions workflows (reuses the repo's
established checker library, gha_summary_lib).

This is a lightweight gate that reuses the existing `tools/gha_summary_lib.py`
GitHub Actions client (via the `gh` CLI) rather than hand-rolling a second
API client. It watches a curated set of critical pipelines, reports their most
recent conclusions in a lookback window, and writes a markdown job summary so
the result is visible in the Actions UI.

Designed to be invoked by .github/workflows/gha-actions-health.yml. The job is
non-blocking by default: it reports health rather than failing CI on transient
upstream flakiness. Set FAIL_IF_UNHEALTHY=1 to fail instead.

Environment:
  GH_TOKEN                  GitHub token with `actions: read` scope.
  GITHUB_REPOSITORY         e.g. "eltonaguiar/findtorontoevents_antigravity.ca".
  GITHUB_STEP_SUMMARY       path to the GitHub step summary file (optional).
  GITHUB_REF_NAME           branch to watch (default "main").
  LOOKBACK_HOURS            lookback window (default 48).
  CRITICAL_WORKFLOWS        JSON list of workflow file names (default = built-in).
  FAIL_IF_UNHEALTHY         set to "1" to exit non-zero on unhealthy workflows.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gha_summary_lib import (  # noqa: E402 - path bootstrap first
    BAD_CONCLUSIONS,
    fetch_bulk_runs,
    list_all_workflows,
    parse_iso,
)

# Default critical workflows. These are the pipelines our audit/measurement
# story depends on: the walk-forward gate, the audit dashboard, DB freshness,
# cross-DB consistency, and the nightly pick funnel.
DEFAULT_CRITICAL_WORKFLOWS = [
    "walkforward-gate.yml",
    "audit-dashboard.yml",
    "audit-hourly-update.yml",
    "db-freshness-check.yml",
    "cross-db-consistency.yml",
    "db-freshness-guardian.yml",
    "pick-funnel-nightly.yml",
    "deploy-alpha-dashboard.yml",
    "deploy_bundle.yml",
]


def _log(msg: str) -> None:
    print(msg, flush=True)


def _within(run: dict, since: datetime) -> bool:
    created = parse_iso(run.get("created_at") or run.get("createdAt"))
    if created is None:
        return True  # unknown -> keep, let downstream classify
    return created >= since


def main() -> int:
    token = os.environ.get("GH_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    try:
        lookback_h = int(os.environ.get("LOOKBACK_HOURS", "48"))
    except ValueError:
        lookback_h = 48
    fail_if_unhealthy = os.environ.get("FAIL_IF_UNHEALTHY", "0") == "1"

    if not token or not repo:
        _log("ERROR: GH_TOKEN and GITHUB_REPOSITORY are required.")
        return 2

    raw_critical = os.environ.get("CRITICAL_WORKFLOWS")
    if raw_critical:
        try:
            critical = json.loads(raw_critical)
        except json.JSONDecodeError:
            _log("ERROR: CRITICAL_WORKFLOWS is not valid JSON.")
            return 2
    else:
        critical = DEFAULT_CRITICAL_WORKFLOWS

    since = datetime.now(timezone.utc) - timedelta(hours=lookback_h)
    _log(f"Watching branch '{branch}' health since {since.isoformat()} (lookback {lookback_h}h)")
    _log(f"Critical workflows tracked: {len(critical)}")

    # 1) Reuse existing checker lib to enumerate workflows + bulk runs.
    workflows = list_all_workflows(repo)
    wf_by_file = {}
    for w in workflows:
        wf_by_file[(w.get("path") or "").lower()] = w
    _log(f"Discovered {len(workflows)} workflows via gha_summary_lib.")

    runs = fetch_bulk_runs(repo, branch, limit=400)
    recent = [r for r in runs if _within(r, since)]
    _log(f"Fetched {len(runs)} runs; {len(recent)} within window.")

    # 2) Build per-critical-workflow health.
    rows = []  # (file, workflow_name, runs, bad, bad_samples)
    for wf in critical:
        wf_l = wf.lower()
        matched_wf = wf_by_file.get(wf_l)
        if matched_wf is None:
            # fallback: match by name-suffix
            for path_l, w in wf_by_file.items():
                if path_l.endswith(wf_l):
                    matched_wf = w
                    break
        if matched_wf is None:
            rows.append((wf, "?", 0, 0, ["workflow not found in repo"]))
            continue

        wname = matched_wf.get("name") or matched_wf.get("id") or wf
        wid = matched_wf.get("id")
        wf_runs = [
            r
            for r in recent
            if r.get("workflow_id") == wid or (r.get("workflow_name") or "") == wname
        ]
        bad = []
        for r in wf_runs:
            conclusion = r.get("conclusion")
            if conclusion in BAD_CONCLUSIONS or r.get("status") in BAD_CONCLUSIONS:
                bad.append((conclusion, r.get("id"), r.get("html_url")))
        rows.append((wf, wname, len(wf_runs), len(bad), bad[:5]))

    # 3) Build summary.
    lines = ["## GitHub Actions health", ""]
    lines.append(f"- Branch: **{branch}** | lookback: **{lookback_h}h** (since {since.strftime('%Y-%m-%d %H:%M')} UTC)")
    lines.append(f"- Runs inspected: **{len(recent)}** (of {len(runs)} fetched)")
    lines.append(f"- Critical workflows tracked: **{len(critical)}**")
    lines.append("")

    unhealthy = [r for r in rows if r[3] > 0]
    missing = [r for r in rows if r[1] == "?"]
    if unhealthy or missing:
        lines.append("### ❌ Unhealthy / missing workflows")
        lines.append("")
        for wf, wname, n, bad, samples in rows:
            if bad == 0 and wname != "?":
                continue
            if wname == "?":
                lines.append(f"- **{wf}** — workflow not found in repo")
            else:
                lines.append(f"- **{wf}** ({wname}): {bad}/${n} run(s) bad in window")
                for concl, rid, url in samples:
                    lines.append(f"  - `{concl}` run #{rid}")
        lines.append("")
    else:
        lines.append("### ✅ All critical workflows healthy (no failures in window)")
        lines.append("")

    for wf, wname, n, bad, _samples in rows:
        status = "❌" if bad else "✅"
        show = wname if wname != "?" else "(missing)"
        lines.append(f"- {status} **{wf}** ({show}): {n} run(s), {bad} bad")
    lines.append("")

    report = "\n".join(lines)
    if summary_path:
        try:
            with open(summary_path, "w", encoding="utf-8") as fh:
                fh.write(report)
        except Exception as exc:  # noqa: BLE001
            _log(f"  [warn] could not write step summary: {exc}")
    _log(report)

    if (unhealthy or missing) and fail_if_unhealthy:
        _log("FAIL_IF_UNHEALTHY=1 and unhealthy/missing workflows found -> exiting 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
