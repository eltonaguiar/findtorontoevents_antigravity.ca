"""
Live scanner integration for Unique Edge strategies (LSR, OBB, VDR, VRM, SMC).

Uses real OHLCV from ``unique_edge_strategies.fetch_real_data`` (Binance / KuCoin / OKX
failover) on the same 45-pair universe as the 8,803-trade backtest. Emits a pick only
when the latest *completed* bar (index -2) matches a signal — no lookahead.

Scanner contract: ``(data: dict, context: dict | None) -> list[dict]`` (``data`` unused;
feeds match other live Binance-backed crypto strategies).
"""

from __future__ import annotations

import importlib.util
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
UES_PATH = REPO_ROOT / "unique_edge_strategies.py"

ues: Any = None
if UES_PATH.is_file():
    _spec = importlib.util.spec_from_file_location("unique_edge_strategies", str(UES_PATH))
    if _spec and _spec.loader:
        ues = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(ues)

try:
    from config import CRYPTO_SYMBOLS
except ImportError:
    CRYPTO_SYMBOLS = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sleep_rl() -> None:
    time.sleep(0.04)


# Same scanner pass runs multiple edge strategies — cache OHLCV briefly per (exchange, symbol, interval).
_FETCH_CACHE: dict[tuple[str, str, str], tuple[float, Optional[list]]] = {}
_FETCH_TTL_SEC = 90.0


def _get_candles(exchange: str, symbol: str, interval: str) -> Optional[list]:
    if ues is None:
        return None
    key = (exchange, symbol, interval)
    now = time.monotonic()
    ent = _FETCH_CACHE.get(key)
    if ent is not None and (now - ent[0]) < _FETCH_TTL_SEC:
        return ent[1]
    candles = ues.fetch_real_data(exchange, symbol, interval)
    _sleep_rl()
    _FETCH_CACHE[key] = (now, candles)
    return candles


def _pick_from_signals(
    symbol: str,
    strategy_key: str,
    signals: list,
    candles: list,
    timeframe: str,
) -> Optional[dict]:
    if not signals or not candles or len(candles) < 10:
        return None
    idx_target = len(candles) - 2
    sig = None
    for s in reversed(signals):
        if s.get("index") == idx_target:
            sig = s
            break
    if sig is None:
        return None
    direction = str(sig.get("type", "LONG")).upper()
    st = "BUY" if direction == "LONG" else "SELL"
    entry = float(sig["entry"])
    sl = float(sig["sl"])
    tp = float(sig["tp"])
    rr = float(sig.get("rr") or (abs(tp - entry) / max(abs(entry - sl), 1e-12)))
    cat = CRYPTO_SYMBOLS.get(symbol, {}).get("cat", "crypto_alt")
    conf = min(0.78, 0.52 + min(rr / 4.0, 0.12) + (0.04 if strategy_key == "unique_edge_smc" else 0.0))
    return {
        "strategy": strategy_key,
        "symbol": symbol,
        "category": cat,
        "signal_type": st,
        "direction": direction,
        "entry_price": round(entry, 10),
        "take_profit": round(tp, 10),
        "stop_loss": round(sl, 10),
        "confidence": round(conf, 3),
        "risk_reward": round(rr, 2),
        "reason": str(sig.get("reason", strategy_key)),
        "timeframe": timeframe,
        "max_hold_bars": 48,
        "timestamp": _now_iso(),
        "extra": {"unique_edge": True, "edge_code": strategy_key.replace("unique_edge_", "").upper()},
    }


def _scan_simple(
    strategy_key: str,
    fn: Callable[[list], list],
    interval: str = "1h",
) -> List[dict]:
    if ues is None:
        return []
    picks: List[dict] = []
    pairs = getattr(ues, "USER_PICKS", [])
    for exchange, symbol in pairs:
        candles = _get_candles(exchange, symbol, interval)
        if not candles or len(candles) < 55:
            continue
        try:
            sigs = fn(candles)
        except Exception:
            continue
        p = _pick_from_signals(symbol, strategy_key, sigs, candles, interval)
        if p:
            picks.append(p)
    return picks


def unique_edge_lsr(data: dict, context: Optional[dict] = None) -> List[dict]:
    del data, context
    if ues is None:
        return []
    return _scan_simple("unique_edge_lsr", ues.strategy_liquidity_sweep, "1h")


def unique_edge_obb(data: dict, context: Optional[dict] = None) -> List[dict]:
    del data, context
    if ues is None:
        return []
    return _scan_simple("unique_edge_obb", ues.strategy_order_block, "1h")


def unique_edge_vdr(data: dict, context: Optional[dict] = None) -> List[dict]:
    del data, context
    if ues is None:
        return []
    return _scan_simple("unique_edge_vdr", ues.strategy_vwap_deviation, "1h")


def unique_edge_vrm(data: dict, context: Optional[dict] = None) -> List[dict]:
    del data, context
    if ues is None:
        return []
    return _scan_simple("unique_edge_vrm", ues.strategy_volatility_regime, "1h")


def unique_edge_smc(data: dict, context: Optional[dict] = None) -> List[dict]:
    del data, context
    if ues is None:
        return []
    picks: List[dict] = []
    for exchange, symbol in getattr(ues, "USER_PICKS", []):
        d15 = _get_candles(exchange, symbol, "15m")
        d1h = _get_candles(exchange, symbol, "1h")
        d4h = _get_candles(exchange, symbol, "4h")
        if not d15 or not d1h or not d4h or len(d1h) < 55:
            continue
        try:
            sigs = ues.strategy_smart_money_confluence(d15, d1h, d4h)
        except Exception:
            continue
        p = _pick_from_signals(symbol, "unique_edge_smc", sigs, d1h, "MTF")
        if p:
            picks.append(p)
    return picks


UNIQUE_EDGE_CRYPTO_STRATEGIES = {
    "unique_edge_lsr": unique_edge_lsr,
    "unique_edge_obb": unique_edge_obb,
    "unique_edge_vdr": unique_edge_vdr,
    "unique_edge_vrm": unique_edge_vrm,
    "unique_edge_smc": unique_edge_smc,
}
