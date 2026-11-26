#!/usr/bin/env python3
"""
Actually EXECUTE workflows locally with `act`, one at a time, and classify the
outcome. This is the execution counterpart to the static checks in
`tools/gha_local_run_check.py`: it does not parse the YAML, it runs the steps in
a container and reads what happened.

Why it exists: the run matrix (`tools/gha_workflow_run_matrix.py`) showed 175 of
386 registered workflows have never executed on GitHub. "Never ran" is not the
same as "broken", so each one is executed here and sorted into:

  PASS            every job ran green locally
  BLOCKED_ENV     failed only on something a local box cannot supply — a secret,
                  MySQL/FTP credentials, a non-ubuntu runner, network egress
  FAIL            failed for a reason that is ours: missing script, import
                  error, bad argument, shell syntax, missing file
  SKIP_RUNNER     needs windows-latest / macos-latest (act cannot emulate)
  TIMEOUT         exceeded --timeout-per-workflow

Output: reports/GHA_ACT_LOCAL_RUN_RESULTS.{json,md} plus one log per workflow
under reports/act_logs/. Logs of PASSes are truncated to keep the tree light.

Usage:
    python3 tools/gha_act_batch.py --class NEVER_RUN --jobs 3
    python3 tools/gha_act_batch.py --only meme-scanner.yml --verbose
    python3 tools/gha_act_batch.py --resume            # skip already-done files
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS = REPO_ROOT / "reports"
LOGDIR = REPORTS / "act_logs"
MATRIX = REPORTS / "GHA_PER_WORKFLOW_RUN_MATRIX.json"
OUT_JSON = REPORTS / "GHA_ACT_LOCAL_RUN_RESULTS.json"
OUT_MD = REPORTS / "GHA_ACT_LOCAL_RUN_RESULTS.md"

RUNNER_IMAGE = "catthehacker/ubuntu:act-latest"
RUNNER_LABELS = ("ubuntu-latest", "ubuntu-22.04", "ubuntu-20.04", "ubuntu-24.04")

# Things a local box genuinely cannot provide. Ordered most-specific first.
ENV_BLOCKERS = [
    (r"Input required and not supplied: .*token", "missing secret"),
    (r"Missing required secret", "missing secret"),
    (r"secret .* (?:is )?not set", "missing secret"),
    (r"\[Errno 111\] Connection refused", "db/socket unreachable"),
    (r"Can't connect to MySQL server", "mysql unreachable"),
    (r"Unknown MySQL server host", "mysql unreachable"),
    (r"Access denied for user", "db credentials"),
    (r"DB_PASS|DB_HOST|DB_USER", "db credentials not injected"),
    (r"FTP|ftplib|530 Login", "ftp credentials"),
    (r"Resource not accessible by integration", "token scope"),
    (r"dial tcp .*: i/o timeout", "network egress"),
    (r"Temporary failure in name resolution", "network egress"),
    (r"Could not resolve host", "network egress"),
]

# Ours to fix.
REAL_FAILURES = [
    (r"ModuleNotFoundError: No module named '([^']+)'", "missing dependency"),
    (r"No such file or directory: '([^']+)'", "missing file"),
    (r"can't open file '([^']+)'", "missing script"),
    (r"unrecognized arguments:", "bad CLI argument"),
    (r"error: pathspec", "bad git path"),
    (r"syntax error", "syntax error"),
    (r"IndentationError", "python syntax"),
    (r"command not found", "missing binary"),
]


def load_matrix() -> list[dict]:
    if not MATRIX.exists():
        sys.exit(f"{MATRIX} missing — run tools/gha_workflow_run_matrix.py first")
    return json.loads(MATRIX.read_text())


def event_for(wf: dict) -> str:
    trig = wf.get("triggers") or []
    for ev in ("workflow_dispatch", "schedule", "push"):
        if ev in trig:
            return ev
    return trig[0] if trig else "push"


def classify_log(log: str, returncode: int) -> tuple[str, str]:
    if returncode == 0 and "Job failed" not in log:
        return "PASS", ""
    for pat, why in ENV_BLOCKERS:
        if re.search(pat, log, re.I):
            return "BLOCKED_ENV", why
    for pat, why in REAL_FAILURES:
        m = re.search(pat, log, re.I)
        if m:
            extra = f" ({m.group(1)})" if m.groups() and m.group(1) else ""
            return "FAIL", why + extra
    if "Job failed" in log or returncode != 0:
        return "FAIL", "unclassified non-zero exit"
    return "PASS", ""


def needs_other_runner(wf: dict) -> bool:
    """act can only run linux containers; windows/macos jobs cannot be emulated."""
    path = REPO_ROOT / ".github" / "workflows" / wf["file"]
    try:
        text = path.read_text()
    except OSError:
        return False
    return bool(re.search(r"runs-on:\s*(windows|macos)", text, re.I))


def run_one(wf: dict, timeout: int) -> dict:
    file = wf["file"]
    if needs_other_runner(wf):
        return {"file": file, "class": "SKIP_RUNNER", "reason": "windows/macos runner"}

    event = event_for(wf)
    # NOTE: do not pin --container-architecture. On this arm64 host, forcing
    # linux/amd64 makes the container exit immediately and every step fails with
    # "failed to create exec: container ... is not running".
    cmd = ["act", event, "-W", f".github/workflows/{file}", "--pull=false"]
    for label in RUNNER_LABELS:
        cmd += ["-P", f"{label}={RUNNER_IMAGE}"]
    try:
        token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                               timeout=20).stdout.strip()
    except Exception:
        token = ""
    if token:
        cmd += ["-s", f"GITHUB_TOKEN={token}"]

    LOGDIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    try:
        r = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True,
                           timeout=timeout)
        log = (r.stdout or "") + (r.stderr or "")
        cls, why = classify_log(log, r.returncode)
    except subprocess.TimeoutExpired as e:
        log = ((e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes)
               else (e.stdout or ""))
        cls, why = "TIMEOUT", f">{timeout}s"
    elapsed = round(time.time() - started, 1)

    # keep only the tail of long logs
    tail = "\n".join(log.splitlines()[-400:])
    (LOGDIR / f"{file}.log").write_text(f"# act {event} -W .github/workflows/{file}\n\n{tail}\n")

    print(f"  {cls:12s} {file:52s} {elapsed:6.1f}s  {why}", flush=True)
    return {"file": file, "class": cls, "reason": why, "seconds": elapsed,
            "event": event, "log": str((LOGDIR / f'{file}.log').relative_to(REPO_ROOT))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="classes", action="append",
                    help="matrix class to run (repeatable); default NEVER_RUN")
    ap.add_argument("--only", action="append", help="specific workflow file(s)")
    ap.add_argument("--jobs", type=int, default=3, help="parallel act containers")
    ap.add_argument("--timeout-per-workflow", type=int, default=600)
    ap.add_argument("--resume", action="store_true", help="skip files already in results")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    rows = load_matrix()
    by_file = {r["file"]: r for r in rows}
    if args.only:
        todo = [by_file[f] for f in args.only if f in by_file]
        missing = [f for f in args.only if f not in by_file]
        for f in missing:
            print(f"[warn] not in matrix: {f}", file=sys.stderr)
    else:
        classes = set(args.classes or ["NEVER_RUN"])
        todo = [r for r in rows if r["class"] in classes]

    done: dict[str, dict] = {}
    if OUT_JSON.exists():
        try:
            done = {r["file"]: r for r in json.loads(OUT_JSON.read_text())}
        except Exception:
            done = {}
    if args.resume:
        todo = [r for r in todo if r["file"] not in done or done[r["file"]]["class"] == "TIMEOUT"]
    if args.limit:
        todo = todo[:args.limit]

    print(f"[act-batch] executing {len(todo)} workflow(s), {args.jobs} at a time", flush=True)
    results = []
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for res in ex.map(lambda w: run_one(w, args.timeout_per_workflow), todo):
            results.append(res)
            done[res["file"]] = res
            OUT_JSON.write_text(json.dumps(list(done.values()), indent=2) + "\n")

    counts: dict[str, int] = {}
    for r in results:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    print(f"[act-batch] finished in {round(time.time()-started)}s: {counts}")

    # markdown summary
    allres = list(done.values())
    counts_all: dict[str, int] = {}
    for r in allres:
        counts_all[r["class"]] = counts_all.get(r["class"], 0) + 1
    lines = ["# Local `act` execution results", "",
             "Every row was actually executed in a container with "
             "`catthehacker/ubuntu:act-latest`; the class says how it went.", "",
             "| Class | Count | Meaning |", "|---|---|---|",
             f"| PASS | {counts_all.get('PASS',0)} | ran green locally |",
             f"| BLOCKED_ENV | {counts_all.get('BLOCKED_ENV',0)} | needs a secret / DB / FTP / network the local box cannot supply |",
             f"| FAIL | {counts_all.get('FAIL',0)} | broke for a reason in our control |",
             f"| SKIP_RUNNER | {counts_all.get('SKIP_RUNNER',0)} | windows/macos runner, act cannot emulate |",
             f"| TIMEOUT | {counts_all.get('TIMEOUT',0)} | exceeded the per-workflow timeout |",
             "", "## Failures worth fixing", ""]
    for cls in ("FAIL", "TIMEOUT"):
        for r in sorted([x for x in allres if x["class"] == cls], key=lambda x: x["file"]):
            lines.append(f"- `{r['file']}` — {r['reason']} ([log]({r.get('log','')}))")
    lines += ["", "## Env-blocked by cause", ""]
    causes: dict[str, list[str]] = {}
    for r in allres:
        if r["class"] == "BLOCKED_ENV":
            causes.setdefault(r["reason"], []).append(r["file"])
    for why, files in sorted(causes.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"- **{why}** ({len(files)}): " + ", ".join(f"`{f}`" for f in sorted(files)[:12])
                     + (" …" if len(files) > 12 else ""))
    lines += ["", "## Passing locally", ""]
    for r in sorted([x for x in allres if x["class"] == "PASS"], key=lambda x: x["file"]):
        lines.append(f"- [x] `{r['file']}` ({r['seconds']}s)")
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT_MD.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
