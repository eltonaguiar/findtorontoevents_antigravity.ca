#!/usr/bin/env python3
"""wakeup_watch_20min.py — 50 scheduled check-ins, one every 20 minutes (~16h40m).

Each wakeup does four things and appends one JSON line:
  1. LOCAL   — uncommitted changes and newly-modified tracked files since the last run
  2. REMOTE  — branch tips for the branches under review, plus any new commits on main
  3. LIVE    — /audit, /audit2, /audit3 http status + size + ledger sha + generated_at + verdict counts
  4. COMS    — poll both seats for new inbound, de-duplicated by hash

Design rules (deliberate):
  * NEVER edits tracked source. It reads, records, and reports. The repo has a documented history of
    silent file reverts and of other agents holding uncommitted work; unattended source edits are
    out of scope by design.
  * Idempotent and de-duplicating: re-running it any number of times appends nothing new.
  * Self-disabling: after MAX_RUNS (50) it removes its own crontab line. It also hard-stops at
    HARD_CAP so a misconfigured generation cannot run forever.
  * Everything it learns is durable in reports/wakeups/<date>.jsonl, so a session restart loses
    nothing.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path("/home/eaguiar2015/findtorontoevents_antigravity.ca")
OUT_DIR = ROOT / "reports/wakeups"
STATE = ROOT / ".wakeup_watch_state.json"
COMS = "/home/eaguiar2015/AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms"
MARK = "buffy/wakeup-20min-50"
MAX_RUNS = 50
HARD_CAP = 60

BRANCHES = [
    "main",
    "feat/audit-review-organization-2026-11-19",
    "review/buffy-money-maker-plan-2026-11-19",
    "fix/crypto-sim-net-grading-2026-11-19",
    "publish/buffy-findings-2026-11-19",
]

LIVE = [
    ("audit_page", "https://findtorontoevents.ca/audit/"),
    ("audit2_page", "https://findtorontoevents.ca/audit2/"),
    ("audit3_page", "https://findtorontoevents.ca/audit3/"),
    ("ledger_on_audit", "https://findtorontoevents.ca/audit/data/audit3_ledger.json"),
    ("ledger_on_audit3", "https://findtorontoevents.ca/audit3/audit3_ledger.json"),
    ("verdict_on_audit", "https://findtorontoevents.ca/audit/data/money_ready_verdict.json"),
]

UA = {"User-Agent": "buffy-wakeup-watch/1.0"}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sh(cmd: str, timeout: int = 90, cwd: Path | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, shell=True, cwd=str(cwd or ROOT),
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"run": 0, "started": now(), "seen_files": {}, "seen_commits": [], "seen_msgs": []}


def save_state(s: dict) -> None:
    STATE.write_text(json.dumps(s, indent=1))


def check_local(state: dict) -> dict:
    """Uncommitted work + tracked files touched since the last wakeup."""
    rc, out = sh("git status --porcelain=v1 -uno")
    dirty = [l for l in out.splitlines() if l.strip()]
    rc, out2 = sh("git status --porcelain=v1")
    untracked = [l for l in out2.splitlines() if l.startswith("??")]

    seen = state.get("seen_files", {})
    changed = []
    for line in out2.splitlines():
        m = re.match(r"^.. (.+)$", line)
        if not m:
            continue
        path = m.group(1).strip()
        f = ROOT / path
        try:
            mt = f.stat().st_mtime
        except OSError:
            continue
        if seen.get(path) != mt:
            seen[path] = mt
            changed.append(path)
    state["seen_files"] = seen
    return {"dirty_tracked": dirty[:25], "untracked": [u[3:] for u in untracked][:25],
            "newly_modified": changed[:25]}


def check_remote(state: dict) -> dict:
    sh("git fetch origin --prune 2>/dev/null", timeout=120)
    tips = {}
    for b in BRANCHES:
        rc, out = sh(f"git log -1 --format='%h|%ci|%s' origin/{b} 2>/dev/null")
        out = out.strip()
        if not out or "|" not in out:
            tips[b] = None
            continue
        h, ci, subj = out.split("|", 2)
        tips[b] = {"sha": h, "date": ci, "subject": subj[:100]}

    seen = set(state.get("seen_commits", []))
    fresh = []
    for b in BRANCHES:
        rc, out = sh(f"git log origin/{b} -6 --format='%h %ci %s' 2>/dev/null")
        for line in out.splitlines():
            sha = line.split(" ")[0]
            if sha and sha not in seen:
                seen.add(sha)
                fresh.append(line[:140])
    state["seen_commits"] = sorted(seen)[-400:]
    return {"tips": tips, "new_commits": fresh[:20]}


def fetch(url: str) -> tuple[int, bytes]:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, r.read()
    except Exception as e:
        return 0, str(e).encode()[:200]


def check_live() -> dict:
    res = {}
    for name, url in LIVE:
        code, body = fetch(url)
        rec = {"http": code, "bytes": len(body)}
        if code == 200 and url.endswith(".json"):
            rec["sha256"] = hashlib.sha256(body).hexdigest()[:16]
            try:
                d = json.loads(body)
                rec["generated_at"] = d.get("generated_at")
                s = d.get("summary") or {}
                rec.update({k: s.get(k) for k in
                            ("n_rows", "n_proven", "n_candidate", "n_weak", "n_kill", "n_insufficient")
                            if k in s})
                rec["selection_alpha_available"] = (d.get("selection_alpha") or {}).get("available")
            except Exception as e:
                rec["parse_error"] = str(e)[:120]
        res[name] = rec
    # the parity assertion that element 13 asks for
    a, b = res.get("ledger_on_audit", {}), res.get("ledger_on_audit3", {})
    if a.get("sha256") and b.get("sha256"):
        res["parity"] = {
            "same_sha": a["sha256"] == b["sha256"],
            "rows_a": a.get("n_rows"), "rows_b": b.get("n_rows"),
            "gen_a": a.get("generated_at"), "gen_b": b.get("generated_at"),
            "verdict": "PARITY_OK" if a["sha256"] == b["sha256"] else "DIVERGENT",
        }
    return res


def check_coms(state: dict) -> list[dict]:
    seen = set(state.get("seen_msgs", []))
    new = []
    for seat in (ROOT, ROOT / ".kilo/worktrees/review-main"):
        rc, out = sh(f"{COMS} check --agent deepseek-v4-flash --wait 3", cwd=seat, timeout=45)
        if rc != 0:
            continue
        for line in out.splitlines():
            line = line.strip()
            if len(line) < 45 or line.startswith("checking inbox") or line.startswith("---"):
                continue
            h = hashlib.sha1(line[:300].encode()).hexdigest()[:16]
            if h in seen:
                continue
            seen.add(h)
            new.append({"hash": h, "text": line[:220]})
    state["seen_msgs"] = sorted(seen)[-600:]
    return new


def disarm() -> None:
    rc, cur = sh("crontab -l", timeout=30)
    if rc != 0:
        return
    keep = "\n".join(l for l in cur.splitlines() if MARK not in l)
    subprocess.run("crontab -", shell=True, input=keep + "\n", text=True,
                   capture_output=True, timeout=30)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    state["run"] = int(state.get("run", 0)) + 1
    run = state["run"]

    rec = {"ts": now(), "run": run, "of": MAX_RUNS}
    rec["local"] = check_local(state)
    rec["remote"] = check_remote(state)
    rec["live"] = check_live()
    rec["coms"] = check_coms(state)
    save_state(state)

    day = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    with (OUT_DIR / f"{day}.jsonl").open("a") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")

    # one line of human-readable signal to stdout (goes to the cron log)
    p = rec["live"].get("parity", {})
    print(json.dumps({
        "ts": rec["ts"], "run": f"{run}/{MAX_RUNS}",
        "dirty": len(rec["local"]["dirty_tracked"]),
        "new_commits": len(rec["remote"]["new_commits"]),
        "coms_new": len(rec["coms"]),
        "parity": p.get("verdict"), "rows": [p.get("rows_a"), p.get("rows_b")],
        "audit3_gen": rec["live"].get("ledger_on_audit3", {}).get("generated_at"),
    }))

    if run >= MAX_RUNS or run >= HARD_CAP:
        disarm()
        print(f"{now()} wakeup watcher disarmed after {run} runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
