#!/usr/bin/env python3
"""
MEGA Strategies Forward Runner — scans live symbols and writes picks.

Uses ``mega_crypto_strategies.STRATEGY_REGISTRY`` (long/short Series API), normalizes
Binance OHLCV to Open/High/Low/Close/Volume, matches backtest horizon (4h klines).

Writes ``alpha_engine/data/mega_strategy_picks.json`` for dashboard + smart_picks_engine.

Usage:
    python genome/mutation_lab/mega_forward_runner.py
    python genome/mutation_lab/mega_forward_runner.py --dry-run
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
OUTPUT_FILE = REPO / "alpha_engine" / "data" / "mega_strategy_picks.json"
CONFIG_FILE = REPO / "config" / "mega_strategies_integration.json"

# Base score (0–1) from 4h backtest WR tiers — used before smart_picks mega_weight
MEGA_BASE_SCORE: dict[str, float] = {
    "signal_price_volume_corr": 0.82,
    "signal_open_interest": 0.80,
    "signal_bollinger_squeeze": 0.78,
    "signal_macd_histogram": 0.76,
    "signal_ema_crossover": 0.74,
    "signal_onchain_volume": 0.72,
    "signal_volume_atr_momentum": 0.68,
    "signal_heikin_ashi": 0.62,
    "signal_ttm_squeeze": 0.60,
    "signal_ichimoku": 0.56,
}

# 34 liquid USDT symbols (aligns with MEGA session summary scale)
CRYPTO_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "MATICUSDT", "SHIBUSDT", "LTCUSDT", "BCHUSDT", "ETCUSDT",
    "ATOMUSDT", "NEARUSDT", "APTUSDT", "FILUSDT", "ARBUSDT",
    "OPUSDT", "INJUSDT", "SUIUSDT", "SEIUSDT", "TIAUSDT",
    "WIFUSDT", "PEPEUSDT", "FETUSDT", "RENDERUSDT", "HBARUSDT",
    "STXUSDT", "IMXUSDT", "RUNEUSDT", "GRTUSDT", "FLOWUSDT",
]

BINANCE_MIRRORS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

KL_INTERVAL = "4h"
KL_LIMIT = 500


def _load_forward_eligible() -> set[str]:
    if not CONFIG_FILE.is_file():
        return set()
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return set(cfg.get("forward_test_eligible") or [])
    except Exception:
        return set()


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Binance klines -> columns mega_crypto_strategies expect."""
    if df.empty:
        return df
    out = df.copy()
    cmap = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    for lo, hi in cmap.items():
        if lo in out.columns and hi not in out.columns:
            out[hi] = out[lo]
    need = {"Open", "High", "Low", "Close", "Volume"}
    if not need.issubset(set(out.columns)):
        return pd.DataFrame()
    return out[["Open", "High", "Low", "Close", "Volume"]].copy()


def fetch_ohlcv(symbol: str, interval: str = KL_INTERVAL, limit: int = KL_LIMIT) -> pd.DataFrame:
    import requests

    for mirror in BINANCE_MIRRORS:
        try:
            url = f"{mirror}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 451:
                continue
            resp.raise_for_status()
            data = resp.json()
            raw = pd.DataFrame(
                data,
                columns=[
                    "open_time", "open", "high", "low", "close", "volume",
                    "close_time", "quote_volume", "trades", "taker_buy_base",
                    "taker_buy_quote", "ignore",
                ],
            )
            for col in ["open", "high", "low", "close", "volume"]:
                raw[col] = pd.to_numeric(raw[col], errors="coerce")
            raw["datetime"] = pd.to_datetime(raw["open_time"], unit="ms", utc=True)
            raw.set_index("datetime", inplace=True)
            return raw
        except Exception:
            continue
    return pd.DataFrame()


