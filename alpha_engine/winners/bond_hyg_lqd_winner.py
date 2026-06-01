"""BOND winner: HYG/LQD 6m momentum (backtest PF 1.65 baseline).

Reproducer: python3 tools/backtest_bond_credit_spread_overlay.py
Evidence: audit_dashboard/data/bond_credit_spread_overlay_backtest.json
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

STRATEGY_NAME = "bond_hyg_lqd_momentum_winner"
UNIVERSE = ("HYG", "LQD")
LOOKBACK = 6
MAX_HOLD_HOURS = 720


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_bond_hyg_lqd_winner_picks() -> list[dict[str, Any]]:
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        return []

    df = yf.download(list(UNIVERSE), period="2y", interval="1mo",
                     progress=False, auto_adjust=True)
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df
    if isinstance(closes, pd.Series):
        closes = closes.to_frame()
    rets = closes.pct_change(fill_method=None).dropna(how="all")
    if len(rets) < LOOKBACK + 2:
        return []

    scores = {}
    for sym in UNIVERSE:
        if sym not in rets.columns:
            continue
        w = rets[sym].iloc[-(LOOKBACK + 1):-1] if len(rets) > LOOKBACK else rets[sym]
        if len(w) < LOOKBACK:
            continue
        scores[sym] = float((1 + w).prod() - 1)

    if not scores:
        return []

    winner = max(scores, key=scores.get)
    mom = scores[winner]
    if mom <= 0:
        logger.info("No positive 6m momentum in HYG/LQD")
        return []

    price = float(closes[winner].dropna().iloc[-1])
    conf = min(0.75, 0.58 + mom * 2)
    tp_pct, sl_pct = 3.0, 2.0
    tp = round(price * (1 + tp_pct / 100), 4)
    sl = round(price * (1 - sl_pct / 100), 4)

    return [{
        "symbol": winner,
        "direction": "LONG",
        "strategy": STRATEGY_NAME,
        "asset_class": "BOND",
        "category": "bond",
        "entry_price": price,
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": round(conf, 3),
        "generated_at": _now_iso(),
        "reason": f"Top 6m momentum in credit pair: {winner} {mom*100:+.1f}%",
        "source": "alpha_engine",
        "source_system": STRATEGY_NAME,
        "forced_resolution": {
            "max_hold_hours": MAX_HOLD_HOURS,
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
            "time_exit_at_market": True,
        },
        "paper_pilot": True,
        "academic_citation": "Bessembinder et al. (2009); credit momentum overlay",
        "extra": {"scores": {k: round(v, 4) for k, v in scores.items()}},
    }]
