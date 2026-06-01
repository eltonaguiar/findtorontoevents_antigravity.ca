"""FX Carry + VIX Regime Strategy

Academic basis: Brunnermeier, Nagel, Pedersen (RFS 2009) "Carry Trades and Currency Crashes"
Logic: Long top-3 carry pairs (highest interest rate differential) IF VIX < 20.
Flat if VIX >= 25. Partial at 20-25.
Rebalance: Friday close.

This strategy exploits the well-documented carry trade premium while
avoiding crash risk via VIX regime filter (carry trades blow up in vol spikes).
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# G10 carry universe (approximate current differentials)
CARRY_PAIRS = {
    "AUDUSD=X": {"carry": 0.25},   # RBA vs Fed
    "NZDUSD=X": {"carry": 0.25},   # RBNZ vs Fed
    "USDJPY=X": {"carry": 5.25},   # Fed vs BOJ
    "USDCHF=X": {"carry": 1.25},   # Fed vs SNB
    "USDCAD=X": {"carry": 0.50},   # Fed vs BOC
    "EURUSD=X": {"carry": -0.25},  # ECB vs Fed
    "GBPUSD=X": {"carry": -0.25},  # BOE vs Fed
}


def get_vix_level() -> Optional[float]:
    """Fetch current VIX level."""
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="5d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.error(f"VIX fetch failed: {e}")
        return None


def get_carry_rankings() -> List[dict]:
    """Rank pairs by carry differential, return top candidates."""
    pairs = []
    for symbol, info in CARRY_PAIRS.items():
        pairs.append({"symbol": symbol, "carry": info["carry"]})
    pairs.sort(key=lambda x: x["carry"], reverse=True)
    return pairs


def generate_fx_carry_vix_regime_picks() -> List[dict[str, Any]]:
    """Generate FX carry picks conditioned on VIX regime."""
    vix = get_vix_level()
    if vix is None:
        logger.warning("Cannot fetch VIX, skipping FX carry picks")
        return []

    # VIX regime filter
    if vix >= 25:
        logger.info(f"VIX={vix:.1f} >= 25: FLAT (crash risk too high)")
        return []
    
    # VIX 20-25: partial (top 2 only)
    # VIX < 20: full (top 3)
    n_picks = 3 if vix < 20 else 2
    
    rankings = get_carry_rankings()
    top_pairs = rankings[:n_picks]
    
    picks = []
    now = datetime.now(timezone.utc)
    
    try:
        import yfinance as yf
    except ImportError:
        yf = None

    for pair in top_pairs:
        sym = pair["symbol"]
        entry = None
        if yf is not None:
            try:
                hist = yf.Ticker(sym).history(period="5d")
                if hist is not None and not hist.empty:
                    entry = float(hist["Close"].iloc[-1])
            except Exception as e:
                logger.debug("FX price %s: %s", sym, e)
        if entry is None or entry <= 0:
            continue
        direction = "LONG" if pair["carry"] > 0 else "SHORT"
        tp_pct, sl_pct = 0.015, 0.008
        if direction == "LONG":
            tp, sl = round(entry * (1 + tp_pct), 5), round(entry * (1 - sl_pct), 5)
        else:
            tp, sl = round(entry * (1 - tp_pct), 5), round(entry * (1 + sl_pct), 5)
        picks.append({
            "symbol": sym,
            "direction": direction,
            "strategy": "fx_carry_vix_regime",
            "asset_class": "FOREX",
            "category": "forex",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": 0.65 if vix < 15 else 0.55,
            "generated_at": now.isoformat(),
            "reason": f"Carry={pair['carry']:.2f}% VIX={vix:.1f} (regime: {'LOW' if vix<15 else 'NORMAL' if vix<20 else 'ELEVATED'})",
            "source": "alpha_engine",
            "source_system": "fx_carry_vix_regime",
            "forced_resolution": {
                "max_hold_hours": 168,  # 1 week
                "tp_pct": 1.5,
                "sl_pct": 0.8,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": "Brunnermeier, Nagel, Pedersen (RFS 2009)",
        })
    
    return picks


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    picks = generate_fx_carry_vix_regime_picks()
    print(json.dumps(picks, indent=2))
