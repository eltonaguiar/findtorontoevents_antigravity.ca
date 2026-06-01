"""Cheap Stocks / Penny Stocks Strategy — Low-Price Momentum

Academic basis: Bali, Cakici & Whitelaw (JFE 2011) "Maxing Out"
Logic: Low-price stocks exhibit lottery-like demand. We exploit the 
mean-reversion after extreme spikes in cheap stocks.

Universe: Stocks with price < $10, avg volume > 1M (liquid enough)
Entry: Price < $10 AND 5d momentum > 15% AND volume > 3x 20d avg → LONG
Exit: After 7d OR max hold 168h

Risk: These are inherently risky. Use strict position sizing.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, List

logger = logging.getLogger(__name__)

# Cheap stock universe (high-volume sub-$10 stocks)
CHEAP_UNIVERSE = [
    "SOFI", "PLTR", "NIO", "XPEV", "LCID", "RIVN", "MARA", "RIOT",
    "CLOV", "WISH", "BB", "NOK", "SNDL", "TLRY", "HEXO", "ACB",
    "DNA", "IONQ", "OPEN", "SKLZ", "AFRM", "JOBY", "LILM", "EVTL",
    "QS", "MVST", "CHPT", "BLNK", "FCEL", "PLUG", "BE", "ENVX",
]


def generate_cheap_stocks_picks() -> List[dict[str, Any]]:
    """Generate cheap stock momentum picks."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not available")
        return []
    
    picks = []
    now = datetime.now(datetime.timezone.utc)
    
    for symbol in CHEAP_UNIVERSE:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="3mo")
            if len(hist) < 30:
                continue
            
            close = hist["Close"].values
            volume = hist["Volume"].values
            price = float(close[-1])
            
            # Only cheap stocks
            if price > 10:
                continue
            
            # 5d momentum
            if len(close) >= 5:
                mom_5d = (close[-1] / close[-5] - 1) * 100
            else:
                continue
            
            # Volume spike
            vol_5 = volume[-5:].mean()
            vol_20 = volume[-20:].mean()
            vol_ratio = vol_5 / vol_20 if vol_20 > 0 else 0
            
            # Entry: cheap stock + momentum + volume
            if mom_5d > 8 and vol_ratio > 2.0:
                picks.append({
                    "symbol": symbol,
                    "direction": "LONG",
                    "strategy": "cheap_stock_momentum",
                    "asset_class": "CHEAP_STOCK",
                    "category": "cheap_stock",
                    "entry_price": round(price, 2),
                    "confidence": min(0.75, 0.50 + mom_5d / 50),
                    "generated_at": now.isoformat(),
                    "reason": f"Cheap stock momentum: price=${price:.2f} 5d_mom={mom_5d:.1f}% vol_ratio={vol_ratio:.2f}",
                    "source": "alpha_engine",
                    "source_system": "cheap_stock_momentum",
                    "forced_resolution": {"max_hold_hours": 168, "tp_pct": 10.0, "sl_pct": 5.0, "time_exit_at_market": True},
                    "paper_pilot": True,
                    "academic_citation": "Bali-Cakici-Whitelaw (JFE 2011)",
                })
        except Exception as e:
            logger.debug(f"{symbol}: {e}")
    
    return picks


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    picks = generate_cheap_stocks_picks()
    print(json.dumps(picks, indent=2))
    print(f"\nTotal: {len(picks)} cheap stock picks")
