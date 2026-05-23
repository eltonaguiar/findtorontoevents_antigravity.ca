#!/usr/bin/env python3
"""State manager for the /goal skill — a persistent standing objective that
survives across turns, modeled on the Hermes Agent /goal feature.

State lives in .claude/goal_state.json, keyed by session id so multiple
concurrent Claude instances do not clobber each other's goals.

Usage:
  goal_state.py set    --session SID --text "GOAL TEXT" [--max-turns N]
  goal_state.py status --session SID
  goal_state.py tick   --session SID            # increment turn counter
  goal_state.py judge  --session SID --done BOOL --reason "..."
  goal_state.py pause  --session SID
  goal_state.py resume --session SID            # also resets turn counter
  goal_state.py clear  --session SID

Exit code 0 on success, 1 on error. Prints a JSON line on stdout.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "goal_state.json"
)
DEFAULT_MAX_TURNS = 20


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def _emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["set", "status", "tick", "judge",
                                       "pause", "resume", "clear"])
    ap.add_argument("--session", required=True)
    ap.add_argument("--text")
    ap.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    ap.add_argument("--done")
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    data = _load()
    key = f"goal:{args.session}"
    goal = data.get(key)

    if args.action == "set":
        if not args.text:
            _emit({"ok": False, "error": "set requires --text"})
            return 1
        data[key] = {
            "text": args.text,
            "state": "active",
            "turns_used": 0,
            "max_turns": args.max_turns,
            "created_utc": _now(),
            "updated_utc": _now(),
            "last_reason": "",
        }
        _save(data)
        _emit({"ok": True, "goal": data[key]})
        return 0

    if goal is None and args.action not in ("status",):
        _emit({"ok": False, "error": "no active goal for this session"})
        return 1

    if args.action == "status":
        _emit({"ok": True, "goal": goal})  # goal may be None
        return 0

    if args.action == "tick":
        goal["turns_used"] += 1
        goal["updated_utc"] = _now()
        if goal["turns_used"] >= goal["max_turns"] and goal["state"] == "active":
            goal["state"] = "budget_exhausted"
        _save(data)
        _emit({"ok": True, "goal": goal})
        return 0

    if args.action == "judge":
        done = str(args.done).lower() in ("1", "true", "yes")
        goal["last_reason"] = args.reason
        goal["updated_utc"] = _now()
        if done:
            goal["state"] = "achieved"
        _save(data)
        _emit({"ok": True, "done": done, "goal": goal})
        return 0

    if args.action == "pause":
        goal["state"] = "paused"
        goal["updated_utc"] = _now()
        _save(data)
        _emit({"ok": True, "goal": goal})
        return 0

    if args.action == "resume":
        goal["state"] = "active"
        goal["turns_used"] = 0
        goal["updated_utc"] = _now()
        _save(data)
        _emit({"ok": True, "goal": goal})
        return 0

    if args.action == "clear":
        del data[key]
        _save(data)
        _emit({"ok": True, "cleared": key})
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
