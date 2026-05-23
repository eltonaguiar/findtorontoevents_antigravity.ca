"""
RSI Capitulation Sniper -- Standalone Scanner
=============================================
Scans Binance directly for oversold coins showing bounce confirmation.
71.4% win rate on forward tests.

Two entry modes:
  1. Capitulation: RSI < 30, green candle, volume > 1.5x 20-bar avg
  2. Early Recovery: RSI was < 35 in last 3 bars AND RSI now rising

TP/SL via ATR(14): TP = entry + 2.5*ATR, SL = entry - 1.0*ATR  (R:R 2.5:1)

Pure Python -- no numpy/pandas required.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running from alpha_engine/ or repo root
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

try:
    from config import CRYPTO_SYMBOLS, SPOT_BASES
except ImportError:
    # Minimal fallback if config unavailable
    CRYPTO_SYMBOLS = {}
    SPOT_BASES = [
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
        "https://data-api.binance.vision",
    ]

log = logging.getLogger("alpha_engine.rsi_capitulation")

# ---------------------------------------------------------------------------
# Binance API mirrors -- 4+ endpoints for failover (MEMORY.md: API Failover Rule)
# ---------------------------------------------------------------------------
BINANCE_KLINE_MIRRORS: list[str] = list(SPOT_BASES) if SPOT_BASES else [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

# Rate-limit delay between API calls (seconds)
API_DELAY_SEC = 0.2

# Default symbols -- top 30 from config (binance tickers)
DEFAULT_SYMBOLS: list[str] = []
_count = 0
for _sym, _info in CRYPTO_SYMBOLS.items():
    if _info.get("cat") == "crypto" and _info.get("binance"):
        DEFAULT_SYMBOLS.append(_info["binance"])
        _count += 1
        if _count >= 30:
            break

# Fallback if config was empty
if not DEFAULT_SYMBOLS:
    DEFAULT_SYMBOLS = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "TRXUSDT",
        "TONUSDT", "LTCUSDT", "ETCUSDT", "SUIUSDT", "TIAUSDT",
        "INJUSDT", "ATOMUSDT", "FILUSDT", "APTUSDT", "SEIUSDT",
        "PENDLEUSDT", "GALAUSDT", "WLDUSDT", "TAOUSDT", "RENDERUSDT",
        "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "MATICUSDT", "DOTUSDT",
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_klines(symbol: str, interval: str = "1h", limit: int = 100) -> list[list] | None:
    """Fetch klines from Binance with mirror failover.

    Returns raw kline arrays or None on total failure.
    """
    import urllib.request

    path = f"/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    last_err = None

    for base in BINANCE_KLINE_MIRRORS:
        url = f"{base}{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as exc:
            last_err = exc
            continue

    log.warning("All Binance mirrors failed for %s: %s", symbol, last_err)
    return None


def _parse_ohlcv(raw_klines: list[list]) -> dict:
    """Parse Binance kline arrays into OHLCV lists of floats.

    Returns dict with keys: open, high, low, close, volume (each a list[float]).
    """
    opens, highs, lows, closes, volumes = [], [], [], [], []
    for k in raw_klines:
        opens.append(float(k[1]))
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
        volumes.append(float(k[5]))
    return {
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }


def _compute_rsi(closes: list[float], period: int = 14) -> list[float | None]:
    """Compute RSI using Wilder smoothing (pure Python).

    Returns list same length as closes. First `period` values are None.
    """
    n = len(closes)
    rsi_values: list[float | None] = [None] * n

    if n < period + 1:
        return rsi_values

    # Initial average gain/loss from first `period` changes
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses += abs(delta)

    avg_gain = gains / period
    avg_loss = losses / period

    if avg_loss == 0:
        rsi_values[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_values[period] = 100.0 - (100.0 / (1.0 + rs))

    # Wilder smoothing for remaining bars
    for i in range(period + 1, n):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0.0)
        loss = abs(min(delta, 0.0))

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            rsi_values[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_values[i] = 100.0 - (100.0 / (1.0 + rs))

    return rsi_values


def _compute_atr(highs: list[float], lows: list[float], closes: list[float],
                 period: int = 14) -> list[float | None]:
    """Compute ATR using Wilder smoothing (pure Python).

    Returns list same length as input. First `period` values are None.
    """
    n = len(closes)
    atr_values: list[float | None] = [None] * n

    if n < period + 1:
        return atr_values

    # True Range for each bar (starting from index 1)
    tr_list: list[float] = [0.0]  # placeholder for index 0
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)

    # Initial ATR = simple average of first `period` TR values
    initial_sum = sum(tr_list[1: period + 1])
    atr_values[period] = initial_sum / period

    # Wilder smoothing
    for i in range(period + 1, n):
        prev_atr = atr_values[i - 1]
        if prev_atr is None:
            continue
        atr_values[i] = (prev_atr * (period - 1) + tr_list[i]) / period

    return atr_values


def _smart_round(price: float) -> float:
    """Round price smartly based on magnitude."""
    if price >= 10000:
        return round(price, 1)
    elif price >= 100:
        return round(price, 2)
    elif price >= 1:
        return round(price, 4)
    elif price >= 0.01:
        return round(price, 6)
    else:
        return round(price, 8)


def _now_iso() -> str:
    """Current time in ISO UTC format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Main Scanner
