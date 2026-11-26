#!/usr/bin/env python3
"""
Audit the LATEST RUN LOG of every workflow for warnings, errors and suspicious
output — not just the pass/fail conclusion.

`gha_workflow_run_matrix.py` says whether the last run was green. A green run can
still be full of `::warning::`, `DeprecationWarning`, swallowed exceptions,
`symbol not found`, NaN metrics or `KeyError`s. This tool downloads the log of
each workflow's latest run and counts them, keeping samples so a human can judge.

Input : reports/GHA_PER_WORKFLOW_RUN_MATRIX.json  (latest_run.id per workflow)
Output: reports/GHA_LATEST_RUN_LOG_AUDIT.{json,md}

Usage:
    python3 tools/gha_latest_run_log_audit.py --workers 4
    python3 tools/gha_latest_run_log_audit.py --only mirror-site.yml --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS = REPO_ROOT / "reports"
MATRIX = REPORTS / "GHA_PER_WORKFLOW_RUN_MATRIX.json"
LOGDIR = REPORTS / "latest_run_logs"
OUT_JSON = REPORTS / "GHA_LATEST_RUN_LOG_AUDIT.json"
OUT_MD = REPORTS / "GHA_LATEST_RUN_LOG_AUDIT.md"

# (regex, human label). First match wins per line for bucketing.
ERRORS = [
    (r"##\[error\]", "##[error] annotation"),
    (r"ModuleNotFoundError: No module named '([^']+)'", "missing python module"),
    (r"ImportError", "import error"),
    (r"Traceback \(most recent call last\)", "python traceback"),
    (r"KeyError: '?([A-Za-z0-9_\-\.]+)'?", "KeyError"),
    (r"(?:^|\W)ERROR(?:\W|$)", "ERROR line"),
    (r"fatal: ", "git fatal"),
    (r"command not found", "missing binary"),
    (r"No such file or directory: '([^']+)'", "missing file"),
    (r"permission denied", "permission denied"),
    (r"HTTP Error 4\d\d", "http 4xx"),
    (r"HTTP Error 5\d\d", "http 5xx"),
]
WARNINGS = [
    (r"##\[warning\]", "##[warning] annotation"),
    (r"::warning::", "workflow warning"),
    (r"\bWARNING\b", "WARNING line"),
    (r"DeprecationWarning", "deprecation"),
    (r"deprecated", "deprecated"),
    (r"Node\.js \d+ actions are deprecated|set-output.*deprecat", "action deprecation"),
]
SUSPICIOUS = [
    (r"symbol not found", "symbol not found"),
    (r"\bNaN\b", "NaN in output"),
    (r"\binf\b|\binfinity\b", "inf in output"),
    (r"undefined", "undefined value"),
    (r"division by zero", "division by zero"),
    (r"skipping|skipped", "skipped work"),
    (r"\bno data\b|no data found", "no data"),
]

MAX_SAMPLES = 6
RESUME = "--resume" in sys.argv


def gh(args: list[str], timeout: int = 180) -> tuple[bool, str]:
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    if r.returncode != 0:
        return False, (r.stderr or r.stdout or "").strip()[:300]
    return True, r.stdout


# GitHub prints the whole `run:` block into the log before executing it, so an
# error-handling branch that says `echo 'ERROR: ...'` matches the ERROR regex
# even though it never executed. Two consecutive self-hosted runs (45762289378
# swarm-sync-v2, 45762068793 strategy-funnel) were scored ERRORS purely from
# that echo text. Skip command-echo lines: they are source, not output.
_ECHO_SOURCE = re.compile(r"(?<![\w.\-/])echo\s+['\"]", re.I)


def _is_echoed_source(line: str) -> bool:
    return bool(_ECHO_SOURCE.search(line))


def bucket(text: str, patterns, counter: dict, samples: dict, limit=MAX_SAMPLES) -> int:
    hits = 0
    for line in text.splitlines():
        # Command-echo lines are script source GitHub prints before running it;
        # `echo 'ERROR: ...'` in an error branch is not an emitted error.
        if _ECHO_SOURCE.search(line):
            continue
        low = line
        for pat, label in patterns:
            if re.search(pat, low):
                hits += 1
                counter[label] = counter.get(label, 0) + 1
                if len(samples.setdefault(label, [])) < limit:
                    # strip the leading timestamp / job prefix gh adds
                    clean = re.sub(r"^\S+\t\S+\t\d{4}-\d\d-\d\dT\S+\s?", "", line).strip()
                    samples[label].append(clean[:300])
                break
    return hits


def latest_runs_by_name(limit: int = 1200) -> dict[str, dict]:
    """One call for the whole fleet: newest run per workflow NAME.

    The matrix snapshot goes stale within minutes on this repo (a dozen scheduled
    workflows start runs constantly), so the run id is resolved here instead.
    """
    ok, out = gh(["run", "list", "--limit", str(limit),
                  "--json", "workflowName,conclusion,status,databaseId,createdAt,headSha,event"])
    if not ok:
        print(f"[log-audit] run list failed: {out[:200]}", file=sys.stderr)
        return {}
    best: dict[str, dict] = {}
    for r in json.loads(out):
        name = r.get("workflowName")
        if not name:
            continue
        if name not in best or r["createdAt"] > best[name]["createdAt"]:
            best[name] = r
    return best


def audit_one(row: dict, verbose: bool, runs_by_name: dict | None = None) -> dict:
    file = row["file"]
    run_id = (row.get("latest_run") or {}).get("id")
    if runs_by_name:
        fresh = runs_by_name.get(row.get("name") or "")
        if fresh and fresh.get("databaseId"):
            run_id = fresh["databaseId"]
            row = dict(row, latest_run={"conclusion": fresh.get("conclusion"),
                                        "id": fresh["databaseId"],
                                        "sha": (fresh.get("headSha") or "")[:8]})
    if not run_id:
        return {"file": file, "class": row["class"], "audited": False,
                "reason": "no run on record"}
    cached = LOGDIR / f"{file}.log"
    if RESUME and cached.exists() and cached.stat().st_size > 0:
        out = cached.read_text()
        ok = True
    else:
        ok, out = gh(["run", "view", str(run_id), "--log"])
    if not ok:
        return {"file": file, "class": row["class"], "audited": False,
                "run_id": run_id, "reason": f"log unavailable: {out[:120]}"}

    LOGDIR.mkdir(parents=True, exist_ok=True)
    cached.write_text(out)

    ec, wc, sc = {}, {}, {}
    es, ws, ss = {}, {}, {}
    n_err = bucket(out, ERRORS, ec, es)
    n_warn = bucket(out, WARNINGS, wc, ws)
    n_susp = bucket(out, SUSPICIOUS, sc, ss)
    lines = out.count("\n")

    verdict = "ERRORS" if n_err else ("WARNINGS" if n_warn else ("SUSPICIOUS" if n_susp else "CLEAN"))
    if verbose:
        print(f"  {verdict:10s} {file:50s} err={n_err} warn={n_warn} susp={n_susp} lines={lines}",
              flush=True)
    return {
        "file": file,
        "class": row["class"],
        "audited": True,
        "run_id": run_id,
        "run_conclusion": (row.get("latest_run") or {}).get("conclusion"),
        "verdict": verdict,
        "lines": lines,
        "errors": n_err,
        "warnings": n_warn,
        "suspicious": n_susp,
        "error_kinds": ec,
        "warning_kinds": wc,
        "suspicious_kinds": sc,
        "samples": {"errors": es, "warnings": ws, "suspicious": ss},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", action="append")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--resume", action="store_true",
                    help="reuse logs already saved under reports/latest_run_logs/")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    rows = json.loads(MATRIX.read_text())
    if args.only:
        rows = [r for r in rows if r["file"] in set(args.only)]
    if args.limit:
        rows = rows[:args.limit]

    print(f"[log-audit] resolving latest runs in one call...", flush=True)
    runs_by_name = latest_runs_by_name()
    print(f"[log-audit] {len(rows)} workflows, {len(runs_by_name)} have a run on record", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for res in ex.map(lambda r: audit_one(r, args.verbose, runs_by_name), rows):
            results.append(res)
            OUT_JSON.write_text(json.dumps(results, indent=2) + "\n")

    audited = [r for r in results if r.get("audited")]
    counts = {}
    for r in audited:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print(f"[log-audit] audited {len(audited)}/{len(results)}: {counts}", flush=True)

    md = ["# Latest-run log audit", "",
          "Every workflow's most recent run, log downloaded and scanned for errors, warnings and "
          "suspicious output. A green run is not a clean run.", "",
          f"- workflows examined: **{len(results)}**",
          f"- logs audited: **{len(audited)}**",
          f"- no run on record: **{len(results) - len(audited)}**", "",
          "| Verdict | Count |", "|---|---|"]
    for k in ("ERRORS", "WARNINGS", "SUSPICIOUS", "CLEAN"):
        md.append(f"| {k} | {counts.get(k, 0)} |")
    md += ["", "## Workflows whose log contains errors", ""]
    for r in sorted([x for x in audited if x["verdict"] == "ERRORS"],
                    key=lambda x: -x["errors"]):
        md.append(f"### `{r['file']}` — {r['errors']} error line(s), conclusion `{r['run_conclusion']}`")
        for kind, n in sorted(r["error_kinds"].items(), key=lambda kv: -kv[1]):
            md.append(f"- {n}× {kind}")
            for s in r["samples"]["errors"].get(kind, [])[:2]:
                md.append(f"    - `{s}`")
        md.append("")
    md += ["## Warnings only", ""]
    for r in sorted([x for x in audited if x["verdict"] == "WARNINGS"],
                    key=lambda x: -x["warnings"]):
        kinds = ", ".join(f"{n}× {k}" for k, n in list(r["warning_kinds"].items())[:3])
        md.append(f"- `{r['file']}` — {r['warnings']} warning(s): {kinds}")
    md += ["", "## Suspicious output only", ""]
    for r in sorted([x for x in audited if x["verdict"] == "SUSPICIOUS"],
                    key=lambda x: -x["suspicious"]):
        kinds = ", ".join(f"{n}× {k}" for k, n in list(r["suspicious_kinds"].items())[:3])
        md.append(f"- `{r['file']}` — {r['suspicious']}: {kinds}")
    md += ["", "## Not auditable", ""]
    for r in results:
        if not r.get("audited"):
            md.append(f"- `{r['file']}` — {r['class']}: {r.get('reason', '')}")
    OUT_MD.write_text("\n".join(md) + "\n")
    print(f"wrote {OUT_MD.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
