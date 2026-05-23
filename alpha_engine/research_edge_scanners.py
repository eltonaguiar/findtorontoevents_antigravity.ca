"""
Research-backed edge scanners (Gainer / FX desk synthesis).

1) crypto_rvol_1h_momentum_scanner — Binance 1H klines: RVOL >= 3x vs 20-bar mean,
   taker buy ratio >= 0.65, RSI(14) > 50 on hourly closes. Multi-mirror Binance
   failover; universe = top N USDT pairs by 24h quote volume (real API data).

No placeholder symbols — scans live exchange metadata + klines only.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

_ae_dir = Path(__file__).resolve().parent
if str(_ae_dir) not in sys.path:
    sys.path.insert(0, str(_ae_dir))
from config import CRYPTO_SYMBOLS

BINANCE_KLINE_BASES: tuple[str, ...] = (
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
)

# Scan depth: balance API load vs coverage (ticker = 1 call; klines = 1/symbol)
_TOP_VOLUME_N = 40
_RVOL_LOOKBACK = 20
_RVOL_MIN = 3.0
_BUY_RATIO_MIN = 0.65
_RSI_MIN = 50.0
_KLINES_LIMIT = 120


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_get_json(url: str, timeout: float = 12.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AlphaEngine/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _top_usdt_by_quote_volume(limit: int) -> list[str]:
    """Return top ``limit`` USDT spot symbols by 24h quote volume."""
    for base in BINANCE_KLINE_BASES:
        try:
            raw = _http_get_json(f"{base}/api/v3/ticker/24hr")
        except Exception:
            continue
        if not isinstance(raw, list):
            continue
        cands: list[tuple[str, float]] = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            sym = str(row.get("symbol") or "")
            if not sym.endswith("USDT"):
                continue
            # Skip obvious leveraged / structured tokens (heuristic)
            if any(x in sym for x in ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")):
                continue
            try:
                qv = float(row.get("quoteVolume") or 0.0)
            except (TypeError, ValueError):
                qv = 0.0
            cands.append((sym, qv))
        cands.sort(key=lambda t: t[1], reverse=True)
        out = [s for s, _ in cands[:limit]]
        if out:
            return out
    return []


def _fetch_klines_1h(symbol: str) -> Optional[list[list[Any]]]:
    sym = symbol.upper()
    for base in BINANCE_KLINE_BASES:
        url = f"{base}/api/v3/klines?symbol={sym}&interval=1h&limit={_KLINES_LIMIT}"
        try:
            raw = _http_get_json(url)
        except Exception:
            continue
        if isinstance(raw, list) and len(raw) >= _RVOL_LOOKBACK + 5:
            return raw
    return None


def _rsi_last(closes: np.ndarray, period: int = 14) -> float:
    """Wilder RSI on the last bar (``closes`` oldest -> newest)."""
    if len(closes) < period + 1:
        return float("nan")
    s = pd.Series(closes, dtype=float)
    d = s.diff()
    up = d.clip(lower=0.0)
    down = (-d).clip(lower=0.0)
    ma_u = up.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    ma_d = down.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = ma_u / ma_d.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return float(rsi.iloc[-1])


def _atr_pct(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 14) -> float:
    if len(close) < n + 1:
        return 0.01
    h = pd.Series(high, dtype=float)
    l = pd.Series(low, dtype=float)
    c = pd.Series(close, dtype=float)
    pc = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = float(tr.ewm(span=n, adjust=False).mean().iloc[-1])
    last = float(c.iloc[-1])
    return atr / last if last > 0 else 0.01


def crypto_rvol_1h_momentum_scanner(
    data: dict[str, pd.DataFrame],
    context: Optional[dict] = None,
) -> list[dict]:
    """
    LONG when last *completed* 1h bar shows volume spike + aggressive buys + RSI>50.

    Uses closed bar index -2 (exclude still-forming -1).
    """
    del data, context  # live Binance data; daily ``data`` not used for signal path
    signals: list[dict] = []
    syms = _top_usdt_by_quote_volume(_TOP_VOLUME_N)
    if not syms:
        return []

    for sym in syms:
        kl = _fetch_klines_1h(sym)
        if not kl:
            continue
        # Parse OHLCV + taker buy base volume (index 9)
        highs, lows, closes, vols, taker_buy = [], [], [], [], []
        for k in kl:
            if not isinstance(k, (list, tuple)) or len(k) < 11:
                continue
            try:
                highs.append(float(k[2]))
                lows.append(float(k[3]))
                closes.append(float(k[4]))
                vols.append(float(k[5]))
                taker_buy.append(float(k[9]))
            except (TypeError, ValueError):
                continue
        n = len(closes)
        if n < _RVOL_LOOKBACK + 4:
            continue

        # Completed bar = -2
        i = -2
        v_now = vols[i]
        win = vols[i - _RVOL_LOOKBACK : i]
        if not win or min(win) <= 0:
            continue
        v_avg = float(np.mean(win))
        if v_avg <= 0:
            continue
        rvol = v_now / v_avg
        t_buy = taker_buy[i]
        buy_ratio = t_buy / v_now if v_now > 0 else 0.0

        c_slice = np.array(closes[: i + 1], dtype=float)
        rsi_v = _rsi_last(c_slice, 14)
        if np.isnan(rsi_v):
            continue

        if rvol < _RVOL_MIN or buy_ratio < _BUY_RATIO_MIN or rsi_v <= _RSI_MIN:
            continue

        price = float(closes[i])
        h_arr = np.array(highs[: i + 1], dtype=float)
        l_arr = np.array(lows[: i + 1], dtype=float)
        c_arr = c_slice
        ap = _atr_pct(h_arr, l_arr, c_arr, 14)
        tp = price * (1.0 + 2.5 * max(ap, 0.002))
        sl = price * (1.0 - 1.8 * max(ap, 0.002))
        rr = (tp - price) / max(price - sl, 1e-12)
        if rr < 1.0:
            continue

        cat = CRYPTO_SYMBOLS.get(sym, {}).get("cat", "crypto_alt")
        conf = min(0.72, 0.52 + min(rvol / 10.0, 0.12) + min((buy_ratio - 0.65) * 0.5, 0.08))

        signals.append(
            {
                "strategy": "crypto_rvol_1h_momentum_scanner",
                "symbol": sym,
                "category": cat,
                "signal_type": "BUY",
                "entry_price": round(price, 8),
                "take_profit": round(tp, 8),
                "stop_loss": round(sl, 8),
                "confidence": round(conf, 3),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"1H RVOL={rvol:.2f}x (>= {_RVOL_MIN}), buy_ratio={buy_ratio:.2f}, "
                    f"RSI={rsi_v:.1f} — research: vol spike + aggressive takers early move"
                ),
                "timeframe": "1h",
                "max_hold_bars": 36,
                "rsi_at_entry": round(rsi_v, 1),
                "extra": {
                    "rvol": round(rvol, 3),
                    "buy_ratio": round(buy_ratio, 3),
                    "volume_avg_20h": round(v_avg, 2),
                },
                "timestamp": _now_iso(),
            }
        )

    return signals


RESEARCH_EDGE_SCANNERS = {
    "crypto_rvol_1h_momentum_scanner": crypto_rvol_1h_momentum_scanner,
}
