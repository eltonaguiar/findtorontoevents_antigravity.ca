"""
Wakeup harness for an unfinished todo list.

WHY THIS EXISTS
---------------
A todo list that lives only in a conversation is a todo list that gets dropped. It happened
once already this session: 13 todos were written, announced, and then nothing ran. This
script makes "am I done" a checkable fact rather than a feeling, so a cron job, a heartbeat,
or the next agent cannot quietly conclude there was nothing to do.

Exit codes (deliberate, so cron can act on them):
    0  all todos done
    1  work remains        <- a cron job should re-invoke the worker
    2  state file missing  <- recreating beats silently passing

Usage:
    python3 tools/todo_wakeup.py            # report + exit code
    python3 tools/todo_wakeup.py --prompt   # emit the resume prompt for a fresh agent
    python3 tools/todo_wakeup.py --done 3   # mark todo 3 complete
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "TODOS_ACTIVE.json"

RESUME = """You have an unfinished todo list at TODOS_ACTIVE.json in
/home/eaguiar2015/findtorontoevents_antigravity.ca.

RULE: you are NOT authorized to stop until every todo status is "done".
Work in blocks; commit each block before starting the next.

Open items:
{items}

Blocked items must be reported as BLOCKED with the specific missing access,
never silently dropped and never marked done.

When finished run: python3 tools/todo_wakeup.py   (must exit 0)
"""


def load() -> dict:
    if not STATE.exists():
        raise SystemExit(2)
    return json.loads(STATE.read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", action="store_true")
    ap.add_argument("--done", type=int, default=None)
    ap.add_argument("--block", type=int, default=None)
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    d = load()
    todos = d["todos"]

    if args.done is not None:
        for t in todos:
            if t["id"] == args.done:
                t["status"] = "done"
                t["closed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        STATE.write_text(json.dumps(d, indent=1))
        print(f"marked todo {args.done} done")

    if args.block is not None:
        for t in todos:
            if t["id"] == args.block:
                t["status"] = "blocked"
                t["blocker"] = args.reason or t.get("blocker", "unspecified")
        STATE.write_text(json.dumps(d, indent=1))
        print(f"marked todo {args.block} blocked")

    open_items = [t for t in todos if t["status"] == "open"]
    blocked = [t for t in todos if t["status"] == "blocked"]
    done = [t for t in todos if t["status"] == "done"]

    if args.prompt:
        lines = []
        for t in open_items:
            cond = f"  [condition: {t['operator_conditions']}]" if t.get("operator_conditions") else ""
            lines.append(f"{t['id']}. {t['title']}{cond}")
        for t in blocked:
            lines.append(f"{t['id']}. {t['title']}  <-- BLOCKED: {t.get('blocker')}")
        print(RESUME.format(items="\n".join(lines) or "(none)"))
        return 0

    print(f"owner  : {d.get('owner')}")
    print(f"branch : {d.get('branch')}")
    print(f"done   : {len(done)}/{len(todos)}")
    for t in todos:
        mark = {"done": "[x]", "open": "[ ]", "blocked": "[!]"}[t["status"]]
        extra = f"  ({t.get('blocker')})" if t["status"] == "blocked" and t.get("blocker") else ""
        print(f"  {mark} {t['id']:>2}. {t['title']}{extra}")

    if open_items:
        print(f"\nWORK REMAINS: {len(open_items)} open. Not authorized to stop.")
        return 1
    print("\nALL TODOS DONE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
