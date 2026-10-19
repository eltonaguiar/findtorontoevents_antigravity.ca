#!/usr/bin/env python3
"""forward_pilot_register.py — register a strategy for forward-pilot n-accumulation.

Purpose
-------
Put a strategy into paper-only forward-test mode WITHOUT contaminating live
sizing or the consensus / scoring layer. The smallest-increment way to wire
an external / experimental / n-short strategy into the forward-test harness
when the strategy source file lives outside alpha_engine/strategies/.

What this script does
---------------------
Creates / maintains `audit_dashboard/data/forward_pilot_registry.json` — a
manifest that downstream forward ingestion hooks (e.g. an updated stamp in
tools/stamp_entry_conditions.py OR forward_n100_tracker.py) read to determine
which (strategy, direction) pairs emit with `forward_test_only: True` on
their picks. That field is honored at runtime in
`alpha_engine/non_crypto_policy.py`:

  Line 131: ``if p.get("forward_test_only") in (True, 1, "1", "true", "True"):``
  Line 200: ``if forward_test_only: ... bypass daily cap``  (shadow lane)

So picks with the flag bypass live sizing and never enter consensus scoring.

Why a registry file (not env var, not hardcode)
------------------------------------------------
* Per AGENTS.md: every code change MUST be documented + reproducible; a
  registry file with explicit rows is auditable, diff-friendly.
* A `--target-n` knob per entry lets us set the bar at 5 (HC tier) vs 30
  (class-mates per-strategy) vs 80+ (forward_candidate_scoreboard promoted).
* Cron-driven regeneration of `forward_candidate_scoreboard.json` cannot
  overwrite this registry because it lives at a separate path and is
  hand-maintained; it persists across cron runs.

Usage
-----
Register:
    python3 tools/forward_pilot_register.py \\
        --strategy battleground_luxalgo --direction LONG \\
        --target-n 30 --note "PF 2.83 WR 71.4% n=14; needs ~16 more resolved"

List:
    python3 tools/forward_pilot_register.py --list

Remove (single direction):
    python3 tools/forward_pilot_register.py --remove \\
        --strategy battleground_luxalgo --direction LONG

Remove (all directions):
    python3 tools/forward_pilot_register.py --remove --strategy battleground_luxalgo

Custom registry path (for sandboxed / multi-pool setups):
    python3 tools/forward_pilot_register.py --strategy foo --direction SHORT \\
        --registry /tmp/foo_forward_pilot.json

Per AGENTS.md: every code change MUST be documented in a `.MD` file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _positive_int(value: str) -> int:
    """Argparse type: parse a positive int, reject 0 and negatives loudly
    rather than silently normalizing (transparent in --help)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"expected an integer, got {value!r}")
    if n < 1:
        raise argparse.ArgumentTypeError(
            f"--target-n must be >= 1 (HC tier floor); got {n}"
        )
    return n

REPO = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = REPO / "audit_dashboard" / "data" / "forward_pilot_registry.json"


def _load(path: Path) -> dict:
    """Load the registry JSON. Empty schema on absent / corrupt file."""
    if not path.exists():
        return {"generated_at": "", "registry_version": "1.0", "candidates": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Crash loudly; don't overwrite a corrupt registry silently.
        raise SystemExit(f"FATAL: registry at {path} is not valid JSON; refusing to overwrite")


def _save(path: Path, data: dict) -> None:
    """Save the registry JSON ATOMICALLY via write+os.replace on a sibling
    temp file (crash-safe: a concurrent --list never sees a half-written
    file). Re-serializes with sorted=False to preserve insertion order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _print_list(data: dict, registry_path: Path) -> None:
    rows = data.get("candidates", [])
    if not rows:
        print(f"registry: {registry_path}\n(no candidates registered)")
        return
    print(f"registry: {registry_path}  generated_at: {data.get('generated_at', '?')}")
    print(f"  {'STRATEGY':<32} {'DIR':<5} {'TARGET_N':>8} {'FWD_TEST_ONLY':>13}  NOTE")
    for c in rows:
        print(
            f"  {c['strategy']:<32} {c.get('direction', '?'):<5} "
            f"{c.get('target_n', '?'):>8} {str(c.get('forward_test_only', False)):>13}  "
            f"{c.get('note', '')}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Register a strategy for forward-pilot n-accumulation (paper-only).",
    )
    parser.add_argument("--strategy", type=str, help="strategy name")
    parser.add_argument(
        "--direction",
        choices=["LONG", "SHORT"],
        help="direction (LONG or SHORT) for the candidate entry",
    )
    parser.add_argument("--note", type=str, default="", help="verdict / context note")
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help=f"registry path (default: {DEFAULT_REGISTRY})",
    )
    parser.add_argument(
        "--target-n",
        type=_positive_int,
        default=30,
        help="n-accumulation target to promote: 5 = HC tier; 30 = class-mates bar; 80 = forward_candidate_scoreboard promoted (default 30, must be >= 1)",
    )
    parser.add_argument("--list", action="store_true", help="list current registry entries and exit")
    parser.add_argument("--remove", action="store_true", help="remove a candidate (--strategy required)")
    args = parser.parse_args(argv)

    # --list short-circuit
    if args.list:
        _print_list(_load(args.registry), args.registry)
        return 0

    if not args.strategy:
        parser.error("--strategy required for register / remove")

    data = _load(args.registry)
    data.setdefault("candidates", [])

    # --remove path
    if args.remove:
        before = len(data["candidates"])
        if args.direction:
            data["candidates"] = [
                c
                for c in data["candidates"]
                if not (c.get("strategy") == args.strategy and c.get("direction") == args.direction)
            ]
            action = f"{args.strategy}/{args.direction}"
        else:
            data["candidates"] = [c for c in data["candidates"] if c.get("strategy") != args.strategy]
            action = f"all directions of {args.strategy}"
        after = len(data["candidates"])
        if before == after:
            print(f"No matching entry found for {action}", file=sys.stderr)
            return 1
        data["generated_at"] = _now_iso()
        _save(args.registry, data)
        print(f"Removed {action} (was {before - after} row); {after} entries remain at {args.registry}")
        return 0

    # --register path
    if not args.direction:
        parser.error("--direction required for register")

    new_row = {
        "strategy": args.strategy,
        "direction": args.direction,
        "target_n": args.target_n,
        "forward_test_only": True,
        "registered_at": _now_iso(),
        "note": args.note,
    }

    # Idempotent re-register: one entry per (strategy, direction). Update-in-place.
    existing_idx = next(
        (
            i
            for i, c in enumerate(data["candidates"])
            if c.get("strategy") == args.strategy and c.get("direction") == args.direction
        ),
        None,
    )
    verb = "Updated" if existing_idx is not None else "Registered"
    if existing_idx is not None:
        # Preserve note from CLI; keep the older registered_at as audit history.
        previous_registered = data["candidates"][existing_idx].get("registered_at")
        new_row["registered_at"] = previous_registered or new_row["registered_at"]
        data["candidates"][existing_idx] = new_row
    else:
        data["candidates"].append(new_row)

    data["generated_at"] = _now_iso()
    _save(args.registry, data)
    print(
        f"{verb} {args.strategy}/{args.direction} with target_n={args.target_n}"
        f" (paper-only, forward_test_only=true) at {args.registry}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
