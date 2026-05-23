#!/usr/bin/env python3
"""
Portfolio Reset Script
Removes low-score, blacklisted, and duplicate positions from portfolio_20x.json.
Run after quality investigation to enforce updated filters.
"""
import json
import os
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio_20x.json")

MIN_SCORE = 68
SYMBOL_BLACKLIST = {
    "BTCUSDT", "ADAUSDT", "ADA-USD", "WIF-USD", "WIFUSDT",
    "SOL-USD", "AVAX-USD", "DOT-USD", "TIA-USD", "ETC-USD",
    "SPY", "QQQ", "BONK-USD", "FLOKI-USD", "STRKUSDT",
    "INJUSDT", "POLUSDT",
}


def normalize_symbol(sym):
    sym = sym.upper().replace("-USD", "USDT").replace("/", "")
    if not sym.endswith("USDT") and "USD" in sym and "=" not in sym:
        sym += "T"
    return sym


def main():
    with open(PORTFOLIO_FILE, encoding="utf-8") as f:
        pf = json.load(f)

    now = datetime.now(timezone.utc)
    removed = []
    kept = {}
    seen_syms = set()

    for pk, pos in pf["positions"].items():
        sym = pos.get("symbol", "")
        score = float(pos.get("score", 0))
        norm = normalize_symbol(sym)

        if sym in SYMBOL_BLACKLIST or norm in SYMBOL_BLACKLIST:
            removed.append((pk, "BLACKLIST sym=" + sym))
        elif score < MIN_SCORE:
            removed.append((pk, "LOW_SCORE score=" + str(score)))
        elif norm in seen_syms:
            removed.append((pk, "DUPLICATE_SYM " + norm))
        else:
            kept[pk] = pos
            seen_syms.add(norm)

    print(f"REMOVING {len(removed)} positions:")
    for pk, reason in removed:
        print(f"  {pk}: {reason}")
    print(f"\nKEEPING {len(kept)} positions:")
    for pk, pos in kept.items():
        print(f"  {pk}: score={pos['score']} dir={pos['direction']}")

    pf["positions"] = kept
    pf["current_balance"] = 10000
    pf["starting_balance"] = 10000
    pf["snapshots"] = [{
        "time": now.isoformat(),
        "balance": 10000,
        "unrealized_pnl": 0,
        "equity": 10000,
        "open_positions": len(kept),
        "total_trades": len(kept),
        "wins": 0,
        "losses": 0,
        "liquidations": 0,
        "note": "RESET: removed low-score/blacklist/duplicate positions",
    }]
    pf["stats"] = {
        "total_trades": len(kept),
        "wins": 0,
        "losses": 0,
        "liquidations": 0,
        "tp_hits": 0,
        "sl_hits": 0,
        "total_pnl_usdt": 0,
        "best_trade_pnl": 0,
        "worst_trade_pnl": 0,
    }
    pf["reset_at"] = now.isoformat()
    pf["reset_reason"] = (
        "Removed positions below score 68, blacklisted symbols, and duplicates "
        "per quality investigation 2026-03-17. Filters: MIN_SCORE=68, BLACKOUT_HOURS, SYMBOL_BLACKLIST."
    )

    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(pf, f, indent=2)
    print(f"\nPortfolio saved. {len(kept)} clean positions remain.")


if __name__ == "__main__":
    main()
