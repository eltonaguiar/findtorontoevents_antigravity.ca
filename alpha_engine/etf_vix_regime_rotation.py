"""
ETF VIX-Regime Rotation — sector momentum top-3 with VIX overlay.

⚠ INTrabar CAUTION (2026-06-09): The headline PF 4.50 / WR 80.8% is a RAW
backtest (tools/backtest_etf_rotation_vix_regime.py, 2015-2026 monthly data).
This has NOT been validated on the intrabar-true first-touch ledger
(at_signal_outcomes). The strategy is wired to production as a FORWARD-TRACK
ONLY emitter — do NOT size on these backtest numbers. Re-classify as "proven"
only after forward n>=20 WR>=50% PF>1.5 on intrabar data.

Strategy logic:
  1. Rank 11 SPDR sector ETFs by 12-1 month momentum
  2. Long top-3 sectors  
  3. Skip the month when VIX > 25 (defensive overlay)
  4. Monthly rebalance

Wire-Up Rule: wired — etf-agent.yml calls this function directly (forward-track).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 11 SPDR sector ETFs — the core universe for this rotation strategy
VIX_SECTOR_SYMBOLS = [
    "XLF", "XLE", "XLK", "XLV", "XLI",
    "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC",
]

VIX_THRESHOLD = 25  # Skip rebalance month if VIX close > 25
LOOKBACK_MONTHS = 12  # 12-month momentum lookback
SKIP_MONTH = 1  # Skip last month to avoid short-term reversal
N_LONG = 3  # Top N sectors to hold


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _etf_tp_sl(
    close: pd.Series, high: pd.Series, low: pd.Series, direction: str
) -> tuple[float, float, float]:
    """Compute ATR-based entry, TP, SL for ETF positions (monthly timeframe)."""
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=7).mean().iloc[-1]
    if pd.isna(atr) or atr <= 0:
        atr = float(close.iloc[-1] * 0.02)  # fallback: 2% of price

    price = float(close.iloc[-1])
    if direction == "BUY":
        return price, price + 2.5 * atr, price - 1.5 * atr
    else:
        return price, price - 2.5 * atr, price + 1.5 * atr


def etf_vix_regime_rotation(data: dict[str, pd.DataFrame]) -> list[dict]:
    """ETF top-3 sector momentum with VIX<25 regime gate.

    Args:
        data: Dict of symbol -> OHLCV DataFrame with at least 2y history.
              Must include '^VIX' or 'VIX' for the VIX overlay.

    Returns:
        List of pick dicts (empty if VIX > threshold or no signal).
    """
    signals: list[dict[str, Any]] = []

    # ── VIX gate ────────────────────────────────────────────────────────
    vix_df = data.get("^VIX")
    if vix_df is None:
        vix_df = data.get("VIX")
    current_vix: float | None = None
    if vix_df is not None and len(vix_df) > 0:
        vix_close = vix_df["Close"].dropna()
        if len(vix_close) > 0:
            current_vix = float(vix_close.iloc[-1])
            # Also check VIX was recently below threshold — don't enter right
            # after a spike breaks above 25 (volatility clustering)
            recent_vix = vix_close.tail(5).mean()
            if current_vix > VIX_THRESHOLD or recent_vix > VIX_THRESHOLD:
                logger.info(
                    "ETF VIX rotation SKIPPED: VIX=%.1f (threshold=%d, recent5=%.1f)",
                    current_vix, VIX_THRESHOLD, recent_vix,
                )
                return signals  # VIX too high — no rotation this month

    # ── Rank sectors by 12-1 month momentum ──────────────────────────────
    momentum_scores: list[tuple[str, float, pd.DataFrame]] = []
    for symbol in VIX_SECTOR_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 255:
            continue
        close = df["Close"]
        if pd.isna(close.iloc[-1]) or close.iloc[-1] <= 0:
            continue

        # 12-month return, skip last 21 trading days (1 month)
        if len(close) >= 252:
            r12m = float(close.iloc[-22] / close.iloc[-252] - 1)
        elif len(close) >= 126:
            r12m = float(close.iloc[-22] / close.iloc[-126] - 1)  # fallback: 6m
        else:
            continue

        momentum_scores.append((symbol, r12m, df))

    if len(momentum_scores) < N_LONG:
        logger.info("ETF VIX rotation SKIPPED: only %d sectors with data", len(momentum_scores))
        return signals

    # Sort descending by momentum
    momentum_scores.sort(key=lambda x: x[1], reverse=True)

    # Top N sectors with positive momentum → LONG
    top_n = momentum_scores[:N_LONG]
    for rank, (sym, r12m, df) in enumerate(top_n, 1):
        if r12m <= 0:
            continue  # Only buy sectors with positive momentum

        close = df["Close"]
        entry, tp, sl = _etf_tp_sl(close, df["High"], df["Low"], "BUY")
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0

        if rr < 1.20:
            continue

        # Confidence: higher momentum = higher confidence, capped at 0.80
        confidence = round(min(0.80, 0.55 + min(0.25, r12m)), 2)

        signals.append({
            "strategy": "etf_vix_regime_rotation",
            "symbol": sym,
            "category": "etf",
            # 2026-06-09: SHADOW until forward-validated. The PF=4.50/WR=80.8% that
            # motivated this emitter is a BACKTEST number, not intrabar-true forward
            # evidence. Emit to BUILD forward n, but never size on it until it has a
            # clean intrabar-true forward cohort (n>=30) — guards the "promote on raw
            # backtest" trap. See reports/registry_block_verification_2026-06-09.md.
            "forward_test_only": True,
            "forward_validated": False,
            "signal_type": "BUY",
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"VIX Regime Rotation: #{rank} sector, "
                f"12m return={r12m:.1%}, "
                + (f"VIX={current_vix:.0f}<{VIX_THRESHOLD}, " if current_vix is not None else "")
                + f"{sym}"
            ),
            "timeframe": "1M",  # Monthly rebalance
            "extra": {
                "r12m": round(r12m, 4),
                "rank": rank,
                "vix_at_signal": round(float(current_vix), 1) if current_vix is not None else None,
                "total_sectors_ranked": len(momentum_scores),
                "total_bought": len(top_n),
            },
            "timestamp": _now_iso(),
        })

    return signals
