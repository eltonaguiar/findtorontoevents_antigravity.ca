"""Callable wrappers for dormant winner strategies.

These wrappers expose private helper masks from
``alpha_engine/crypto_strategy_harness.py`` as pick-emitting callables that
return ``list[dict]`` rows compatible with the audit pick schema.

NON-PRODUCTION: these wrappers do not write to any DB, do not mutate the
strategy registry, and do not call ``calculate_smart_score`` /
``passes_active_gate``. They are read-only generators intended for the
dormant-winners revival flow (operator triggers + opt-in sidecar use).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# Universe + OHLCV fetcher
# ---------------------------------------------------------------------------

# Top-15 USDT perps mirrors the universe used by ``justin_breakout`` wrappers
# (BTC/ETH/SOL/BNB/XRP + the highest-volume mid-caps). Keeping the list
# co-located so both wrappers stay in sync without an extra module import.
TOP15_USDT_PERPS: List[str] = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "TRXUSDT",
    "DOTUSDT", "MATICUSDT", "LTCUSDT", "BCHUSDT", "ATOMUSDT",
]


def _interval_to_minutes(interval: str) -> int:
    """Crude interval -> minutes converter for non-Binance providers."""
    s = interval.strip().lower()
    if s.endswith("m"):
        return int(s[:-1])
    if s.endswith("h"):
        return int(s[:-1]) * 60
    if s.endswith("d"):
        return int(s[:-1]) * 60 * 24
    return 60  # default 1h


def _kucoin_interval(interval: str) -> str:
    """Map Binance-style interval to KuCoin's klines `type` param."""
    table = {"1m":"1min","3m":"3min","5m":"5min","15m":"15min","30m":"30min",
             "1h":"1hour","2h":"2hour","4h":"4hour","6h":"6hour","8h":"8hour",
             "12h":"12hour","1d":"1day","1w":"1week"}
    return table.get(interval, "1hour")


