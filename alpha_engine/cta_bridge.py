#!/usr/bin/env python3
"""
CTA Bridge -- Connect CTA Strategy Replicator to Alpha Engine Scanner
=====================================================================
Wraps the 7 academic CTA strategies (TSMOM, Donchian, Golden Cross,
FX Multifactor, Commodity Momentum, Cross-Asset TSMOM) from
copy_trader_intel/cta_strategy_replicator.py into the scanner's
standard strategy dict format.

Also provides conflict resolution: no simultaneous BUY+SELL on same symbol.

Usage:
    from cta_bridge import CTA_BRIDGE_STRATEGIES
    # Then merge into scanner's strategy pool
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Quality gates -- same as forex_strategies.py / proven_forex_strategies.py
try:
    from non_crypto_quality_gate import forex_conf_cap as _gate_conf_cap
    _HAS_CONF_CAP = True
except ImportError:
    _gate_conf_cap = None
    _HAS_CONF_CAP = False

try:
    from auto_tuner import PERMANENTLY_KILLED as _PERMANENTLY_KILLED
except ImportError:
    _PERMANENTLY_KILLED = set()

# Import CTA replicator strategies
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "copy_trader_intel"))

try:
    from cta_strategy_replicator import (
        tsmom_blended,
        donchian_breakout_55,
        golden_cross_200,
        fx_multifactor,
        commodity_momentum_term,
        cross_asset_tsmom,
        CTA_UNIVERSE,
        COMMODITY_SYMBOLS,
        FOREX_SYMBOLS as CTA_FOREX_SYMBOLS,
    )
    _HAS_CTA = True
except ImportError as e:
    print(f"[cta_bridge] WARN: CTA replicator not available: {e}")
    _HAS_CTA = False

# Minimum thresholds for CTA picks to be promoted
MIN_CONFIDENCE = 0.55
MIN_RISK_REWARD = 1.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fx_regime_ok(df: pd.DataFrame) -> tuple[bool, float]:
    """Per-symbol FX volatility regime check (mirrors forex_strategies._fx_regime_ok).

    Returns (ok, vol_ratio) where ok=False means recent vol > 2x baseline.
    This filters out flash-crash and news-event conditions where directional
    strategies lose edge.
    """
    if df is None or len(df) < 65:
        return True, 1.0
    close = df["Close"]
    returns = close.pct_change().dropna()
    if len(returns) < 65:
        return True, 1.0
    vol_20d = float(returns.iloc[-20:].std()) * (252 ** 0.5)
    vol_60d = float(returns.iloc[-60:].std()) * (252 ** 0.5)
    ratio = vol_20d / vol_60d if vol_60d > 0 else 1.0
    return ratio <= 2.0, ratio


def _cta_conf_cap(conf: float, strategy: str) -> float:
    """Apply forex/CTA confidence cap.

    CTA strategies are unvalidated in forward testing, so they get the same
    cap as unvalidated forex strategies (0.65) via the central gate.
    Falls back to a hardcoded 0.65 cap if the gate module isn't available.
    """
    if _HAS_CONF_CAP and _gate_conf_cap is not None:
        return _gate_conf_cap(conf, strategy)
    return min(conf, 0.65)


def _cta_pick_to_signal(pick: dict, strategy_name: str = "") -> dict:
    """Convert a CTA replicator pick dict to the alpha engine signal format.

    Applies forex_conf_cap to keep CTA picks at parity with other
    unvalidated forex/macro strategies (cap 0.65 unless validated).
    """
    raw_conf = pick.get("confidence", 0.6)
    capped_conf = _cta_conf_cap(raw_conf, strategy_name or pick.get("strategy", "cta_unknown"))
    return {
        "strategy": pick.get("strategy", "cta_unknown"),
        "symbol": pick["symbol"],
        "category": pick.get("category", "unknown"),
        "signal_type": pick.get("signal_type", "BUY"),
        "direction": pick.get("direction", "LONG"),
        "entry_price": round(pick["entry_price"], 6),
        "take_profit": round(pick["take_profit"], 6),
        "stop_loss": round(pick["stop_loss"], 6),
        "confidence": round(capped_conf, 3),
        "risk_reward": pick.get("risk_reward", 1.0),
        "reason": pick.get("reason", "CTA academic strategy"),
        "timeframe": "1d",
        "max_hold_bars": pick.get("extra", {}).get("lookback_months", 3) * 5,  # ~weeks
        "source_system": "cta_replicator",
        "extra": pick.get("extra", {}),
        "timestamp": _now_iso(),
    }


def _resolve_conflicts(signals: list[dict]) -> list[dict]:
    """
    Conflict Resolution: if multiple CTA strategies disagree on direction
    for the same symbol, use majority vote. If tied, drop the symbol entirely.
    """
    from collections import defaultdict

    symbol_signals = defaultdict(list)
    for s in signals:
        symbol_signals[s["symbol"]].append(s)

    resolved = []
    for symbol, sigs in symbol_signals.items():
        buy_count = sum(1 for s in sigs if s["signal_type"] == "BUY")
        sell_count = sum(1 for s in sigs if s["signal_type"] == "SELL")

        if buy_count > 0 and sell_count > 0:
            # Conflict detected — use majority vote
            if buy_count > sell_count:
                # Keep only BUY signals, pick highest confidence
                winner = max(
                    [s for s in sigs if s["signal_type"] == "BUY"],
                    key=lambda x: x.get("confidence", 0)
                )
                winner["reason"] = f"[Consensus {buy_count}v{sell_count} BUY] " + winner.get("reason", "")
                resolved.append(winner)
            elif sell_count > buy_count:
                # Keep only SELL signals, pick highest confidence
                winner = max(
                    [s for s in sigs if s["signal_type"] == "SELL"],
                    key=lambda x: x.get("confidence", 0)
                )
                winner["reason"] = f"[Consensus {sell_count}v{buy_count} SELL] " + winner.get("reason", "")
                resolved.append(winner)
            else:
                # Tied — drop entirely (no edge)
                continue
        else:
            # No conflict — keep highest confidence signal per symbol
            best = max(sigs, key=lambda x: x.get("confidence", 0))
            resolved.append(best)

    return resolved


# ---------------------------------------------------------------------------
# Strategy wrapper functions (Pattern 3: func(data) -> list[dict])
# ---------------------------------------------------------------------------

def cta_tsmom_blend(data: dict[str, pd.DataFrame]) -> list[dict]:
    """TSMOM Blended (1/3/12 month) across all CTA universe assets."""
    if not _HAS_CTA:
        return []
    signals = []
    for symbol in CTA_UNIVERSE:
        df = data.get(symbol)
        if df is None:
            continue
        # Volatility regime gate (same as forex_strategies)
        regime_ok, _vr = _fx_regime_ok(df)
        if not regime_ok:
            continue
        try:
            pick = tsmom_blended(df, symbol)
            if pick and pick.get("confidence", 0) >= MIN_CONFIDENCE:
                sig = _cta_pick_to_signal(pick, "cta_tsmom_blend")
                sig["strategy"] = "cta_tsmom_blend"
                signals.append(sig)
        except Exception:
            pass
    return signals


def cta_donchian_55(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Donchian 55-day breakout (Turtle Trading System 2)."""
    if not _HAS_CTA:
        return []
    signals = []
    for symbol in CTA_UNIVERSE:
        df = data.get(symbol)
        if df is None:
            continue
        regime_ok, _vr = _fx_regime_ok(df)
        if not regime_ok:
            continue
        try:
            pick = donchian_breakout_55(df, symbol)
            if pick and pick.get("confidence", 0) >= MIN_CONFIDENCE:
                sig = _cta_pick_to_signal(pick, "cta_donchian_55")
                sig["strategy"] = "cta_donchian_55"
                signals.append(sig)
        except Exception:
            pass
    return signals


