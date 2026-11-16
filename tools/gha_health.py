#!/usr/bin/env python3
"""GitHub Actions health detectors — measures the six failure modes that matter.

Why this exists
---------------
A flat "list the failures" report is useless on a repo with ~1,000 runs/day: 190 of
those failures are flapping workflows that recover minutes later. This tool answers
the questions that actually cost money or data freshness:

  1. BROKEN           last completed run failed and nothing has succeeded since
  2. NEVER_PASSED     no success anywhere in the sampled history
  3. SKIP_DOMINATED   jobs that are skipped in (almost) every run  [job-level]
  4. CANCEL_CHURN     concurrency group eats its own runs (cancelled/total > threshold)
  5. QUEUE_WAIT       runs waiting a long time between queued and started
  6. LONG_RUN         workflows whose own p90 runtime makes the schedule a lie
  7. STALE            active workflow with no runs at all in history

Auth: GHA_TOKEN env var, else `gh auth token`, else `git credential fill`.
Unauthenticated access is 60 req/hr and will not finish this sweep.

Usage:
    python tools/gha_health.py --repo OWNER/NAME --per-workflow 30 --out report.json --md report.md
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

API = "https://api.github.com"

# Buckets are inclusive of these conclusions only; `skipped` is NOT a failure.
FAIL = {"failure", "timed_out", "startup_failure"}


def get_token() -> str:
    tok = os.environ.get("GHA_TOKEN", "").strip()
    if tok:
        return tok
    try:
        tok = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=15).stdout.strip()
        if tok:
            return tok
    except Exception:
        pass
    try:
        p = subprocess.run(
            "printf 'protocol=https\\nhost=github.com\\n\\n' | git credential fill",
            shell=True, capture_output=True, text=True, timeout=15,
        ).stdout
        for line in p.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


class Client:
    def __init__(self, repo: str, token: str):
        self.repo = repo
        self.token = token
        self.calls = 0
        self.errors = 0  # non-404 failures: these make the report UNTRUSTWORTHY

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json", "User-Agent": "gha-health"}
        if self.token:
            h["Authorization"] = "token " + self.token
        return h

    def get(self, path: str) -> dict:
        self.calls += 1
        req = urllib.request.Request(API + path, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            if e.code != 404:  # 404 from /runs legitimately means "this workflow has no runs"
                self.errors += 1
            if e.code in (403, 429):
                return {"_err": "RATE_LIMITED", "_detail": body}
            return {"_err": e.code, "_detail": body}
        except Exception as e:  # network hiccup — surface, never silently green
            return {"_err": "NETWORK", "_detail": str(e)[:200]}

    def rate_limit(self) -> dict:
        d = self.get("/rate_limit")
        return d.get("resources", {}).get("core", {})


def parse_ts(s: str | None):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def minutes(a, b) -> float | None:
    if not a or not b:
        return None
    return (b - a).total_seconds() / 60.0


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    idx = max(0, min(len(v) - 1, int(len(v) * q) - 1))
    return v[idx]


def list_workflows(c: Client) -> list[dict]:
    out, page = [], 1
    while True:
        d = c.get(f"/repos/{c.repo}/actions/workflows?per_page=100&page={page}")
        if "_err" in d:
            print(f"  ! workflows page {page}: {d['_err']} {d.get('_detail','')[:120]}", file=sys.stderr)
            break
        batch = d.get("workflows", [])
        out += batch
        if len(batch) < 100:
            break
        page += 1
    return out


def analyse(c: Client, per_workflow: int, sample_runs_for_jobs: int) -> dict:
    wfs = list_workflows(c)
    print(f"  workflows: {len(wfs)}", file=sys.stderr)

    buckets = {k: [] for k in ("broken", "never_passed", "cancel_churn", "queue_wait",
                               "long_run", "stale", "unknown")}
    job_skips: list[dict] = []
    now = datetime.now(timezone.utc)

    for i, w in enumerate(wfs):
        if i and i % 50 == 0:
            print(f"  scanned {i}/{len(wfs)} ({c.calls} calls)", file=sys.stderr)
        d = c.get(f"/repos/{c.repo}/actions/workflows/{w['id']}/runs?per_page={per_workflow}&status=completed")
        if "_err" in d:
            if d["_err"] == 404:
                runs = []            # GitHub 404s /runs for workflows with zero runs — real stale
            else:
                # rate limit / network / permissions: we do NOT know. Never call this stale.
                buckets["unknown"].append({"name": w["name"], "path": w["path"], "error": d["_err"]})
                continue
        else:
            runs = d.get("workflow_runs", [])

        if not runs:
            if w.get("state") == "active":
                buckets["stale"].append({"name": w["name"], "path": w["path"], "id": w["id"]})
            continue

        last = runs[0]
        succ = [r for r in runs if r["conclusion"] == "success"]

        if last["conclusion"] in FAIL:
            last_ts = parse_ts(last["created_at"])
            newer_ok = [r for r in succ[1:] if parse_ts(r["created_at"]) > last_ts]
            if not newer_ok:
                buckets["broken"].append({
                    "name": w["name"], "path": w["path"], "conclusion": last["conclusion"],
                    "last_failed": last["created_at"],
                    "attempt": last.get("run_attempt"),
                    "age_hours": round(minutes(last_ts, now) or 0, 1),
                })

        if not succ:
            buckets["never_passed"].append({
                "name": w["name"], "path": w["path"],
                "runs": len(runs), "last": runs[0]["created_at"],
            })

        cancelled = sum(1 for r in runs if r["conclusion"] == "cancelled")
        if len(runs) >= 4 and cancelled / len(runs) > 0.5:
            buckets["cancel_churn"].append({
                "name": w["name"], "path": w["path"],
                "cancelled": cancelled, "total": len(runs),
                "ratio": round(cancelled / len(runs), 2),
            })

        waits = [minutes(parse_ts(r["created_at"]), parse_ts(r.get("run_started_at"))) for r in runs]
        waits = [x for x in waits if x is not None]
        q90 = pct(waits, 0.9)
        if q90 is not None and q90 > 60:
            buckets["queue_wait"].append({
                "name": w["name"], "path": w["path"],
                "p90_wait_min": round(q90), "max_wait_min": round(max(waits)),
            })

        durs = [minutes(parse_ts(r.get("run_started_at")), parse_ts(r["updated_at"])) for r in runs]
        durs = [x for x in durs if x is not None]
        d90 = pct(durs, 0.9)
        if d90 is not None and d90 > 60:
            buckets["long_run"].append({
                "name": w["name"], "path": w["path"],
                "p90_min": round(d90), "max_min": round(max(durs)), "n": len(durs),
            })

        # job-level skip analysis only where it can matter: workflows that skip a lot
        if sample_runs_for_jobs and len(runs) >= 2:
            per_job = defaultdict(lambda: [0, 0])
            for r in runs[:sample_runs_for_jobs]:
                j = c.get(f"/repos/{c.repo}/actions/runs/{r['id']}/jobs?per_page=100")
                for job in j.get("jobs", []):
                    key = job["name"][:60]
                    per_job[key][1] += 1
                    if job.get("conclusion") == "skipped":
                        per_job[key][0] += 1
            for name, (sk, tot) in per_job.items():
                if tot >= 2 and sk == tot:
                    job_skips.append({
                        "workflow": w["name"], "path": w["path"],
                        "job": name, "skipped": sk, "sampled": tot,
                    })

    return {
        "generated_utc": now.isoformat(),
        "repo": c.repo,
        "api_calls": c.calls,
        "fetch_errors": c.errors,
        "workflow_count": len(wfs),
        "buckets": buckets,
        "always_skipped_jobs": sorted(job_skips, key=lambda x: -x["sampled"]),
    }


def render_md(rep: dict) -> str:
    b = rep["buckets"]
    L = [
        f"# GitHub Actions health — {rep['repo']}",
        "",
        f"- generated: `{rep['generated_utc']}`  ·  workflows scanned: **{rep['workflow_count']}**"
        f"  ·  API calls: {rep['api_calls']}  ·  fetch errors: **{rep['fetch_errors']}**",
        "",
        ("> **UNTRUSTWORTHY RUN** — {0} workflow histories could not be fetched (rate limit or auth). "
         "Those are listed as `unknown`, NOT as stale; re-run before acting.".format(rep["fetch_errors"])
         if rep["fetch_errors"] else "> All workflow histories fetched cleanly."),
        "",
        "| Detector | Count |",
        "|---|---|",
    ]
    for k in ("broken", "never_passed", "cancel_churn", "queue_wait", "long_run", "stale", "unknown"):
        L.append(f"| {k} | **{len(b[k])}** |")
    L.append(f"| always-skipped jobs | **{len(rep['always_skipped_jobs'])}** |")

    def table(key, cols, rows):
        if not rows:
            L.extend(["", f"## {key} — none", ""])
            return
        L.extend(["", f"## {key} — {len(rows)}", "", "| " + " | ".join(cols) + " |",
                  "|" + "---|" * len(cols)])
        for r in rows:
            L.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")

    table("BROKEN (failed, no later success)",
          ["name", "conclusion", "last_failed", "age_hours"], b["broken"])
    table("NEVER PASSED in sampled history", ["name", "runs", "last"], b["never_passed"])
    table("CANCEL CHURN (>50% cancelled)", ["name", "cancelled", "total", "ratio"], b["cancel_churn"])
    table("QUEUE WAIT p90 > 60 min", ["name", "p90_wait_min", "max_wait_min"], b["queue_wait"])
    table("LONG RUN p90 > 60 min", ["name", "p90_min", "max_min"], b["long_run"])
    table("STALE (active, no runs in history)", ["name", "path"], b["stale"])
    table("UNKNOWN (history unreadable — NOT stale)", ["name", "error"], b["unknown"])
    table("ALWAYS-SKIPPED JOBS", ["workflow", "job", "skipped", "sampled"], rep["always_skipped_jobs"])
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="OWNER/NAME")
    ap.add_argument("--per-workflow", type=int, default=30)
    ap.add_argument("--job-sample", type=int, default=2, help="runs to sample per job (0 = skip job analysis)")
    ap.add_argument("--out", default="gha_health.json")
    ap.add_argument("--md", default="gha_health.md")
    a = ap.parse_args()

    tok = get_token()
    if not tok:
        print("ERROR: no token. Set GHA_TOKEN — unauthenticated 60 req/hr cannot run this sweep.", file=sys.stderr)
        return 2

    c = Client(a.repo, tok)
    rl = c.rate_limit()
    if rl.get("remaining") is not None and rl["remaining"] < 200:
        print(f"WARNING: only {rl['remaining']} API calls left this hour (resets "
              f"{datetime.fromtimestamp(rl['reset'], timezone.utc).isoformat()}). "
              f"This sweep needs roughly 4x the workflow count.", file=sys.stderr)

    rep = analyse(c, a.per_workflow, a.job_sample)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    with open(a.md, "w", encoding="utf-8") as f:
        f.write(render_md(rep))

    print(f"wrote {a.out} and {a.md} ({c.calls} API calls, {c.errors} fetch errors)")
    if rep["fetch_errors"] > max(5, 0.05 * rep["workflow_count"]):
        print(f"ERROR: {c.errors} workflows could not be read — report is NOT trustworthy. "
              f"Check /rate_limit and re-run.", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
