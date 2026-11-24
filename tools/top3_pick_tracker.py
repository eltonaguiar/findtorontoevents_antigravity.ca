#!/usr/bin/env python3
"""top3_pick_tracker.py — mark the pre-registered top-3-per-class picks to market.

The register (reports/top3_picks_<date>.json) is written BEFORE any price is recorded,
so the pick cannot be quietly changed after the fact. This tool only does arithmetic on
prices it fetches now; it never edits the thesis, the tier or the falsifier.

Usage
  python3 tools/top3_pick_tracker.py --init     # fetch and freeze entry prices (once)
  python3 tools/top3_pick_tracker.py --run      # mark to market, append to history
  python3 tools/top3_pick_tracker.py --status   # print the table from the register

Honesty rules
  * a pick with no entry price after --init is reported NO_PRICE, never silently skipped;
  * a symbol with no data is reported NO_DATA, not dropped from the denominator;
  * the tracker never reorders or re-ranks picks - ranking is frozen at registration.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "reports" / "top3_picks_2026-11-22.json"
HISTORY = ROOT / "data" / "top3_picks_history.jsonl"


def load_register(path: Path) -> dict:
    return json.loads(path.read_text())


def save_register(path: Path, reg: dict) -> None:
    path.write_text(json.dumps(reg, indent=1) + "\n")


def all_picks(reg: dict) -> list[dict]:
    out = []
    for cls in reg.get("classes", []):
        for p in cls.get("picks", []):
            p = dict(p)
            p["asset_class"] = cls["asset_class"]
            out.append(p)
    return out


def last_close(symbol: str) -> float | None:
    try:
        import warnings
        import yfinance as yf
        warnings.filterwarnings("ignore")
        df = yf.download(symbol, period="5d", progress=False, auto_adjust=True, threads=False)
        if df is None or len(df) == 0:
            return None
        close = df["Close"]
        if hasattr(close, "columns"):
            close = close.iloc[:, 0]
        close = close.dropna()
        return float(close.iloc[-1]) if len(close) else None
    except Exception:  # noqa: BLE001
        return None


def mark_to_market(picks: list[dict], prices: dict[str, float | None]) -> list[dict]:
    rows = []
    for p in picks:
        entry = p.get("entry_price")
        now = prices.get(p["symbol"])
        if entry in (None, 0) or now is None:
            rows.append({**p, "last_price": now, "return_pct": None,
                         "state": "NO_PRICE" if entry in (None, 0) else "NO_DATA"})
            continue
        ret = (now / entry - 1.0) * 100.0
        rows.append({**p, "last_price": now, "return_pct": round(ret, 4),
                     "state": "OPEN"})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--register", default=str(REGISTER))
    ap.add_argument("--offline", action="store_true", help="skip network; prices unknown")
    a = ap.parse_args()
    path = Path(a.register)
    reg = load_register(path)
    picks = all_picks(reg)

    if a.init:
        missing = 0
        for p in picks:
            if p.get("entry_price") is not None:
                continue
            price = None if a.offline else last_close(p["symbol"])
            if price is None:
                missing += 1
                p["entry_price_state"] = "NO_DATA"
            else:
                p["entry_price"] = round(price, 6)
                p["entry_date"] = reg.get("as_of")
                p["entry_price_state"] = "FROZEN"
        save_register(path, reg)
        print(f"init: {len(picks)} picks, {missing} without a price")
        if missing:
            print("  picks without a price stay NO_DATA in every report; they are not dropped")

    prices = {}
    if not a.offline:
        for sym in {p["symbol"] for p in picks}:
            prices[sym] = last_close(sym)

    rows = mark_to_market(picks, prices)
    for r in rows:
        rp = "   n/a" if r["return_pct"] is None else f"{r['return_pct']:+7.2f}%"
        print(f"{r['asset_class']:12s} {r['rank']} {r['symbol']:8s} {r['tier']:12s} "
              f"entry={r.get('entry_price')} last={r.get('last_price')} {rp} {r['state']}")

    if a.run:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY.open("a") as fh:
            fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                 "as_of": reg.get("as_of"), "rows": rows}) + "\n")
        print(f"appended {len(rows)} rows to {HISTORY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
