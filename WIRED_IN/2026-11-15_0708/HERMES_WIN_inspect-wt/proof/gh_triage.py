"""GH Actions triage — bucket by sequence context, not by failure list.

Implements the 4-bucket methodology:
  1 BROKEN      latest completed run failed AND no success after it
  2 RECOVERED   failure followed by a later success (informational; flappers called out)
  3 QUEUE HOGS  zombie queued, runner hogs (long in_progress), cancel churn
  4 STALE/PRUNE no run beyond expected cadence, never-run, disabled

Trigger facts come from LOCAL .github/workflows/*.yml (free, and it is the only
way to know a workflow is workflow_dispatch-only — the anti-pattern that makes
naive audits flag quiet-by-design jobs as stale).

Usage:
    python proof/gh_triage.py --repo-root . [--pages 12] [--json]
API budget: pages + 2 calls.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone

import yaml

API = "https://api.github.com"
FAIL = {"failure", "timed_out"}
DONE = {"success", "failure", "timed_out", "action_required", "startup_failure",
        "cancelled", "skipped", "neutral", "stale"}


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "hermes-triage"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def age_h(ts: str | None, now: datetime) -> float | None:
    if not ts:
        return None
    return (now - datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() / 3600


def cron_cadence_hours(cron: str) -> float | None:
    """Rough expected interval in hours from a cron expression."""
    try:
        parts = cron.split()
        minute, hour, dom, month, dow = parts[:5]
        if hour.startswith("*/"):
            return float(hour[2:])
        if hour.isdigit():
            hours = [int(x) for x in hour.split(",")]
            if len(hours) > 1:
                diffs = [b - a for a, b in zip(hours, hours[1:]) if b > a]
                return float(min(diffs)) if diffs else 24.0
            return 24.0
        if "," in hour:
            hours = [int(x) for x in hour.split(",")]
            diffs = [b - a for a, b in zip(sorted(hours), sorted(hours)[1:]) if b > a]
            return float(min(diffs)) if diffs else 24.0
        if dow != "*":
            return 24.0 * 7
        if dom != "*":
            return 24.0 * 30
        return 24.0
    except Exception:
        return None


def load_local_workflows(root: str) -> dict[str, dict]:
    out = {}
    for f in glob.glob(os.path.join(root, ".github", "workflows", "*.yml")):
        try:
            d = yaml.safe_load(open(f, encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        on = d.get(True) or d.get("on") or {}
        if isinstance(on, str):
            keys = {on}
        elif isinstance(on, dict):
            keys = set(on.keys())
        else:
            keys = set()
        cron = None
        if isinstance(on, dict) and isinstance(on.get("schedule"), list) and on["schedule"]:
            cron = (on["schedule"][0] or {}).get("cron")
        conc = d.get("concurrency")
        out[str(d.get("name") or os.path.basename(f))] = {
            "file": os.path.basename(f),
            "triggers": sorted(keys),
            "manual_only": keys == {"workflow_dispatch"},
            "cron": cron,
            "expected_hours": cron_cadence_hours(cron) if cron else None,
            "cancel_in_progress": bool(isinstance(conc, dict) and conc.get("cancel-in-progress")),
        }
    return out


def collect_runs(repo: str, pages: int) -> list[dict]:
    runs = []
    for p in range(1, pages + 1):
        try:
            d = fetch(f"{API}/repos/{repo}/actions/runs?per_page=100&page={p}")
        except Exception as e:
            print(f"WARN page {p}: {e}", file=sys.stderr)
            break
        b = d.get("workflow_runs", [])
        if not b:
            break
        runs.extend(b)
    return runs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="eltonaguiar/findtorontoevents_antigravity.ca")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--pages", type=int, default=12)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    now = datetime.now(timezone.utc)
    local = load_local_workflows(a.repo_root)
    runs = collect_runs(a.repo, a.pages)

    by_wf: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        by_wf[r.get("name") or "?"].append(r)
    for v in by_wf.values():
        v.sort(key=lambda r: r["created_at"], reverse=True)

    # queue state (separate queries; queued runs can be ancient and fall outside the window)
    partial = []
    try:
        queued = fetch(f"{API}/repos/{a.repo}/actions/runs?status=queued&per_page=100&branch=main").get("workflow_runs", [])
    except Exception as e:
        queued = []; partial.append(f"queued unavailable ({e.__class__.__name__})")
    try:
        inprog = fetch(f"{API}/repos/{a.repo}/actions/runs?status=in_progress&per_page=100&branch=main").get("workflow_runs", [])
    except Exception as e:
        inprog = []; partial.append(f"in_progress unavailable ({e.__class__.__name__})")

    broken, recovered, flappers, stale, never_run, retrying = [], [], [], [], [], []
    cancel_churn = []

    for name, rs in by_wf.items():
        meta = local.get(name, {})
        completed = [r for r in rs if r.get("conclusion") in DONE]
        if not completed:
            continue
        last = completed[0]
        succ = [r for r in completed if r["conclusion"] == "success"]
        last_succ_at = succ[0]["created_at"] if succ else None
        fails = [r for r in completed if r["conclusion"] in FAIL]
        recent15 = [r for r in completed if r["conclusion"] != "cancelled"][:15]
        fails15 = sum(1 for r in recent15 if r["conclusion"] in FAIL)
        cancelled = sum(1 for r in completed if r["conclusion"] == "cancelled")
        cadence = meta.get("expected_hours")

        row = {"workflow": name, "last": last["conclusion"],
               "last_at": last["created_at"], "age_h": round(age_h(last["created_at"], now) or 0, 1),
               "last_success_at": last_succ_at, "fails15": fails15,
               "cadence_h": cadence, "url": last.get("html_url"),
               "cancel_ratio": round(cancelled / len(completed), 2) if completed else 0}

        if last["conclusion"] in FAIL:
            # an in-flight run newer than the last completed failure means the
            # workflow is retrying right now — not broken. GitHub's own retry
            # (run_attempt > 1) shows up exactly this way.
            inflight = [r for r in rs
                        if r.get("status") in ("in_progress", "queued", "waiting", "requested")
                        and r["created_at"] > last["created_at"]]
            if inflight:
                row["note"] = ("in-flight retry (attempt %s)" % inflight[0].get("run_attempt", "?"))
                retrying.append(row)
                continue
            if not last_succ_at or last_succ_at < last["created_at"]:
                # severity by how many cycles were missed
                cyc = (row["age_h"] / cadence) if cadence else None
                row["missed_cycles"] = round(cyc, 1) if cyc else None
                row["severity"] = "P1" if (cyc and cyc >= 3) else "P2"
                if not succ:
                    row["severity"] = "P0-never-passed"
                broken.append(row)
        else:
            recovered.append(row)
            if fails15 >= 5:
                flappers.append(row)
        if row["cancel_ratio"] > 0.5 and len(completed) >= 10:
            cancel_churn.append(row)

    # stale / never-run, using triggers
    for name, meta in local.items():
        rs = by_wf.get(name, [])
        if meta["manual_only"]:
            continue
        if not rs:
            (never_run if meta["triggers"] else stale).append(
                {"workflow": name, "file": meta["file"], "triggers": meta["triggers"],
                 "cron": meta["cron"], "verdict": "never-run-in-window"})
            continue
        last = rs[0]
        hrs = age_h(last["created_at"], now) or 0
        exp = meta.get("expected_hours")
        if exp and hrs > max(exp * 3, 48):
            stale.append({"workflow": name, "file": meta["file"], "cron": meta["cron"],
                          "last_run": last["created_at"], "age_h": round(hrs, 1),
                          "expected_h": exp, "verdict": "stale-trigger-dead"})

    # queue hogs
    zombies = [r for r in queued if (age_h(r["created_at"], now) or 0) > 24]
    hogs = [r for r in inprog if (age_h(r.get("run_started_at") or r["created_at"], now) or 0) > 1]

    # volume
    span = 0
    if runs:
        span = (datetime.fromisoformat(runs[0]["created_at"].replace("Z", "+00:00")) -
                datetime.fromisoformat(runs[-1]["created_at"].replace("Z", "+00:00"))).days or 1
    vol = Counter({n: len(v) for n, v in by_wf.items()})
    top_vol = [{"workflow": n, "runs": c, "per_day": round(c / span, 1)} for n, c in vol.most_common(8)]

    for b in broken:
        b["fixable"] = b["workflow"] in local

    if not runs:
        print("RATE_LIMITED: no runs could be fetched — this is NOT a green result.")
        return 2

    report = {
        "partial": partial,
        "window_runs": len(runs), "window_days": span, "workflows_with_runs": len(by_wf),
        "local_workflows": len(local),
        "broken": sorted(broken, key=lambda r: (r["severity"] != "P0-never-passed", -(r.get("missed_cycles") or 0))),
        "retrying": retrying,
        "recovered_count": len(recovered), "flappers": sorted(flappers, key=lambda r: -r["fails15"])[:10],
        "zombie_count": len(zombies), "zombie_oldest": min((r["created_at"] for r in zombies), default=None),
        "runner_hogs": [{"workflow": r["name"], "run": r["id"], "age_h": round(age_h(r.get("run_started_at") or r["created_at"], now) or 0, 1)} for r in hogs][:10],
        "cancel_churn": sorted(cancel_churn, key=lambda r: -r["cancel_ratio"])[:10],
        "stale": stale[:20], "never_run": never_run[:20],
        "top_volume": top_vol,
    }

    if a.json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    print("=" * 78)
    print(f"GH ACTIONS TRIAGE — {len(runs)} runs over {span}d, {len(by_wf)} workflows with activity")
    print("=" * 78)

    print(f"\n1. BROKEN NOW — {len(report['broken'])}")
    for r in report["broken"][:12]:
        cyc = f" missed~{r['missed_cycles']} cycles" if r.get("missed_cycles") else ""
        print(f"  [{r['severity']:16}] {r['workflow'][:44]:44} last={r['last']} {r['age_h']}h{cyc}")
        if r["severity"] == "P0-never-passed":
            print(f"       never passed in window -> broken-from-birth; fix or delete")
        print(f"       {r['url']}")

    print(f"\n2. FLAPPING — {len(report['flappers'])} (of {report['recovered_count']} recovered, suppressed as noise)")
    for r in report["flappers"]:
        print(f"  {r['workflow'][:46]:46} fails15={r['fails15']:2}  last_fail_age={r['age_h']}h")

    print(f"\n3. QUEUE HOGS")
    print(f"  zombie queued >24h: {report['zombie_count']}  oldest={report['zombie_oldest']}")
    for r in report["runner_hogs"]:
        print(f"  in_progress >1h: {r['workflow'][:44]:44} {r['age_h']}h  run={r['run']}")
    print(f"  cancel-churn (>50% cancelled):")
    for r in report["cancel_churn"]:
        print(f"    {r['workflow'][:48]:48} {r['cancel_ratio']:.0%} cancelled")

    print(f"\n4. STALE / PRUNE — stale={len(report['stale'])} never-run={len(report['never_run'])}")
    for r in report["stale"][:8]:
        print(f"  STALE {r['workflow'][:44]:44} last={str(r.get('last_run'))[:16]} age={r.get('age_h')}h exp={r.get('expected_h')}h")
    for r in report["never_run"][:8]:
        print(f"  NEVER {r['workflow'][:44]:44} triggers={','.join(r['triggers'])}")

    if report.get("partial"):
        print("\nPARTIAL: " + "; ".join(report["partial"]))

    print(f"\n5. TOP VOLUME (runs/day)")
    for r in report["top_volume"]:
        print(f"  {r['workflow'][:52]:52} {r['runs']:4} runs  {r['per_day']}/day")

    print(f"\nNOT AN ISSUE: {report['recovered_count']} workflows failed and then recovered (suppressed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
