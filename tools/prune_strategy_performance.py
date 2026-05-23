#!/usr/bin/env python3
"""Daily auto-prune for alpha_engine/data/strategy_performance.json.

Drops entries whose ``last_seen`` ISO timestamp is older than 30 days. Entries
without a ``last_seen`` field, with an unparseable timestamp, or whose value is
not a dict are kept defensively (see ``alpha_engine.atomic_json.prune_stale``).

The companion ``merge_write_json`` helper (commit 1002af0cfa) stamps every
entry it writes with ``last_seen``, so newly merged data is always prune-ready.
Legacy entries written before that commit lack the stamp and are therefore
kept until they get touched by the next merge cycle (which will stamp them).

Usage:
    python tools/prune_strategy_performance.py                # write changes
    python tools/prune_strategy_performance.py --dry-run      # just report

Exit code is always 0 -- prune failures are non-fatal and must not block the
daily cron. All errors are logged to stdout for trend monitoring.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `from alpha_engine.atomic_json import ...`
# works regardless of the cwd the cron invokes us from.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_TARGET = REPO_ROOT / "alpha_engine" / "data" / "strategy_performance.json"
MAX_AGE_DAYS = 30
TS_FIELD = "last_seen"


def _log(msg: str) -> None:
    """Single-line stdout log so GHA logs aggregate cleanly for trend tracking."""
    print(f"[prune_strategy_performance] {msg}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prune entries older than 30 days from strategy_performance.json"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_TARGET,
        help=f"Path to JSON file to prune (default: {DEFAULT_TARGET})",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=MAX_AGE_DAYS,
        help=f"Drop entries older than this many days (default: {MAX_AGE_DAYS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be pruned without writing.",
    )
    args = parser.parse_args(argv)

    try:
        from alpha_engine.atomic_json import (
            atomic_write_json,
            prune_stale,
            read_json,
        )
    except Exception as exc:  # pragma: no cover - import failure path
        _log(f"ERROR importing alpha_engine.atomic_json: {exc!r} -- exiting 0 (non-fatal)")
        return 0

    target: Path = args.path
    if not target.exists():
        _log(f"target not found: {target} -- nothing to prune (exit 0)")
        return 0

    try:
        data = read_json(target, default={})
    except Exception as exc:  # pragma: no cover - read_json catches OSError already
        _log(f"ERROR reading {target}: {exc!r} -- exiting 0 (non-fatal)")
        return 0

    if not isinstance(data, dict):
        _log(f"data is {type(data).__name__}, not dict -- skipping (exit 0)")
        return 0

    before = len(data)
    try:
        pruned = prune_stale(data, max_age_days=args.max_age_days, ts_field=TS_FIELD)
    except Exception as exc:
        _log(f"ERROR in prune_stale: {exc!r} -- exiting 0 (non-fatal)")
        return 0

    after = len(pruned)
    removed = before - after

    if args.dry_run:
        _log(
            f"DRY-RUN target={target.name} before={before} after={after} "
            f"would_prune={removed} max_age_days={args.max_age_days} ts_field={TS_FIELD}"
        )
        if removed:
            dropped = sorted(set(data.keys()) - set(pruned.keys()))
            _log(f"DRY-RUN keys_to_drop={dropped}")
        return 0

    if removed == 0:
        _log(
            f"no-op target={target.name} entries={before} "
            f"max_age_days={args.max_age_days} (nothing older than cutoff)"
        )
        return 0

    try:
        atomic_write_json(target, pruned)
    except Exception as exc:
        _log(f"ERROR writing pruned file {target}: {exc!r} -- exiting 0 (non-fatal)")
        return 0

    _log(
        f"pruned target={target.name} before={before} after={after} "
        f"removed={removed} max_age_days={args.max_age_days}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
