"""H-002 PEAD shadow data collector.

Accumulates shadow PEAD picks into alpha_engine/data/pead_shadow_log.jsonl for
M-107 harness gate validation. Runs daily in CI (pead-shadow-collector.yml)
with EQUITY_PEAD_ENABLED=1. Never writes to active_picks.json or production paths.

Usage:
    python tools/pead_shadow_runner.py [--dry-run]
    EQUITY_PEAD_ENABLED=1 python tools/pead_shadow_runner.py

Exit codes: 0=success (even if 0 signals — fail-open).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ALPHA_ENGINE_DIR = str(REPO_ROOT / "alpha_engine")
if ALPHA_ENGINE_DIR not in sys.path:
    sys.path.insert(0, ALPHA_ENGINE_DIR)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_SHADOW_LOG = REPO_ROOT / "alpha_engine" / "data" / "pead_shadow_log.jsonl"
_PRUNE_DAYS = 90


def _prune_old_entries(lines: list[str]) -> list[str]:
    """Discard entries older than _PRUNE_DAYS to bound file size."""
    cutoff_ts = datetime.now(timezone.utc).timestamp() - _PRUNE_DAYS * 86400
    kept = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            ts_str = obj.get("_runner_ts") or obj.get("runner_ts", "")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                if ts >= cutoff_ts:
                    kept.append(line)
                # else: prune
            else:
                kept.append(line)  # no timestamp → keep (defensive)
        except Exception:
            kept.append(line)
    return kept


def main(dry_run: bool = False, output_path: Path | None = None) -> int:
    """Run PEAD shadow collector.

    Args:
        dry_run: Print signals but do not write to disk.
        output_path: Override default shadow log path (used in tests).
    """
    # Enable gate regardless of env so runner works standalone
    os.environ.setdefault("EQUITY_PEAD_ENABLED", "1")

    try:
        from alpha_engine.equity_pead_strategy import equity_pead_signals
    except ImportError as e:
        print(f"[pead_shadow_runner] SKIP: could not import equity_pead_signals: {e}", flush=True)
        return 0

    signals = equity_pead_signals()
    run_ts = datetime.now(timezone.utc).isoformat()

    print(f"[pead_shadow_runner] {run_ts} — {len(signals)} PEAD shadow signal(s)", flush=True)
    for s in signals:
        print(
            f"  {s['symbol']:8} surprise={s.get('earnings_surprise_pct', '?')}%"
            f"  days_since={s.get('days_since_earnings', '?')}"
            f"  conf={s.get('confidence', '?')}",
            flush=True,
        )

    if dry_run:
        print("[pead_shadow_runner] dry-run: no file written", flush=True)
        return 0

    log_path = output_path or _SHADOW_LOG

    # Read existing log, prune old entries, append new ones
    existing: list[str] = []
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8").splitlines()

    existing = _prune_old_entries(existing)

    new_lines = []
    for sig in signals:
        record = dict(sig)
        record["_runner_ts"] = run_ts
        new_lines.append(json.dumps(record, separators=(",", ":")))

    all_lines = existing + new_lines
    if new_lines or existing != _prune_old_entries(existing):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("\n".join(all_lines) + ("\n" if all_lines else ""), encoding="utf-8")
        print(
            f"[pead_shadow_runner] wrote {len(new_lines)} new entries; total={len(all_lines)} in log",
            flush=True,
        )
    else:
        print("[pead_shadow_runner] no new signals; log unchanged", flush=True)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="H-002 PEAD shadow pick collector")
    parser.add_argument("--dry-run", action="store_true", help="Print signals but do not write log")
    args = parser.parse_args()
    sys.exit(main(dry_run=args.dry_run))