def _pick_from_ls(
    symbol: str,
    strategy_key: str,
    fn: Callable[[pd.DataFrame], dict[str, Any]],
    df_raw: pd.DataFrame,
    forward_eligible: set[str],
) -> Optional[dict]:
    df_norm = _normalize_ohlcv(df_raw)
    if df_norm.empty or len(df_norm) < 60:
        return None
    try:
        result = fn(df_norm)
    except Exception as e:
        log.debug("%s %s: strategy error %s", symbol, strategy_key, e)
        return None
    if not result:
        return None
    long_s = result.get("long")
    short_s = result.get("short")
    if long_s is None or short_s is None:
        return None
    try:
        is_long = bool(long_s.iloc[-1])
        is_short = bool(short_s.iloc[-1])
    except Exception:
        return None
    if is_long and is_short:
        return None
    if not is_long and not is_short:
        return None

    tp_pct = float(result.get("tp", 0.03))
    sl_pct = float(result.get("sl", 0.015))
    entry = float(df_norm["Close"].iloc[-1])
    if entry <= 0:
        return None

    if is_long:
        direction = "LONG"
        tp = entry * (1.0 + tp_pct)
        sl = entry * (1.0 - sl_pct)
    else:
        direction = "SHORT"
        tp = entry * (1.0 - tp_pct)
        sl = entry * (1.0 + sl_pct)

    base_score = MEGA_BASE_SCORE.get(strategy_key, 0.52)
    if base_score < 0.38:
        return None

    now = datetime.now(timezone.utc)
    pick = {
        "symbol": symbol,
        "strategy": strategy_key,
        "direction": direction,
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "entry_price": round(entry, 8),
        "take_profit": round(tp, 8),
        "stop_loss": round(sl, 8),
        "confidence": round(min(base_score, 0.85), 4),
        "score": round(base_score * 100.0, 1),
        "source_system": "mega_strategies",
        "asset_class": "CRYPTO",
        "category": "crypto",
        "trade_timeframe": "SWING",
        "timeframe": KL_INTERVAL,
        "timestamp": now.isoformat(),
        "created_at": now.isoformat(),
        "_mega_strategy": True,
        "forward_test_eligible": strategy_key in forward_eligible,
        "_signal_details": {
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
            "registry": strategy_key.replace("signal_", "", 1),
        },
    }
    return pick


def _build_crypto_signals() -> dict[str, Callable[[pd.DataFrame], dict[str, Any]]]:
    from genome.mutation_lab.mega_crypto_strategies import STRATEGY_REGISTRY

    out: dict[str, Callable[[pd.DataFrame], dict[str, Any]]] = {}
    for reg_key, fn in STRATEGY_REGISTRY.items():
        out[f"signal_{reg_key}"] = fn
    return out


def run_scan(dry_run: bool = False) -> list:
    """Run all MEGA crypto strategies against live 4h data."""
    forward_eligible = _load_forward_eligible()
    try:
        CRYPTO_SIGNALS = _build_crypto_signals()
    except ImportError as e:
        log.warning("Could not import STRATEGY_REGISTRY: %s", e)
        CRYPTO_SIGNALS = {}

    picks: list[dict] = []
    now = datetime.now(timezone.utc)

    for symbol in CRYPTO_SYMBOLS:
        log.info("Scanning %s...", symbol)
        df_raw = fetch_ohlcv(symbol)
        if df_raw.empty or len(df_raw) < 60:
            log.warning("  %s: insufficient data (%d bars)", symbol, len(df_raw))
            continue

        for strat_name, signal_fn in CRYPTO_SIGNALS.items():
            pick = _pick_from_ls(symbol, strat_name, signal_fn, df_raw, forward_eligible)
            if pick:
                picks.append(pick)
                log.info("  %s %s %s conf=%.2f", symbol, strat_name, pick["direction"], pick["confidence"])

    log.info("Total picks: %d", len(picks))

    if dry_run:
        log.info("[DRY RUN] Not writing files.")
        for p in picks[:12]:
            log.info("  %s %s %s", p["symbol"], p["strategy"], p["direction"])
        return picks

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": now.isoformat(),
        "kline_interval": KL_INTERVAL,
        "kline_limit": KL_LIMIT,
        "strategy_count": len(CRYPTO_SIGNALS),
        "symbol_count": len(CRYPTO_SYMBOLS),
        "picks_count": len(picks),
        "picks": picks,
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
    log.info("Saved %d picks to %s", len(picks), OUTPUT_FILE)

    return picks


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    run_scan(dry_run=dry)
