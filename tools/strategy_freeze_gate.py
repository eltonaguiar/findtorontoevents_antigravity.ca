"""Strategy-freeze gate (N7).

Reads ``reports/strategy_freeze.json`` and exits non-zero while a P0 item is
open, so new-strategy generation is blocked instead of merely documented.

Usage:
    python3 tools/strategy_freeze_gate.py                # exit 1 if frozen
    python3 tools/strategy_freeze_gate.py --json         # print state, exit 0/1
    python3 tools/strategy_freeze_gate.py --manifest PATH
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "reports" / "strategy_freeze.json"


def load_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("freeze manifest must be a JSON object")
    return data


def is_frozen(manifest: dict) -> bool:
    return bool(manifest.get("frozen", False))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Enforce the strategy-generation freeze")
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--json", action="store_true", help="print the state as JSON")
    args = ap.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read freeze manifest {args.manifest}: {exc}",
              file=sys.stderr)
        return 2

    frozen = is_frozen(manifest)
    if args.json:
        print(json.dumps({
            "frozen": frozen,
            "p0": manifest.get("p0", []),
            "rule": manifest.get("rule", ""),
            "unfreeze_when": manifest.get("unfreeze_when", []),
            "manifest": args.manifest,
        }, indent=1))
    if frozen:
        print("Strategy generation is FROZEN: " + str(manifest.get("rule", "")),
              file=sys.stderr)
        for item in manifest.get("p0", []):
            detail = (manifest.get("p0_detail") or {}).get(item, "")
            print(f"  P0 {item}: {detail}".rstrip(), file=sys.stderr)
        print("New-strategy generation is blocked until every P0 item is closed.",
              file=sys.stderr)
        return 1
    print("Strategy generation is not frozen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
