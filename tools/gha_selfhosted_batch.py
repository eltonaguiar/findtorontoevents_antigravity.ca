#!/usr/bin/env python3
"""
Run workflows on the self-hosted runner in small batches, validate the log, and
leave nothing pinned to it.

Operator protocol this implements:
  1. one or two workflows at a time on the runner,
  2. read the run's LOG (not just the conclusion),
  3. switch back to the cloud runner,
  4. move on to the next batch.

How the switch works without touching `main`:

  * If the workflow takes a `runner` input (`runs-on: ${{ inputs.runner || ... }}`),
    it is dispatched directly on `main` with `-f runner=<label>`. Nothing to revert.
  * Otherwise a throw-away branch is created from `origin/main`, `runs-on:` is
    rewritten to the self-hosted labels only on that branch, the run is dispatched
    with `--ref <branch>`, and the branch is deleted afterwards. `main` never
    contains a self-hosted pin, so an offline runner can never wedge a scheduled
    workflow — that is the failure mode this avoids.

Usage:
    python3 tools/gha_selfhosted_batch.py --workflow master-picks-health.yml
    python3 tools/gha_selfhosted_batch.py -w a.yml -w b.yml --max-parallel 2
    python3 tools/gha_selfhosted_batch.py -w alpha-engine-live.yml --runner-input
    python3 tools/gha_selfhosted_batch.py --list        # who can take a runner

Every dispatch is logged to reports/GHA_SELFHOSTED_BATCH.jsonl so a batch in
flight is visible to anyone else (and to the next COMS note).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS = REPO_ROOT / "reports"

# Branch work (rewriting runs-on, committing, pushing, deleting) must never touch
# the operator's main checkout — it is normally sitting on someone else's branch.
# A scratch worktree is used when one exists.
SCRATCH = Path(os.environ.get("GHA_BATCH_WORKDIR", "/tmp/ghrun"))
WORKDIR = SCRATCH if (SCRATCH / ".git").exists() else REPO_ROOT
LEDGER = REPORTS / "GHA_SELFHOSTED_BATCH.jsonl"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

# Legacy default, kept because callers may import it. dispatch now goes through
# pick_runner(), which chooses a runner that can actually ACCEPT the job.
SELF_HOSTED_LABELS = "[self-hosted, Linux, ARM64]"
REPO = "eltonaguiar/findtorontoevents_antigravity.ca"

# Tried in order against the pool of online+idle runners. A fixed label is the bug
# this replaces: on 2026-11-26 all three ARM64 runners were busy while the only
# idle Linux box was X64, so an ARM64 pin would have queued until job timeout.
RUNNER_PREFERENCE = [
    ["self-hosted", "Linux", "X64"],
    ["self-hosted", "Linux", "ARM64"],
    ["self-hosted", "Windows", "X64"],
    ["self-hosted"],
]

# Same buckets as tools/gha_latest_run_log_audit.py, kept small on purpose.
ERROR_PATTERNS = [
    (r"##\[error\]", "error annotation"),
    (r"ModuleNotFoundError: No module named '([^']+)'", "missing module"),
    (r"Traceback \(most recent call last\)", "traceback"),
    (r"(?:^|\W)ERROR(?:\W|$)", "ERROR line"),
    (r"fatal: ", "git fatal"),
    (r"command not found", "missing binary"),
]
ENV_PATTERNS = [
    (r"must have admin rights|Resource not accessible", "token scope"),
    (r"Can't connect to MySQL|Connection refused", "db unreachable"),
    (r"530 Login|authentication failed", "credentials"),
    (r"dial tcp .*i/o timeout|Could not resolve host", "network egress"),
]


def sh(args: list[str], timeout: int = 240, cwd: Path | None = None) -> tuple[int, str]:
    r = subprocess.run(args, cwd=cwd or WORKDIR, capture_output=True, text=True,
                       timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def gh(*args: str, timeout: int = 240) -> str:
    rc, out = sh(["gh", *args], timeout=timeout)
    if rc != 0:
        raise RuntimeError(out.strip()[:400])
    return out


def takes_runner_input(path: Path) -> bool:
    try:
        text = path.read_text()
    except OSError:
        return False
    return bool(re.search(r"inputs\.runner|runner:\s*\n[\s\S]{0,200}?description", text))


def runners() -> list[dict]:
    out = gh("api", f"repos/{REPO}/actions/runners", "--paginate",
             "-q", ".runners")
    raw = out.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # `gh api -q .runners` prints JSON-ish; fall back to the full call
        return json.loads(gh("api", f"repos/{REPO}/actions/runners", "--paginate"))


def pick_runner(prefer: str | None = None, want_os: str | None = None) -> tuple[str, str]:
    """Return (runs-on expression, runner name) for an online AND idle runner.

    Dispatching at an offline or busy runner does not fail fast - the job sits
    queued until the workflow times out, which reads like a hang. Only
    status=online and busy=False are acceptable targets.

    `prefer` may be a runner name (laptop-zerou-wsl) or one of its custom labels
    (wsl-ubuntu-2404); it is matched against the idle pool only, so asking for a
    busy box raises instead of silently waiting.

    `want_os` is 'linux', 'windows' or 'macos' and is derived from the workflow's
    own runs-on line. This matters: a bash workflow handed to a Windows runner
    fails on the first shell step with an error that looks like a workflow bug,
    so a cross-OS fallback is worse than refusing.
    """
    pool = runners()
    idle = [r for r in pool if r.get("status") == "online" and not r.get("busy")]
    if not idle:
        raise RuntimeError(
            "no self-hosted runner is both online and idle: "
            + ", ".join(f"{r['name']}={r['status']}/busy={str(r['busy']).lower()}"
                        for r in pool))

    def labels_of(r: dict) -> list[str]:
        return [l["name"] for l in r.get("labels", [])]

    def generic(labels: list[str]) -> str:
        """Minimal runs-on expression for a runner's OS+arch.

        Using the runner's FULL label set is a trap: it includes that box's own
        name and site tags (wsl-desktop, gx10, laptop-zerou-wsl). GitHub then
        requires that one specific runner, so if it drops offline the job stays
        queued forever even when a compatible box is idle. Observed on
        2026-11-26: desktop-081g9oh-wsl-1 took the dispatch, went offline, and
        laptop-zerou-wsl sat idle unable to accept the job because it lacks the
        wsl-desktop tag. Generic labels let ANY matching runner pick it up.
        """
        keep = ["self-hosted"]
        for tok in ("Linux", "Windows", "macOS", "X64", "ARM64"):
            if tok in labels:
                keep.append(tok)
        return "[" + ", ".join(keep) + "]"

    OS_TOKEN = {"linux": "Linux", "windows": "Windows", "macos": "macOS"}

    if prefer:
        chosen = [r for r in idle
                  if r["name"] == prefer
                  or prefer in labels_of(r)]
        if not chosen:
            raise RuntimeError(
                f"runner {prefer!r} is not online+idle; idle right now: "
                + ", ".join(r["name"] for r in idle))
        idle = chosen

    if want_os:
        tok = OS_TOKEN.get(want_os.lower())
        on_os = [r for r in idle if tok in labels_of(r)] if tok else idle
        if not on_os:
            raise RuntimeError(
                f"this workflow wants {want_os} but no {want_os} runner is idle; "
                "idle right now: "
                + ", ".join(f"{r['name']}({[l for l in labels_of(r) if l in OS_TOKEN.values()]})"
                            for r in idle)
                + "\n  -> wait for one to free up, or rerun with --runner <name> to override")
        idle = on_os

    for wanted in RUNNER_PREFERENCE:
        match = [r for r in idle if all(w in labels_of(r) for w in wanted)]
        if match:
            r = match[0]
            return generic(labels_of(r)), r["name"]
    r = idle[0]
    return generic(labels_of(r)), r["name"]


def wait_for_runner(prefer: str | None, want_os: str | None,
                    wait_sec: int) -> tuple[str, str]:
    """pick_runner, retried until a suitable idle runner appears or wait_sec expires.

    The self-hosted pool flaps constantly (runners go busy for minutes at a time),
    so a single probe produces false "nothing available" results. Polling is
    cheaper than a failed dispatch.
    """
    deadline = time.time() + max(0, wait_sec)
    last: Exception | None = None
    while True:
        try:
            return pick_runner(prefer, want_os)
        except RuntimeError as exc:
            last = exc
            if time.time() >= deadline:
                raise
            time.sleep(15)
            print(f"[batch] waiting for an idle {want_os or 'any'} runner "
                  f"({int(deadline - time.time())}s left)...", flush=True)
            assert last is not None


def os_of_workflow(path) -> str | None:
    """'linux' / 'windows' / 'macos' from a workflow's first runs-on line.

    PyYAML is not used here because it parses the `on:` key as the boolean True
    and this needs to survive that; a line scan is enough for runs-on.
    """
    try:
        text = path.read_text()
    except OSError:
        return None
    m = re.search(r"^\s*runs-on:\s*(.+)$", text, re.M)
    if not m:
        return None
    val = m.group(1).lower()
    if "windows" in val:
        return "windows"
    if "macos" in val or "mac-os" in val:
        return "macos"
    if "ubuntu" in val or "linux" in val:
        return "linux"
    return None


def list_capability() -> None:
    print("Self-hosted runners:")
    for r in runners():
        labels = ",".join(l["name"] for l in r.get("labels", []))
        print(f"  id={r['id']:>3} {r['name']:<22} {r['status']:<8} busy={str(r['busy']):<5} {labels}")
    print("\nWorkflows that can take a runner without an edit:")
    for p in sorted(WORKFLOW_DIR.glob("*.yml")):
        if takes_runner_input(p):
            print(f"  {p.name}")
    print("\nEverything else is dispatched on a throw-away branch.")


def dispatch(workflow: str, ref: str, extra: list[str]) -> int:
    """Dispatch and resolve the new run id.

    `gh workflow run` prints nothing useful, and the run does not appear in
    `gh run list` instantly — polling with a short retry loop is required, a
    single 3-second lookup intermittently returns an empty list.
    """
    gh("workflow", "run", workflow, "--ref", ref, *extra)
    for attempt in range(20):
        time.sleep(3)
        js = gh("run", "list", "--workflow", workflow, "--branch", ref, "--limit", "3",
                "--json", "databaseId,status,createdAt")
        runs = json.loads(js or "[]")
        if runs:
            return runs[0]["databaseId"]
    raise RuntimeError(
        f"dispatched {workflow} on {ref} but no run appeared within 60s "
        "(check `gh run list --workflow " + workflow + "`)")


def wait_for_run(run_id: int, timeout_min: int = 60) -> dict:
    deadline = time.time() + timeout_min * 60
    while time.time() < deadline:
        js = gh("run", "view", str(run_id), "--json", "status,conclusion")
        d = json.loads(js)
        if d["status"] == "completed":
            return d
        time.sleep(15)
    return {"status": "timeout", "conclusion": None}


def classify(log: str) -> tuple[str, list[str]]:
    for pat, why in ENV_PATTERNS:
        if re.search(pat, log, re.I):
            return "BLOCKED_ENV", [why]
    notes = []
    for pat, why in ERROR_PATTERNS:
        n = len(re.findall(pat, log, re.M))
        if n:
            notes.append(f"{n}x {why}")
    return ("ERRORS" if notes else "CLEAN"), notes


def log_of(run_id: int) -> str:
    rc, out = sh(["gh", "run", "view", str(run_id), "--log"], timeout=300)
    return out


def run_batch(workflows: list[str], runner_input: bool, timeout_min: int,
              max_parallel: int, runner: str | None = None,
              wait_runner_sec: int = 600) -> int:
    results = []
    for i, wf in enumerate(workflows):
        path = WORKFLOW_DIR / wf
        if not path.exists():
            print(f"[skip] {wf}: no such workflow")
            continue
        # Chosen per workflow, not once up front: the fleet flaps, and a Linux
        # workflow must never be handed a Windows box.
        labels, runner_name = wait_for_runner(runner, os_of_workflow(path),
                                              wait_runner_sec)
        print(f"[batch] {wf}: runner={runner_name}  runs-on: {labels}", flush=True)
        branch = None
        extra: list[str] = []
        ref = "main"

        if runner_input or takes_runner_input(path):
            extra = ["-f", "runner=self-hosted"]
        else:
            branch = f"selfhosted-batch/{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{wf.replace('.yml','')}"
            rc, out = sh(["bash", "-c",
                          f"git fetch -q origin main && "
                          f"git checkout -q -B '{branch}' origin/main && "
                          f"python3 - <<'PY'\n"
                          f"import re,pathlib\n"
                          f"p=pathlib.Path('.github/workflows/{wf}')\n"
                          f"s=p.read_text()\n"
                          f"s2=re.sub(r'runs-on:.*', 'runs-on: {labels}', s, count=1)\n"
                          f"p.write_text(s2)\n"
                          f"PY\n"
                          f"git commit -qam 'ci(temp): run {wf} on the self-hosted runner' && "
                          f"git push -q -f origin '{branch}'"])
            if rc != 0:
                print(f"[fail] {wf}: could not create batch branch\n{out[-400:]}")
                results.append({"workflow": wf, "verdict": "SETUP_FAILED"})
                continue
            ref = branch

        try:
            run_id = dispatch(wf, ref, extra)
        except Exception as e:
            print(f"[fail] {wf}: dispatch failed: {e}")
            results.append({"workflow": wf, "verdict": "DISPATCH_FAILED", "error": str(e)})
            if branch:
                sh(["bash", "-c", f"git push -q origin --delete '{branch}' || true"])
            continue

        print(f"[batch] {wf} -> run {run_id} on {ref} (runner={'self-hosted' if extra else 'self-hosted via branch'})",
              flush=True)
        state = wait_for_run(run_id, timeout_min)
        log = log_of(run_id)
        verdict, notes = classify(log)
        if state.get("conclusion") and state["conclusion"] != "success" and verdict == "CLEAN":
            verdict = "FAILED_NO_ERROR_TEXT"
        rec = {"workflow": wf, "run_id": run_id, "ref": ref,
               "conclusion": state.get("conclusion"), "verdict": verdict,
               "notes": notes, "at": datetime.now(timezone.utc).isoformat()}
        results.append(rec)
        REPORTS.mkdir(exist_ok=True)
        with LEDGER.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")

        # revert: the branch is deleted, so main never carries the pin
        if branch:
            sh(["bash", "-c", f"git checkout -q main 2>/dev/null || git checkout -q -B main origin/main; "
                              f"git push -q origin --delete '{branch}' || true"])
        print(f"[batch] {wf}: {rec['conclusion']} | {verdict} {notes}")

        if max_parallel <= 1:
            continue
    print("\n=== batch summary ===")
    for r in results:
        print(f"  {r['workflow']:<44} {r.get('conclusion') or '-':<10} {r['verdict']} {r.get('notes') or ''}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-w", "--workflow", action="append", help="workflow file (repeatable)")
    ap.add_argument("--list", action="store_true", help="show runners and runner-capable workflows")
    ap.add_argument("--runner-input", action="store_true",
                    help="force the -f runner=self-hosted path")
    ap.add_argument("--timeout-min", type=int, default=60)
    ap.add_argument("--max-parallel", type=int, default=1,
                    help="1 or 2; anything more violates the batch protocol")
    ap.add_argument("--runner", default=None,
                    help="force a runner by name or custom label (must be online+idle)")
    ap.add_argument("--wait-runner", type=int, default=600, metavar="SEC",
                    help="wait up to SEC for a suitable idle runner (default 600; 0 = fail fast)")
    args = ap.parse_args()

    if args.list or not args.workflow:
        list_capability()
        return 0
    if len(args.workflow) > 2:
        print("[warn] operator protocol is 1-2 workflows per batch; trimming to 2",
              file=sys.stderr)
        args.workflow = args.workflow[:2]
    return run_batch(args.workflow, args.runner_input, args.timeout_min,
                     args.max_parallel, args.runner, args.wait_runner)


if __name__ == "__main__":
    raise SystemExit(main())
