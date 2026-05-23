#!/usr/bin/env python3
"""
HF-P3 / ops: validate predictions/data/kol_consensus_picks.json after KOL consensus engine.

- Malformed JSON or wrong top-level type -> exit 1 (fail CI).
- Empty list -> exit 0 + GitHub Actions warning (data incident signal; HF doc).
- Non-empty -> each pick must carry required keys for downstream integrator/audit.

Usage:
  python tools/verify_kol_consensus_export.py
  python tools/verify_kol_consensus_export.py path/to/kol_consensus_picks.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_PATH = REPO / "predictions" / "data" / "kol_consensus_picks.json"

REQUIRED_KEYS = frozenset(
    {
        "source_system",
        "strategy",
        "symbol",
        "direction",
        "confidence",
        "status",
    }
)


def _gha_warning(msg: str) -> None:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::warning title=KOL consensus::{msg}")
    else:
        print(f"[WARN] {msg}", file=sys.stderr)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    if not path.is_file():
        print(f"verify_kol_consensus_export: missing file {path}", file=sys.stderr)
        return 1

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"verify_kol_consensus_export: invalid JSON in {path}: {e}", file=sys.stderr)
        return 1

    if not isinstance(data, list):
        print(f"verify_kol_consensus_export: expected JSON array, got {type(data).__name__}", file=sys.stderr)
        return 1

    if len(data) == 0:
        _gha_warning(
            "kol_consensus_picks.json is empty — pipeline ran but produced no signals "
            "(check DB ingest, scrapers, or age window). See docs/HEDGE_FUND_QUALITY_NEXT_STEPS.md P3."
        )
        return 0

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            print(f"verify_kol_consensus_export: item {i} is not an object", file=sys.stderr)
            return 1
        missing = REQUIRED_KEYS - set(item.keys())
        if missing:
            print(
                f"verify_kol_consensus_export: item {i} missing keys {sorted(missing)}",
                file=sys.stderr,
            )
            return 1
        if str(item.get("source_system", "")).strip() != "kol_consensus":
            print(
                f"verify_kol_consensus_export: item {i} source_system must be kol_consensus, "
                f"got {item.get('source_system')!r}",
                file=sys.stderr,
            )
            return 1

    print(f"verify_kol_consensus_export: OK {len(data)} pick(s) in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
