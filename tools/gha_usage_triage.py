#!/usr/bin/env python3
"""Join GitHub Actions usage (billing) exports with the repo workflow inventory
and the per-workflow run/log audit, then emit a cost-weighted triage list.

Two CSV shapes are accepted (both are what the GitHub "Actions usage" export
gives you):

  workflow-level: Workflow,Total minutes,Workflow runs,Jobs,Runner type,Runtime OS
  job-level:      Job,Workflow,Total minutes,Job runs,Runner type,Runner labels

Inputs are never modified. Outputs are deterministic (sorted) so re-running on
the same inputs produces identical files.

Usage:
  python3 tools/gha_usage_triage.py \
      --jobs-csv /path/job_export.csv \
      --workflows-csv /path/workflow_export.csv \
      --workflows-dir .github/workflows \
      --matrix reports/GHA_PER_WORKFLOW_RUN_MATRIX.json \
      --audit reports/GHA_LATEST_RUN_LOG_AUDIT.json \
      --out-md reports/GHA_USAGE_TRIAGE.md \
      --out-json reports/GHA_USAGE_TRIAGE.json
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import os
import sys
from collections import defaultdict

# Triage buckets, in the order they appear in the report.
BUCKET_ORDER = [
    "ERRORS",            # latest audited log has error lines
    "SUSPICIOUS",        # log looks wrong but no hard error annotation
    "NEVER_RAN",         # repo workflow with no billed runs and no run seen
    "AUDIT_INCOMPLETE",  # runs exist but the log audit had no log to read
    "DELETED",           # billed minutes, workflow file gone, no successor
    "RENAMED",           # billed minutes under a name the repo no longer uses
    "DISABLED",          # billed minutes, file now ends in .disabled
    "WARN_ONLY",         # warnings but no errors
    "UNAUDITED",         # no run anywhere and no audit entry
    "CLEAN",             # audited, nothing found
    "MANAGED",           # GitHub-generated workflow (pages, code scanning)
]

# Workflows GitHub creates itself; they have no file in .github/workflows and
# are not ours to fix.
MANAGED_WORKFLOWS = {"pages-build-deployment", "update-graph", "dependency-graph"}

# Buckets that mean real work for us, in the order they matter.
INVESTIGATE = ("ERRORS", "SUSPICIOUS", "NEVER_RAN", "AUDIT_INCOMPLETE", "DELETED")


def _int(v: str | None) -> int:
    if v is None:
        return 0
    v = v.strip().replace(",", "")
    if not v:
        return 0
    try:
        return int(float(v))
    except ValueError:
        return 0


def _basename(path: str) -> str:
    return os.path.basename(path.strip().replace("\\", "/"))


def load_workflow_csv(path: str) -> dict[str, dict]:
    """Workflow-level export -> {basename: {minutes, runs, jobs, runner_type, os}}."""
    out: dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            key = _basename(row.get("Workflow") or "")
            if not key:
                continue
            out[key] = {
                "minutes": _int(row.get("Total minutes")),
                "runs": _int(row.get("Workflow runs")),
                "jobs": _int(row.get("Jobs")),
                "runner_type": (row.get("Runner type") or "").strip(),
                "os": (row.get("Runtime OS") or "").strip(),
            }
    return out


def load_job_csv(path: str) -> dict[str, dict]:
    """Job-level export aggregated per workflow file."""
    agg: dict[str, dict] = defaultdict(
        lambda: {"minutes": 0, "runs": 0, "jobs": [], "runner_types": set()}
    )
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            wf = _basename(row.get("Workflow") or "")
            if not wf:
                continue
            a = agg[wf]
            a["minutes"] += _int(row.get("Total minutes"))
            a["runs"] += _int(row.get("Job runs"))
            job = (row.get("Job") or "").strip()
            if job:
                a["jobs"].append((job, _int(row.get("Total minutes"))))
            rt = (row.get("Runner type") or "").strip()
            if rt:
                a["runner_types"].add(rt)
    out = {}
    for wf, a in agg.items():
        jobs = sorted(a["jobs"], key=lambda x: (-x[1], x[0]))
        out[wf] = {
            "minutes": a["minutes"],
            "runs": a["runs"],
            "job_count": len(a["jobs"]),
            "top_jobs": [{"job": j, "minutes": m} for j, m in jobs[:3]],
            "runner_types": sorted(a["runner_types"]),
        }
    return out


def load_json_list(path: str | None) -> dict[str, dict]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"WARN: {path} is not valid JSON ({exc}); ignoring", file=sys.stderr)
        return {}
    if isinstance(data, dict):
        data = list(data.values())
    out = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        key = item.get("file") or item.get("workflow") or ""
        if key:
            out[_basename(key)] = item
    return out


def inventory(workflows_dir: str) -> set[str]:
    names = set()
    if not os.path.isdir(workflows_dir):
        return names
    for name in os.listdir(workflows_dir):
        if name.endswith((".yml", ".yaml")):
            names.add(name)
    return names


def _stem(path: str) -> str:
    return path[:-4] if path.endswith((".yml", ".yaml")) else path


def _leading_token(path: str) -> str:
    """First meaningful token of a workflow name: cross-db-audit -> 'cross'."""
    for tok in _stem(path).lower().replace(".", "-").replace("_", "-").split("-"):
        if len(tok) >= 3:
            return tok
    return _stem(path).lower()


def _rename_target(name: str, repo: set[str]) -> str | None:
    """Best current-file candidate for a billed workflow that no longer exists.

    A rename keeps the subject of the workflow, so require the same leading
    token (daily-price-refresh -> daily-prices-yf-refresh) and a close name.
    Without that, a loosely-similar name (mermaid-test-deploy vs
    backtest-and-deploy, both containing "deploy") would be a false rename.
    """
    stem = _stem(name)
    lead = _leading_token(name)
    best, best_ratio = None, 0.0
    for cand in repo:
        if _leading_token(cand) != lead:
            continue
        ratio = difflib.SequenceMatcher(None, stem.lower(), _stem(cand).lower()).ratio()
        if ratio > best_ratio:
            best, best_ratio = cand, ratio
    return best if best_ratio >= 0.6 else None


def classify_missing(name: str, repo: set[str], workflows_dir: str) -> tuple[str, str]:
    """(bucket, detail) for a workflow that appears in usage but not in the repo."""
    if name in MANAGED_WORKFLOWS:
        return "MANAGED", "GitHub-generated workflow"
    if os.path.exists(os.path.join(workflows_dir, name + ".disabled")):
        return "DISABLED", name + ".disabled"
    target = _rename_target(name, repo)
    if target:
        return "RENAMED", target
    return "DELETED", ""


def audit_bucket(entry: dict | None, runs_seen: int) -> str:
    if not entry:
        return "UNAUDITED"
    verdict = (entry.get("verdict") or "").upper()
    if verdict in ("ERRORS", "SUSPICIOUS", "WARN_ONLY", "CLEAN"):
        return verdict
    if entry.get("audited") is False and runs_seen > 0:
        return "AUDIT_INCOMPLETE"
    if entry.get("errors"):
        return "ERRORS"
    if entry.get("suspicious"):
        return "SUSPICIOUS"
    if entry.get("warnings"):
        return "WARN_ONLY"
    if entry.get("audited"):
        return "CLEAN"
    return "UNAUDITED"


def build(args) -> dict:
    job_csv = load_job_csv(args.jobs_csv) if args.jobs_csv else {}
    wf_csv = load_workflow_csv(args.workflows_csv) if args.workflows_csv else {}
    matrix = load_json_list(args.matrix)
    audit = load_json_list(args.audit)
    repo = inventory(args.workflows_dir)

    # A workflow can appear in either/both CSVs; prefer the workflow-level row
    # for runs, the job-level row for minutes-per-job detail.
    all_files = set(wf_csv) | set(job_csv) | repo | set(matrix) | set(audit)
    rows = []
    for f in sorted(all_files):
        usage = wf_csv.get(f, {})
        jobs = job_csv.get(f, {})
        mat = matrix.get(f) or {}
        aud = audit.get(f)

        minutes = usage.get("minutes", jobs.get("minutes", 0))
        runs = usage.get("runs", jobs.get("runs", 0))
        if not minutes and jobs.get("minutes"):
            minutes = jobs["minutes"]
        if not runs and jobs.get("runs"):
            runs = jobs["runs"]

        seen = int(mat.get("runs_seen") or 0)
        bucket = audit_bucket(aud, seen)
        detail = ""
        exists = f in repo
        if not exists and (minutes or runs):
            bucket, detail = classify_missing(f, repo, args.workflows_dir)
        elif exists and not minutes and not runs and bucket == "UNAUDITED":
            if seen == 0:
                bucket = "NEVER_RAN"

        latest = mat.get("latest_run") or {}
        rows.append(
            {
                "file": f,
                "exists": exists,
                "minutes": minutes,
                "runs": runs,
                "class": mat.get("class") or "",
                "state": mat.get("state") or "",
                "latest_conclusion": latest.get("conclusion") or "",
                "runs_seen": int(mat.get("runs_seen") or 0),
                "successes_seen": int(mat.get("successes_seen") or 0),
                "audit": {
                    "verdict": (aud or {}).get("verdict") or "",
                    "errors": (aud or {}).get("errors") or 0,
                    "warnings": (aud or {}).get("warnings") or 0,
                    "suspicious": (aud or {}).get("suspicious") or 0,
                    "error_kinds": (aud or {}).get("error_kinds") or {},
                },
                "bucket": bucket,
                "bucket_detail": detail,
                "job_count": jobs.get("job_count", 0),
                "top_jobs": jobs.get("top_jobs", []),
            }
        )

    total_minutes = sum(r["minutes"] for r in rows)
    total_runs = sum(r["runs"] for r in rows)

    # Priority: is it broken?, does it cost?, does it run at all?
    weight = {
        "ERRORS": 5000,
        "SUSPICIOUS": 4000,
        "NEVER_RAN": 3000,
        "AUDIT_INCOMPLETE": 2500,
        "DELETED": 1500,
        "RENAMED": 500,
        "DISABLED": 200,
        "WARN_ONLY": 1000,
        "UNAUDITED": 800,
        "CLEAN": 0,
        "MANAGED": 0,
    }
    for r in rows:
        r["priority"] = weight.get(r["bucket"], 0) + min(r["minutes"], 40000) // 10
    rows.sort(key=lambda r: (-r["priority"], -r["minutes"], r["file"]))

    buckets: dict[str, dict] = {}
    for name in BUCKET_ORDER:
        members = [r for r in rows if r["bucket"] == name]
        if not members:
            continue
        buckets[name] = {
            "count": len(members),
            "minutes": sum(r["minutes"] for r in members),
            "runs": sum(r["runs"] for r in members),
            "files": [r["file"] for r in members],
        }

    return {
        "generated_from": {
            "jobs_csv": args.jobs_csv,
            "workflows_csv": args.workflows_csv,
            "workflows_dir": args.workflows_dir,
            "matrix": args.matrix,
            "audit": args.audit,
        },
        "totals": {
            "workflows_in_repo": len(repo),
            "workflows_in_usage": len(wf_csv) or len(job_csv),
            "workflows_joined": len(rows),
            "total_minutes": total_minutes,
            "total_runs": total_runs,
            "renamed_count": sum(1 for r in rows if r["bucket"] == "RENAMED"),
            "deleted_count": sum(1 for r in rows if r["bucket"] == "DELETED"),
            "never_ran_count": sum(1 for r in rows if r["bucket"] == "NEVER_RAN"),
            "audit_incomplete_count": sum(1 for r in rows if r["bucket"] == "AUDIT_INCOMPLETE"),
            "needs_investigation": sum(1 for r in rows if r["bucket"] in INVESTIGATE),
        },
        "buckets": buckets,
        "rows": rows,
    }


def _fmt(n: int) -> str:
    return f"{n:,}"


def render_md(data: dict, top: int) -> str:
    t = data["totals"]
    rows = data["rows"]
    out = []
    out.append("# GitHub Actions Usage Triage\n")
    out.append(
        "Cost-weighted join of the GitHub Actions usage export (minutes + run counts) "
        "against the repo workflow inventory, the per-workflow run matrix, and the "
        "latest-run log audit.\n"
    )
    out.append("## Headline\n")
    out.append("| Metric | Value |")
    out.append("|--------|------:|")
    out.append(f"| Workflow files in repo | {_fmt(t['workflows_in_repo'])} |")
    out.append(f"| Workflows present in usage export | {_fmt(t['workflows_in_usage'])} |")
    out.append(f"| Billed minutes | {_fmt(t['total_minutes'])} |")
    out.append(f"| Billed runs | {_fmt(t['total_runs'])} |")
    out.append(f"| **Workflows needing investigation** | **{_fmt(t['needs_investigation'])}** |")
    out.append(f"| — with errors in latest log | {_fmt(data['buckets'].get('ERRORS', {}).get('count', 0))} |")
    out.append(f"| — suspicious log | {_fmt(data['buckets'].get('SUSPICIOUS', {}).get('count', 0))} |")
    out.append(f"| — never ran (no billed runs) | {_fmt(t['never_ran_count'])} |")
    out.append(f"| — audit had no log to read | {_fmt(t['audit_incomplete_count'])} |")
    out.append(f"| — billed under a deleted file name | {_fmt(t['deleted_count'])} |")
    out.append(f"| — billed under a renamed file name | {_fmt(t['renamed_count'])} |")
    out.append("")

    out.append("## Buckets\n")
    out.append("| Bucket | Workflows | Minutes | Runs |")
    out.append("|--------|----------:|--------:|-----:|")
    for name in BUCKET_ORDER:
        b = data["buckets"].get(name)
        if b:
            out.append(f"| {name} | {b['count']} | {_fmt(b['minutes'])} | {_fmt(b['runs'])} |")
    out.append("")

    out.append(f"## Top {top} by priority\n")
    out.append("| # | Workflow | Bucket | Minutes | Runs | Latest | Errors |")
    out.append("|--:|----------|--------|--------:|-----:|--------|-------:|")
    for i, r in enumerate(rows[:top], 1):
        out.append(
            f"| {i} | `{r['file']}` | {r['bucket']} | {_fmt(r['minutes'])} | "
            f"{_fmt(r['runs'])} | {r['latest_conclusion'] or '—'} | {r['audit']['errors']} |"
        )
    out.append("")

    out.append("## Most expensive workflows\n")
    expensive = sorted(rows, key=lambda r: (-r["minutes"], r["file"]))[:top]
    out.append("| # | Workflow | Minutes | Runs | Bucket | Top job |")
    out.append("|--:|----------|--------:|-----:|--------|---------|")
    for i, r in enumerate(expensive, 1):
        top_job = r["top_jobs"][0] if r["top_jobs"] else None
        job_txt = f"`{top_job['job']}` ({_fmt(top_job['minutes'])})" if top_job else "—"
        out.append(
            f"| {i} | `{r['file']}` | {_fmt(r['minutes'])} | {_fmt(r['runs'])} | "
            f"{r['bucket']} | {job_txt} |"
        )
    out.append("")

    missing = [r for r in rows if r["bucket"] in ("RENAMED", "DELETED", "DISABLED", "MANAGED")]
    if missing:
        out.append("## Billed under a name the repo no longer has\n")
        out.append("| Billed workflow | Minutes | Runs | Classification | Successor |")
        out.append("|-----------------|--------:|-----:|----------------|-----------|")
        for r in sorted(missing, key=lambda r: (-r["minutes"], r["file"])):
            out.append(
                f"| `{r['file']}` | {_fmt(r['minutes'])} | {_fmt(r['runs'])} | "
                f"{r['bucket']} | {('`' + r['bucket_detail'] + '`') if r['bucket_detail'] else '—'} |"
            )
        out.append("")

    # Where the money actually goes.
    billable = sorted((r for r in rows if r["minutes"]), key=lambda r: -r["minutes"])
    if billable:
        out.append("## Cost concentration\n")
        for n in (10, 25, 50):
            share = sum(r["minutes"] for r in billable[:n])
            if billable and n <= len(billable):
                pct = 100.0 * share / t["total_minutes"]
                out.append(f"- Top {n} workflows = {_fmt(share)} min ({pct:.1f}% of billed minutes)")
        out.append("")

    out.append(
        "\n> Minutes are the provider's billed total for the export window, not a "
        "per-run wall clock. A workflow with 0 minutes and 0 runs never executed in "
        "that window; it is still `active` in the repo and will execute the moment its "
        "trigger fires. See `reports/GHA_VALIDATION_LEDGER.md` for the per-workflow "
        "verdict ledger and `reports/GHA_PER_WORKFLOW_RUN_TODOS.md` for actions.\n"
    )
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs-csv", help="job-level usage export")
    ap.add_argument("--workflows-csv", help="workflow-level usage export")
    ap.add_argument("--workflows-dir", default=".github/workflows")
    ap.add_argument("--matrix", default="reports/GHA_PER_WORKFLOW_RUN_MATRIX.json")
    ap.add_argument("--audit", default="reports/GHA_LATEST_RUN_LOG_AUDIT.json")
    ap.add_argument("--out-md", default="reports/GHA_USAGE_TRIAGE.md")
    ap.add_argument("--out-json", default="reports/GHA_USAGE_TRIAGE.json")
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args(argv)

    if not args.jobs_csv and not args.workflows_csv:
        ap.error("at least one of --jobs-csv / --workflows-csv is required")
    for p in (args.jobs_csv, args.workflows_csv):
        if p and not os.path.exists(p):
            ap.error(f"no such CSV: {p}")

    data = build(args)
    md = render_md(data, args.top)
    for path, payload in ((args.out_md, md), (args.out_json, json.dumps(data, indent=1, sort_keys=True))):
        if not path:
            continue
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(payload if payload.endswith("\n") else payload + "\n")
        print(f"wrote {path}")

    t = data["totals"]
    print(
        f"inventory={t['workflows_in_repo']} usage={t['workflows_in_usage']} "
        f"minutes={t['total_minutes']} runs={t['total_runs']} "
        f"needs_investigation={t['needs_investigation']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