def _fetch_klines_cryptocompare(symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    """CryptoCompare public histohour/histoday endpoints. No API key needed."""
    import requests
    base_sym = symbol.replace("USDT", "").replace("USD", "")
    quote_sym = "USDT" if symbol.endswith("USDT") else "USD"
    mins = _interval_to_minutes(interval)
    # Map to histo endpoint
    if mins >= 1440:
        endpoint, agg = "histoday", mins // 1440
    elif mins >= 60:
        endpoint, agg = "histohour", mins // 60
    else:
        endpoint, agg = "histominute", mins
    try:
        r = requests.get(
            f"https://min-api.cryptocompare.com/data/v2/{endpoint}",
            params={"fsym": base_sym, "tsym": quote_sym, "limit": limit, "aggregate": agg},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        data = r.json().get("Data", {}).get("Data", [])
        if not data:
            return None
        df = pd.DataFrame(data)
        df = df.rename(columns={"time": "open_time", "volumefrom": "volume"})
        df["open_time"] = df["open_time"] * 1000  # match Binance ms
        return df[["open_time", "open", "high", "low", "close", "volume"]].dropna()
    except Exception:
        return None


def _fetch_klines_kucoin(symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    """KuCoin public market/candles endpoint."""
    import requests
    # KuCoin uses BTC-USDT format
    base_sym = symbol.replace("USDT", "")
    pair = f"{base_sym}-USDT"
    try:
        r = requests.get(
            "https://api.kucoin.com/api/v1/market/candles",
            params={"symbol": pair, "type": _kucoin_interval(interval)},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        rows = r.json().get("data") or []
        if not rows:
            return None
        # KuCoin returns newest first; reverse + slice
        rows = list(reversed(rows))[-limit:]
        df = pd.DataFrame(rows, columns=["open_time", "open", "close", "high", "low", "volume", "turnover"])
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["open_time"] = pd.to_numeric(df["open_time"]) * 1000
        return df[["open_time", "open", "high", "low", "close", "volume"]].dropna()
    except Exception:
        return None


def _fetch_klines_binance(symbol: str, interval: str = "1h", limit: int = 200) -> Optional[pd.DataFrame]:
    """Fetch OHLCV with API failover chain per CLAUDE.md "API Failover Rule":

      Binance mirrors (api, api1, api2, api3) -> CryptoCompare -> KuCoin

    Binance returns HTTP 451 from GitHub Actions / AWS / Azure IPs (geo-block).
    The 2026-06-02 cron dry-run found every Binance mirror 451'd. This failover
    chain ensures the strategy receives data from at least one source.

    Returns a DataFrame with columns: open_time, open, high, low, close, volume.
    Returns None on total failure (caller skips the symbol).
    """
    import requests  # local import — keeps module importable when offline

    # ----- Try 1: Binance mirrors (fastest when not 451'd) -----
    mirrors = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]
    saw_451 = False
    for base in mirrors:
        try:
            r = requests.get(
                f"{base}/api/v3/klines",
                params={"symbol": symbol, "interval": interval, "limit": limit},
                timeout=8,
            )
            if r.status_code == 451:
                saw_451 = True
                # All Binance mirrors are geo-blocked from the same egress IP;
                # skip the remaining mirrors and try a different provider.
                break
            if r.status_code != 200:
                continue
            rows = r.json()
            if not rows:
                continue
            df = pd.DataFrame(
                rows,
                columns=[
                    "open_time", "open", "high", "low", "close", "volume",
                    "close_time", "qav", "trades", "tbb", "tbq", "ignore",
                ],
            )
            for col in ("open", "high", "low", "close", "volume"):
                df[col] = pd.to_numeric(df[col], errors="coerce")
            return df[["open_time", "open", "high", "low", "close", "volume"]].dropna()
        except Exception:
            continue

    # ----- Try 2: CryptoCompare (no API key, generous public tier) -----
    df = _fetch_klines_cryptocompare(symbol, interval, limit)
    if df is not None and not df.empty:
        return df

    # ----- Try 3: KuCoin (no geo-block from most cloud IPs) -----
    df = _fetch_klines_kucoin(symbol, interval, limit)
    if df is not None and not df.empty:
        return df

    return None


# ---------------------------------------------------------------------------
# Keltner indicator (mirrors crypto_strategy_harness.keltner_channels)
# ---------------------------------------------------------------------------

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _keltner_channels(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    ema_period: int = 20,
    atr_period: int = 10,
    mult: float = 2.0,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    middle = _ema(close, ema_period)
    atr_val = _atr(high, low, close, atr_period)
    upper = middle + mult * atr_val
    lower = middle - mult * atr_val
    return upper, middle, lower


def _detect_lower_band_bounce(df: pd.DataFrame, ema_p: int = 20, atr_p: int = 10, mult: float = 2.0) -> bool:
    """Replicates `CryptoStrategyHarness._keltner_bounce` semantics:
    close was at-or-below lower band on prior bar and crossed above on the last bar.
    """
    if len(df) < max(ema_p, atr_p) + 5:
        return False
    _, _, lower = _keltner_channels(df["high"], df["low"], df["close"], ema_p, atr_p, mult)
    close = df["close"]
    mask = (close > lower) & (close.shift(1) <= lower.shift(1))
    return bool(mask.iloc[-1])


# ---------------------------------------------------------------------------
# Public callable
# ---------------------------------------------------------------------------

def generate_keltner_bounce_picks(
    symbols: Optional[List[str]] = None,
    interval: str = "1h",
    ema_period: int = 20,
    atr_period: int = 10,
    mult: float = 2.0,
    tp_pct: float = 0.02,
    sl_pct: float = 0.015,
    max_hold_hours: int = 48,
) -> List[Dict[str, Any]]:
    """Emit LONG picks for top-15 USDT perps that just bounced off the lower Keltner band.

    Standard config: EMA(close,20) +/- 2.0 * ATR(10). Entry when the last
    closed candle crosses up through the lower band (prior close <= lower,
    current close > lower).

    Returns a list of pick dicts. Empty list if no bounces or all fetches failed.
    """
    syms = symbols or TOP15_USDT_PERPS
    picks: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=max_hold_hours)

    for sym in syms:
        df = _fetch_klines_binance(sym, interval=interval, limit=max(ema_period, atr_period) * 5 + 50)
        if df is None or df.empty:
            continue
        if not _detect_lower_band_bounce(df, ema_period, atr_period, mult):
            continue

        entry = float(df["close"].iloc[-1])
        tp = entry * (1.0 + tp_pct)
        sl = entry * (1.0 - sl_pct)

        picks.append({
            "source_system": "dormant_keltner_bounce",
            "symbol": sym,
            "asset_class": "CRYPTO",
            "direction": "LONG",
            "entry_price": entry,
            "take_profit": tp,
            "stop_loss": sl,
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
            "max_hold_hours": max_hold_hours,
            "interval": interval,
            "signal_ts": now.isoformat(),
            "expires_at": expires.isoformat(),
            "strategy": "keltner_bounce",
            "params": {
                "ema_period": ema_period,
                "atr_period": atr_period,
                "mult": mult,
            },
            "rationale": (
                f"close crossed above lower Keltner band "
                f"(EMA{ema_period} - {mult}*ATR{atr_period}) on {interval}"
            ),
        })

    return picks


# ---------------------------------------------------------------------------
# justin_breakout_volume_v2 wrapper
# ---------------------------------------------------------------------------

def generate_justin_breakout_picks(
    symbols: Optional[List[str]] = None,
    interval: str = "1h",
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Zero-arg callable wrapper for ``justin_breakout_volume_v2``.

    Fetches OHLCV for the top-15 USDT perps and invokes the underlying
    strategy. Returns the strategy's pick dicts unchanged (schema:
    symbol, direction, entry_price, take_profit, stop_loss, confidence,
    strategy, timestamp, reason).
    """
    # Local import keeps this module importable even if the strategy file
    # has a heavy transitive import chain.
    from alpha_engine.justin_bravo_strategies_v2 import justin_breakout_volume_v2

    syms = symbols or TOP15_USDT_PERPS
    data: Dict[str, pd.DataFrame] = {}
    for sym in syms:
        df = _fetch_klines_binance(sym, interval=interval, limit=limit)
        if df is None or len(df) < 30:
            continue
        # justin_breakout_volume_v2 reads df['close'/'high'/'low'/'volume']
        data[sym] = df[["open", "high", "low", "close", "volume"]].reset_index(drop=True)

    if not data:
        return []

    try:
        picks = justin_breakout_volume_v2(data)
    except Exception:
        return []

    return picks or []


# ---------------------------------------------------------------------------
# Mutation-validated paper-pilot variant (M-107 mutation protocol pass, 2026-06-01)
# ---------------------------------------------------------------------------

def generate_keltner_bounce_v2_wide_picks() -> List[Dict[str, Any]]:
    """Paper-pilot Keltner-bounce variant — wider bands (mult=3.0).

    Mutation-hunt 2026-06-01 (tools/mutation_hunt_2026-06-01.py +
    reports/mutation_hunt_2026-06-01.json) ran the M-107 3-axis mutation
    protocol on the baseline keltner_bounce (PF 0.995 NO_EDGE) and found
    that the wider mult=3.0 band yields T3-passing performance:

        ema_period=20, atr_period=10, mult=3.0
        n=677, WR=46.4%, PF=1.145, DSR=7.88, PF_LB95=1.10

    Fewer-but-higher-quality bounces — the wider band rejects noise that
    fired the baseline strategy too often. Wilson LB on WR remains
    sub-50 (~41%) so this is asymmetric-payoff edge, not WR edge.

    Tagged with a distinct strategy name so the resolver tracks it
    independently from the baseline keltner_bounce (which goes to the
    block-list separately).

    Per CLAUDE.md: this is paper-pilot only. Sizing requires 30+ days of
    rolling forward proof + PF_LB > 1.05 on rolling 60d window.
    """
    picks = generate_keltner_bounce_picks(
        ema_period=20,
        atr_period=10,
        mult=3.0,
        tp_pct=0.02,
        sl_pct=0.015,
        max_hold_hours=48,
    )
    # Re-tag strategy so attribution + block-list management stays clean
    for p in picks:
        p["strategy"] = "keltner_bounce_v2_wide"
        p["paper_pilot"] = True
        p["forward_test_only"] = True
        p["forward_validated"] = False
    return picks


if __name__ == "__main__":
    # Dry-run helper (no DB writes).
    out = generate_keltner_bounce_picks()
    print(f"keltner_bounce dry-run: {len(out)} pick(s)")
    for p in out:
        print(f"  {p['symbol']:10s} entry={p['entry_price']:.6g} tp={p['take_profit']:.6g} sl={p['stop_loss']:.6g}")

    out_wide = generate_keltner_bounce_v2_wide_picks()
    print(f"keltner_bounce_v2_wide dry-run: {len(out_wide)} pick(s)")
    for p in out_wide:
        print(f"  {p['symbol']:10s} entry={p['entry_price']:.6g} tp={p['take_profit']:.6g} sl={p['stop_loss']:.6g}")

    out2 = generate_justin_breakout_picks()
    print(f"justin_breakout_volume_v2 dry-run: {len(out2)} pick(s)")
    for p in out2[:5]:
        print(f"  {p.get('symbol'):10s} {p.get('direction')} entry={p.get('entry_price')}")
