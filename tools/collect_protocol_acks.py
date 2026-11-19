#!/usr/bin/env python3
"""collect_protocol_acks.py — poll COMS for [ACK-v1] lines and accumulate them.

WHY: COMS is MQTT with qos1 and NOT retained. An agent that is asleep when a
message is published simply never receives it, so "collect confirmations" cannot
be a single send-and-wait. This collector polls my seat on a schedule, parses any
`[ACK-v1] key=value ...` line it finds, dedupes by seat, and rewrites a status
table so the answer to "who has confirmed?" is a file, not a memory.

Run from cron every 5 minutes. Safe to run repeatedly: state lives in
reports/protocol_v1_acks.jsonl and nothing is ever overwritten destructively.

Exit 0 always — a collector that fails loudly on every tick trains people to
ignore it.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

COMS = "/home/eaguiar2015/AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms"
SEAT_AGENT = "deepseek-v4-flash"
REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "reports" / "protocol_v1_acks.jsonl"
REPORT = REPO / "reports" / "PROTOCOL_V1_ACKS.md"

# The eight agents on the bus as briefed by the operator.
EXPECTED = [
    ("deepseek-flash (Linux)", "inbox/gx10-c9b9/review-main/deepseek-v4-flash"),
    ("Kilo — IDE extension", "inbox/gx10-c9b9/vanilla-handsaw/kilo"),
    ("Kilo — Linux CLI", "inbox/gx10-c9b9/findtorontoevents_antigravity-ca/kilo"),
    ("FreeBuff (Linux CLI)", "?"),
    ("GitHub Copilot (VS Code)", "inbox/gx10-c9b9/findtorontoevents_antigravity-ca/copilot-cli-moneyresearch"),
    ("Google Swarm (Linux CLI)", "?"),
    ("Hermes (Windows)", "?"),
    ("OpenCode (Windows)", "?"),
]

ACK_RE = re.compile(r"\[ACK-v1\](.*)", re.IGNORECASE)
KV_RE = re.compile(r"(\w+)\s*=\s*([^\s]+(?:\s(?!\w+=)[^\s]+)*)")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def poll() -> str:
    try:
        r = subprocess.run([COMS, "check", "--agent", SEAT_AGENT, "--wait", "5"],
                           capture_output=True, text=True, timeout=60)
        return r.stdout + r.stderr
    except Exception as exc:  # noqa: BLE001 - collector must never crash cron
        print(f"poll failed: {exc}", file=sys.stderr)
        return ""


def parse(raw: str) -> list[dict]:
    found = []
    for line in raw.splitlines():
        m = ACK_RE.search(line)
        if not m:
            continue
        body = m.group(1).strip()
        rec = {"ts": now(), "raw": body[:500]}
        for k, v in KV_RE.findall(body):
            rec[k.lower()] = v.strip().rstrip(",;")
        if "seat" in rec or "verdict" in rec:
            found.append(rec)
    return found


def load_existing() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    return out


def main() -> int:
    existing = load_existing()
    seen = {(r.get("seat"), r.get("verdict")) for r in existing}

    new = []
    for rec in parse(poll()):
        sig = (rec.get("seat"), rec.get("verdict"))
        if sig in seen:
            continue
        seen.add(sig)
        new.append(rec)

    if new:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a") as fh:
            for rec in new:
                fh.write(json.dumps(rec) + "\n")
        existing.extend(new)

    by_seat = {r.get("seat"): r for r in existing if r.get("seat")}
    lines = [
        "# Protocol v1 — confirmation status",
        "",
        f"Last poll: **{now()}** · collector: `tools/collect_protocol_acks.py`",
        "",
        "COMS is MQTT qos1 and **not retained**: an agent asleep at send time never",
        "receives the message. That is why this is a rolling poll, not a one-shot send.",
        "",
        "| Agent | Seat | Verdict | Worktree | Branch | Dirty | Backup |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, seat in EXPECTED:
        rec = by_seat.get(seat) or {}
        lines.append(
            f"| {name} | {seat} | {rec.get('verdict', '—')} | {rec.get('worktree', '—')} "
            f"| {rec.get('branch', '—')} | {rec.get('dirty', '—')} | {rec.get('backup', '—')} |"
        )
    unknown = [s for s in by_seat if s not in {seat for _, seat in EXPECTED}]
    if unknown:
        lines += ["", "## Additional seats heard from", ""]
        for s in unknown:
            lines.append(f"- `{s}` → {by_seat[s].get('verdict', '—')}")

    lines += [
        "",
        "## How to be counted",
        "",
        "```",
        "[ACK-v1] seat=<inbox path> worktree=<dir> branch=<branch> dirty=<n> "
        "backup=<refs/backup/... | none> verdict=CONFIRM | CHANGE:<clause>:<reason>",
        "```",
        "",
        "Reply to `inbox/gx10-c9b9/review-main/deepseek-v4-flash`. No seat? Run",
        "`COMS register --agent <name>` inside your own worktree first — a protocol you",
        "cannot receive is not a protocol.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")

    print(f"{now()} collected={len(new)} total={len(existing)} "
          f"seats={len(by_seat)}/{len(EXPECTED)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
