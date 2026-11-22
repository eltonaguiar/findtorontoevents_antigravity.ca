#!/usr/bin/env python3
"""Per-class data readiness gate.

For each asset class, report whether the inputs required for an honest
point-in-time backtest exist on disk. A class that is not READY must not be
backtested for edge; it is recorded as BLOCKED_DATA.

The point of this gate is to stop the failure mode where a backtest runs on
survivorship-biased or look-ahead-contaminated data and produces a confident
number. Empty cache directories and single-snapshot earnings estimates are
treated as blockers, not as minor inconveniences.

Usage:
    python3 tools/class_data_readiness.py
    python3 tools/class_data_readiness.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"


def _has_files(p: Path) -> int:
    """Count real (non-.gitkeep) files, recursively."""
    if not p.exists():
        return 0
    return sum(1 for f in p.rglob("*") if f.is_file() and f.name != ".gitkeep")


def _earnings_vintage_ok() -> tuple[bool, str]:
    """PEAD needs point-in-time consensus.

    data/earnings/<TICKER>/latest.json holds only a few quarters and a single
    eps_estimate snapshot taken at fetch time. Applying that estimate to older
    quarters is look-ahead, so this is never READY as-is.
    """
    sample = DATA / "earnings" / "AAPL" / "latest.json"
    if not sample.exists():
        return False, "no earnings cache at all"
    obj = json.loads(sample.read_text())
    hist = obj.get("history") or []
    if hist and all("estimate_asof" in h for h in hist):
        return True, "vintage-stamped estimates present"
    return False, (
        f"{len(hist)} quarters only, eps_estimate is a single non-vintage snapshot "
        f"(fetched_at={obj.get('fetched_at')}) - applying it to older quarters is look-ahead"
    )


# (label, path, minimum). A path with a suffix is treated as a single file.
REQUIREMENTS: dict[str, list[tuple[str, Path | None, int]]] = {
    "CRYPTO": [("funding symbols", DATA / "funding_rate_archive", 20)],
    "EQUITY": [("price history", DATA / "equity_quote_cache", 100),
               ("point-in-time earnings", None, 0),
               ("survivorship-free universe", DATA / "universe", 0)],
    "ETF": [("price history", DATA / "equity_quote_cache", 20)],
    # FX spot exchange rates are NOT a yield/rate curve. Bond research needs
    # genuine curve data (yields/tenors), so it gets its own directory; until
    # that exists BOND stays BLOCKED_DATA rather than piggy-backing on FX prices.
    "BOND": [("rate curve", DATA / "rate_curve_cache", 1)],
    "FOREX": [("fx rates", DATA / "forex_rate_cache", 100)],
    "COMMODITY": [("futures prices", DATA / "commodity_price_cache", 20),
                  ("COT history", DATA / "cftc_cot", 100)],
    "FUTURES": [("futures prices", DATA / "commodity_price_cache", 20)],
    "PENNY_STOCK": [("universe seed", DATA / "penny_universe_seed.json", 1)],
    "INDEX": [("price history", DATA / "equity_quote_cache", 20)],
    "MEME": [],        # measured from trading_picks only
    "MUTUAL_FUND": [],  # structural: NAV-only, no harness
    "SPORTS": [("kalshi snapshots", DATA / "kalshi_snapshots", 1)],
}


def _check(label: str, path: Path | None, minimum: int) -> str | None:
    """Return a gap string, or None when this requirement is satisfied."""
    if label == "point-in-time earnings":
        ok, why = _earnings_vintage_ok()
        return None if ok else f"{label}: {why}"
    if label == "survivorship-free universe":
        # A current-constituent list is survivorship-biased by construction.
        cur = path / "sp500_tickers.txt" if path else None
        if cur and cur.exists():
            return ("survivorship-free universe: only current S&P constituents "
                    "present; delisted names are missing (S10 gap)")
        return "survivorship-free universe: not available"
    if path is None:
        return f"{label}: no path configured"
    got = (1 if path.exists() else 0) if path.suffix else _has_files(path)
    if got < minimum:
        return f"{label}: have {got}, need {minimum}"
    return None


def readiness() -> dict:
    out = {}
    for cls, reqs in REQUIREMENTS.items():
        gaps = [g for g in (_check(*r) for r in reqs) if g]
        out[cls] = {"ready": not gaps, "gaps": gaps}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", dest="as_json", action="store_true")
    args = ap.parse_args()

    r = readiness()
    if args.as_json:
        print(json.dumps(r, indent=2))
        return 0

    for cls, v in r.items():
        print(f"{cls:<14}{'READY' if v['ready'] else 'BLOCKED_DATA'}")
        for g in v["gaps"]:
            print(f"    - {g}")
    ready = sum(1 for v in r.values() if v["ready"])
    print(f"\nready: {ready}/{len(r)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
