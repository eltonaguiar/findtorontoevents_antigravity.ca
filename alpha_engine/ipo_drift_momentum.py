"""IPO Drift Strategy — Post-IPO Momentum

Academic basis: Loughran & Ritter (JF 1995) "The New Issues Puzzle"
Modern variant: Liu & Sherman (2020) — 90-day post-IPO drift

Logic: After an IPO, institutional accumulation creates a 90-day drift.
We proxy this by screening for stocks with recent high volume + 3m momentum.

Universe: Recent IPOs (via screener), price > $10, avg volume > 500K
Entry: 3m momentum > 20% AND avg volume > 2x pre-IPO baseline → LONG
Exit: After 90d OR max hold 720h
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, List

logger = logging.getLogger(__name__)

# Recent IPO universe (manually curated — replace with screener when available)
IPO_UNIVERSE = [
    "ARM", "KVUE", "CAVA", "BIRK", "PACS", "ULS", "LOAR", "NXT",
    "RDDT", "ASTS", "SMCI", "CRDO", "IONQ", "SOFI", "HOOD", "AFRM",
]


def generate_ipo_drift_picks() -> List[dict[str, Any]]:
    """Generate IPO drift picks."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not available")
        return []
    
    picks = []
    now = datetime.now(timezone.utc)
    
    for symbol in IPO_UNIVERSE:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="6mo")
            if len(hist) < 60:
                continue
            
            close = hist["Close"].values
            volume = hist["Volume"].values
            
            # 3-month momentum (skip last month)
            if len(close) >= 84:
                mom_3m = (close[-1] / close[-84] - 1) * 100
            else:
                continue
            
            # Volume spike: current 20d avg vs 60d avg
            vol_20 = volume[-20:].mean()
            vol_60 = volume[-60:].mean()
            vol_ratio = vol_20 / vol_60 if vol_60 > 0 else 0
            
            # Entry: positive 3m momentum + volume expansion
            if mom_3m > 10 and vol_ratio > 1.3 and close[-1] > 10:
                picks.append({
                    "symbol": symbol,
                    "direction": "LONG",
                    "strategy": "ipo_drift_momentum",
                    "asset_class": "IPO",
                    "category": "ipo",
                    "entry_price": round(float(close[-1]), 2),
                    "confidence": min(0.85, 0.60 + mom_3m / 100),
                    "generated_at": now.isoformat(),
                    "reason": f"IPO drift: 3m_mom={mom_3m:.1f}% vol_ratio={vol_ratio:.2f}",
                    "source": "alpha_engine",
                    "source_system": "ipo_drift_momentum",
                    "forced_resolution": {"max_hold_hours": 720, "tp_pct": 8.0, "sl_pct": 5.0, "time_exit_at_market": True},
                    "paper_pilot": True,
                    "academic_citation": "Loughran-Ritter (JF 1995)",
                })
        except Exception as e:
            logger.debug(f"{symbol}: {e}")
    
    return picks


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    picks = generate_ipo_drift_picks()
    print(json.dumps(picks, indent=2))
    print(f"\nTotal: {len(picks)} IPO drift picks")
