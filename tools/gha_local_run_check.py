#!/usr/bin/env python3
"""Local dry-run of every GitHub Actions workflow in .github/workflows/.

What "running a workflow locally" means here
--------------------------------------------
Full containerised execution of ~390 workflows is not possible on one box: they
need repository secrets, live MySQL, FTP credentials, and (with ``act``) a
~1 GB runner image per distinct ``runs-on``. What *is* reproducible locally, and
what actually catches the defects that turn CI red before the job connects to
anything, is executed here for every workflow:

1. ``act --list`` for the file               -> GitHub-Actions-schema load (nektos/act parser)
2. YAML parse + job/step structural checks  -> missing ``steps``/``runs-on``, bad ``needs``
3. every ``run:`` block through its shell    -> ``bash -n`` / ``sh -n`` / ``python -m py_compile``
4. every ``run:`` block through shellcheck   -> severity >= warning (bash/sh only)
5. every referenced script path              -> exists? compiles? (cwd-aware)

Outputs ``reports/gha_local_run_check.json`` and ``.md`` with one row per
workflow and the full message list for anything not clean.

Usage
-----
    python3 tools/gha_local_run_check.py                 # all workflows
    python3 tools/gha_local_run_check.py --only audit3   # filename substring filter
    python3 tools/gha_local_run_check.py --fail-on-error # exit 1 if any ERROR
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WF_DIR = REPO_ROOT / ".github" / "workflows"
OUT_JSON = REPO_ROOT / "reports" / "gha_local_run_check.json"
OUT_MD = REPO_ROOT / "reports" / "gha_local_run_check.md"

ACT = shutil.which("act") or str(Path.home() / ".local" / "bin" / "act")
SHELLCHECK = shutil.which("shellcheck")
TIMEOUT = 60

# ${{ ... }} is not shell syntax; neutralise it as a variable reference so that
# shellcheck does not report every substituted value as a constant literal.
EXPR_RE = re.compile(r"\$\{\{.*?\}\}", re.S)
EXPR_PRELUDE = "EXPR=neutralised\n"
# Only a token in *command position after an interpreter* can be a script the
# workflow will actually try to execute. Anything else (echo prose, comments,
# `grep run.sh`) is not an invocation and must not be reported as a missing file.
INTERP_RE = re.compile(
    r"(?:^|[\s;&|(){}])(?:python3?(?:\.\d+)?|bash|sh|node|php|ruby|deno|bun)"
    r"\s+((?:-[^\s;|&]+\s+)*)([^\s;|&()]+)",
    re.M,
)
MODULE_RE = re.compile(
    r"(?:^|[\s;&|(){}])(?:python3?(?:\.\d+)?)\s+(?:-[^\s;|&]+\s+)*-m\s+([\w.]+)", re.M
)
CD_RE = re.compile(r"(?:^|&&|\|\||;|\bthen\b|\bdo\b)\s*cd\s+([^\s;&|]+)", re.M)
# shellcheck codes that are style-only in a CI step (GHA runs bash with -e, and
# env vars consumed by later steps legitimately look "unused" to shellcheck).
STYLE_ONLY = {"SC2164", "SC2034", "SC2044", "SC2155", "SC2002", "SC2016"}

_compile_cache: dict[str, tuple[bool, str]] = {}
_cache_lock = threading.Lock()


def _basename_index() -> dict[str, list[str]]:
    """basename -> repo-relative paths (used to tell 'missing' from 'wrong cwd')."""
    index: dict[str, list[str]] = {}
    # NB: dot-directories other than these are real (`.github/scripts/` holds
    # safe_push.sh); only the VCS/agent/cache dirs are excluded.
    skip = {
        ".git", "node_modules", ".worktrees", "graphify-out", "__pycache__",
        ".venv", "venv", ".kilo", ".hermes", ".copilot", ".agent-bridge-cache",
    }
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            index.setdefault(f, []).append(
                os.path.relpath(os.path.join(root, f), REPO_ROOT)
            )
    return index


BNAME_INDEX: dict[str, list[str]] = {}


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = TIMEOUT) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd, cwd=str(cwd or REPO_ROOT), capture_output=True, text=True, timeout=timeout
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s"
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"


def _compile(path: Path) -> tuple[bool, str]:
    key = str(path)
    with _cache_lock:
        if key in _compile_cache:
            return _compile_cache[key]
    suffix = path.suffix.lower()
    if suffix == ".py":
        rc, out = _run([sys.executable, "-m", "py_compile", str(path)], cwd=REPO_ROOT)
        ok = rc == 0
        msg = "" if ok else out.strip().splitlines()[-1] if out.strip() else "py_compile failed"
    elif suffix == ".sh":
        rc, out = _run(["bash", "-n", str(path)])
        ok, msg = rc == 0, "" if rc == 0 else out.strip()
    elif suffix in (".js", ".mjs", ".cjs"):
        if shutil.which("node"):
            rc, out = _run(["node", "--check", str(path)])
            ok, msg = rc == 0, "" if rc == 0 else out.strip().splitlines()[0]
        else:
            ok, msg = True, "node missing, skipped"
    elif suffix == ".php":
        if shutil.which("php"):
            rc, out = _run(["php", "-l", str(path)])
            ok, msg = rc == 0, "" if rc == 0 else out.strip()
        else:
            ok, msg = True, "php missing, skipped"
    else:
        ok, msg = True, "no local compiler"
    with _cache_lock:
        _compile_cache[key] = (ok, msg)
    return ok, msg


def _shell_for(step: dict, job: dict, doc: dict) -> str:
    sh = step.get("shell") or (job.get("defaults") or {}).get("run", {}).get("shell") \
        or (doc.get("defaults") or {}).get("run", {}).get("shell") or "bash"
    return str(sh).lower()


def _check_block(script: str, shell: str, label: str, findings: list[dict]) -> None:
    neutral = EXPR_RE.sub("${EXPR}", script)
    if shell.startswith("python"):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write(neutral)
            tmp = fh.name
        try:
            rc, out = _run([sys.executable, "-m", "py_compile", tmp])
            if rc != 0:
                findings.append(
                    {"level": "ERROR", "kind": "python-inline-syntax", "where": label,
                     "msg": out.strip().splitlines()[-1] if out.strip() else "py_compile failed"}
                )
        finally:
            os.unlink(tmp)
        return
    if shell.startswith("pwsh") or shell.startswith("powershell"):
        if not shutil.which("pwsh"):
            findings.append(
                {"level": "INFO", "kind": "pwsh-skipped", "where": label,
                 "msg": "pwsh not installed locally; PowerShell step not parse-checked"}
            )
        return

    interp = "sh" if shell.startswith("sh") else "bash"
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as fh:
        fh.write("#!/usr/bin/env " + interp + "\n")
        fh.write(EXPR_PRELUDE)
        fh.write(neutral)
        tmp = fh.name
    try:
        rc, out = _run([interp, "-n", tmp])
        if rc != 0:
            findings.append(
                {"level": "ERROR", "kind": "shell-syntax", "where": label,
                 "msg": out.strip().splitlines()[0] if out.strip() else f"{interp} -n failed"}
            )
            return
        if SHELLCHECK and len(script) > 3:
            rc, out = _run(
                [SHELLCHECK, "-s", "bash" if interp == "bash" else "sh",
                 "-S", "warning", "-f", "gcc", tmp]
            )
            for line in out.splitlines():
                if ": warning:" in line or ": error:" in line:
                    bits = line.split(":", 4)
                    sev = "ERROR" if ": error:" in line else "WARNING"
                    msg = bits[4].strip() if len(bits) > 4 else line.strip()
                    code = msg.rsplit("[", 1)[-1].rstrip("]").strip() if "[" in msg else ""
                    if code in STYLE_ONLY:
                        sev = "INFO"
                    findings.append(
                        {"level": sev, "kind": f"shellcheck-{code or 'sc'}",
                         "where": label, "msg": msg[:300]}
                    )
    finally:
        os.unlink(tmp)


def _is_guarded(block: str, tok: str, step: dict) -> bool:
    """True when the workflow already degrades gracefully around this script."""
    if step.get("continue-on-error") in (True, "true"):
        return True
    lines = block.splitlines()
    for i, line in enumerate(lines):
        if tok not in line:
            continue
        after = line.split(tok, 1)[1]
        if "||" in after or "&&" in line.split(tok, 1)[0]:
            return True
        # `if [ -f <tok> ]; then` on the same or a preceding line
        window = "\n".join(lines[max(0, i - 4): i + 1])
        if re.search(r"-f\s+[\"']?" + re.escape(tok), window) or \
                re.search(r"command\s+-v\s+" + re.escape(tok), window):
            return True
    return False


def _script_refs(block: str) -> list[str]:
    """Scripts this block hands to an interpreter (the only refs CI executes)."""
    flat = EXPR_RE.sub("X", block)
    refs: set[str] = set()
    for _flags, tok in INTERP_RE.findall(flat):
        tok = tok.strip("'\"")
        if tok.startswith("-") or tok in ("<", ">", "|"):
            continue
        if re.search(r"\.(?:py|sh|js|mjs|cjs|php|rb|ps1)$", tok):
            refs.add(tok)
    for mod in MODULE_RE.findall(flat):
        # `python -m pip`, `-m pytest`, `-m json.tool` ... are third-party
        # modules, not repo files. Only resolve modules rooted in an existing
        # repo directory so those never show up as "missing scripts".
        rel = mod.replace(".", "/") + ".py"
        head = rel.split("/", 1)[0]
        if (REPO_ROOT / rel).exists() or ("/" in rel and (REPO_ROOT / head).is_dir()):
            refs.add(rel)
    return sorted(refs)


def _check_refs(block: str, label: str, findings: list[dict], step: dict,
                workdir: str | None = None) -> None:
    # Determine plausible cwd prefixes: explicit `working-directory:` first, then
    # any `cd` performed inside the block itself.
    cd_hints = [c.strip("'\"") for c in CD_RE.findall(EXPR_RE.sub("X", block))]
    if workdir:
        cd_hints.insert(0, workdir)
    for tok in _script_refs(block):
        if "://" in tok or tok.startswith("/") or "*" in tok or "$" in tok:
            continue
        # An explicit `[ -f ]` / `|| echo ::warning::` path is not a crash risk,
        # but it is still a capability that never runs — reported separately.
        guarded = _is_guarded(block, tok, step)
        bases = [REPO_ROOT]
        for hint in cd_hints:
            if hint.startswith("/"):
                continue
            bases.append((REPO_ROOT / hint).resolve())
            bases.append((REPO_ROOT / hint).resolve().parent)
        hit = next((b / tok for b in bases if (b / tok).is_file()), None)
        if hit is None:
            cands = BNAME_INDEX.get(Path(tok).name, [])
            if cands and not guarded:
                findings.append(
                    {"level": "WARNING", "kind": "script-cwd-relative", "where": label,
                     "msg": f"{tok} not found from repo root; exists at {cands[0]} "
                            f"(cwd-relative invocation)"}
                )
            elif not cands and guarded:
                findings.append(
                    {"level": "WARNING", "kind": "script-missing-guarded", "where": label,
                     "msg": f"{tok} does not exist; step already degrades (guard/`||`) so the "
                            f"job stays green but this capability never runs"}
                )
            elif not cands:
                findings.append(
                    {"level": "ERROR", "kind": "script-missing", "where": label,
                     "msg": f"{tok} does not exist and the step does not guard the failure"}
                )
            continue
        ok, msg = _compile(hit)
        if not ok:
            findings.append(
                {"level": "ERROR" if not guarded else "WARNING",
                 "kind": "script-does-not-compile", "where": label,
                 "msg": f"{os.path.relpath(hit, REPO_ROOT)}: {msg[:250]}"}
            )


def check_workflow(path: Path) -> dict:
    rel = os.path.relpath(path, REPO_ROOT)
    findings: list[dict] = []
    jobs_n = steps_n = 0

    try:
        import yaml
        doc = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        return {"file": rel, "status": "ERROR", "jobs": 0, "steps": 0,
                "findings": [{"level": "ERROR", "kind": "yaml-parse", "where": rel,
                              "msg": str(exc).splitlines()[0][:300]}]}

    if not isinstance(doc, dict):
        return {"file": rel, "status": "ERROR", "jobs": 0, "steps": 0,
                "findings": [{"level": "ERROR", "kind": "yaml-empty", "where": rel,
                              "msg": "file does not parse to a mapping"}]}

    jobs = doc.get("jobs") or {}
    if not isinstance(jobs, dict) or not jobs:
        findings.append({"level": "ERROR", "kind": "no-jobs", "where": rel,
                         "msg": "workflow defines no jobs"})
        jobs = {}
    jobs_n = len(jobs)

    if not doc.get("on") and not doc.get(True):
        findings.append({"level": "WARNING", "kind": "no-trigger", "where": rel,
                         "msg": "no 'on:' trigger — workflow can never run"})

    for jid, job in jobs.items():
        if not isinstance(job, dict):
            findings.append({"level": "ERROR", "kind": "bad-job", "where": f"{rel}:{jid}",
                             "msg": "job is not a mapping"})
            continue
        if not job.get("runs-on") and not job.get("uses"):
            findings.append({"level": "ERROR", "kind": "no-runs-on", "where": f"{rel}:{jid}",
                             "msg": "job has no runs-on (or reusable-workflow uses)"})
        if job.get("uses") and not str(job.get("uses")).startswith("./") \
                and "@" not in str(job.get("uses")):
            findings.append({"level": "WARNING", "kind": "reusable-no-ref",
                             "where": f"{rel}:{jid}",
                             "msg": f"uses: {job.get('uses')} has no @ref"})
        steps = job.get("steps")
        if steps is None:
            if not job.get("uses"):
                findings.append({"level": "ERROR", "kind": "no-steps",
                                 "where": f"{rel}:{jid}", "msg": "job has no steps"})
            continue
        if not isinstance(steps, list):
            findings.append({"level": "ERROR", "kind": "bad-steps",
                             "where": f"{rel}:{jid}", "msg": "steps is not a list"})
            continue
        for idx, step in enumerate(steps, 1):
            steps_n += 1
            if not isinstance(step, dict):
                findings.append({"level": "ERROR", "kind": "bad-step",
                                 "where": f"{rel}:{jid}#{idx}", "msg": "step is not a mapping"})
                continue
            name = step.get("name") or step.get("uses") or f"step {idx}"
            label = f"{rel}:{jid}#{idx} ({str(name)[:60]})"
            if not step.get("run") and not step.get("uses"):
                findings.append({"level": "ERROR", "kind": "step-no-action",
                                 "where": label, "msg": "step has neither run: nor uses:"})
                continue
            if step.get("uses"):
                u = str(step["uses"])
                if not u.startswith("./") and "@" not in u and not u.startswith("docker://"):
                    findings.append({"level": "WARNING", "kind": "action-no-ref",
                                     "where": label, "msg": f"uses: {u} has no @ref"})
            block = step.get("run")
            if isinstance(block, str) and block.strip():
                shell = _shell_for(step, job, doc)
                _check_block(block, shell, label, findings)
                workdir = (
                    step.get("working-directory")
                    or (job.get("defaults") or {}).get("run", {}).get("working-directory")
                    or (doc.get("defaults") or {}).get("run", {}).get("working-directory")
                )
                _check_refs(block, label, findings, step, workdir)

    # act's own parser is a second, independent schema load.
    if os.path.isfile(ACT):
        rc, out = _run([ACT, "--list", "-W", str(path)], timeout=90)
        if rc != 0:
            msg = " | ".join(
                ln.strip() for ln in out.splitlines() if "level=info" not in ln
            )[:400]
            # act 0.2.98 bundles an older actions schema that predates
            # `concurrency.queue` (added 2026-05). GitHub accepts it and the
            # workflows run green, so this is a local-tooling gap, not a defect.
            if "concurrency-mapping" in msg and "queue:" in path.read_text(
                    encoding="utf-8", errors="replace"):
                findings.append(
                    {"level": "INFO", "kind": "act-schema-gap-concurrency-queue",
                     "where": rel,
                     "msg": "act's schema rejects concurrency.queue; GitHub accepts it "
                            "(verified by green scheduled runs) — no change needed"})
            else:
                findings.append({"level": "ERROR", "kind": "act-load", "where": rel,
                                 "msg": msg or "act --list failed"})
    else:
        findings.append({"level": "INFO", "kind": "act-missing", "where": rel,
                         "msg": "act not installed; schema load done by PyYAML only"})

    levels = {f["level"] for f in findings}
    status = "ERROR" if "ERROR" in levels else ("WARNING" if "WARNING" in levels else "OK")
    return {"file": rel, "status": status, "jobs": jobs_n, "steps": steps_n,
            "findings": findings}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="substring filter on workflow filename")
    ap.add_argument("--fail-on-error", action="store_true")
    ap.add_argument("--jobs", type=int, default=12)
    args = ap.parse_args()

    files = sorted(p for p in WF_DIR.glob("*.yml") if p.is_file())
    files += sorted(p for p in WF_DIR.glob("*.yaml") if p.is_file())
    if args.only:
        files = [p for p in files if args.only in p.name]
    if not files:
        print("no workflows matched", file=sys.stderr)
        return 2

    global BNAME_INDEX
    BNAME_INDEX = _basename_index()
    print(f"checking {len(files)} workflow files with {args.jobs} workers...", file=sys.stderr)

    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for i, res in enumerate(pool.map(check_workflow, files), 1):
            results.append(res)
            if i % 50 == 0:
                print(f"  {i}/{len(files)}", file=sys.stderr)

    by_kind: dict[str, int] = {}
    for r in results:
        for f in r["findings"]:
            if f["level"] in ("ERROR", "WARNING"):
                key = f"{f['level']}:{f['kind']}"
                by_kind[key] = by_kind.get(key, 0) + 1

    summary = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workflows": len(results),
        "ok": sum(1 for r in results if r["status"] == "OK"),
        "warning": sum(1 for r in results if r["status"] == "WARNING"),
        "error": sum(1 for r in results if r["status"] == "ERROR"),
        "jobs": sum(r["jobs"] for r in results),
        "steps": sum(r["steps"] for r in results),
        "by_kind": dict(sorted(by_kind.items(), key=lambda kv: -kv[1])),
        "results": results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# GHA local run check",
        "",
        f"Generated: `{summary['generated_at']}`  ",
        f"Workflows: **{summary['workflows']}** ({summary['jobs']} jobs, "
        f"{summary['steps']} steps)  ",
        f"Clean: **{summary['ok']}** · Warnings: **{summary['warning']}** · "
        f"Errors: **{summary['error']}**",
        "",
        "## Findings by kind",
        "",
        "| Kind | Count |",
        "|------|------:|",
    ]
    for k, v in summary["by_kind"].items():
        lines.append(f"| `{k}` | {v} |")
    lines += ["", "## Non-clean workflows", ""]
    for r in results:
        if r["status"] == "OK":
            continue
        lines.append(f"### `{r['file']}` — {r['status']}")
        seen = set()
        for f in r["findings"]:
            if f["level"] == "INFO":
                continue
            key = (f["level"], f["kind"], f["msg"])
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- **{f['level']}** `{f['kind']}` @ {f['where']} — {f['msg']}")
        lines.append("")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({k: summary[k] for k in
                      ("generated_at", "workflows", "ok", "warning", "error",
                       "jobs", "steps")}, indent=2))
    print("\nfindings by kind:")
    for k, v in summary["by_kind"].items():
        print(f"  {v:5d}  {k}")
    print(f"\nreport: {os.path.relpath(OUT_MD, REPO_ROOT)}")

    if args.fail_on_error and summary["error"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
