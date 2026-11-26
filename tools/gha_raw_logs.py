#!/usr/bin/env python3
"""Fetch GitHub Actions *raw* job logs and extract the actual failure cause.

The UI's "View raw logs" link is just a redirect to a signed Azure blob URL that
expires in ~10 minutes. That redirect can be followed directly with the
authenticated session, so raw logs are available programmatically:

    gh api /repos/{repo}/actions/jobs/{job_id}/logs   -> plain-text job log

Three modes:

    # one job (accepts a full .../actions/runs/<run>/job/<job> URL)
    python3 tools/gha_raw_logs.py --job https://github.com/o/r/actions/runs/1/job/2

    # every job in one run
    python3 tools/gha_raw_logs.py --run 45722879024

    # latest run of every workflow seen recently; pull logs for the failing ones
    python3 tools/gha_raw_logs.py --latest-failing --limit 250

Written logs land in reports/gha_logs/<run>-<job>-<slug>.log and the summary in
reports/gha_raw_logs_latest.{json,md}.

API cost: 1 paginated run-list call, then 1 job-list + 1 log call per failing
job. Roughly 40 calls for a repo with ~15 currently-failing workflows.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REPO = "eltonaguiar/findtorontoevents_antigravity.ca"
LOG_DIR = Path("reports/gha_logs")

# Timestamps prefixed to every line by the runner: "2026-11-25T23:23:22.6916319Z ".
TS_RE = re.compile(r"^\ufeff?\d{4}-\d\d-\d\dT[\d:.]+Z ?")

# Ordered by diagnostic value: a specific annotation beats a bare exit code.
# `##[error]` is the runner's own annotation format and is authoritative. The bare
# `::error::` workflow command must be matched too, but ONLY when it is real output —
# the log also contains the step's script source, so `echo "::error::..."` and
# `print(f"::error::...")` lines are source, not events (see SOURCE_LINE_RE).
CAUSE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("error_command", re.compile(r"##\[error\](.+)")),
    ("error_annotation", re.compile(r"^::error::(.+)")),
    ("fatal", re.compile(r"\bfatal: (.+)")),
    ("python_error", re.compile(r"^(\w*(?:Error|Exception|Exit)\b.*)$")),
    ("failed_assert", re.compile(r"\b(?:AssertionError|assert .* failed)(.*)")),
    ("failure_line", re.compile(r"^(?:FAILED|FAIL|✗|✘)\b(.*)")),
    ("exit_code", re.compile(r"exit code (\d+)")),
]

# These only restate that something already failed; they cannot identify a cause.
GENERIC = (
    "Process completed with exit code",
    "The process '/usr/bin/git' failed",
    "The process '/usr/bin/bash' failed",
)

# The job log embeds the step's own script (heredocs, echo/print of ::error:: commands).
# Matching those would report the source line instead of the runtime failure.
SOURCE_LINE_RE = re.compile(
    r'(?:echo\s+"::error::|print\(f?"::error::|print\(f?\'::error::|^\s*#|^\s*(?:echo|print|printf)\b)'
)


def sh(cmd: list[str], binary: bool = False) -> bytes:
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        err = p.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"{' '.join(cmd[:3])}... failed rc={p.returncode}: {err[:300]}")
    return p.stdout if binary else p.stdout.decode("utf-8", "replace")


def api_json(path: str) -> dict:
    return json.loads(sh(["gh", "api", path]))


def api_raw(path: str) -> bytes:
    return sh(["gh", "api", path], binary=True)


def parse_id(value: str, kind: str = "run") -> int:
    """Accept a bare id or any GitHub URL containing /runs/<n> or /job/<n>."""
    if value.isdigit():
        return int(value)
    marker = "/job/" if kind == "job" else "/runs/"
    if marker in value:
        tail = value.split(marker, 1)[1]
        num = re.match(r"(\d+)", tail)
        if num:
            return int(num.group(1))
    raise SystemExit(f"cannot parse {kind} id from: {value!r}")


def clean_lines(raw: bytes) -> list[str]:
    text = raw.decode("utf-8", "replace")
    return [TS_RE.sub("", ln) for ln in text.splitlines()]


def extract_cause(lines: list[str]) -> tuple[str, list[str], str | None]:
    """Return (best cause line, up to 6 supporting lines, terminal outcome).

    The FIRST authoritative error is usually the root cause; the LAST one is how the
    job actually ended (timeout, cancelled, exit code). Both matter, so both are kept.
    """
    hits: dict[str, list[str]] = {}
    for idx, ln in enumerate(lines):
        if not ln.strip():
            continue
        for name, pat in CAUSE_PATTERNS:
            m = pat.search(ln)
            if not m:
                continue
            if any(g in ln for g in GENERIC):
                continue  # recorded under exit_code only, never as the cause
            if name in ("error_annotation", "python_error", "failure_line") and SOURCE_LINE_RE.search(ln):
                continue  # script source being echoed, not an event
            hits.setdefault(name, []).append(ln.strip()[:400])
            if name == "python_error" and idx + 1 < len(lines):
                nxt = lines[idx + 1].strip()
                if nxt and not nxt.startswith(("File ", "at ")):
                    hits["python_error"].append(nxt[:400])
            break

    annotated = [ln.strip()[:400] for ln in lines
                 if ln.startswith("##[error]") and not any(g in ln for g in GENERIC)]
    outcome = annotated[-1] if annotated else None

    for name, _ in CAUSE_PATTERNS:
        found = hits.get(name)
        if found:
            support = [ln for ln in found[1:6] if ln != outcome]
            return found[0], support, outcome
    return "no error line found in log", [], outcome


def fetch_job(repo: str, job_id: int, job_name: str, run_id: int, save: bool) -> dict:
    raw = api_raw(f"/repos/{repo}/actions/jobs/{job_id}/logs")
    lines = clean_lines(raw)
    cause, support, outcome = extract_cause(lines)
    log_path = None
    if save:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", job_name).strip("-")[:60] or "job"
        log_path = LOG_DIR / f"{run_id}-{job_id}-{slug}.log"
        log_path.write_bytes(raw)
    return {
        "job_id": job_id,
        "job_name": job_name,
        "log_bytes": len(raw),
        "log_lines": len(lines),
        "log_path": str(log_path) if log_path else None,
        "cause": cause,
        "outcome": outcome,
        "support": support,
        "tail": [ln for ln in lines if ln.strip()][-5:],
    }


def failing_step(job: dict) -> str:
    for step in job.get("steps") or []:
        if step.get("conclusion") in ("failure", "timed_out"):
            return step.get("name", "?")
    return "-"


def run_jobs(repo: str, run_id: int) -> list[dict]:
    data = api_json(f"/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100")
    return data.get("jobs") or []


def summarise_run(repo: str, run: dict, save: bool, workers: int) -> dict:
    jobs = run_jobs(repo, run["id"])
    bad = [j for j in jobs if j.get("conclusion") in ("failure", "timed_out")]
    if not bad:  # whole-run failure with no failed job (e.g. setup error)
        bad = [j for j in jobs if j.get("conclusion") != "success"]

    def one(job: dict) -> dict:
        info = fetch_job(repo, job["id"], job.get("name", "job"), run["id"], save)
        info["step"] = failing_step(job)
        info["job_url"] = f"https://github.com/{repo}/actions/runs/{run['id']}/job/{job['id']}"
        return info

    with ThreadPoolExecutor(max_workers=min(workers, max(len(bad), 1))) as pool:
        results = list(pool.map(one, bad))
    return {**run, "failed_jobs": results}


def latest_failing(repo: str, limit: int, save: bool, workers: int,
                   include_cancelled: bool) -> dict:
    runs = json.loads(sh([
        "gh", "run", "list", "--repo", repo, "--limit", str(limit),
        "--json", "databaseId,name,workflowName,conclusion,createdAt,event,headBranch,headSha",
    ]))
    # gh returns newest first. Keep every run per workflow so the latest run and the
    # latest COMPLETED run can differ: a workflow still running must not hide the
    # failure of the run before it.
    per_wf: dict[str, list[dict]] = {}
    for r in runs:
        wf = r.get("workflowName") or r.get("name") or "unknown"
        per_wf.setdefault(wf, []).append(r)

    DONE = {"success", "failure", "cancelled", "timed_out", "skipped", "action_required", "stale"}
    latest: dict[str, dict] = {}
    for wf, rs in per_wf.items():
        newest = rs[0]
        completed = next((r for r in rs if (r.get("conclusion") or "") in DONE), newest)
        latest[wf] = {
            "workflow": wf,
            "id": completed["databaseId"],
            "conclusion": completed.get("conclusion"),
            "created_at": completed.get("createdAt"),
            "event": completed.get("event"),
            "branch": completed.get("headBranch"),
            "sha": (completed.get("headSha") or "")[:9],
            "newest_run_id": newest["databaseId"],
            "newest_in_progress": (newest.get("conclusion") or "") not in DONE,
        }

    wanted = {"failure", "timed_out"} | ({"cancelled"} if include_cancelled else set())
    targets = [v for v in latest.values() if v["conclusion"] in wanted]
    targets.sort(key=lambda v: v["workflow"].lower())

    detailed = []
    for t in targets:
        try:
            detailed.append(summarise_run(repo, t, save, workers))
        except RuntimeError as exc:
            detailed.append({**t, "error": str(exc), "failed_jobs": []})

    mix: dict[str, int] = {}
    for v in latest.values():
        mix[v["conclusion"] or "unknown"] = mix.get(v["conclusion"] or "unknown", 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": repo,
        "runs_scanned": len(runs),
        "workflows_seen": len(latest),
        "mix": mix,
        "latest_failing": detailed,
    }


def render_md(report: dict) -> str:
    out = [
        f"# GitHub Actions raw-log triage — {report['generated_at']}",
        "",
        f"Repo: `{report['repo']}`  ",
        f"Runs scanned: **{report['runs_scanned']}** · workflows seen: **{report['workflows_seen']}**  ",
        "Latest-run mix: " + ", ".join(f"{k}={v}" for k, v in sorted(report["mix"].items())),
        "",
        "Each entry below is the **latest** run of that workflow, with the raw job log fetched and the",
        "first diagnostic line extracted (specific `::error::` beats a bare exit code).",
        "",
    ]
    runs = report.get("latest_failing") or []
    if not runs:
        out.append("No failing workflows among the latest runs scanned.")
        return "\n".join(out) + "\n"

    for r in runs:
        out.append(f"## {r['workflow']}")
        out.append(f"- run `{r['id']}` · {r['conclusion']} · {r.get('event')} on `{r.get('branch')}` "
                   f"@ `{r.get('sha')}` · {r.get('created_at')}")
        out.append(f"- https://github.com/{report['repo']}/actions/runs/{r['id']}")
        if r.get("newest_in_progress"):
            out.append(f"- _newer run `{r['newest_run_id']}` is still in progress; this is the last "
                       f"completed run_")
        elif r.get("newest_run_id") and r["newest_run_id"] != r["id"]:
            out.append(f"- _latest run is `{r['newest_run_id']}`_")
        if r.get("error"):
            out.append(f"- **fetch error:** {r['error']}")
        for job in r.get("failed_jobs") or []:
            out.append(f"- job `{job['job_name']}` — failing step: **{job['step']}** "
                       f"({job['log_lines']} log lines)")
            out.append(f"  - cause: `{job['cause']}`")
            if job.get("outcome") and job["outcome"] != job["cause"]:
                out.append(f"  - outcome: `{job['outcome']}`")
            for s in job.get("support") or []:
                out.append(f"  - {s}")
            if job.get("log_path"):
                out.append(f"  - log: `{job['log_path']}`")
        out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--job", help="job id or .../actions/runs/<run>/job/<job> URL")
    ap.add_argument("--run", help="run id or .../actions/runs/<run> URL")
    ap.add_argument("--latest-failing", action="store_true",
                    help="latest run per workflow; fetch logs for the failing ones")
    ap.add_argument("--limit", type=int, default=250, help="runs to scan for latest-per-workflow")
    ap.add_argument("--include-cancelled", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-save", action="store_true", help="do not write raw .log files")
    ap.add_argument("--out", default="reports/gha_raw_logs_latest")
    args = ap.parse_args()

    save = not args.no_save

    if args.job:
        jid = parse_id(args.job, "job")
        info = fetch_job(args.repo, jid, f"job-{jid}", 0, save)
        print(json.dumps(info, indent=2))
        return 0

    if args.run:
        rid = parse_id(args.run, "run")
        meta = api_json(f"/repos/{args.repo}/actions/runs/{rid}")
        run = {"workflow": meta.get("name"), "id": rid, "conclusion": meta.get("conclusion"),
               "created_at": meta.get("created_at"), "event": meta.get("event"),
               "branch": meta.get("head_branch"), "sha": (meta.get("head_sha") or "")[:9]}
        report = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "repo": args.repo, "runs_scanned": 1, "workflows_seen": 1,
                  "mix": {meta.get("conclusion") or "unknown": 1},
                  "latest_failing": [summarise_run(args.repo, run, save, args.workers)]}
    elif args.latest_failing:
        report = latest_failing(args.repo, args.limit, save, args.workers, args.include_cancelled)
    else:
        ap.print_help()
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(report, indent=2))
    md = render_md(report)
    out.with_suffix(".md").write_text(md)
    print(md)
    print(f"wrote {out.with_suffix('.json')} and {out.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
