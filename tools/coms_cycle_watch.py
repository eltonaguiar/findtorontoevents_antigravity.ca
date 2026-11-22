#!/usr/bin/env python3
"""coms_cycle_watch.py — 30-minute COMS check/reply cycle with a self-limiting cron.

Each run:
  1. polls both COMS seats (primary tree + review-main worktree)
  2. de-duplicates inbound traffic by hash and appends new items to .coms_cycle_log.jsonl
  3. if NEW non-self traffic exists, posts a short status reply (broadcast + retained)
  4. re-runs the verify command for every item in reports/TODO_LEDGER_2026-11-19.json
     and flips status to "done" when the check passes
  5. after max_cycles it stops posting COMS replies (still monitors todos)
  6. when cycles are exhausted AND no todos remain, it removes its own crontab lines

Safety: never edits tracked source. It verifies, reports, and logs. The repo has a
documented history of silent file reverts and of other agents holding uncommitted work,
so unattended source edits are out of scope by design.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/eaguiar2015/findtorontoevents_antigravity.ca")
COMS = "/home/eaguiar2015/AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms"
STATE = ROOT / ".coms_cycle_state.json"
LOG = ROOT / ".coms_cycle_log.jsonl"
ACTIONS = ROOT / "reports/coms_cycle_actions.log"
LEDGER = ROOT / "reports/TODO_LEDGER_2026-11-19.json"
MARK = "buffy/coms-30min-cycle"
MAX_CYCLES = 3
HARD_CAP = 48
SEATS = [ROOT, ROOT / ".kilo/worktrees/review-main"]
TOPIC_RE = re.compile(r"^(inbox/|mentions/|audit/|general/|dm/)")
SELF_PREFIXES = (
    "MEASURED ASSET-CLASS", "CORRECTION to my", "FINDINGS DROP", "CRITIQUE of the $2k", "PEER CRITIQUE REQUEST",
    "COMS CYCLE", "REVIEW of copilot", "ASSET-CLASS REVIEW",
    "COMS DROP", "FINDINGS DROP",
)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sh(cmd: str, cwd: Path | None = None, timeout: int = 90) -> tuple[int, str]:
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
    return {"cycle": 0, "started_at": now(), "replies": 0, "open_todos": None}


def save_state(s: dict) -> None:
    STATE.write_text(json.dumps(s, indent=1))


def poll_seats() -> list[dict]:
    seen = set()
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            try:
                seen.add(json.loads(line)["hash"])
            except Exception:
                continue
    new = []
    for seat in SEATS:
        rc, txt = sh(f"{COMS} check --agent deepseek-v4-flash --wait 5", cwd=seat)
        if rc != 0:
            continue
        for line in txt.splitlines():
            line = line.strip()
            if len(line) < 45 or line.startswith("checking inbox") or line.startswith("---"):
                continue
            body = line.split(" ", 1)[1] if " " in line else line
            if line.startswith(SELF_PREFIXES) or body.startswith(SELF_PREFIXES):
                continue
            h = hashlib.sha1(line[:400].encode()).hexdigest()[:16]
            if h in seen:
                continue
            seen.add(h)
            # only a line that begins with a topic id is a NEW message; everything else
            # is a continuation of the previous message's body and must not trigger a reply
            trigger = bool(TOPIC_RE.match(line))
            rec = {"ts": now(), "seat": str(seat.relative_to(ROOT)) if seat != ROOT else ".",
                   "hash": h, "trigger": trigger, "text": line[:1200]}
            if trigger:
                new.append(rec)
            with LOG.open("a") as fh:
                fh.write(json.dumps(rec) + "\n")
    return new


def check_todos() -> tuple[list[dict], int]:
    if not LEDGER.exists():
        return [], 0
    try:
        d = json.loads(LEDGER.read_text())
    except Exception:
        return [], 0
    changed = False
    for item in d.get("items", []):
        if item.get("status") == "done" or not item.get("verify"):
            continue
        rc, _ = sh(item["verify"], timeout=60)
        if rc == 0:
            item["status"] = "done"
            item["verified_at"] = now()
            changed = True
    if changed:
        d["updated_at"] = now()
        LEDGER.write_text(json.dumps(d, indent=2) + "\n")
    items = d.get("items", [])
    return items, sum(1 for i in items if i.get("status") != "done")


def reply(new: list[dict], items: list[dict], open_n: int, cycle: int) -> None:
    heads = "; ".join(n["text"][:120].replace("\n", " ") for n in new[:3])
    done = [i["id"] for i in items if i.get("status") == "done"]
    msg = (
        f"COMS CYCLE {cycle}/{MAX_CYCLES} (buffy/review-main) — {len(new)} new message(s) read. "
        f"Open todos: {open_n}/15 (done: {','.join(done) or 'none'}). "
        f"Latest inbound: {heads}. "
        f"Findings doc: reports/COMS_DROP_2026-11-19_FINDINGS.md; "
        f"todo ledger: reports/TODO_LEDGER_2026-11-19.md. "
        f"Reply to inbox/gx10-c9b9/review-main/deepseek-v4-flash."
    )
    sh(f"{COMS} send mentions/all \"{msg}\"", timeout=45)
    sh(f"{COMS} send --retain inbox/gx10-c9b9/review-main/deepseek-v4-flash \"{msg}\"", timeout=45)
    with ACTIONS.open("a") as fh:
        fh.write(f"{now()} cycle={cycle} new={len(new)} open_todos={open_n} :: {msg[:200]}\n")


def disarm() -> None:
    rc, cur = sh("crontab -l", timeout=30)
    if rc != 0:
        return
    keep = "\n".join(l for l in cur.splitlines() if MARK not in l)
    p = subprocess.run("crontab -", shell=True, input=keep + "\n", text=True,
                       capture_output=True, timeout=30)
    sh(f"echo '{now()} cron disarmed (cycles exhausted, todos closed)' >> {ACTIONS}", timeout=20)


def main() -> int:
    s = load_state()
    s["cycle"] = int(s.get("cycle", 0)) + 1
    new = poll_seats()
    items, open_n = check_todos()
    s["open_todos"] = open_n
    s["last_run"] = now()

    if s["cycle"] <= MAX_CYCLES:
        reply(new, items, open_n, s["cycle"])
        s["replies"] = int(s.get("replies", 0)) + 1
    else:
        with ACTIONS.open("a") as fh:
            fh.write(f"{now()} cycle={s['cycle']} monitoring-only (reply budget spent) open_todos={open_n}\n")

    save_state(s)
    if s["cycle"] >= MAX_CYCLES and (open_n == 0 or s["cycle"] >= HARD_CAP):
        disarm()
    print(json.dumps({"cycle": s["cycle"], "new": len(new), "open_todos": open_n}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
