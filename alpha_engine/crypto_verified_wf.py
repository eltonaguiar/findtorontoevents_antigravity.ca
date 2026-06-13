"""
Walk-forward validated crypto sidecars — VWAP reversion + Bollinger MR (Hyro pilot).

Gates (default OFF — opt-in per CLAUDE.md Wire-Up Rule; these sleeves are
backtest / walk-forward validated, NOT forward-validated, so they must not
promote into production by default):
  CRYPTO_VERIFIED_VWAP_ENABLED=1
  CRYPTO_VERIFIED_BOLLINGER_MR_ENABLED=1

Requires WALKFORWARD_REPORT.json sleeve verdict PASS (refresh via walkforward_suite
--only hyro). If that gate module cannot be imported, the sleeve is treated as
NOT-verified and stays off (fail-closed).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]


def _vwap_enabled() -> bool:
    # Default OFF (opt-in): backtest-validated, not forward-validated.
    return os.environ.get("CRYPTO_VERIFIED_VWAP_ENABLED", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _bollinger_enabled() -> bool:
    # Default OFF (opt-in): backtest-validated, not forward-validated.
    return os.environ.get("CRYPTO_VERIFIED_BOLLINGER_MR_ENABLED", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _gate_ok(gate_fn: Callable[[], bool], sleeve: str) -> bool:
    try:
        from verified_strategies.walkforward_gate import sleeve_verdict

        if sleeve_verdict(sleeve) != "PASS":
            logger.warning(
                "crypto_verified_wf: %s blocked — walk-forward verdict != PASS "
                "(run: python3 verified_strategies/walkforward_suite.py --only hyro)",
                sleeve,
            )
            return False
        return gate_fn() if callable(gate_fn) else True
    except ImportError:
        # Fail-CLOSED: if the walk-forward gate module is unavailable we cannot
        # confirm the sleeve passed, so treat it as not-verified and keep it off.
        logger.warning(
            "crypto_verified_wf: %s gate module unavailable — failing closed (sleeve off)",
            sleeve,
        )
        return False


def _scan_with(
    symbols: Optional[List[str]],
    scan_fn: Callable,
    strategy: str,
    source_system: str,
    confidence: float,
    gate_sleeve: str,
    enabled: bool,
) -> List[Dict[str, Any]]:
    if not enabled:
        return []
    if not _gate_ok(lambda: True, gate_sleeve):
        return []

    symbols = symbols or DEFAULT_SYMBOLS
    picks: List[Dict[str, Any]] = []
    try:
        from verified_strategies.data_fetcher import fetch_crypto_ohlcv_paginated
    except ImportError as exc:
        logger.warning("crypto_verified_wf: data_fetcher import failed: %s", exc)
        return []

    now = datetime.now(timezone.utc).isoformat()
    today = now[:10].replace("-", "")

    for sym in symbols:
        try:
            df, _ = fetch_crypto_ohlcv_paginated(sym, target_bars=400)
            if df is None or len(df) < 60:
                continue
            sig = scan_fn(df)
            if not sig:
                continue
            direction = sig.get("direction", "LONG")
            signal_type = "BUY" if direction == "LONG" else "SELL"
            entry = float(sig["entry_price"])
            picks.append({
                "strategy": strategy,
                "source_system": source_system,
                "symbol": sym,
                "asset_class": "CRYPTO",
                "signal_type": signal_type,
                "direction": direction,
                "entry_price": round(entry, 8),
                "take_profit": round(float(sig["tp"]), 8),
                "stop_loss": round(float(sig["sl"]), 8),
                "confidence": round(float(sig.get("confidence", confidence)), 3),
                "reason": sig.get("reason", strategy),
                "timeframe": "1d",
                "timestamp": now,
                "id": f"{strategy}::{sym}::{today}",
            })
        except Exception as exc:
            logger.debug("%s %s: %s", strategy, sym, exc)
    return picks


def scan_crypto_verified_vwap(symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    from verified_strategies.live_signal_scanner import scan_vwap_reversion

    return _scan_with(
        symbols,
        scan_vwap_reversion,
        "crypto_verified_vwap",
        "crypto_verified_vwap",
        0.65,
        "vwap_reversion",
        _vwap_enabled(),
    )


def scan_crypto_verified_bollinger_mr(symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    from verified_strategies.live_signal_scanner import scan_bollinger_mr

    return _scan_with(
        symbols,
        scan_bollinger_mr,
        "crypto_verified_bollinger_mr",
        "crypto_verified_bollinger_mr",
        0.62,
        "bollinger_mr",
        _bollinger_enabled(),
    )