def cta_golden_cross(data: dict[str, pd.DataFrame]) -> list[dict]:
    """50/200 SMA Golden/Death Cross with ADX trending filter."""
    if not _HAS_CTA:
        return []
    signals = []
    for symbol in CTA_UNIVERSE:
        df = data.get(symbol)
        if df is None:
            continue
        regime_ok, _vr = _fx_regime_ok(df)
        if not regime_ok:
            continue
        try:
            pick = golden_cross_200(df, symbol)
            if pick and pick.get("confidence", 0) >= MIN_CONFIDENCE:
                sig = _cta_pick_to_signal(pick, "cta_golden_cross")
                sig["strategy"] = "cta_golden_cross"
                signals.append(sig)
        except Exception:
            pass
    return signals


def cta_fx_multifactor(data: dict[str, pd.DataFrame]) -> list[dict]:
    """FX Carry + Momentum + Value multifactor (Brunnermeier et al. 2009)."""
    if not _HAS_CTA:
        return []
    signals = []
    for symbol in CTA_FOREX_SYMBOLS:
        df = data.get(symbol)
        if df is None:
            continue
        regime_ok, _vr = _fx_regime_ok(df)
        if not regime_ok:
            continue
        try:
            pick = fx_multifactor(df, symbol)
            if pick and pick.get("confidence", 0) >= MIN_CONFIDENCE:
                sig = _cta_pick_to_signal(pick, "cta_fx_multifactor")
                sig["strategy"] = "cta_fx_multifactor"
                sig["category"] = "forex"
                signals.append(sig)
        except Exception:
            pass
    return signals