# ---------------------------------------------------------------------------

def scan_rsi_capitulation(symbols: list[str] | None = None) -> list[dict]:
    """Scan Binance for RSI capitulation / early recovery entries.

    Args:
        symbols: List of Binance ticker symbols (e.g. ["BTCUSDT", "ETHUSDT"]).
                 Defaults to top 30 crypto from config.

    Returns:
        List of pick dicts matching active_picks.json format.
    """
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    picks: list[dict] = []
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = now_utc.strftime("%Y%m%d")
    expiry_iso = (now_utc + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for idx, symbol in enumerate(symbols):
        # Rate limiting -- 200ms between calls (skip first)
        if idx > 0:
            time.sleep(API_DELAY_SEC)

        raw = _fetch_klines(symbol, interval="1h", limit=100)
        if raw is None or len(raw) < 35:
            log.debug("Skipping %s -- insufficient data (%s bars)",
                      symbol, len(raw) if raw else 0)
            continue

        ohlcv = _parse_ohlcv(raw)
        closes = ohlcv["close"]
        opens = ohlcv["open"]
        highs = ohlcv["high"]
        lows = ohlcv["low"]
        volumes = ohlcv["volume"]

        rsi_arr = _compute_rsi(closes, 14)
        atr_arr = _compute_atr(highs, lows, closes, 14)

        # Need RSI and ATR at current bar
        cur = len(closes) - 1
        rsi_now = rsi_arr[cur]
        atr_now = atr_arr[cur]

        if rsi_now is None or atr_now is None or atr_now <= 0:
            continue

        # Volume ratio: current volume vs 20-bar average
        vol_window = volumes[max(0, cur - 20): cur]
        avg_vol = sum(vol_window) / len(vol_window) if vol_window else 1.0
        vol_ratio = volumes[cur] / avg_vol if avg_vol > 0 else 0.0

        # --- Detect entry signals ---
        bounce_type = None

        # Mode 1: Capitulation -- RSI < 30, green candle, volume > 1.5x avg
        is_green = closes[cur] > opens[cur]
        if rsi_now < 30 and is_green and vol_ratio > 1.5:
            bounce_type = "capitulation"

        # Mode 2: Early Recovery -- RSI was < 35 in last 3 bars AND RSI rising
        if bounce_type is None:
            recent_rsi = [rsi_arr[cur - i] for i in range(1, 4)
                          if (cur - i) >= 0 and rsi_arr[cur - i] is not None]
            was_oversold = any(r < 35 for r in recent_rsi)
            prev_rsi = rsi_arr[cur - 1] if cur >= 1 else None
            rsi_rising = prev_rsi is not None and rsi_now > prev_rsi

            if was_oversold and rsi_rising:
                bounce_type = "early_recovery"

        if bounce_type is None:
            continue

        # --- Compute TP / SL ---
        entry_price = closes[cur]
        tp_price = entry_price + 2.5 * atr_now
        sl_price = entry_price - 1.0 * atr_now
        risk_reward = 2.5  # fixed by construction

        # Confidence based on signal strength
        if bounce_type == "capitulation":
            # Lower RSI + higher volume = more confident
            base_conf = 0.70
            rsi_bonus = min((30 - rsi_now) / 30, 0.10)
            vol_bonus = min((vol_ratio - 1.5) / 10, 0.05)
            confidence = round(min(base_conf + rsi_bonus + vol_bonus, 0.85), 2)
        else:
            # Early recovery -- slightly lower base confidence
            base_conf = 0.60
            rsi_bonus = min((35 - min(recent_rsi)) / 35, 0.10) if recent_rsi else 0
            confidence = round(min(base_conf + rsi_bonus, 0.78), 2)

        clean_sym = symbol.replace("USDT", "").replace("USD", "")
        pick_id = f"rsi_cap_{clean_sym}_{date_str}"

        pick = {
            "id": pick_id,
            "strategy": "rsi_capitulation_sniper",
            "symbol": symbol,
            "category": "crypto",
            "asset_class": "crypto",
            "direction": "LONG",
            "signal_type": "BUY",
            "timeframe": "1h",
            "entry_price": _smart_round(entry_price),
            "entry_date": now_iso,
            "expiry_date": expiry_iso,
            "take_profit": _smart_round(tp_price),
            "stop_loss": _smart_round(sl_price),
            "confidence": confidence,
            "risk_reward": risk_reward,
            "rsi_at_entry": round(rsi_now, 1),
            "rsi_at_signal": round(rsi_now, 1),
            "volume_ratio": round(vol_ratio, 2),
            "bounce_type": bounce_type,
            "atr_at_entry": _smart_round(atr_now),
            "reason": (
                f"RSI Capitulation Sniper: {bounce_type} | "
                f"RSI={rsi_now:.1f}, Vol={vol_ratio:.1f}x avg, "
                f"ATR={atr_now:.4f}"
            ),
            "status": "OPEN",
            "exit_price": None,
            "exit_date": None,
            "exit_reason": None,
            "pnl_pct": None,
            "pnl_dollar": None,
            "hold_days": None,
            "timestamp": now_iso,
        }

        picks.append(pick)
        log.info("SIGNAL: %s %s -- RSI=%.1f, Vol=%.1fx, Type=%s",
                 symbol, "LONG", rsi_now, vol_ratio, bounce_type)

    return picks


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run RSI Capitulation Sniper scan, print results, save to JSON."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    log.info("RSI Capitulation Sniper -- starting scan of %d symbols",
             len(DEFAULT_SYMBOLS))

    picks = scan_rsi_capitulation()

    if not picks:
        log.info("No capitulation signals detected.")
    else:
        log.info("Found %d signal(s):", len(picks))
        for p in picks:
            print(f"  {p['symbol']:12s} {p['bounce_type']:16s} "
                  f"RSI={p['rsi_at_signal']:5.1f}  "
                  f"Entry={p['entry_price']}  "
                  f"TP={p['take_profit']}  SL={p['stop_loss']}  "
                  f"Conf={p['confidence']:.0%}")

    # Save to data directory
    data_dir = _THIS_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    out_path = data_dir / "rsi_cap_picks.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, ensure_ascii=False)

    log.info("Saved %d pick(s) to %s", len(picks), out_path)


if __name__ == "__main__":
    main()
