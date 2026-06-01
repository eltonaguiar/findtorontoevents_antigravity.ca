"""ETF winner: Faber SMA200 + 3m sector momentum (backtest PF 2.05, WR 70%)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

STRATEGY_NAME = "etf_sector_momentum_winner"
SECTOR_ETFS = ("XLK", "XLF", "XLE", "XLV", "IWM", "TLT", "HYG")
LOOKBACK_SMA = 200
LOOKBACK_MOM = 63
TOP_N = 3
TP_PCT, SL_PCT = 0.05, 0.03


def generate_etf_sector_momentum_winner_picks() -> list[dict[str, Any]]:
    """Inline Faber filter — avoids etf_strategies legacy `from config` import."""
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        return []

    raw = yf.download(list(SECTOR_ETFS), period="1y", progress=False, auto_adjust=True)
    if raw is None or raw.empty:
        return []

    scored: list[tuple[float, str, float, float]] = []
    for sym in SECTOR_ETFS:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                if sym not in raw.columns.get_level_values(1):
                    continue
                close = raw["Close", sym].dropna()
            else:
                continue
            if len(close) < LOOKBACK_SMA + 5:
                continue
            price = float(close.iloc[-1])
            sma200 = float(close.rolling(LOOKBACK_SMA).mean().iloc[-1])
            if price < sma200:
                continue
            ago = float(close.iloc[-LOOKBACK_MOM - 1])
            if ago <= 0:
                continue
            r3m = (price - ago) / ago
            if r3m <= 0:
                continue
            scored.append((r3m, sym, price, r3m))
        except Exception:
            continue

    scored.sort(key=lambda x: x[0], reverse=True)
    now = datetime.now(timezone.utc).isoformat()
    picks: list[dict[str, Any]] = []

    for rank, (_score, sym, px, r3m) in enumerate(scored[:TOP_N], 1):
        conf = min(0.75, max(0.55, 0.58 + 0.10 * min(1.0, r3m * 5)))
        picks.append({
            "symbol": sym,
            "direction": "LONG",
            "strategy": STRATEGY_NAME,
            "asset_class": "ETF",
            "category": "etf",
            "entry_price": round(px, 2),
            "take_profit": round(px * (1 + TP_PCT), 2),
            "stop_loss": round(px * (1 - SL_PCT), 2),
            "confidence": round(conf, 3),
            "generated_at": now,
            "reason": f"ETF sector momentum rank #{rank}: 3m {r3m*100:+.1f}% above SMA200",
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": 720,
                "tp_pct": TP_PCT * 100,
                "sl_pct": SL_PCT * 100,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
        })

    logger.info("%s: %d picks", STRATEGY_NAME, len(picks))
    return picks
