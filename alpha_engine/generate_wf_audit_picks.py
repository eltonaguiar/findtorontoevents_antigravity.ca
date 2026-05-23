#!/usr/bin/env python3
"""
Emit dashboard picks from walk-forward builtin signals using live Binance OHLCV.

Reads aggregate OOS stats from alpha_engine/data/walk_forward_results.json (when
present) to set confidence from real backtest metadata — not invented numbers.

Output: alpha_engine/data/wf_audit_picks.json (consumed by audit_trail/dashboard_generator).

Excluded from live export: ema_crossover (negative OOS in walk-forward history).
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from alpha_engine.walk_forward_backtester import (  # noqa: E402
    BUILTIN_SIGNALS,
    DEFAULT_SYMBOLS,
    fetch_historical_klines,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
WF_RESULTS = DATA_DIR / "walk_forward_results.json"
OUT_PATH = DATA_DIR / "wf_audit_picks.json"

CANDIDATE_STRATEGIES = (
    "bollinger_bounce",
    "rsi_reversal",
    "funding_rate_contrarian",
)
MIN_AGGREGATE_OOS_WR = 52.0

# ~48h freshness on 4h bars (12 candles); tight 5-bar window often yields zero honest signals.
RECENT_BARS = 12
TP_PCT = 0.03
SL_PCT = 0.015
INTERVAL = "4h"
FETCH_DAYS = 120


def _load_walk_forward_oos_wr() -> dict[str, float]:
    if not WF_RESULTS.exists():
        return {}
    try:
        raw = json.loads(WF_RESULTS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, float] = {}
    for name, payload in (raw.get("strategies") or {}).items():
        agg = (payload or {}).get("aggregate_oos") or {}
        wr = agg.get("win_rate")
        if wr is not None:
            try:
                out[name] = float(wr)
            except (TypeError, ValueError):
                continue
    return out


def _confidence_from_oos(strategy: str, oos_map: dict[str, float]) -> float:
    wr = oos_map.get(strategy)
    if wr is None or math.isnan(wr):
        return 0.55
    c = 0.55 + (max(0.0, min(40.0, wr - 50.0)) / 40.0) * 0.27
    return round(min(0.82, max(0.52, c)), 4)


def _tp_sl(entry: float, side: str) -> tuple[float, float]:
    if side == "BUY":
        return entry * (1.0 + TP_PCT), entry * (1.0 - SL_PCT)
    return entry * (1.0 - TP_PCT), entry * (1.0 + SL_PCT)


def generate_picks() -> list[dict]:
    oos_map = _load_walk_forward_oos_wr()
    picks: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    live_strategies = []
    for s in CANDIDATE_STRATEGIES:
        wr = oos_map.get(s)
        if wr is None:
            continue
        if wr >= MIN_AGGREGATE_OOS_WR:
            live_strategies.append(s)

    for strat_name in live_strategies:
        fn = BUILTIN_SIGNALS.get(strat_name)
        if fn is None:
            continue
        for symbol in DEFAULT_SYMBOLS:
            ohlcv = fetch_historical_klines(symbol, interval=INTERVAL, days=FETCH_DAYS)
            if not ohlcv or len(ohlcv) < 50:
                continue
            try:
                signals = fn(ohlcv)
            except Exception:
                continue
            if not signals:
                continue
            last = signals[-1]
            idx = int(last.get("index", -1))
            if idx < len(ohlcv) - RECENT_BARS:
                continue
            side = str(last.get("side", "")).upper()
            if side not in ("BUY", "SELL"):
                continue
            entry = float(ohlcv[-1][4])
            if entry <= 0:
                continue
            tp, sl = _tp_sl(entry, side)
            signal_type = "LONG" if side == "BUY" else "SHORT"
            oos_wr = oos_map.get(strat_name)
            reason_parts = [
                f"WF builtin {strat_name} @ {INTERVAL}",
                f"signal bar index {idx} (last {RECENT_BARS} bars)",
            ]
            if oos_wr is not None:
                reason_parts.append(f"walk-forward aggregate OOS WR {oos_wr:.1f}%")
            if strat_name == "funding_rate_contrarian":
                reason_parts.append(
                    "proxy: extreme 8-bar momentum (not on-chain funding); regime-sensitive"
                )
            conf = _confidence_from_oos(strat_name, oos_map)
            picks.append(
                {
                    "strategy": strat_name,
                    "symbol": symbol.upper(),
                    "category": "crypto",
                    "signal_type": signal_type,
                    "direction": signal_type,
                    "entry_price": entry,
                    "take_profit": round(tp, 8),
                    "stop_loss": round(sl, 8),
                    "confidence": conf,
                    "risk_reward": round(TP_PCT / SL_PCT, 4),
                    "timeframe": INTERVAL,
                    "reason": "; ".join(reason_parts),
                    "timestamp": now,
                    "extra": {
                        "wf_signal_bar_index": idx,
                        "wf_oos_win_rate_pct": oos_wr,
                        "data_source": "binance_klines_walk_forward_builtin",
                    },
                }
            )
    return picks


def main() -> int:
    os.environ.setdefault("PYTHONUTF8", "1")
    picks = generate_picks()
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "description": "Walk-forward builtins (4h); only strategies with aggregate OOS WR >= 52% in walk_forward_results.json",
        "picks": picks,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(picks)} picks to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
