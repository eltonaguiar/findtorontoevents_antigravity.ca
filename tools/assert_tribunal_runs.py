#!/usr/bin/env python3
"""assert_tribunal_runs.py — a branch is not "verified" until a real ledger run exits 0.

WHY THIS EXISTS
---------------
On 2026-11-20 `hotfix/required-n-power` was recommended for merge on the strength of
`py_compile` (OK) and `--help` (exit 0). On the first real invocation it died:

    TypeError: build_report() got an unexpected keyword argument 'require_alpha'

`--help` exits *inside* `argparse`, before `main()` ever builds a report, so it cannot
detect a signature/contract mismatch, a missing kwarg, or a producer/consumer skew —
which is exactly the class of bug that reached a merge recommendation. `py_compile`
only proves the file is syntactically valid Python.

This tool runs the thing. It is the pre-push gate that must pass before any branch or
patch is called verified.

USAGE
-----
    # the tree you are standing in
    python3 tools/assert_tribunal_runs.py

    # any git ref, in a throwaway worktree (removed afterwards)
    python3 tools/assert_tribunal_runs.py --ref origin/main
    python3 tools/assert_tribunal_runs.py --ref hotfix/required-n-power --expect-fail

    # also demand the sleeve gate actually produced output
    python3 tools/assert_tribunal_runs.py --ref origin/main --require-sleeves

EXIT CODES
----------
0 = help parses AND a real run on real picks exits 0 AND the required keys are present
1 = any of the above fails (never call such a branch verified)
2 = could not run at all (missing picks file, no git repo, worktree refused)

`--expect-fail` inverts the verdict: it passes when the ref *does* fail, so a bug can
be pinned as a regression test instead of being argued about in prose.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:  # direct `python3 tools/assert_tribunal_runs.py`
    sys.path.insert(0, str(REPO_ROOT))

MODULE = "alpha_engine.audit3_tribunal"
# Keys a published audit3 ledger must carry. Not a schema test — a "did the producer
# actually reach the point of writing a report" test. Keep this list small; every key
# here is one whose silent disappearance would mislead a reader of the page.
REQUIRED_KEYS = ("schema", "generated_at", "summary", "coverage", "denylist_hits")
DEFAULT_PICKS = "audit_dashboard/data/dashboard_data.json"
PF_CEILING = 25.0


def _run(cmd: list[str], cwd: Path, timeout: int = 900) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"::timeout after {timeout}s:: {' '.join(cmd)}"


def check_tree(tree: Path, picks: Path, out: Path, require_sleeves: bool) -> tuple[bool, list[str]]:
    """Return (ok, log lines). Every line is stated as a fact, never a guess."""
    log: list[str] = []
    ok = True

    # 1. Cheap signal only. Explicitly NOT authoritative — this is the check that
    #    fooled me on 2026-11-20, so it is recorded but never decides the verdict.
    rc, txt = _run([sys.executable, "-m", MODULE, "--help"], tree, timeout=180)
    log.append(f"help            exit={rc}  (informational — argparse exits before main())")
    if rc != 0:
        log.append("  " + (txt.strip().splitlines() or ["<no output>"])[-1][:300])
        ok = False

    # 2. The check that actually matters: run it on real picks.
    cmd = [sys.executable, "-m", MODULE, "--picks", str(picks), "--out", str(out)]
    if require_sleeves:
        cmd += ["--sleeves", str(picks)]
    rc, txt = _run(cmd, tree)
    log.append(f"real run        exit={rc}  (authoritative)")
    if rc != 0:
        tail = [ln for ln in txt.strip().splitlines() if ln.strip()][-6:]
        for ln in tail:
            log.append("  " + ln[:300])
        return False, log

    # 3. Output must exist and be parseable.
    if not out.exists() or out.stat().st_size == 0:
        log.append(f"  FAIL no ledger written to {out}")
        return False, log
    try:
        doc = json.loads(out.read_text())
    except Exception as exc:  # noqa: BLE001 - any parse failure is a failure
        log.append(f"  FAIL ledger is not valid JSON: {type(exc).__name__}: {exc}")
        return False, log

    # 4. Keys that prove the producer reached the report, not just the entrypoint.
    missing = [k for k in REQUIRED_KEYS if k not in doc]
    if missing:
        log.append(f"  FAIL missing required keys: {missing}")
        ok = False
    summary = doc.get("summary") or {}
    log.append(
        f"ledger          schema={doc.get('schema')} n_rows={summary.get('n_rows')} "
        f"denylist_hits={doc.get('denylist_hits')} "
        f"verdict_churn={'yes' if 'verdict_churn' in doc else 'no'}"
    )
    if int(summary.get("n_rows") or 0) < 100:
        log.append(f"  FAIL n_rows={summary.get('n_rows')} — a thin ledger means the run did not see real input")
        ok = False

    # 5. Optional: the sleeve gate must have produced output and must not publish an
    #    implausible PF as rankable. A gate that runs but never fires is decoration.
    if require_sleeves:
        sleeves = doc.get("sleeves")
        if not isinstance(sleeves, list):
            log.append("  FAIL --require-sleeves: ledger has no 'sleeves' list")
            return False, log
        rankable = [s for s in sleeves if s.get("rankable")]
        bad = [s for s in rankable if float(s.get("pf") or 0) > PF_CEILING]
        log.append(
            f"sleeves         count={len(sleeves)} rankable={len(rankable)} "
            f"flagged={len(sleeves) - len(rankable)}"
        )
        if bad:
            names = ", ".join(str(s.get("strategy_name") or s.get("strategy"))[:40] for s in bad)
            log.append(f"  FAIL implausible PF published as rankable (>{PF_CEILING}): {names}")
            ok = False

    return ok, log


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the audit3 tribunal for real before trusting a branch")
    ap.add_argument("--ref", help="git ref to test in a throwaway worktree (default: this tree)")
    ap.add_argument("--picks", default=None,
                    help=f"closed-pick payload (default: <tree>/{DEFAULT_PICKS})")
    ap.add_argument("--require-sleeves", action="store_true",
                    help="also require a 'sleeves' list with no implausible-PF rankable sleeve")
    ap.add_argument("--expect-fail", action="store_true",
                    help="invert: pass when the ref fails (pin a known-broken branch)")
    args = ap.parse_args()

    wt: Path | None = None
    try:
        if args.ref:
            tmpdir = Path(tempfile.mkdtemp(prefix="tribunal_gate_"))
            wt = tmpdir / "wt"
            rc, txt = _run(["git", "worktree", "add", "--detach", "-f", str(wt), args.ref],
                           REPO_ROOT, timeout=300)
            if rc != 0:
                print(f"::error::could not create a worktree at {args.ref}\n{txt[-500:]}")
                return 2
            tree = wt
        else:
            tree = REPO_ROOT

        picks = Path(args.picks) if args.picks else (tree / DEFAULT_PICKS)
        if not picks.is_absolute():
            picks = (tree / picks).resolve()
        if not picks.exists():
            print(f"::error::picks payload not found: {picks}")
            print("  The gate must run on real input — a synthetic fixture cannot catch a "
                  "producer/consumer contract mismatch.")
            return 2

        out = Path(tempfile.mkdtemp(prefix="tribunal_out_")) / "ledger.json"
        label = args.ref or str(tree)
        print(f"assert_tribunal_runs: target={label}")
        print(f"                      picks={picks}")
        ok, log = check_tree(tree, picks, out, args.require_sleeves)
        for line in log:
            print("  " + line if not line.startswith("  ") else line)

        verdict = "PASS" if ok else "FAIL"
        want = "FAIL" if args.expect_fail else "PASS"
        print(f"verdict: {verdict} (expected {want})")
        if verdict != want:
            if args.expect_fail:
                print("::error::expected this ref to fail, but it ran clean — update the pin")
            else:
                print("::error::do NOT call this branch verified; it does not run")
            return 1
        return 0
    finally:
        if wt is not None:
            _run(["git", "worktree", "remove", "--force", str(wt)], REPO_ROOT, timeout=300)
            _run(["git", "worktree", "prune"], REPO_ROOT, timeout=120)
            shutil.rmtree(wt.parent, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
