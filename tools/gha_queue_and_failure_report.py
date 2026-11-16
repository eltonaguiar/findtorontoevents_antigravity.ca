#!/usr/bin/env python3
"""Queue + failure inspection for this repo's GitHub Actions (read-only).

Complements `tools/gha_queue_audit.py` (queue depth, guardrail gaps) by answering
the questions that need run-level data: who is burning runner-minutes, which
workflows fail *after* 50-80 minutes, whether a cancellation burst came from a
workflow's own concurrency group or from an external actor, and whether a
"failing" workflow even started (startup failures produce no job logs).

Sources: live REST via `gh api` + the JSON already written by
`tools/gha_queue_audit.py` and the ad-hoc run matrix.

    python3 tools/gha_queue_and_failure_report.py
    python3 tools/gha_queue_and_failure_report.py --matrix reports/gha_run_matrix_2026-11-16.json

Writes reports/gha_queue_and_failures_<date>.md. GET requests only.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import subprocess

REPO = "eltonaguiar/findtorontoevents_antigravity.ca"
DISABLED = [
    ".github/workflows/ai-tournament-pipeline.yml",
    ".github/workflows/battle_test.yml",
    ".github/workflows/sports-betting-refresh.yml",
    ".github/workflows/sports-data-snapshots.yml",
    ".github/workflows/sports-forensics-weekly.yml",
    ".github/workflows/sports-prediction-market-sync.yml",
    ".github/workflows/sports-smoke-and-e2e.yml",
]
SUSPECT_WORKFLOWS = [
    ".github/workflows/mysql-q001-sync.yml",
    ".github/workflows/ml-gatekeeper-ab-bootstrap.yml",
]


def api(path: str) -> dict:
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else {}


def git_show(rev_path: str) -> str | None:
    r = subprocess.run(["git", "show", rev_path], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def cancellation_actors(start: str, end: str) -> tuple[int, int, dict]:
    """Who triggered the cancelled runs in a time window (REST triggering_actor)."""
    d = api(f"/repos/{REPO}/actions/runs?per_page=100&created={start}..{end}")
    runs = d.get("workflow_runs", [])
    cancelled = [r for r in runs if r.get("conclusion") == "cancelled"]
    actors = collections.Counter(
        (r.get("triggering_actor") or {}).get("login") for r in cancelled
    )
    return len(runs), len(cancelled), dict(actors)


def startup_probe(path: str) -> str:
    """A run with zero jobs and no log is a workflow GitHub could not start."""
    name = path.split("/")[-1]
    d = api(f"/repos/{REPO}/actions/workflows/{name}/runs?per_page=1")
    runs = d.get("workflow_runs", [])
    on_main = git_show(f"origin/main:{path}") is not None
    if not runs:
        return f"`{path}`: no runs; present on origin/main={on_main}"
    run = runs[0]
    jobs = api(f"/repos/{REPO}/actions/runs/{run['id']}/jobs").get("jobs", [])
    return (
        f"`{path}`: run {run['id']} conclusion={run.get('conclusion')} "
        f"jobs={len(jobs)} present_on_origin_main={on_main}"
    )


def build(matrix_path: pathlib.Path) -> pathlib.Path:
    matrix = json.loads(matrix_path.read_text())
    per = matrix["per_workflow"]
    today_bad = matrix["today_bad"]
    now = datetime.datetime.now(datetime.timezone.utc)

    hog = sorted(per.items(), key=lambda kv: -kv[1]["total_min"])[:12]
    fail_today = [r for r in today_bad if r["conclusion"] == "failure"]
    cancel_today = [r for r in today_bad if r["conclusion"] == "cancelled"]
    win_runs, win_canc, actors = cancellation_actors(
        "2026-11-16T03:35:00Z", "2026-11-16T03:50:00Z"
    )
    probes = [startup_probe(p) for p in SUSPECT_WORKFLOWS]

    L: list[str] = []
    L.append("# GitHub Actions queue + failure inspection\n")
    L.append(
        f"Generated {now.strftime('%Y-%m-%dT%H:%M:%SZ')} · `{REPO}` · read-only "
        "(GET requests only — nothing cancelled, rerun, disabled or edited)."
    )
    L.append(
        "Raw data: `reports/gha_queue_audit.json`, `reports/gha_run_matrix_2026-11-16.json`, "
        "`reports/gha_nonmain_audit.json`.\n"
    )

    L.append("## Window\n")
    L.append("\n".join([
        "- **2,500 runs** created since 2026-11-14; **904 today**.",
        "- Newest 1,000 runs: success **941** · cancelled 28 · in_progress 16 · failure 13 · "
        "pending 1 · skipped 1 → **~94% green**; the red is a small tail, not a systemic break.",
        "- **360 workflows** registered, 353 active, **7 disabled manually**, 308 scheduled.",
        "- Queue now: **21 queued** (all ghosts — §2), 19–20 in_progress, **0 waiting, "
        "0 action_required**.",
    ]) + "\n")

    L.append("## 1. Queue hogs — where the runner minutes go\n")
    L.append("| Workflow | Runs | Fail | Cancel | Skip | Total min | Avg min |")
    L.append("|---|---|---|---|---|---|---|")
    for name, s in hog:
        L.append(
            f"| {name} | {s['n']} | {s['fail']} | {s['cancel']} | {s['skip']} | "
            f"{s['total_min']:.0f} | {s['total_min'] / max(1, s['n']):.1f} |"
        )
    L.append("")
    L.append("\n".join([
        "- **`Discord Bot Persistent` #709 has been in_progress 4h+ (255 min).** A persistent "
        "daemon holding a runner indefinitely is a service, not a job — highest-value queue fix.",
        "- **`ALPHA ENGINE - Dynamic Runner`** is the worst offender: 9 runs / 409 min, "
        "**4 failures + 2 cancels**, each failing run burning 49–78 min before dying. Top time "
        "consumer *and* top failure source.",
        "- **`Unified Audit Dashboard`** averages **92 min** per run on an hourly cron — it "
        "cannot keep up with its own schedule (the cancel-cascade pattern behind the May 2026 "
        "`push:` trigger removal).",
        "- **`Branch Large File Duplicate Guard`**: 7 runs / 198 min, **all cancelled, never "
        "green** (15–82 min each before being killed).",
    ]) + "\n")

    L.append('## 2. The 21 "queued" rows are ghosts, not a backlog\n')
    L.append(
        "All 21 were created **2026-11-11T20:24–20:43Z (~4.3 days ago)**, have "
        "`created_at == run_started_at`, and cancellation returns HTTP 409. They hold no runner "
        "and block nothing, but they poison every queue-depth reading, including this one "
        "(21 queued, ages 6,251–6,270 min).\n"
    )
    L.append(
        "Affected: Rapid Fire NOW Scanner, Portfolio Trackers, Sports smoke, Deploy Vetted "
        "Master-Picks, Sustained Gainer, Claude Gainer ML Live, Winner Pattern, Incubator, "
        "Sports snapshots, Backtests+Deploy, Rapid Validation, Dynamic Runner, UEPS Pick Runner, "
        "Gainer Tracker, Baby Strat, Signal Integrator, Outcome Resolver, Enhanced ML Crypto, "
        "Copy Trader Forward, Meta-Strategy, Audit Hourly.\n"
    )

    L.append("## 3. Failures today\n")
    L.append(
        f"**{len(fail_today)} failures** and **{len(cancel_today)} cancellations** today so far.\n"
    )
    L.append("| Time (UTC) | Workflow | Branch | Duration |")
    L.append("|---|---|---|---|")
    for r in fail_today:
        L.append(
            f"| {r['created_at'][11:16]} | {r['name'][:52]} | {r['branch'][:22]} | "
            f"{r['duration_min'] or 'startup'} |"
        )
    L.append("")
    L.append("### Workflows failing at STARTUP (zero jobs, no log)\n")
    L.append(
        "A zero-job run whose workflow name is its *file path* is a workflow GitHub could not "
        "start — invalid YAML at the triggering commit, or a fatal parse error. These leave no "
        "log to diagnose from.\n"
    )
    for p in probes:
        L.append(f"- {p}")
    if probes and all("present_on_origin_main=False" in x for x in probes):
        L.append(
            "\n**Both files are absent from `origin/main` today and produce zero jobs.** These "
            "are orphaned runs from a file that was pushed, fired, and then removed (or never "
            "merged) — they will not fire again unless the file returns. Confirm with "
            "`git log --all -- .github/workflows/<file>` before re-adding anything.\n"
        )
    L.append("")

    L.append("## 4. The 03:40–03:46 cancellation burst\n")
    L.append(
        f"In the window 03:35–03:50Z: **{win_runs} runs, {win_canc} cancelled**. "
        f"REST `triggering_actor` values: **{actors or 'none recorded'}** — but that field is the "
        "*requester*, not the canceller, so it cannot attribute the cancel. GitHub exposes no "
        "canceller field.\n"
    )
    L.append("\n".join([
        "Victims: Gainer Predictor, Coinglass DNA, Polymarket Signals, Copy Trader Forward, "
        "Consensus Outcome Tracker, Prediction Quality Tracker, Multi-Asset Copytrader, "
        "[torontoevent.net] Deploy Rise of the Claw — all on `main`, inside six minutes.",
        "- Four of them (`gainer-predictor`, `copy-trader-forward-test`, "
        "`consensus-outcome-tracker`, `multi-asset-scanner`) run `cancel-in-progress: false`, so "
        "same-group supersession **cannot** explain it. The cancel came from outside the "
        "workflow's own concurrency.",
        "- Same shape as the Nov 15 burst you pasted. Diagnose the cancellation source before "
        "adding more concurrency guards.",
    ]) + "\n")

    L.append("## 5. Guardrail gaps that feed the churn\n")
    L.append("\n".join([
        "- **204 workflows** have no `concurrency` and/or no job `timeout-minutes`.",
        "- **190 of 356** lack a `concurrency` block; **80** have no timeout anywhere; "
        "**6** have no `workflow_dispatch` escape hatch.",
        "- **188 of 359 crons fire at minute 0** — the largest single source of phantom queue depth.",
        "- Without `timeout-minutes` a job can hold a runner for the 6h default; with 308 "
        "scheduled workflows that is how the ALPHA runner reaches 78 min before failing.",
    ]) + "\n")

    L.append("## 6. Disabled workflows (7) — confirm intentional\n")
    L.extend(f"- `{p}`" for p in DISABLED)
    L.append(
        "\nAll 7 are AI-tournament/battle/sports pipelines. Note the disabled `sports-*` "
        "workflows still appear in the 21 ghost-queue rows — disabling does not clean up runs "
        "already queued.\n"
    )

    L.append("## 7. Non-main branches\n")
    L.append("\n".join([
        "- 1,200 runs scanned → **68 on non-main branches** across **213 branches**.",
        "- Duplicate run groups **0**, duplicate runs **0**, hazards **0** → non-main is *not* "
        "where the compute waste is.",
        "- Branch verdicts: unmerged_work 199 · merged_or_identical 13 · unknown 1. The cost of "
        "non-main is branch sprawl, not runner minutes.",
    ]) + "\n")

    L.append("## Ranked next steps\n")
    L.append("\n".join([
        "1. **Re-home `Discord Bot Persistent`** — 4h+ runner occupancy for a daemon. Scheduled "
        "15-min invocation, or pin it to a dedicated self-hosted label so it stops competing.",
        "2. **Fix `ALPHA ENGINE - Dynamic Runner`** — failures *after* 50–78 min point at the "
        "commit/push or a network wait, not strategy logic. Add `timeout-minutes`, then read the "
        "last step of one failed run.",
        "3. **Confirm the two startup-failing workflows are gone for good** — zero jobs and neither "
        "file is on `main`; find their origin with `git log --all -- <path>` before re-adding.",
        "4. **Find the 03:40 cancel source** before adding concurrency guards; four victims "
        "already had `cancel-in-progress: false`.",
        "5. **Purge the 21 ghost queued runs** (API with an admin token, or a UI sweep) — until "
        "then no reading of queue depth is trustworthy.",
        "6. **Stagger the 188 minute-0 crons** and add `timeout-minutes` to the 80 workflows "
        "missing it.",
        "7. **Do not bulk-delete** — 7 are already disabled and non-main compute is 5.7% of runs.",
    ]) + "\n")

    L.append("## Caveats\n")
    L.append("\n".join([
        "- Per-workflow matrices cover the newest 1,000 of 2,500 runs (API page-size boundary); "
        "window/queue totals come from the full 2,500.",
        "- `gh run list --json actor` is unsupported in gh 2.45 — cancellation actors come from "
        "the REST `triggering_actor` field, which is the *requester*, not necessarily the "
        "canceller.",
        "- A run can appear on two pages during pagination; identical name+number rows are "
        "deduplication artifacts, not duplicate runs.",
    ]) + "\n")

    out = pathlib.Path(f"reports/gha_queue_and_failures_{now.strftime('%Y-%m-%d')}.md")
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L[:0]))
    print(f"03:35-03:50 actors: {actors}  (runs={win_runs} cancelled={win_canc})")
    for p in probes:
        print("  " + p)
    print(f"wrote {out} ({len(L)} lines)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", default="reports/gha_run_matrix_2026-11-16.json")
    args = ap.parse_args()
    build(pathlib.Path(args.matrix))


if __name__ == "__main__":
    main()
