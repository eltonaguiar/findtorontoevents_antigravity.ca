"""emit_observe_pods — resolve observe-pod picks into forward observations.

The forward-observation contract rejects a row unless ``intrabar_first_touch``
is True, so a pick can only enter the forward clock after its first stop/target
touch is resolved from bars. This tool does that, and refuses to invent rows:

* ``--bars`` is required. It is a JSON map ``{symbol: [ {high, low, open?,
  close?, timestamp}, ... ]}`` (oldest first) covering each pick's life.
* A pick with no bars is reported as UNRESOLVED and skipped, never emitted.
* ``--dry-run`` (default) prints the rows; ``--apply`` appends them to
  ``reports/forward_observations.jsonl``.

Data requirement: the bars file must come from the price tables
(``crypto_ohlcv`` / ``equity_daily_ohlcv`` / ``fx_prices`` / ...) or an exchange
API. This tool does not fetch; that is deliberate so a missing price feed can
never turn into fabricated evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from alpha_engine.intrabar_resolver import stamp_pick  # noqa: E402

LEDGER = REPO / "reports" / "forward_observations.jsonl"
REGISTRY = REPO / "reports" / "hypothesis_registry.json"


def _known_hypotheses() -> set[str]:
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            ident = node.get("id")
            if isinstance(ident, str) and ident.strip():
                found.add(ident.strip().upper())
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--picks", required=True, help="JSON list of observe-pod picks")
    ap.add_argument("--bars", required=True, help="JSON map symbol -> list of OHLC bars")
    ap.add_argument("--apply", action="store_true", help="append to the forward ledger")
    args = ap.parse_args(argv)

    picks = json.loads(Path(args.picks).read_text(encoding="utf-8"))
    if isinstance(picks, dict):
        picks = picks.get("picks") or []
    bars_by_symbol = json.loads(Path(args.bars).read_text(encoding="utf-8"))
    known = _known_hypotheses()

    emitted, unresolved = [], []
    for pick in picks:
        hid = str(pick.get("hypothesis_id") or "").strip()
        if not hid or (known and hid.upper() not in known):
            unresolved.append((pick.get("id"), f"hypothesis_id {hid!r} not registered"))
            continue
        bars = bars_by_symbol.get(str(pick.get("symbol"))) or []
        if not bars:
            unresolved.append((pick.get("id"), "no bars for symbol"))
            continue
        row = stamp_pick(pick, bars)
        if not row.get("intrabar_first_touch"):
            unresolved.append((pick.get("id"), "could not resolve a first touch"))
            continue
        emitted.append(row)

    print(f"resolved={len(emitted)} unresolved={len(unresolved)}")
    for pid, why in unresolved:
        print(f"  UNRESOLVED {pid}: {why}")
    if args.apply and emitted:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER, "a", encoding="utf-8") as f:
            for row in emitted:
                f.write(json.dumps(row, sort_keys=True) + "\n")
        print(f"appended {len(emitted)} rows to {LEDGER}")
    elif emitted:
        print("dry-run: pass --apply to append")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
