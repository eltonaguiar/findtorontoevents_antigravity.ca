"""FUTURES winner: diversified time-series momentum (backtest PF 1.68, WR 58%).

Reproducer: python3 tools/backtest_futures_ts_momentum.py
Evidence: audit_dashboard/data/futures_ts_momentum_backtest.json
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

STRATEGY_NAME = "futures_tsmom_winner"
UNIVERSE = ("ES=F", "NQ=F", "GC=F", "HG=F", "ZN=F", "6E=F")
LOOKBACK = 12
MAX_HOLD_HOURS = 720


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_futures_tsmom_winner_picks() -> list[dict[str, Any]]:
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        logger.warning("yfinance required for futures_tsmom_winner")
        return []

    end = datetime.now(timezone.utc)
    start = (end.replace(year=end.year - 2)).strftime("%Y-%m-%d")
    tickers = list(UNIVERSE)
    df = yf.download(tickers, start=start, end=end.strftime("%Y-%m-%d"),
                     interval="1mo", progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series):
        closes = closes.to_frame()
    rets = closes.pct_change(fill_method=None).dropna(how="all")
    if len(rets) < LOOKBACK + 2:
        return []

    picks: list[dict[str, Any]] = []
    now = _now_iso()

    for sym in tickers:
        if sym not in rets.columns:
            continue
        col = rets[sym].dropna()
        if len(col) < LOOKBACK:
            continue
        mom = float((1 + col.iloc[-LOOKBACK:]).prod() - 1)
        if abs(mom) < 0.02:
            continue
        direction = "LONG" if mom > 0 else "SHORT"
        try:
            px = float(closes[sym].dropna().iloc[-1])
        except Exception:
            continue
        if px <= 0:
            continue
        conf = min(0.76, 0.58 + min(abs(mom), 0.15) * 1.2)
        tp_pct = 4.0
        sl_pct = 2.5
        if direction == "LONG":
            tp, sl = round(px * (1 + tp_pct / 100), 4), round(px * (1 - sl_pct / 100), 4)
        else:
            tp, sl = round(px * (1 - tp_pct / 100), 4), round(px * (1 + sl_pct / 100), 4)

        picks.append({
            "symbol": sym,
            "direction": direction,
            "strategy": STRATEGY_NAME,
            "asset_class": "FUTURES",
            "category": "futures",
            "entry_price": px,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(conf, 3),
            "generated_at": now,
            "reason": f"12m TS-momentum {mom*100:+.1f}% → {direction} (Moskowitz et al. 2012)",
            "source": "alpha_engine",
            "source_system": STRATEGY_NAME,
            "forced_resolution": {
                "max_hold_hours": MAX_HOLD_HOURS,
                "tp_pct": tp_pct,
                "sl_pct": sl_pct,
                "time_exit_at_market": True,
            },
            "paper_pilot": True,
            "academic_citation": "Moskowitz, Ooi & Pedersen (2012)",
            "extra": {"momentum_12m": round(mom, 4), "probation": True},
        })

    logger.info("%s: %d contract signals", STRATEGY_NAME, len(picks))
    return picks