def cta_commodity_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Commodity Momentum + Term Structure ranking (Moskowitz et al. 2012)."""
    if not _HAS_CTA:
        return []
    signals = []
    for symbol in COMMODITY_SYMBOLS:
        df = data.get(symbol)
        if df is not None:
            regime_ok, _vr = _fx_regime_ok(df)
            if not regime_ok:
                continue
        try:
            pick = commodity_momentum_term(data, symbol)
            if pick and pick.get("confidence", 0) >= MIN_CONFIDENCE:
                sig = _cta_pick_to_signal(pick, "cta_commodity_momentum")
                sig["strategy"] = "cta_commodity_momentum"
                sig["category"] = "commodity"
                signals.append(sig)
        except Exception:
            pass
    return signals


def cta_cross_asset_tsmom(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Cross-Asset TSMOM (Pitkajarvi & Suominen 2020, Sharpe ~1.84)."""
    if not _HAS_CTA:
        return []
    try:
        picks = cross_asset_tsmom(data)
        signals = []
        for pick in picks:
            if pick.get("confidence", 0) >= MIN_CONFIDENCE:
                # Vol regime gate per symbol
                sym = pick.get("symbol", "")
                df = data.get(sym)
                if df is not None:
                    regime_ok, _vr = _fx_regime_ok(df)
                    if not regime_ok:
                        continue
                sig = _cta_pick_to_signal(pick, "cta_cross_asset_tsmom")
                sig["strategy"] = "cta_cross_asset_tsmom"
                signals.append(sig)
        return signals
    except Exception:
        return []


def cta_all_strategies(data: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Master CTA bridge: runs ALL CTA strategies, applies conflict resolution,
    and returns deduplicated signals.

    This is the recommended entry point for the scanner.
    """
    if not _HAS_CTA:
        return []

    all_signals = []

    # Run each CTA strategy
    for func in [cta_tsmom_blend, cta_donchian_55, cta_golden_cross,
                 cta_fx_multifactor, cta_commodity_momentum, cta_cross_asset_tsmom]:
        # Use case-insensitive comparison
        if func.__name__.lower() in {s.lower() for s in _PERMANENTLY_KILLED}:
            continue
        try:
            sigs = func(data)
            if sigs:
                all_signals.extend(sigs)
        except Exception:
            pass

    # Apply conflict resolution (majority vote on same-symbol disagreements)
    resolved = _resolve_conflicts(all_signals)

    # Filter by minimum R:R
    resolved = [s for s in resolved if s.get("risk_reward", 0) >= MIN_RISK_REWARD]

    return resolved


# ---------------------------------------------------------------------------
# Strategy dict for scanner integration
# ---------------------------------------------------------------------------

CTA_BRIDGE_STRATEGIES = {
    "cta_tsmom_blend": cta_tsmom_blend,
    "cta_donchian_55": cta_donchian_55,
    "cta_golden_cross": cta_golden_cross,
    "cta_fx_multifactor": cta_fx_multifactor,
    "cta_commodity_momentum": cta_commodity_momentum,
    "cta_cross_asset_tsmom": cta_cross_asset_tsmom,
}


if __name__ == "__main__":
    print("CTA Bridge -- Testing strategy availability")
    print(f"  CTA available: {_HAS_CTA}")
    print(f"  Strategies: {list(CTA_BRIDGE_STRATEGIES.keys())}")
    if _HAS_CTA:
        print(f"  CTA Universe: {len(CTA_UNIVERSE)} assets")
        print(f"  Commodity symbols: {COMMODITY_SYMBOLS}")
        print(f"  Forex symbols: {CTA_FOREX_SYMBOLS}")
