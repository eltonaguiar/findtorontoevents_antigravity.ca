"""Thin wrapper: loads CRYPTO OHLCV data → calls atr_percentile_gate_scanner.

Follows trio_bot_strategies.py pattern: self-contained data loading via
alpha_engine.api_failover.fetch_klines() (Binance multi-mirror failover chain).

Wire-Up Rule: wired — production_scanner.py imports and calls this directly.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Same symbol list as proven_edge_strategies.ATR_GATE_SYMBOLS
ATR_GATE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "AVAXUSDT", "LINKUSDT", "ADAUSDT", "DOTUSDT", "NEARUSDT",
    "LTCUSDT", "UNIUSDT", "APTUSDT", "SUIUSDT", "DOGEUSDT",
    "SEIUSDT", "HYPEUSDT", "RENDERUSDT", "OPUSDT", "INJUSDT",
    "ARBUSDT", "FILUSDT", "ATOMUSDT", "TIAUSDT", "PENDLEUSDT",
    "TAOUSDT", "WIFUSDT", "JUPUSDT", "STRKUSDT", "ALGOUSDT", "ETCUSDT",
]


def _to_yf_key(symbol: str) -> str:
    """BTCUSDT → BTC-USD"""
    return symbol.replace("USDT", "-USD")


def _build_data_dict(symbols: list[str], interval: str = "1h", limit: int = 200) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV klines for each symbol, return {yf_key: DataFrame}."""
    from alpha_engine.api_failover import fetch_klines

    data: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            raw = fetch_klines(sym, interval=interval, limit=limit)
            if not raw or len(raw) < 50:
                continue
            # Binance kline format: [time, open, high, low, close, volume, ...]
            df = pd.DataFrame(raw, columns=[
                "timestamp", "Open", "High", "Low", "Close", "Volume",
                "close_time", "quote_vol", "trades", "taker_buy_vol",
                "taker_buy_quote", "ignore",
            ])
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(subset=["Close", "High", "Low"])
            key = _to_yf_key(sym)
            data[key] = df
            logger.debug("ATR gate loaded %s (%d bars)", sym, len(df))
        except Exception as exc:
            logger.warning("ATR gate fetch failed %s: %s", sym, exc)
    return data


def scan_atr_gate(fear_greed: int | None = None) -> list[dict[str, Any]]:
    """Load CRYPTO data → run atr_percentile_gate_scanner → return signals.

    Call from production_scanner.py's signal generation phase.
    Deduplication (symbol+direction) handled by the caller.
    """
    from alpha_engine.proven_edge_strategies import atr_percentile_gate_scanner

    data = _build_data_dict(ATR_GATE_SYMBOLS, interval="1h", limit=200)
    if not data:
        logger.warning("ATR gate: no data loaded, skipping")
        return []

    signals = atr_percentile_gate_scanner(data, fear_greed=fear_greed)
    # 2026-06-09: SHADOW until forward-validated. atr_percentile_gate has only n=2
    # live-resolved picks and ZERO intrabar-true rows — its 58.6% WR is a backtest
    # claim, not forward evidence (it was correctly NOT in CRYPTO_PROVEN_STRATEGIES).
    # Emit to BUILD forward n, but never size on it until it has a clean intrabar-true
    # forward cohort. See reports/registry_block_verification_2026-06-09.md.
    for s in signals:
        s["forward_test_only"] = True
        s["forward_validated"] = False
    logger.info("ATR gate: %d signals from %d symbols loaded (forward_test_only)", len(signals), len(data))
    return signals
