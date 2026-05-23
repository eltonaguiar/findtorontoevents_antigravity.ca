#!/usr/bin/env python3
"""Wave 2 ML walk-forward validation check."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WAVE2_SYMBOLS = {"TRXUSDT", "OPUSDT", "LINKUSDT", "AVAXUSDT", "SUIUSDT", "ARBUSDT", "APTUSDT", "LTCUSDT", "ZKUSDT"}
WAVE2_PREFIX = "ml_enhanced_"

def main():
    # Active picks
    active_path = ROOT / "alpha_engine" / "data" / "active_picks.json"
    if active_path.exists():
        active = json.loads(active_path.read_text(encoding="utf-8"))
        w2 = [p for p in active if p.get("symbol") in WAVE2_SYMBOLS and WAVE2_PREFIX in str(p.get("strategy", ""))]
        print(f"Wave2 ACTIVE picks: {len(w2)}")
        for p in w2:
            sym = p.get("symbol", "?")
            d = p.get("direction", "?")
            c = p.get("confidence", 0)
            s = p.get("strategy", "")
            print(f"  {sym} {d} conf={c:.2f} strategy={s}")
    else:
        print("active_picks.json not found")

    # Closed picks from dashboard payload
    payload_path = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    if payload_path.exists():
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        closed = payload.get("picks", {}).get("recent_closed", [])
        w2c = [p for p in closed if p.get("symbol") in WAVE2_SYMBOLS and WAVE2_PREFIX in str(p.get("strategy", ""))]
        print(f"\nWave2 CLOSED picks in payload: {len(w2c)}")
        wins = sum(1 for p in w2c if str(p.get("status", "")).upper() == "WON")
        losses = sum(1 for p in w2c if str(p.get("status", "")).upper() == "LOST")
        if w2c:
            wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
            avg_pnl = sum(float(p.get("pnl_pct", 0) or 0) for p in w2c) / len(w2c)
            print(f"  OOS Win Rate: {wr:.1f}%  ({wins}W/{losses}L)  Avg PnL: {avg_pnl:+.3f}%")
            for p in w2c[:20]:
                sym = p.get("symbol", "?")
                d = p.get("direction", "?")
                st = p.get("status", "?")
                pnl = float(p.get("pnl_pct", 0) or 0)
                strat = p.get("strategy", "")
                print(f"  {sym:12s} {d:5s} {st:6s} pnl={pnl:+.3f}% strat={strat}")
        # Also check all ml_enhanced Wave2 across any strategy variant
        w2_any = [p for p in closed if p.get("symbol") in WAVE2_SYMBOLS and "ml_enhanced" in str(p.get("source_system", "")).lower()]
        if w2_any and len(w2_any) != len(w2c):
            print(f"\nWave2 picks via source_system=ml_enhanced: {len(w2_any)}")
    else:
        print("dashboard_payload.json not found")

if __name__ == "__main__":
    main()
