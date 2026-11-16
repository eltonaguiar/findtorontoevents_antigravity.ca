#!/usr/bin/env python3
"""
gha_health_audit.py — hardened GitHub Actions health guardian (rules R1-R12).

Specs:
  - R1-R12 rule set (authoritative): GHACTIONS_2026-11-16/2026-11-15_21-45_EST_ghactions/
    06_GHA_BEST_PRACTICES_APPROACH.md, section 2.
  - Queue/skip monitoring intent: reports/gha_phase3_recommendations.md.
  - Output format (5 sections incl. "NOT AN ISSUE (recovered)"): AGENT_PROMPT_job_analysis.md
    section 5.

Runs from inside GitHub Actions against the GitHub REST API using GITHUB_TOKEN.
Budget-conscious: list endpoints preferred over per-workflow calls, `created=>=<date>`
windows plus a local `run_performed_at >=` bound, hard pagination caps and a global
API-call budget (default 300). Any rule that trips the budget or the rate limit emits
"SKIPPED(rate)" instead of crashing the audit.

Dependency-free: stdlib only. PyYAML is OPTIONAL — when present, workflow `on:`
triggers are parsed with ``yaml.safe_load`` (never ``yaml.load``); otherwise a
minimal fallback scanner extracts name/events/cron/workflow_run lines.

Outputs (live mode):
  GHACTIONS_LIVE/gha_health.json         full machine report (incl. R2 watchlist)
  GHACTIONS_LIVE/gha_health_summary.md   5-section human summary

Files are rewritten only when the findings payload actually changed (volatile keys
like the timestamp are excluded from the comparison), so the job's `git diff`
guard never produces empty/identical commits.

Modes (all offline-safe except the default live mode):
  python3 tools/gha_health_audit.py --help
  python3 tools/gha_health_audit.py --dry-run    # fixture report, NO network, NO writes
  python3 tools/gha_health_audit.py              # live audit (needs GITHUB_TOKEN/GH_TOKEN)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # optional; used ONLY via safe_load
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback path
    yaml = None  # type: ignore


# ---------------------------------------------------------------------------
# Config blocks
# ---------------------------------------------------------------------------

API_BASE = "https://api.github.com"
DEFAULT_REPO = "eltonaguiar/findtorontoevents_antigravity.ca"

API_BUDGET_MAX = int(os.getenv("GHA_HEALTH_API_BUDGET", "300"))
RUNS_WINDOW_DAYS = int(os.getenv("GHA_HEALTH_WINDOW_DAYS", "8"))
MAX_RUN_PAGES = int(os.getenv("GHA_HEALTH_MAX_RUN_PAGES", "80"))       # 80 x 100 = 8000 runs
MAX_WORKFLOW_PAGES = 4                                                   # 367 workflows -> 4 pages
MAX_STATUS_PAGES = 3                                                     # queued / in_progress lists
MAX_JOB_PROBES = int(os.getenv("GHA_HEALTH_MAX_JOB_PROBES", "40"))       # run->jobs calls (R3/R4/R8)
MAX_R9_PROBES = int(os.getenv("GHA_HEALTH_MAX_R9_PROBES", "50"))         # per-workflow latest-run calls
MAX_WATCHLIST_PROBES = 8                                                 # R2 lookback probes

BAD_CONCLUSIONS = {"failure", "timed_out", "action_required", "startup_failure", "stale"}
FLAP_FAILS_MIN = 5
FLAP_WINDOW = 15
CHURN_CANCEL_MIN = 0.50
CHURN_WINDOW = 15
PHANTOM_QUEUE_HOURS = 24.0
RUNNER_HOG_HOURS = 2.0
MASS_CANCEL_MIN_RUNS = 5
MASS_CANCEL_MIN_WFS = 2
SKIP_RATIO_MIN = 0.80
SKIP_MIN_RUNS = 5

STALE_THRESHOLD_DAYS = {"hourly": 30, "daily": 30, "weekly": 60, "monthly": 90, "unknown": 60}

INFRA_STEP_HINTS = (
    "pip", "npm", "yarn", "pnpm", "install", "setup", "playwright", "docker",
    "apt", "checkout", "upload", "download", "cache",
)

# R5: designed 24/7 singleton(s) — REPORT, don't "fix" (06 S2 / measured audit).
KNOWN_DESIGNED_HOGS = {
    "discord bot - persistent": "designed 24/7 occupier (singleton, no concurrency group)",
}

# R8: known always-skipped jobs inside green runs (dead code / broken if: filter).
KNOWN_ALWAYS_SKIPPED_JOBS = [
    {"workflow": "dynamic-alpha-engine", "job": "wsl-direct",
     "note": "measured 2026-11-16 audit: job if: always false"},
]

# R12: no-consumer outputs — static list from known findings (2026-11-16 audit, measured x3).
R12_NO_CONSUMER_OUTPUTS = [
    {"artifact": "db_freshness.json", "producer": "tools/db_freshness_check.py",
     "note": "written/published with zero repo consumers (latent trap)"},
    {"artifact": "daily_top_picks_filter.json", "producer": "pick-funnel-nightly chain",
     "note": "written/published with zero repo consumers (latent trap)"},
    {"artifact": "alpha_engine/output/latest_picks.json", "producer": "alpha_engine scanners",
     "note": "written/published with zero repo consumers (latent trap)"},
]

VOLATILE_JSON_KEYS = ("generated_at", "api_calls_used", "window_start", "window_end")


class RateLimitedError(Exception):
    """API budget exhausted or GitHub rate limit hit."""


class ApiError(Exception):
    pass


# ---------------------------------------------------------------------------
# Small utils
# ---------------------------------------------------------------------------

def _iso_to_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _run_start(r: Dict[str, Any]) -> Optional[datetime]:
    return _iso_to_dt(r.get("run_started_at") or r.get("run_performed_at") or r.get("created_at"))


def _run_end(r: Dict[str, Any]) -> Optional[datetime]:
    return _iso_to_dt(r.get("run_ended_at") or r.get("updated_at") or r.get("run_performed_at"))


def _run_sort_key(r: Dict[str, Any]) -> str:
    return (r.get("run_ended_at") or r.get("updated_at") or r.get("run_performed_at")
            or r.get("created_at") or "")


def _age_hours(now: datetime, dt: Optional[datetime]) -> Optional[float]:
    if dt is None:
        return None
    return round((now - dt).total_seconds() / 3600.0, 2)


def _esc(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


# ---------------------------------------------------------------------------
# API client (live) — stdlib urllib, global call budget
# ---------------------------------------------------------------------------

class ApiClient:
    def __init__(self, token: str, repo: str, budget: int = API_BUDGET_MAX):
        self.token = token
        self.repo = repo
        self.budget = budget
        self.calls = 0

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.calls >= self.budget:
            raise RateLimitedError(f"api budget exhausted ({self.budget} calls)")
        self.calls += 1
        url = f"{API_BASE}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "gha-health-audit/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:400]
            except Exception:
                pass
            if exc.code in (403, 429) and "rate limit" in body.lower():
                raise RateLimitedError(f"rate limited on {path}") from exc
            raise ApiError(f"{exc.code} on {path}: {body}") from exc


# ---------------------------------------------------------------------------
# Trigger parsing from the checked-out tree (R9/R10/R11 need `on:`)
# ---------------------------------------------------------------------------

class TriggerInfo:
    def __init__(self, path: str):
        self.path = path
        self.name = Path(path).stem
        self.events: List[str] = []
        self.crons: List[str] = []
        self.push: Any = None
        self.workflow_run_upstreams: List[str] = []
        self.dispatch_only = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path, "name": self.name, "events": self.events,
            "crons": self.crons, "push": self.push,
            "workflow_run_upstreams": self.workflow_run_upstreams,
            "dispatch_only": self.dispatch_only,
        }


def _trigger_info_from_yaml(path: str, data: Any) -> TriggerInfo:
    info = TriggerInfo(path)
    if not isinstance(data, dict):
        return info
    if isinstance(data.get("name"), str):
        info.name = data["name"]
    on = data.get("on") if "on" in data else data.get(True)  # PyYAML parses bare `on:` as True
    if isinstance(on, str):
        info.events = [on]
    elif isinstance(on, list):
        info.events = [str(e) for e in on]
    elif isinstance(on, dict):
        for key, val in on.items():
            key = str(key)
            info.events.append(key)
            if key == "schedule" and isinstance(val, list):
                for entry in val:
                    if isinstance(entry, dict) and entry.get("cron"):
                        info.crons.append(str(entry["cron"]))
            elif key == "push":
                info.push = val
            elif key == "workflow_run" and isinstance(val, dict):
                ups = val.get("workflows") or []
                if isinstance(ups, list):
                    info.workflow_run_upstreams = [str(u) for u in ups]
    info.dispatch_only = info.events == ["workflow_dispatch"]
    return info


_FALLBACK_NAME = re.compile(r"^name:\s*[\"']?([^\"'#\n]+?)[\"']?\s*$", re.M)
_FALLBACK_CRON = re.compile(r"-\s*cron:\s*[\"']([^\"']+)[\"']")
_FALLBACK_EVENT = re.compile(r"^\s{2}([a-z_]+):", re.M)
_FALLBACK_WR = re.compile(r"^\s*-\s*[\"']?([A-Za-z0-9 _.\-/]+?)[\"']?\s*$", re.M)


def _trigger_info_fallback(path: str, text: str) -> TriggerInfo:
    """Minimal scanner used only when PyYAML is unavailable. Best-effort."""
    info = TriggerInfo(path)
    m = _FALLBACK_NAME.search(text)
    if m:
        info.name = m.group(1).strip()
    info.crons = _FALLBACK_CRON.findall(text)
    on_match = re.search(r"^on:\s*$([\s\S]*?)(^\S|\Z)", text, re.M)
    block = on_match.group(1) if on_match else ""
    info.events = sorted(set(_FALLBACK_EVENT.findall(block)))
    if re.search(r"^\s{2}push:\s*$", block, re.M):
        info.push = {}  # presence only
    wr_match = re.search(r"workflow_run:\s*\n\s*workflows:\s*\n([\s\S]*?)(^\s{2}\S|\Z)", block, re.M)
    if wr_match:
        info.workflow_run_upstreams = _FALLBACK_WR.findall(wr_match.group(1))
    info.dispatch_only = info.events == ["workflow_dispatch"]
    return info


def parse_workflow_triggers(repo_root: Path) -> Dict[str, TriggerInfo]:
    out: Dict[str, TriggerInfo] = {}
    wf_dir = repo_root / ".github" / "workflows"
    if not wf_dir.is_dir():
        return out
    for f in sorted(wf_dir.glob("*.y*ml")):
        rel = f".github/workflows/{f.name}"
        text = f.read_text(encoding="utf-8", errors="replace")
        if yaml is not None:
            try:
                data = yaml.safe_load(text)  # NEVER yaml.load
                out[rel] = _trigger_info_from_yaml(rel, data)
                continue
            except Exception:
                pass  # fall through to scanner for malformed/partial files
        out[rel] = _trigger_info_fallback(rel, text)
    return out


def classify_cron(cron_expr: str) -> str:
    parts = cron_expr.split()
    if len(parts) != 5:
        return "unknown"
    _min, hour, dom, month, dow = parts
    if month != "*":
        return "monthly"
    if dom not in ("*",):
        if dom.startswith("*/"):
            try:
                n = int(dom[2:])
                return "weekly" if n >= 7 else "daily"
            except ValueError:
                return "unknown"
        return "monthly"
    if dow != "*":
        return "weekly"
    if hour == "*":
        return "hourly"
    return "daily"


def cadence_class(info: TriggerInfo) -> str:
    """R9 staleness class: schedule-aware, else event-driven -> daily-equivalent."""
    if info.dispatch_only:
        return "dispatch"
    if info.crons:
        return min((classify_cron(c) for c in info.crons),
                   key=lambda k: {"hourly": 0, "daily": 1, "weekly": 2, "monthly": 3}.get(k, 4))
    return "daily" if ("push" in info.events or "workflow_run" in info.events) else "unknown"


def cron_interval_hours(crons: List[str]) -> float:
    if not crons:
        return 24.0
    classes = [classify_cron(c) for c in crons]
    if "hourly" in classes:
        return 1.0
    if "daily" in classes:
        return 24.0
    if "weekly" in classes:
        return 168.0
    return 720.0


# ---------------------------------------------------------------------------
# Data loading (list endpoints, bounded)
# ---------------------------------------------------------------------------

def list_workflows(cli: ApiClient) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for page in range(1, MAX_WORKFLOW_PAGES + 1):
        data = cli.get(f"/repos/{cli.repo}/actions/workflows",
                       {"per_page": 100, "page": page})
        chunk = data.get("workflows", [])
        out.extend(chunk)
        if len(chunk) < 100:
            break
    return out


def list_runs(cli: ApiClient, *, status: Optional[str] = None,
              created_gte: Optional[str] = None, max_pages: int = MAX_RUN_PAGES
              ) -> Tuple[List[Dict[str, Any]], bool]:
    out: List[Dict[str, Any]] = []
    truncated = False
    for page in range(1, max_pages + 1):
        params: Dict[str, Any] = {"per_page": 100, "page": page, "exclude_pull_requests": "true"}
        if status:
            params["status"] = status
        if created_gte:
            params["created"] = f">={created_gte}"
        data = cli.get(f"/repos/{cli.repo}/actions/runs", params)
        chunk = data.get("workflow_runs", [])
        out.extend(chunk)
        if len(chunk) < 100:
            break
        if page == max_pages:
            truncated = True
    return out, truncated


def probe_latest_run(cli: ApiClient, workflow_id: int) -> Optional[Dict[str, Any]]:
    data = cli.get(f"/repos/{cli.repo}/actions/workflows/{workflow_id}/runs",
                   {"per_page": 1, "exclude_pull_requests": "true"})
    runs = data.get("workflow_runs", [])
    return runs[0] if runs else None


def fetch_run_jobs(cli: ApiClient, run_id: Any) -> List[Dict[str, Any]]:
    data = cli.get(f"/repos/{cli.repo}/actions/runs/{run_id}/jobs", {"per_page": 50})
    return data.get("jobs", [])


# ---------------------------------------------------------------------------
# Analysis plumbing
# ---------------------------------------------------------------------------

class Ctx:
    def __init__(self, now: datetime, repo: str, window_start: datetime,
                 runs: List[Dict[str, Any]], queued: List[Dict[str, Any]],
                 running: List[Dict[str, Any]], workflows: List[Dict[str, Any]],
                 triggers: Dict[str, TriggerInfo], prev_watchlist: List[Dict[str, Any]],
                 cli: Any, truncated: bool):
        self.now = now
        self.repo = repo
        self.window_start = window_start
        self.runs = runs
        self.queued = queued
        self.running = running
        self.workflows = workflows
        self.triggers = triggers
        self.prev_watchlist = prev_watchlist
        self.cli = cli
        self.truncated = truncated
        self.job_probes = 0
        self.groups: Dict[Tuple[Any, str], List[Dict[str, Any]]] = {}
        for r in runs:
            wid = r.get("workflow_id")
            branch = r.get("head_branch") or "(none)"
            if wid is None:
                continue
            self.groups.setdefault((int(wid), branch), []).append(r)
        for key in self.groups:
            self.groups[key].sort(key=_run_sort_key, reverse=True)
        self.recovered = 0
        self.plain_green = 0

    def jobs_for(self, run_id: Any) -> List[Dict[str, Any]]:
        if self.job_probes >= MAX_JOB_PROBES:
            raise RateLimitedError("job probe cap reached")
        self.job_probes += 1
        return fetch_run_jobs(self.cli, run_id)

    def wf_name(self, wid: Any) -> str:
        for wf in self.workflows:
            if int(wf.get("id", -1)) == int(wid):
                return wf.get("name") or wf.get("path") or f"workflow-{wid}"
        for key in self.groups:
            if int(key[0]) == int(wid):
                for r in self.groups[key]:
                    if r.get("name"):
                        return r["name"]
        return f"workflow-{wid}"


def _completed(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [r for r in items if r.get("status") == "completed" and r.get("conclusion")]


def _norm_hog_name(name: Any) -> str:
    return str(name).strip().lower().replace("–", "-").replace("—", "-")


# ---------------------------------------------------------------------------
# R1 — failed-no-success (+ recovered / prune classification)
# ---------------------------------------------------------------------------

def rule_r1(ctx: Ctx) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for (wid, branch), items in ctx.groups.items():
        comp = _completed(items)
        if not comp:
            continue
        last_bad_idx = next((i for i, r in enumerate(comp) if r.get("conclusion") in BAD_CONCLUSIONS), None)
        if last_bad_idx is None:
            ctx.plain_green += 1
            continue
        if any(r.get("conclusion") == "success" for r in comp[:last_bad_idx]):
            ctx.recovered += 1  # success completed AFTER the last failure => NOT AN ISSUE
            continue
        run = comp[last_bad_idx]
        ever_passed = any(r.get("conclusion") == "success" for r in items)
        age = _age_hours(ctx.now, _run_end(run)) or 9999.0
        row = {
            "workflow_id": int(wid),
            "workflow": ctx.wf_name(wid),
            "branch": branch,
            "run_id": run.get("id"),
            "run_number": run.get("run_number"),
            "conclusion": run.get("conclusion"),
            "last_failure_ended": run.get("run_ended_at") or run.get("updated_at"),
            "age_hours": age,
            "ever_passed_in_window": ever_passed,
            "html_url": run.get("html_url"),
            "class": "broken",
        }
        if not ever_passed and age > 24 * 7:
            row["class"] = "prune"  # "never passed in life" + dormant => prune row, not an incident
        rows.append(row)
    rows.sort(key=lambda x: x.get("age_hours") or 0.0)
    return {"status": "ok", "rows": rows[:50],
            "notes": f"{len(rows)} failed-no-success group(s); window truncated={ctx.truncated}"}


# ---------------------------------------------------------------------------
# R2 — monitor-next-run candidates (stateful across invocations via report JSON)
# ---------------------------------------------------------------------------

def rule_r2(ctx: Ctx, r1_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    resolved: List[Dict[str, Any]] = []
    still: List[Dict[str, Any]] = []
    probes_left = MAX_WATCHLIST_PROBES

    for entry in ctx.prev_watchlist:
        first = _iso_to_dt(entry.get("first_seen")) or ctx.window_start
        expect_by = _iso_to_dt(entry.get("expect_by"))
        key = (int(entry.get("workflow_id", -1)), entry.get("branch", "(none)"))
        items = [r for r in ctx.groups.get(key, []) if _run_sort_key(r) >= first.isoformat()]
        if not items and first < ctx.window_start and probes_left > 0:
            probes_left -= 1
            try:
                latest = probe_latest_run(ctx.cli, key[0])
            except RateLimitedError:
                latest = None
            if latest and _run_sort_key(latest) >= first.isoformat():
                items = [latest]
        succ_after = [r for r in items if r.get("conclusion") == "success"]
        new_entry = dict(entry)
        new_entry["occurrences_seen"] = len(items)
        if succ_after:
            new_entry["state"] = "resolved_flapping"  # green after failure => reclassify FLAPPING
            resolved.append(new_entry)
            continue
        # (probe failures fall through as "no runs seen" — degraded, not fatal)
        if expect_by and ctx.now > expect_by:
            if items:
                new_entry["state"] = "escalated_still_broken"
            else:
                new_entry["state"] = "escalated_scheduler_dead"  # expected runs never materialized
            resolved.append(new_entry)
            continue
        new_entry["state"] = "watching"
        still.append(new_entry)

    watch: List[Dict[str, Any]] = list(still)
    known = {(e.get("workflow_id"), e.get("branch")) for e in watch}
    for row in r1_rows:
        info = ctx.triggers_for_workflow(row["workflow_id"])
        live = bool(info) and ("schedule" in info.events or "push" in info.events)
        if not live or (row["workflow_id"], row["branch"]) in known:
            continue
        interval = cron_interval_hours(info.crons) if info else 24.0
        watch.append({
            "workflow_id": row["workflow_id"],
            "workflow": row["workflow"],
            "branch": row["branch"],
            "first_seen": ctx.now.isoformat(),
            "expect_by": (ctx.now + timedelta(hours=2 * interval + 1)).isoformat(),
            "cadence_hours": interval,
            "occurrences_seen": 0,
            "state": "watching",
            "note": "R1 candidate with live cadence: watch next 2 occurrences",
        })
        known.add((row["workflow_id"], row["branch"]))

    watch = [e for e in watch
             if (ctx.now - (_iso_to_dt(e.get("first_seen")) or ctx.window_start)).days < 7]
    return {"status": "ok", "rows": watch, "resolved": resolved,
            "notes": f"{len(watch)} watching, {len(resolved)} resolved/escalated this cycle"}


def _ctx_triggers_for_workflow(self: Ctx, wid: Any) -> Optional[TriggerInfo]:
    for wf in self.workflows:
        if int(wf.get("id", -1)) == int(wid):
            base = (wf.get("path") or "").split("@", 1)[0]
            return self.triggers.get(base)
    return None


Ctx.triggers_for_workflow = _ctx_triggers_for_workflow  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# R3 — flapping (>=5 fails / 15 runs, latest green) + failing step names
# ---------------------------------------------------------------------------

def rule_r3(ctx: Ctx) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for (wid, branch), items in ctx.groups.items():
        comp = _completed(items)[:FLAP_WINDOW]
        if len(comp) < FLAP_WINDOW:
            continue
        if comp[0].get("conclusion") != "success":
            continue
        fails = [r for r in comp if r.get("conclusion") in BAD_CONCLUSIONS]
        if len(fails) < FLAP_FAILS_MIN:
            continue
        steps: List[str] = []
        split = {"infra_flake": 0, "real_bug": 0}
        for run in fails[:2]:  # bounded: step names for at most 2 recent failing runs
            try:
                for job in ctx.jobs_for(run.get("id")):
                    for st in (job.get("steps") or []):
                        if st.get("conclusion") in ("failure", "timed_out"):
                            name = st.get("name") or "?"
                            steps.append(name)
                            low = name.lower()
                            if any(h in low for h in INFRA_STEP_HINTS):
                                split["infra_flake"] += 1
                            else:
                                split["real_bug"] += 1
            except RateLimitedError:
                steps.append("SKIPPED(rate)")
                break
        rows.append({
            "workflow_id": int(wid),
            "workflow": ctx.wf_name(wid),
            "branch": branch,
            "fails_in_window": len(fails),
            "window": len(comp),
            "failing_steps": sorted(set(steps))[:6],
            "split": split,
            "html_url": fails[0].get("html_url"),
        })
    rows.sort(key=lambda x: -x["fails_in_window"])
    return {"status": "ok", "rows": rows[:30],
            "notes": f"{len(rows)} flapper(s) (>= {FLAP_FAILS_MIN} fails / {FLAP_WINDOW} runs, latest green)"}


# ---------------------------------------------------------------------------
# R4 — phantom queue (queued > 24h, zero materialized jobs)
# ---------------------------------------------------------------------------

def rule_r4(ctx: Ctx) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for run in ctx.queued:
        age = _age_hours(ctx.now, _iso_to_dt(run.get("created_at")))
        if age is None or age <= PHANTOM_QUEUE_HOURS:
            continue
        try:
            jobs = ctx.jobs_for(run.get("id"))
        except RateLimitedError:
            rows.append({"run_id": run.get("id"), "workflow": run.get("name"),
                         "created_at": run.get("created_at"), "age_hours": age,
                         "jobs_count": "SKIPPED(rate)", "phantom": None})
            continue
        if len(jobs) == 0:
            rows.append({
                "run_id": run.get("id"),
                "workflow": run.get("name") or ctx.wf_name(run.get("workflow_id")),
                "branch": run.get("head_branch"),
                "created_at": run.get("created_at"),
                "age_hours": age,
                "jobs_count": 0,
                "phantom": True,
                "note": "uncancelable (REST 409/403 + UI fail) -> batch for GitHub Support",
            })
    rows.sort(key=lambda x: x.get("created_at") or "")
    return {"status": "ok", "rows": rows[:50],
            "notes": f"{len(rows)} phantom queued run(s) > {PHANTOM_QUEUE_HOURS:.0f}h with 0 jobs"}


# ---------------------------------------------------------------------------
# R5 — runner hogs (in_progress > 2h, or > 2x workflow p90)
# ---------------------------------------------------------------------------

def rule_r5(ctx: Ctx) -> Dict[str, Any]:
    durations: Dict[int, List[float]] = {}
    for (wid, _b), items in ctx.groups.items():
        durs = []
        for r in _completed(items):
            s, e = _run_start(r), _run_end(r)
            if s and e and e > s:
                durs.append((e - s).total_seconds() / 3600.0)
        if durs:
            durations[int(wid)] = sorted(durs)

    rows: List[Dict[str, Any]] = []
    for run in ctx.running:
        start = _run_start(run)
        runtime = _age_hours(ctx.now, start)
        if runtime is None:
            continue
        wid = int(run.get("workflow_id") or -1)
        p90 = None
        durs = durations.get(wid) or []
        if durs:
            p90 = durs[min(len(durs) - 1, int(0.9 * len(durs)))]
        over_p90 = p90 is not None and runtime > 2 * p90
        if runtime <= RUNNER_HOG_HOURS and not over_p90:
            continue
        name = run.get("name") or ctx.wf_name(wid)
        designed = KNOWN_DESIGNED_HOGS.get(_norm_hog_name(name))
        rows.append({
            "run_id": run.get("id"),
            "workflow": name,
            "branch": run.get("head_branch"),
            "started_at": run.get("run_started_at") or run.get("created_at"),
            "runtime_hours": runtime,
            "workflow_p90_hours": round(p90, 2) if p90 is not None else None,
            "reason": f"> {RUNNER_HOG_HOURS:.0f}h" + (" AND > 2x p90" if over_p90 else ""),
            "designed": bool(designed),
            "note": designed or "report, do not kill",
        })
    rows.sort(key=lambda x: -(x.get("runtime_hours") or 0))
    return {"status": "ok", "rows": rows[:30],
            "notes": f"{len(rows)} runner hog(s) (> {RUNNER_HOG_HOURS:.0f}h or > 2x p90)"}


# ---------------------------------------------------------------------------
# R6 — cancel churn (>= 50% cancelled / 15, cancels follow own tick spacing)
# ---------------------------------------------------------------------------

def _gaps_regular(times: List[datetime], interval_hours: Optional[float]) -> bool:
    if len(times) < 3:
        return False
    gaps = [(t2 - t1).total_seconds() / 3600.0 for t1, t2 in zip(times, times[1:])]
    mean = sum(gaps) / len(gaps)
    if mean <= 0:
        return False
    var = sum((g - mean) ** 2 for g in gaps) / len(gaps)
    std = var ** 0.5
    if interval_hours:
        return all(abs(g - interval_hours) / interval_hours < 0.35 for g in gaps)
    return std / mean < 0.5


def rule_r6(ctx: Ctx) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for (wid, branch), items in ctx.groups.items():
        comp = _completed(items)[:CHURN_WINDOW]
        if len(comp) < CHURN_WINDOW:
            continue
        cancels = [r for r in comp if r.get("conclusion") == "cancelled"]
        ratio = len(cancels) / len(comp)
        if ratio < CHURN_CANCEL_MIN:
            continue
        info = ctx.triggers_for_workflow(wid)
        interval = cron_interval_hours(info.crons) if info and info.crons else None
        times = sorted(t for t in (_run_start(r) for r in cancels) if t)
        own_ticks = _gaps_regular(times, interval)
        if not own_ticks:
            continue  # non-periodic cancels => R7 class, not self-inflicted churn
        rows.append({
            "workflow_id": int(wid),
            "workflow": ctx.wf_name(wid),
            "branch": branch,
            "cancelled": len(cancels),
            "window": len(comp),
            "cancel_ratio": round(ratio, 2),
            "own_tick_spacing": True,
            "cadence_hours": interval,
            "verdict": "concurrency cancel-loop (own tick cancels own run)",
        })
    rows.sort(key=lambda x: -x["cancel_ratio"])
    return {"status": "ok", "rows": rows[:30],
            "notes": f"{len(rows)} cancel-churn workflow(s) (>= {int(CHURN_CANCEL_MIN*100)}% / {CHURN_WINDOW}, periodic)"}


# ---------------------------------------------------------------------------
# R7 — external mass-cancel clusters (identical end timestamps across workflows)
# ---------------------------------------------------------------------------

def rule_r7(ctx: Ctx) -> Dict[str, Any]:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for r in ctx.runs:
        if r.get("status") != "completed" or r.get("conclusion") != "cancelled":
            continue
        end = r.get("run_ended_at") or r.get("updated_at")
        if not end:
            continue
        buckets.setdefault(str(end), []).append(r)
    rows: List[Dict[str, Any]] = []
    for ts, runs in buckets.items():
        wfs = {int(r.get("workflow_id") or -1) for r in runs}
        if len(runs) >= MASS_CANCEL_MIN_RUNS and len(wfs) >= MASS_CANCEL_MIN_WFS:
            rows.append({
                "timestamp": ts,
                "runs_cancelled": len(runs),
                "workflows_involved": sorted({r.get("name") or ctx.wf_name(r.get("workflow_id")) for r in runs})[:10],
                "run_ids": [r.get("id") for r in runs][:10],
                "verdict": "external mass-cancel (identical timestamps across unrelated workflows) — find the cancelling actor; do NOT 'fix' configs",
            })
    rows.sort(key=lambda x: -x["runs_cancelled"])
    return {"status": "ok", "rows": rows[:20],
            "notes": f"{len(rows)} external mass-cancel cluster(s)"}


# ---------------------------------------------------------------------------
# R8 — perpetual skips (skipped conclusions + always-skipped jobs)
# ---------------------------------------------------------------------------

def rule_r8(ctx: Ctx) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for (wid, branch), items in ctx.groups.items():
        info = ctx.triggers_for_workflow(wid)
        if info and info.dispatch_only:
            continue
        comp = _completed(items)
        if len(comp) < SKIP_MIN_RUNS:
            continue
        skips = sum(1 for r in comp if r.get("conclusion") == "skipped")
        ratio = skips / len(comp)
        if ratio <= SKIP_RATIO_MIN:
            continue
        skipped_job_names: List[str] = []
        latest = comp[0]
        try:
            for job in ctx.jobs_for(latest.get("id")):
                if job.get("conclusion") == "skipped":
                    skipped_job_names.append(job.get("name") or "?")
        except RateLimitedError:
            skipped_job_names.append("SKIPPED(rate)")
        rows.append({
            "workflow_id": int(wid),
            "workflow": ctx.wf_name(wid),
            "branch": branch,
            "skipped_runs": skips,
            "window": len(comp),
            "skip_ratio": round(ratio, 2),
            "always_skipped_jobs": sorted(set(skipped_job_names))[:8],
            "verdict": "perpetual skip: dead code / broken filter (if: always false or paths never match)",
        })
    rows.extend({
        "workflow": k["workflow"], "branch": "main", "always_skipped_jobs": [k["job"]],
        "skip_ratio": None, "window": 0, "skipped_runs": None,
        "verdict": f"known always-skipped job: {k['note']} (static config)",
    } for k in KNOWN_ALWAYS_SKIPPED_JOBS)
    return {"status": "ok", "rows": rows[:30],
            "notes": f"{len(rows)} perpetual-skip row(s) (run-level > {int(SKIP_RATIO_MIN*100)}% + known dead jobs)"}


# ---------------------------------------------------------------------------
# R9 — stale-by-cadence (trigger-aware from checked-out tree; dispatch-only EXEMPT)
# ---------------------------------------------------------------------------

def rule_r9(ctx: Ctx) -> Dict[str, Any]:
    latest_by_path: Dict[str, Optional[datetime]] = {}
    for (wid, _b), items in ctx.groups.items():
        for wf in ctx.workflows:
            if int(wf.get("id", -1)) == int(wid) and "@" not in (wf.get("path") or ""):
                path = (wf.get("path") or "").split("@", 1)[0]
                dt = _run_start(items[0])
                cur = latest_by_path.get(path)
                if dt and (cur is None or dt > cur):
                    latest_by_path[path] = dt

    rows: List[Dict[str, Any]] = []
    exempt = 0
    probes_left = MAX_R9_PROBES
    for path, info in sorted(ctx.triggers.items()):
        if info.dispatch_only:
            exempt += 1  # dispatch-only = quiet BY DESIGN (docs semantics), never stale
            continue
        cls = cadence_class(info)
        threshold = STALE_THRESHOLD_DAYS.get(cls, 60)
        last = latest_by_path.get(path)
        if last is None:
            wf_meta = next((w for w in ctx.workflows
                            if (w.get("path") or "").split("@", 1)[0] == path
                            and "@" not in (w.get("path") or "")), None)
            if wf_meta is None:
                continue
            if int(wf_meta.get("id", -1)) >= 0 and probes_left > 0:
                probes_left -= 1
                try:
                    latest = probe_latest_run(ctx.cli, int(wf_meta["id"]))
                except RateLimitedError:
                    rows.append({"workflow_path": path, "workflow": info.name, "cadence": cls,
                                 "age_days": "SKIPPED(rate)", "verdict": "SKIPPED(rate)"})
                    continue
                if latest is None:
                    rows.append({"workflow_path": path, "workflow": info.name, "cadence": cls,
                                 "age_days": None, "last_run": None,
                                 "verdict": f"NEVER RUN with live trigger ({cls}) — dead trigger or broken filter"})
                    continue
                last = _run_start(latest)
            else:
                rows.append({"workflow_path": path, "workflow": info.name, "cadence": cls,
                             "age_days": "SKIPPED(budget)", "verdict": "SKIPPED(budget): latest-run probe cap reached"})
                continue
        age_days = (ctx.now - last).total_seconds() / 86400.0 if last else None
        if age_days is not None and age_days > threshold:
            rows.append({
                "workflow_path": path,
                "workflow": info.name,
                "cadence": cls,
                "age_days": round(age_days, 1),
                "threshold_days": threshold,
                "last_run": last.isoformat() if last else None,
                "verdict": f"stale by cadence: silent {age_days:.0f}d as {cls} (threshold {threshold}d)",
            })
    rows.sort(key=lambda x: -(x.get("age_days") if isinstance(x.get("age_days"), (int, float)) else 1e6))
    return {"status": "ok", "rows": rows[:40], "dispatch_exempt": exempt,
            "notes": f"{len(rows)} stale/never-run live-trigger workflow(s); {exempt} dispatch-only EXEMPT"}


# ---------------------------------------------------------------------------
# R10 — non-main push-triggered branch-only workflows
# ---------------------------------------------------------------------------

def rule_r10(ctx: Ctx) -> Dict[str, Any]:
    branch_wfs = {int(wf.get("id", -1)): wf for wf in ctx.workflows if "@" in (wf.get("path") or "")}
    rows: List[Dict[str, Any]] = []
    for wid, wf in branch_wfs.items():
        base, branch = wf["path"].split("@", 1)
        push_runs = [r for r in ctx.groups.get((wid, branch), [])
                     if r.get("event") == "push"]
        if not push_runs:
            continue
        days = max(ctx.window_days(), 0.5)
        rows.append({
            "workflow_id": wid,
            "workflow": wf.get("name") or Path(base).stem,
            "path": wf.get("path"),
            "branch": branch,
            "push_runs_in_window": len(push_runs),
            "est_runs_per_day": round(len(push_runs) / days, 1),
            "latest": push_runs[0].get("html_url"),
            "verdict": "branch-only workflow with push: trigger on its own branch — the only real per-push waste class",
        })
    rows.sort(key=lambda x: -x["push_runs_in_window"])
    return {"status": "ok", "rows": rows[:20],
            "notes": f"{len(rows)} branch-only push-triggered workflow(s) (trigger match inferred from push-event runs)"}


# ---------------------------------------------------------------------------
# R11 — workflow_run fan-in counts
# ---------------------------------------------------------------------------

def rule_r11(ctx: Ctx) -> Dict[str, Any]:
    chains: Dict[str, List[str]] = {}
    for info in ctx.triggers.values():
        if info.workflow_run_upstreams:
            chains[info.name] = sorted(set(info.workflow_run_upstreams))
    days = max(ctx.window_days(), 0.5)
    rows: List[Dict[str, Any]] = []
    for consumer, upstreams in sorted(chains.items(), key=lambda kv: -len(kv[1])):
        run_count = 0
        for (wid, _b), items in ctx.groups.items():
            if ctx.wf_name(wid) == consumer:
                run_count += len(items)
        rows.append({
            "consumer": consumer,
            "upstreams_count": len(upstreams),
            "upstreams": upstreams[:12],
            "chain_runs_in_window": run_count,
            "est_chain_runs_per_day": round(run_count / days, 1),
            "verdict": ("fan-in amplification: add if: conclusion == 'success' + path-change guard"
                        if len(upstreams) >= 2 else "single-upstream consumer (monitor only)"),
        })
    return {"status": "ok", "rows": rows[:20],
            "notes": f"{len(rows)} workflow_run chain(s) from checked-out tree"}


# ---------------------------------------------------------------------------
# R12 — no-consumer outputs (static config from known findings — acceptable per spec)
# ---------------------------------------------------------------------------

def rule_r12(ctx: Ctx) -> Dict[str, Any]:
    rows = [dict(r) for r in R12_NO_CONSUMER_OUTPUTS]
    for r in rows:
        r["verdict"] = "latent trap: zero repo consumers — delete output or wire a consumer"
    return {"status": "ok", "rows": rows,
            "notes": "static config block from known findings (2026-11-16 audit); extend as new artifacts are measured"}


# ---------------------------------------------------------------------------
# Report assembly + 5-section markdown
# ---------------------------------------------------------------------------

def run_rule(name: str, fn) -> Dict[str, Any]:
    try:
        result = fn()
        result.setdefault("status", "ok")
        result["rule"] = name
        return result
    except RateLimitedError as exc:
        return {"rule": name, "status": "SKIPPED(rate)", "rows": [], "notes": str(exc)}
    except Exception as exc:  # degrade gracefully, never crash the audit
        return {"rule": name, "status": f"SKIPPED(error: {type(exc).__name__}: {exc})",
                "rows": [], "notes": "rule degraded"}


def build_report(ctx: Ctx) -> Dict[str, Any]:
    rules: Dict[str, Any] = {}
    rules["R1"] = run_rule("R1 failed-no-success", lambda: rule_r1(ctx))
    rules["R2"] = run_rule("R2 monitor-next-run", lambda: rule_r2(ctx, rules["R1"].get("rows", [])))
    rules["R3"] = run_rule("R3 flapping", lambda: rule_r3(ctx))
    rules["R4"] = run_rule("R4 phantom queue", lambda: rule_r4(ctx))
    rules["R5"] = run_rule("R5 runner hogs", lambda: rule_r5(ctx))
    rules["R6"] = run_rule("R6 cancel churn", lambda: rule_r6(ctx))
    rules["R7"] = run_rule("R7 external mass-cancel", lambda: rule_r7(ctx))
    rules["R8"] = run_rule("R8 perpetual skips", lambda: rule_r8(ctx))
    rules["R9"] = run_rule("R9 stale-by-cadence", lambda: rule_r9(ctx))
    rules["R10"] = run_rule("R10 non-main push branch-only", lambda: rule_r10(ctx))
    rules["R11"] = run_rule("R11 fan-in amplification", lambda: rule_r11(ctx))
    rules["R12"] = run_rule("R12 no-consumer outputs", lambda: rule_r12(ctx))

    report: Dict[str, Any] = {
        "schema": "gha-health-audit/1.0",
        "generated_at": ctx.now.isoformat(),
        "repo": ctx.repo,
        "window_start": ctx.window_start.isoformat(),
        "window_end": ctx.now.isoformat(),
        "runs_scanned": len(ctx.runs),
        "runs_window_truncated": ctx.truncated,
        "workflows_scanned": len(ctx.workflows),
        "api_calls_used": ctx.cli.calls,
        "api_budget": API_BUDGET_MAX,
        "rules": rules,
        "counts": {
            "broken_now": len([r for r in rules["R1"].get("rows", []) if r.get("class") == "broken"]),
            "prune": len([r for r in rules["R1"].get("rows", []) if r.get("class") == "prune"]),
            "monitor_next_run": len([r for r in rules["R2"].get("rows", []) if r.get("state") == "watching"]),
            "flapping": len(rules["R3"].get("rows", [])),
            "queue_hogs": (len(rules["R4"].get("rows", [])) + len(rules["R5"].get("rows", []))
                           + len(rules["R6"].get("rows", [])) + len(rules["R7"].get("rows", []))),
            "stale_skipped_prune": (len(rules["R8"].get("rows", [])) + len(rules["R9"].get("rows", []))
                                    + len(rules["R10"].get("rows", []))),
            "fan_in_chains": len(rules["R11"].get("rows", [])),
            "no_consumer_outputs": len(rules["R12"].get("rows", [])),
            "not_an_issue_recovered": ctx.recovered,
            "plain_green": ctx.plain_green,
        },
        "watchlist": rules["R2"].get("rows", []),
    }
    stable = {k: v for k, v in report.items() if k not in VOLATILE_JSON_KEYS}
    report["findings_hash"] = hashlib.sha256(
        json.dumps(stable, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return report


def render_summary(report: Dict[str, Any]) -> str:
    r = report["rules"]
    c = report["counts"]
    L: List[str] = []
    L.append("# GHA Health Summary (R1-R12)")
    L.append("")
    L.append(f"- **Generated:** {report['generated_at']} · repo `{report['repo']}`")
    L.append(f"- **Window:** {report['window_start']} → {report['window_end']} "
             f"({report['runs_scanned']} runs scanned, truncated={report['runs_window_truncated']}; "
             f"{report['workflows_scanned']} workflows)")
    L.append(f"- **API budget:** {report['api_calls_used']}/{report['api_budget']} calls used")
    L.append("")

    L.append("## 1. BROKEN NOW (action required)")
    broken = [x for x in r["R1"].get("rows", []) if x.get("class") == "broken"]
    if not broken:
        L.append("")
        L.append("_None — no workflow is failed with no subsequent success in window._")
    else:
        L.append("")
        L.append("| Workflow | Branch | Last failure (ended) | Age h | Conclusion | Ever passed? |")
        L.append("|---|---|---|---|---|---|")
        for x in broken[:10]:
            L.append(f"| {_esc(x['workflow'])} | {_esc(x['branch'])} | {_esc(x.get('last_failure_ended'))} "
                     f"| {x.get('age_hours')} | {_esc(x.get('conclusion'))} "
                     f"| {'yes' if x.get('ever_passed_in_window') else 'NEVER (prune candidate if dormant)'} |")
        if len(broken) > 10:
            L.append(f"\n_(+{len(broken) - 10} more in JSON)_")
    L.append("")

    L.append("## 2. FLAPPING (watch list + failing steps)")
    flaps = r["R3"].get("rows", [])
    L.append("")
    if not flaps:
        L.append("_None — no workflow has ≥5 fails in its last 15 runs with a green latest._")
    else:
        L.append("| Workflow | Branch | Fails/15 | Failing steps | Infra vs bug |")
        L.append("|---|---|---|---|---|")
        for x in flaps[:10]:
            split = x.get("split", {})
            L.append(f"| {_esc(x['workflow'])} | {_esc(x['branch'])} | {x['fails_in_window']}/{x['window']} "
                     f"| {_esc(', '.join(x.get('failing_steps') or ['?']))} "
                     f"| infra {split.get('infra_flake', 0)} / bug {split.get('real_bug', 0)} |")
    watch = [x for x in r["R2"].get("rows", []) if x.get("state") == "watching"]
    if watch:
        L.append("")
        L.append(f"**R2 monitor-next-run ({len(watch)} watching):** auto-watch next 2 occurrences; "
                 "green ⇒ reclassify FLAPPING, missing ⇒ escalate (scheduler dead).")
        for x in watch[:5]:
            L.append(f"- {_esc(x.get('workflow'))} @ {_esc(x.get('branch'))} — cadence {x.get('cadence_hours')}h, "
                     f"expect resolution by {_esc(x.get('expect_by'))}")
    resolved = r["R2"].get("resolved", [])
    if resolved:
        L.append("")
        for x in resolved[:5]:
            L.append(f"- resolved: {_esc(x.get('workflow'))} → **{x.get('state')}**")
    L.append("")

    L.append("## 3. QUEUE HOGS (phantom batches, runner hogs, churn %, volume/fan-in)")
    L.append("")
    phantom = r["R4"].get("rows", [])
    L.append(f"- **Phantom queued runs (> {PHANTOM_QUEUE_HOURS:.0f}h, 0 jobs):** {len(phantom)}")
    for x in phantom[:5]:
        L.append(f"  - run {x.get('run_id')} {_esc(x.get('workflow'))} queued {_esc(x.get('created_at'))} "
                 f"(age {x.get('age_hours')}h) — uncancelable ⇒ GitHub Support batch")
    hogs = r["R5"].get("rows", [])
    L.append(f"- **Runner hogs (in_progress > {RUNNER_HOG_HOURS:.0f}h or > 2x p90):** {len(hogs)}")
    for x in hogs[:5]:
        tag = " [DESIGNED HOG — report, don't fix]" if x.get("designed") else ""
        p90 = x.get("workflow_p90_hours")
        p90_txt = f"{p90}h" if isinstance(p90, (int, float)) else "n/a"
        L.append(f"  - {_esc(x.get('workflow'))} — {x.get('runtime_hours')}h running "
                 f"(p90 {p90_txt}){tag}")
    churn = r["R6"].get("rows", [])
    L.append(f"- **Cancel churn (≥{int(CHURN_CANCEL_MIN*100)}% cancelled/{CHURN_WINDOW}, own tick spacing):** {len(churn)}")
    for x in churn[:5]:
        L.append(f"  - {_esc(x['workflow'])} — {x['cancelled']}/{x['window']} cancelled "
                 f"({int(x['cancel_ratio']*100)}%) — {x['verdict']}")
    mass = r["R7"].get("rows", [])
    L.append(f"- **External mass-cancel clusters:** {len(mass)}")
    for x in mass[:5]:
        L.append(f"  - {x['runs_cancelled']} runs across {len(x['workflows_involved'])} workflows at identical "
                 f"timestamp {_esc(x['timestamp'])} — find the cancelling actor")
    fan = r["R11"].get("rows", [])
    L.append(f"- **workflow_run fan-in chains:** {len(fan)}")
    for x in fan[:5]:
        L.append(f"  - {_esc(x['consumer'])} ← {x['upstreams_count']} upstreams ≈ {x['est_chain_runs_per_day']} runs/day")
    L.append("")

    L.append("## 4. STALE / SKIPPED / PRUNE (trigger-aware verdicts)")
    L.append("")
    r8 = r["R8"].get("rows", [])
    r9 = r["R9"].get("rows", [])
    r10 = r["R10"].get("rows", [])
    prune = [x for x in r["R1"].get("rows", []) if x.get("class") == "prune"]
    L.append(f"- **Perpetual skips (R8):** {len(r8)}")
    for x in r8[:5]:
        L.append(f"  - {_esc(x.get('workflow'))} — skip ratio {x.get('skip_ratio')} — {_esc(x.get('verdict'))}")
    L.append(f"- **Stale-by-cadence (R9):** {len(r9)} "
             f"({r['R9'].get('dispatch_exempt', 0)} dispatch-only workflows EXEMPT by design)")
    for x in r9[:8]:
        L.append(f"  - {_esc(x.get('workflow'))} [{x.get('cadence')}] — {_esc(x.get('verdict'))}")
    L.append(f"- **Branch-only push waste (R10):** {len(r10)}")
    for x in r10[:5]:
        L.append(f"  - {_esc(x.get('workflow'))}@{_esc(x.get('branch'))} — {x.get('push_runs_in_window')} push runs "
                 f"(≈ {x.get('est_runs_per_day')}/day)")
    L.append(f"- **Prune rows (R1: never passed + dormant):** {len(prune)}")
    for x in prune[:5]:
        L.append(f"  - {_esc(x['workflow'])} @ {_esc(x['branch'])} — never passed in window, "
                 f"last failure {x.get('age_hours')}h ago")
    L.append("")

    L.append("## 5. NOT AN ISSUE (recovered) — suppressed count")
    L.append("")
    L.append(f"**{c['not_an_issue_recovered']}** workflow/branch group(s) had a success complete AFTER their "
             f"most recent failure — suppressed per triage principle (recovered failures are explicitly "
             f"filtered so 'green' and 'filtered noise' stay distinguishable).")
    L.append(f"- additionally **{c['plain_green']}** group(s) were plain green (no failure in window).")
    L.append(f"- queue-hog / stale rows above are live issues, NOT included in this suppressed count.")
    L.append("")

    L.append("---")
    L.append("")
    L.append("**Rule status:** " + " · ".join(
        f"{k}={v.get('status')}" for k, v in sorted(r.items(), key=lambda kv: int(kv[0][1:]))))
    L.append("")
    L.append("_Spec: 06_GHA_BEST_PRACTICES_APPROACH.md §2 (R1-R12). Output format: AGENT_PROMPT_job_analysis.md §5. "
             "R12 is a static known-findings config block. This report is detection-only: it never retries, "
             "kills or cancels anything._")
    L.append("")
    return "\n".join(L)


def write_outputs(out_dir: Path, report: Dict[str, Any], summary_md: str, dry_run: bool) -> bool:
    """Write JSON+MD only when the findings payload changed. Returns True if written."""
    if dry_run:
        print(summary_md)
        print("=" * 72)
        print(json.dumps(report, indent=2, default=str))
        return False
    jpath = out_dir / "gha_health.json"
    mpath = out_dir / "gha_health_summary.md"
    if jpath.exists():
        try:
            prev = json.loads(jpath.read_text(encoding="utf-8"))
            if prev.get("findings_hash") == report.get("findings_hash"):
                print(f"[gha-health] findings unchanged (hash {report['findings_hash'][:12]}…) — "
                      "leaving files untouched so the job skips the commit")
                return False
        except Exception:
            pass
    out_dir.mkdir(parents=True, exist_ok=True)
    jpath.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    mpath.write_text(summary_md, encoding="utf-8")
    print(f"[gha-health] wrote {jpath} and {mpath}")
    return True


# ---------------------------------------------------------------------------
# Dry-run fixtures — synthetic fleet that trips every rule, zero network
# ---------------------------------------------------------------------------

FIXTURE_NOW = datetime(2026, 11, 16, 3, 30, tzinfo=timezone.utc)


def _mkrun(rid: int, wid: int, name: str, branch: str = "main", *,
           status: str = "completed", conclusion: Optional[str] = None,
           hours_ago: float = 1.0, dur_h: float = 0.5,
           event: str = "schedule", ended_same: Optional[str] = None) -> Dict[str, Any]:
    created = FIXTURE_NOW - timedelta(hours=hours_ago)
    started = created + timedelta(minutes=2)
    ended = created + timedelta(hours=dur_h) if status == "completed" else None
    run = {
        "id": rid, "workflow_id": wid, "name": name, "head_branch": branch,
        "status": status, "conclusion": conclusion, "event": event,
        "run_number": rid, "created_at": created.isoformat().replace("+00:00", "Z"),
        "run_started_at": started.isoformat().replace("+00:00", "Z"),
        "updated_at": (ended or started).isoformat().replace("+00:00", "Z"),
        "html_url": f"https://github.com/{DEFAULT_REPO}/actions/runs/{rid}",
    }
    if ended is not None:
        run["run_ended_at"] = ended.isoformat().replace("+00:00", "Z")
    if ended_same:
        run["run_ended_at"] = ended_same
        run["updated_at"] = ended_same
    return run


def build_fixtures() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]],
                              List[Dict[str, Any]], Dict[str, TriggerInfo], Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    _rid = 5000

    def nxt() -> int:
        nonlocal _rid
        _rid += 1
        return _rid

    # R1 broken + R2 watch: alpha-engine-fast (hourly cron), 3 straight failures
    for h in (2.0, 3.0, 4.0):
        runs.append(_mkrun(nxt(), 101, "alpha-engine-fast", conclusion="failure", hours_ago=h))
    # R1 recovered: ml-train fail then success
    runs.append(_mkrun(nxt(), 102, "ml-train", conclusion="failure", hours_ago=30.0))
    runs.append(_mkrun(nxt(), 102, "ml-train", conclusion="success", hours_ago=20.0, dur_h=3.0))
    # R3 flapping: dup-guard 15 runs, 6 fails interleaved, latest success
    flap_pattern = ["success", "failure", "success", "failure", "success", "failure",
                    "success", "failure", "success", "failure", "success", "failure",
                    "success", "success", "success"]
    for i, conc in enumerate(flap_pattern):
        runs.append(_mkrun(nxt(), 103, "dup-guard", conclusion=conc,
                           hours_ago=1.5 + i * 1.0, event="schedule"))
    # R5 hog + R6 churn: dynamic-runner — 15 runs, ALL cancelled on its own hourly tick
    for i in range(15):
        runs.append(_mkrun(nxt(), 104, "dynamic-runner", conclusion="cancelled",
                           hours_ago=1.0 + i * 1.0, dur_h=0.9, event="schedule"))
    # R8 perpetual skip: dead-filter — 10 push runs, 9 skipped (ratio 0.9 > 0.8)
    for i in range(10):
        runs.append(_mkrun(nxt(), 105, "dead-filter", conclusion="skipped" if i < 9 else "success",
                           hours_ago=2.0 + i * 5.0, event="push"))
    # R10 branch-only push waste: mermaid-test-deploy@wiring
    for i in range(20):
        runs.append(_mkrun(nxt(), 108, "mermaid-test Deploy", branch="wiring",
                           conclusion="failure", hours_ago=2.0 + i * 6.0, event="push"))
    # R11 fan-in consumer runs
    for i in range(3):
        runs.append(_mkrun(nxt(), 109, "deploy-consumer", conclusion="success",
                           hours_ago=6.0 + i * 40.0, dur_h=0.3, event="workflow_run"))
    # R7 external mass-cancel: 5 runs across 3 workflows ending at the SAME instant
    mass_ts = "2026-11-15T02:17:33Z"
    for wid, name in ((103, "dup-guard"), (104, "dynamic-runner"), (105, "dead-filter"),
                      (103, "dup-guard"), (104, "dynamic-runner")):
        runs.append(_mkrun(nxt(), wid, name, conclusion="cancelled", hours_ago=25.3,
                           dur_h=0.2, ended_same=mass_ts))

    queued = [_mkrun(nxt(), 111, "stuck-queue-wf", status="queued", hours_ago=30.0, event="schedule")]
    running = [
        _mkrun(nxt(), 110, "Discord Bot – Persistent", status="in_progress", hours_ago=30.0),
        _mkrun(nxt(), 104, "dynamic-runner", status="in_progress", hours_ago=5.0),
    ]
    # _mkrun sets run_started_at = created+2min; for hogs we want long runtimes -> adjust
    running[0]["run_started_at"] = (FIXTURE_NOW - timedelta(hours=30)).isoformat().replace("+00:00", "Z")
    running[1]["run_started_at"] = (FIXTURE_NOW - timedelta(hours=5)).isoformat().replace("+00:00", "Z")

    workflows = [
        {"id": 101, "name": "alpha-engine-fast", "path": ".github/workflows/alpha-engine-fast.yml", "state": "active"},
        {"id": 102, "name": "ml-train", "path": ".github/workflows/ml-train.yml", "state": "active"},
        {"id": 103, "name": "dup-guard", "path": ".github/workflows/dup-guard.yml", "state": "active"},
        {"id": 104, "name": "dynamic-runner", "path": ".github/workflows/dynamic-runner.yml", "state": "active"},
        {"id": 105, "name": "dead-filter", "path": ".github/workflows/dead-filter.yml", "state": "active"},
        {"id": 106, "name": "old-daily", "path": ".github/workflows/old-daily.yml", "state": "active"},
        {"id": 107, "name": "manual-tool", "path": ".github/workflows/manual-tool.yml", "state": "active"},
        {"id": 108, "name": "mermaid-test Deploy", "path": ".github/workflows/mermaid-test-deploy.yml@wiring",
         "state": "active"},
        {"id": 109, "name": "deploy-consumer", "path": ".github/workflows/deploy-consumer.yml", "state": "active"},
        {"id": 110, "name": "Discord Bot – Persistent", "path": ".github/workflows/discord-bot-persistent.yml",
         "state": "active"},
        {"id": 111, "name": "stuck-queue-wf", "path": ".github/workflows/stuck-queue-wf.yml", "state": "active"},
    ]

    def tri(path: str, name: str, events: List[str], crons: Optional[List[str]] = None,
            push: Any = None, ups: Optional[List[str]] = None) -> TriggerInfo:
        info = TriggerInfo(path)
        info.name = name
        info.events = events
        info.crons = crons or []
        info.push = push
        info.workflow_run_upstreams = ups or []
        info.dispatch_only = events == ["workflow_dispatch"]
        return info

    triggers = {
        ".github/workflows/alpha-engine-fast.yml":
            tri(".github/workflows/alpha-engine-fast.yml", "alpha-engine-fast", ["schedule"], ["5 * * * *"]),
        ".github/workflows/ml-train.yml":
            tri(".github/workflows/ml-train.yml", "ml-train", ["schedule"], ["30 4 * * *"]),
        ".github/workflows/dup-guard.yml":
            tri(".github/workflows/dup-guard.yml", "dup-guard", ["schedule"], ["0 * * * *"]),
        ".github/workflows/dynamic-runner.yml":
            tri(".github/workflows/dynamic-runner.yml", "dynamic-runner", ["schedule"], ["0 * * * *"]),
        ".github/workflows/dead-filter.yml":
            tri(".github/workflows/dead-filter.yml", "dead-filter", ["push"], push={"branches": ["never-matches-*"]}),
        ".github/workflows/old-daily.yml":
            tri(".github/workflows/old-daily.yml", "old-daily", ["schedule"], ["0 6 * * *"]),
        ".github/workflows/manual-tool.yml":
            tri(".github/workflows/manual-tool.yml", "manual-tool", ["workflow_dispatch"]),
        ".github/workflows/mermaid-test-deploy.yml":
            tri(".github/workflows/mermaid-test-deploy.yml", "mermaid-test Deploy", ["push"],
                push={"branches": ["wiring"]}),
        ".github/workflows/deploy-consumer.yml":
            tri(".github/workflows/deploy-consumer.yml", "deploy-consumer", ["workflow_run"],
                ups=["alpha-engine-fast", "ml-train", "dup-guard", "dynamic-runner",
                     "dead-filter", "old-daily", "stuck-queue-wf", "billing-sync"]),
        ".github/workflows/discord-bot-persistent.yml":
            tri(".github/workflows/discord-bot-persistent.yml", "Discord Bot – Persistent", ["push"]),
        ".github/workflows/stuck-queue-wf.yml":
            tri(".github/workflows/stuck-queue-wf.yml", "stuck-queue-wf", ["schedule"], ["15 */4 * * *"]),
    }

    jobs_map: Dict[str, Any] = {}
    # failing step probes for dup-guard flapper (its two latest failing runs)
    flap_fails = [r for r in runs if r["workflow_id"] == 103 and r.get("conclusion") == "failure"]
    if flap_fails:
        jobs_map[str(flap_fails[0]["id"])] = {"jobs": [
            {"name": "scan", "conclusion": "failure",
             "steps": [{"name": "Install dependencies (pip)", "conclusion": "success", "number": 1},
                       {"name": "Compute alpha score", "conclusion": "failure", "number": 2}]}]}
    if len(flap_fails) > 1:
        jobs_map[str(flap_fails[1]["id"])] = {"jobs": [
            {"name": "scan", "conclusion": "failure",
             "steps": [{"name": "Setup Playwright browsers", "conclusion": "failure", "number": 1}]}]}
    # phantom queued run -> zero jobs
    jobs_map[str(queued[0]["id"])] = {"jobs": []}
    # dead-filter LATEST completed run (groups sort desc -> first inserted is newest) -> always-skipped job
    dead_last = [r for r in runs if r["workflow_id"] == 105 and r.get("status") == "completed"][0]
    jobs_map[str(dead_last["id"])] = {"jobs": [
        {"name": "wsl-direct", "conclusion": "skipped", "steps": []},
        {"name": "build", "conclusion": "success", "steps": []}]}

    latest_map: Dict[str, Any] = {
        "106": {"workflow_runs": [_mkrun(9100, 106, "old-daily", conclusion="success", hours_ago=24 * 40)]},
        "107": {"workflow_runs": []},  # never run, dispatch-only => exempt anyway
    }
    fixture_api = {"jobs": jobs_map, "latest": latest_map}
    return runs, queued, running, workflows, triggers, fixture_api


class FixtureClient:
    """Canned-response stand-in for ApiClient — used by --dry-run (no network)."""

    def __init__(self, fixture_api: Dict[str, Any]):
        self.calls = 0
        self.repo = DEFAULT_REPO
        self.fx = fixture_api

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.calls += 1
        m = re.search(r"/actions/runs/(\d+)/jobs$", path)
        if m:
            return self.fx["jobs"].get(m.group(1), {"jobs": []})
        m = re.search(r"/actions/workflows/(\d+)/runs$", path)
        if m:
            return self.fx["latest"].get(m.group(1), {"workflow_runs": []})
        return {}


def window_days_fn(ctx_self: Ctx) -> float:
    return max((ctx_self.now - ctx_self.window_start).total_seconds() / 86400.0, 0.5)


Ctx.window_days = window_days_fn  # type: ignore[attr-defined]


def _mk_ctx(now, repo, window_start, runs, queued, running, workflows, triggers,
            prev_watchlist, cli, truncated) -> Ctx:
    return Ctx(now, repo, window_start, runs, queued, running, workflows, triggers,
               prev_watchlist, cli, truncated)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gha_health_audit.py",
        description="Hardened GitHub Actions health guardian (R1-R12, 06 S2 rule set). "
                    "Detection-only: never retries, kills or cancels runs.",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="emit a sample report from built-in fixture counts; NO network, NO file writes")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parent.parent),
                        help="checked-out repo root (workflow `on:` triggers are read from here)")
    parser.add_argument("--out-dir", default=None,
                        help="output dir (default <repo-root>/GHACTIONS_LIVE)")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", DEFAULT_REPO))
    parser.add_argument("--window-days", type=int, default=RUNS_WINDOW_DAYS)
    parser.add_argument("--max-api-calls", type=int, default=API_BUDGET_MAX)
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    out_dir = Path(args.out_dir) if args.out_dir else repo_root / "GHACTIONS_LIVE"
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=args.window_days)

    if args.dry_run:
        now = FIXTURE_NOW
        window_start = FIXTURE_NOW - timedelta(days=args.window_days)
        runs, queued, running, workflows, triggers, fx = build_fixtures()
        cli: Any = FixtureClient(fx)
        truncated = False
        print("[gha-health] DRY RUN — fixture data, no network, no writes", file=sys.stderr)
    else:
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GIT_PAT_CLASSIC")
        if not token:
            print("ERROR: GITHUB_TOKEN / GH_TOKEN not set (live mode needs it). "
                  "Use --dry-run for an offline sample.", file=sys.stderr)
            return 2
        cli = ApiClient(token, args.repo, budget=args.max_api_calls)
        triggers = parse_workflow_triggers(repo_root)
        print(f"[gha-health] parsed {len(triggers)} workflow file(s) from {repo_root / '.github/workflows'} "
              f"(yaml={'safe_load' if yaml is not None else 'fallback scanner'})", file=sys.stderr)
        workflows = list_workflows(cli)
        gte = (now - timedelta(days=args.window_days)).strftime("%Y-%m-%d")
        runs, truncated = list_runs(cli, created_gte=gte)
        runs = [r for r in runs
                if (_iso_to_dt(r.get("run_performed_at")) or _iso_to_dt(r.get("created_at"))
                    or now) >= window_start]
        queued, _ = list_runs(cli, status="queued", max_pages=MAX_STATUS_PAGES)
        running, _ = list_runs(cli, status="in_progress", max_pages=MAX_STATUS_PAGES)

    prev_watchlist: List[Dict[str, Any]] = []
    jpath = out_dir / "gha_health.json"
    if jpath.exists():
        try:
            prev_watchlist = json.loads(jpath.read_text(encoding="utf-8")).get("watchlist") or []
        except Exception:
            prev_watchlist = []

    ctx = _mk_ctx(now, args.repo, window_start, runs, queued, running, workflows, triggers,
                  prev_watchlist, cli, truncated)
    report = build_report(ctx)
    summary_md = render_summary(report)
    write_outputs(out_dir, report, summary_md, dry_run=args.dry_run)
    print(f"[gha-health] done. api_calls={cli.calls}  recovered={report['counts']['not_an_issue_recovered']}  "
          f"broken={report['counts']['broken_now']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
