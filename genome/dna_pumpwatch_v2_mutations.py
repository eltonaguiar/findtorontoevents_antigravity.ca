#!/usr/bin/env python3
"""
DNA Pumpwatch V2 Mutations — Loss-Prevention Focused Variants
==============================================================

Parent System: pumpwatch (mapped to volume-spike-scout in KIMI Rise of the Claw)
  - Historical: 1W/3L (XOM +$8.01 win, DOT -$10.91, NVDAX -$0.53, COIN -$0.01 losses)
  - Pattern: Losses came from altcoins in downtrends. Win came from momentum play.
  - V1 mutations exist but lack downtrend/BTC-correlation filters

V2 Mutations (focused on loss prevention):
  a. pump_trend_confirmed_v2    — Volume spike + price > 50-EMA (avoids downtrend entries)
  b. pump_btc_correlated_v2     — Only altcoin pumps when BTC > 20-EMA (BTC trend gate)
  c. pump_large_cap_only_v2     — Restrict to top-10 market cap only (avoid small cap traps)
  d. pump_momentum_continuation_v2 — Volume spike + 3-day positive momentum (no dead cats)
  e. pump_fear_greed_filter_v2  — Volume spike only when F&G < 30 (extreme fear contrarian)

All mutations are SANDBOX tier (0.30 weight) until proven via forward testing.
TP = 2x ATR, SL = 1.5x ATR (standard genome format).

Data Sources: Binance API (klines), Alternative.me (Fear & Greed)
Output: Standard pick format consumed by forward_validator / battleground pipeline
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Path setup ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

# Try importing indicators from ml_battleground shared
try:
    sys.path.insert(0, str(ROOT / "ml_battleground"))
    from shared.indicators import rsi, atr, sma, ema
    _HAS_INDICATORS = True
except ImportError:
    _HAS_INDICATORS = False

if not _HAS_INDICATORS:
    # Inline fallback indicators
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).mean()

    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return (100 - 100 / (1 + rs)).fillna(50.0)

    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()


# ── Helpers ───────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value is None or not np.isfinite(value):
        return 0.0
    if abs(value) >= 1000:
        return round(value, 2)
    if abs(value) >= 1:
        return round(value, 4)
    if abs(value) >= 0.01:
        return round(value, 6)
    return round(value, 8)


def _base_signal(strategy: str, symbol: str, signal_type: str, entry: float,
                 tp: float, sl: float, confidence: float, reason: str,
                 parent_system: str, mutation_type: str, **extra) -> dict:
    """Create standardized signal dict with mutation metadata."""
    rr = 0.0
    if signal_type == "BUY" and entry > sl:
        rr = (tp - entry) / (entry - sl)
    elif signal_type == "SELL" and sl > entry:
        rr = (entry - tp) / (sl - entry)

    sig = {
        "strategy": strategy,
        "symbol": symbol,
        "signal_type": signal_type,
        "direction": signal_type,
        "entry_price": _smart_round(entry),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(min(0.85, confidence), 4),
        "risk_reward": round(max(0, rr), 2),
        "reason": reason,
        "timestamp": _now_iso(),
        "category": "crypto",
        "source_system": "genome",
        "trust_tier": "SANDBOX",
        "trust_weight": 0.3,
        "parent_system": parent_system,
        "mutation_type": mutation_type,
    }
    sig.update(extra)
    return sig


# ── Data Fetching (Binance klines) ────────────────────────────────────────

BINANCE_MIRRORS = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://api2.binance.com", "https://api3.binance.com",
    "https://data-api.binance.vision",
]

# Top-10 market cap symbols only (used by large_cap_only mutation)
TOP10_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "DOGEUSDT",
]

# Full scan universe (same as v1 pumpwatch)
PUMPWATCH_V2_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "DOTUSDT",
    "LTCUSDT", "SUIUSDT", "APTUSDT", "INJUSDT", "SEIUSDT",
    "ATOMUSDT", "MATICUSDT", "TRXUSDT", "OPUSDT", "ARBUSDT",
    "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "BONKUSDT", "FLOKIUSDT", "WIFUSDT",
]


def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 300) -> pd.DataFrame:
    """Fetch OHLCV from Binance with mirror rotation."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DNAPumpwatchV2/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data and isinstance(data, list) and len(data) > 20:
                df = pd.DataFrame(data, columns=[
                    "open_time", "Open", "High", "Low", "Close", "Volume",
                    "close_time", "qav", "num_trades", "taker_buy_base",
                    "taker_buy_quote", "ignore"
                ])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
                df.set_index("open_time", inplace=True)
                return df
        except Exception:
            continue
    return pd.DataFrame()


def fetch_fear_greed() -> Optional[int]:
    """Fetch current Fear & Greed index."""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "DNAPumpwatchV2/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return int(data["data"][0]["value"])
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION A: pump_trend_confirmed_v2
# Volume spike + price must be above 50-EMA (no downtrend entries)
# Prevents: DOT loss (bought altcoin in downtrend)
# ═══════════════════════════════════════════════════════════════════════════

def pump_trend_confirmed_v2(data: dict) -> list[dict]:
    """
    V2 Pumpwatch: Volume spike + 50-EMA trend confirmation.

    Root cause fix: DOT lost -$10.91 because it was bought during a downtrend.
    This mutation requires price > 50-EMA before accepting any volume spike,
    ensuring we only buy pumps in established uptrends.

    Entry: volume > 2x 20-day avg AND close > EMA(50) AND close > EMA(20)
    Expected: Eliminates downtrend entries — ~55-65% WR
    """
    signals = []

    for symbol in PUMPWATCH_V2_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Volume spike: 2x 20-bar avg (same as original pumpwatch threshold)
        vol_avg_20 = float(volume.rolling(20).mean().iloc[-1])
        vol_now = float(volume.iloc[-1])
        if vol_avg_20 <= 0:
            continue
        vol_ratio = vol_now / vol_avg_20
        if vol_ratio < 2.0:
            continue

        # TREND FILTER: price must be above 50-EMA (uptrend confirmed)
        ema_50 = float(ema(close, 50).iloc[-1])
        ema_20 = float(ema(close, 20).iloc[-1])
        if pd.isna(ema_50) or pd.isna(ema_20):
            continue

        if current <= ema_50:
            continue  # Below 50-EMA = downtrend, SKIP (this would have avoided DOT loss)

        if current <= ema_20:
            continue  # Below 20-EMA = short-term weakness, SKIP

        # Bonus: EMA stack alignment (20 > 50 = strong uptrend)
        ema_aligned = ema_20 > ema_50

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        # Distance above 50-EMA adds confidence
        trend_strength = (current - ema_50) / ema_50
        conf = min(0.85, 0.50 + (vol_ratio - 2.0) * 0.05 + trend_strength * 2.0 + (0.05 if ema_aligned else 0))

        signals.append(_base_signal(
            "pump_trend_confirmed_v2", symbol, "BUY", current, tp, sl, conf,
            f"PumpV2 trend-confirmed: vol={vol_ratio:.1f}x, price ${current:.4f} > "
            f"EMA50=${ema_50:.4f} > EMA20=${ema_20:.4f} "
            f"{'(EMA stack aligned)' if ema_aligned else ''} — uptrend pump only",
            parent_system="pumpwatch_v2",
            mutation_type="trend_filter",
            volume_ratio=round(vol_ratio, 2),
            ema_50=_smart_round(ema_50),
            ema_20=_smart_round(ema_20),
            ema_aligned=ema_aligned,
            trend_strength=round(trend_strength, 4),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION B: pump_btc_correlated_v2
# Only take altcoin pumps when BTC is also bullish (BTC > 20-EMA)
# Prevents: Buying alts during BTC drawdowns
# ═══════════════════════════════════════════════════════════════════════════

def pump_btc_correlated_v2(data: dict) -> list[dict]:
    """
    V2 Pumpwatch: BTC-correlated altcoin pump filter.

    Insight: Most altcoin losses happen when BTC is in a drawdown.
    Even if an altcoin has a volume spike, it's likely a dead cat bounce
    if BTC is trending down. This mutation gates ALL altcoin entries
    on BTC being above its 20-EMA.

    Entry: volume > 2x AND (symbol == BTC OR BTC_close > BTC_EMA20)
    Expected: Filters out 60-70% of losing altcoin trades — ~58-68% WR
    """
    signals = []

    # Get BTC data for correlation check
    btc_df = data.get("BTCUSDT")
    btc_bullish = False
    btc_ema20_val = None

    if btc_df is not None and len(btc_df) > 25:
        btc_close = float(btc_df["Close"].iloc[-1])
        btc_ema20_val = float(ema(btc_df["Close"], 20).iloc[-1])
        if not pd.isna(btc_ema20_val) and btc_close > btc_ema20_val:
            btc_bullish = True

    for symbol in PUMPWATCH_V2_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Volume spike: 2x
        vol_avg_20 = float(volume.rolling(20).mean().iloc[-1])
        vol_now = float(volume.iloc[-1])
        if vol_avg_20 <= 0:
            continue
        vol_ratio = vol_now / vol_avg_20
        if vol_ratio < 2.0:
            continue

        # BTC CORRELATION GATE: altcoins require BTC bullish
        is_btc = symbol == "BTCUSDT"
        if not is_btc and not btc_bullish:
            continue  # BTC not bullish, skip altcoin entry

        # Own trend check (light): price > SMA(10) for short-term confirmation
        sma_10 = float(sma(close, 10).iloc[-1])
        if pd.isna(sma_10) or current <= sma_10:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        conf = min(0.85, 0.52 + (vol_ratio - 2.0) * 0.06 + (0.08 if btc_bullish else 0))

        btc_status = f"BTC bullish (>${btc_ema20_val:.0f} EMA20)" if btc_bullish else "BTC is entry"
        signals.append(_base_signal(
            "pump_btc_correlated_v2", symbol, "BUY", current, tp, sl, conf,
            f"PumpV2 BTC-correlated: vol={vol_ratio:.1f}x, {btc_status}, "
            f"price > SMA10 — alt pump with BTC tailwind",
            parent_system="pumpwatch_v2",
            mutation_type="btc_correlation",
            volume_ratio=round(vol_ratio, 2),
            btc_bullish=btc_bullish,
            btc_ema20=_smart_round(btc_ema20_val) if btc_ema20_val else None,
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION C: pump_large_cap_only_v2
# Only trade top-10 market cap coins
# Prevents: NVDAX (-$0.53) and other small cap trap losses
# ═══════════════════════════════════════════════════════════════════════════

def pump_large_cap_only_v2(data: dict) -> list[dict]:
    """
    V2 Pumpwatch: Large-cap only volume spike filter.

    Root cause fix: NVDAX lost -$0.53 — a low-liquidity/small-cap token.
    Small caps have wider spreads, lower liquidity, and more manipulation.
    This mutation restricts to TOP-10 market cap coins only.

    Universe: BTC, ETH, SOL, BNB, XRP, ADA, AVAX, DOT, LINK, DOGE
    Entry: volume > 1.8x 20-day avg (slightly relaxed for large caps — they move slower)
    Expected: Higher quality universe eliminates micro-cap traps — ~55-65% WR
    """
    signals = []

    for symbol in TOP10_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Volume spike: 1.8x (slightly relaxed — large caps have steadier volume)
        vol_avg_20 = float(volume.rolling(20).mean().iloc[-1])
        vol_now = float(volume.iloc[-1])
        if vol_avg_20 <= 0:
            continue
        vol_ratio = vol_now / vol_avg_20
        if vol_ratio < 1.8:
            continue

        # Basic trend check: close > SMA(20) for upward bias
        sma_20 = float(sma(close, 20).iloc[-1])
        if pd.isna(sma_20) or current <= sma_20:
            continue

        # RSI filter: not overbought (< 70)
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14) or rsi_14 >= 70:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        conf = min(0.85, 0.55 + (vol_ratio - 1.8) * 0.08 + (70 - rsi_14) / 200)

        signals.append(_base_signal(
            "pump_large_cap_only_v2", symbol, "BUY", current, tp, sl, conf,
            f"PumpV2 large-cap: {symbol} (top-10), vol={vol_ratio:.1f}x, "
            f"RSI={rsi_14:.1f}, price > SMA20 — high-quality universe only",
            parent_system="pumpwatch_v2",
            mutation_type="large_cap_filter",
            volume_ratio=round(vol_ratio, 2),
            rsi_14=round(rsi_14, 1),
            is_top10=True,
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION D: pump_momentum_continuation_v2
# Volume spike + 3-day positive momentum (close > close[3])
# Prevents: Dead cat bounces that reverse immediately
# ═══════════════════════════════════════════════════════════════════════════

def pump_momentum_continuation_v2(data: dict) -> list[dict]:
    """
    V2 Pumpwatch: Momentum continuation filter.

    Insight: The XOM win was a momentum continuation play — price was already
    moving up when volume spiked. Losses (DOT, COIN) were mean-reversion attempts
    that failed. This mutation requires 3-bar positive momentum BEFORE the
    volume spike, confirming it's continuation not a dead cat bounce.

    Entry: volume > 2x AND close > close[-3] (3-bar momentum) AND close > close[-1]
    Expected: Catches continuation not reversal — ~58-68% WR
    """
    signals = []

    for symbol in PUMPWATCH_V2_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Volume spike: 2x
        vol_avg_20 = float(volume.rolling(20).mean().iloc[-1])
        vol_now = float(volume.iloc[-1])
        if vol_avg_20 <= 0:
            continue
        vol_ratio = vol_now / vol_avg_20
        if vol_ratio < 2.0:
            continue

        # MOMENTUM CONTINUATION: close > close[3] bars ago
        if len(close) < 4:
            continue
        close_3_ago = float(close.iloc[-4])
        close_1_ago = float(close.iloc[-2])
        if close_3_ago <= 0 or close_1_ago <= 0:
            continue

        momentum_3d = (current - close_3_ago) / close_3_ago
        if momentum_3d <= 0:
            continue  # No positive momentum = dead cat bounce, SKIP

        # Additional: latest bar must be green (close > previous close)
        if current <= close_1_ago:
            continue  # Latest bar is red = momentum fading

        # Count consecutive green bars for strength assessment
        green_bars = 0
        for i in range(1, min(6, len(close))):
            if float(close.iloc[-i]) > float(close.iloc[-i-1]):
                green_bars += 1
            else:
                break

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        conf = min(0.85, 0.52 + momentum_3d * 3.0 + green_bars * 0.03 + (vol_ratio - 2.0) * 0.04)

        signals.append(_base_signal(
            "pump_momentum_continuation_v2", symbol, "BUY", current, tp, sl, conf,
            f"PumpV2 momentum: vol={vol_ratio:.1f}x + 3-bar momentum={momentum_3d:.2%}, "
            f"{green_bars} green bars — continuation confirmed, not dead cat",
            parent_system="pumpwatch_v2",
            mutation_type="momentum_continuation",
            volume_ratio=round(vol_ratio, 2),
            momentum_3d=round(momentum_3d, 4),
            green_bars=green_bars,
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION E: pump_fear_greed_filter_v2
# Only take volume spikes when F&G < 30 (extreme fear = best entries)
# Tighter than v1's F&G < 40 threshold
# ═══════════════════════════════════════════════════════════════════════════

def pump_fear_greed_filter_v2(data: dict, fear_greed: Optional[int] = None) -> list[dict]:
    """
    V2 Pumpwatch: Extreme Fear & Greed contrarian filter.

    Tighter than v1 (F&G < 30 vs F&G < 40). The best pump entries historically
    occur during extreme fear when smart money accumulates while retail panic sells.
    Volume spikes at F&G < 30 are almost always institutional accumulation.

    Entry: volume > 1.8x AND F&G < 30 AND RSI < 45
    Expected: Highest conviction pump signals — ~65-75% WR (extreme contrarian)
    """
    signals = []

    # Get Fear & Greed
    fg = fear_greed if fear_greed is not None else fetch_fear_greed()
    if fg is None:
        print("  [WARN] pump_fear_greed_filter_v2: Could not fetch Fear & Greed index")
        return signals

    # Only active during EXTREME fear (tighter than v1's < 40)
    if fg >= 30:
        print(f"  [INFO] pump_fear_greed_filter_v2: F&G={fg} (>= 30) — not extreme fear, skipping")
        return signals

    for symbol in PUMPWATCH_V2_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Volume spike: 1.8x (slightly relaxed — during fear, volume is depressed)
        vol_avg_20 = float(volume.rolling(20).mean().iloc[-1])
        vol_now = float(volume.iloc[-1])
        if vol_avg_20 <= 0:
            continue
        vol_ratio = vol_now / vol_avg_20
        if vol_ratio < 1.8:
            continue

        # RSI must be depressed too (< 45 = not already recovered)
        rsi_14 = float(rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14) or rsi_14 >= 45:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current + 2.0 * atr_val
        sl = current - 1.5 * atr_val

        # Very high confidence when F&G is extremely low
        fg_bonus = (30 - fg) / 60  # F&G=5 -> +0.42 bonus, F&G=25 -> +0.08
        conf = min(0.85, 0.55 + fg_bonus + (vol_ratio - 1.8) * 0.06)

        signals.append(_base_signal(
            "pump_fear_greed_filter_v2", symbol, "BUY", current, tp, sl, conf,
            f"PumpV2 extreme-fear: vol={vol_ratio:.1f}x at F&G={fg} (<30), "
            f"RSI={rsi_14:.1f} — institutional accumulation during panic",
            parent_system="pumpwatch_v2",
            mutation_type="extreme_fear_contrarian",
            volume_ratio=round(vol_ratio, 2),
            fear_greed=fg,
            rsi_14=round(rsi_14, 1),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRY — All Pumpwatch V2 Mutations
# ═══════════════════════════════════════════════════════════════════════════

DNA_PUMPWATCH_V2_MUTATIONS = {
    "pump_trend_confirmed_v2": {
        "fn": pump_trend_confirmed_v2,
        "parent": "pumpwatch_v2",
        "mutation": "trend_filter",
        "trust_weight": 0.3,
        "description": "Volume spike + price > 50-EMA — prevents downtrend entries (DOT fix)",
    },
    "pump_btc_correlated_v2": {
        "fn": pump_btc_correlated_v2,
        "parent": "pumpwatch_v2",
        "mutation": "btc_correlation",
        "trust_weight": 0.3,
        "description": "Alt pumps only when BTC > 20-EMA — prevents BTC drawdown alt losses",
    },
    "pump_large_cap_only_v2": {
        "fn": pump_large_cap_only_v2,
        "parent": "pumpwatch_v2",
        "mutation": "large_cap_filter",
        "trust_weight": 0.3,
        "description": "Top-10 market cap only — prevents small cap traps (NVDAX fix)",
    },
    "pump_momentum_continuation_v2": {
        "fn": pump_momentum_continuation_v2,
        "parent": "pumpwatch_v2",
        "mutation": "momentum_continuation",
        "trust_weight": 0.3,
        "description": "Volume spike + 3-bar momentum — catches continuation not dead cats",
    },
    "pump_fear_greed_filter_v2": {
        "fn": pump_fear_greed_filter_v2,
        "parent": "pumpwatch_v2",
        "mutation": "extreme_fear_contrarian",
        "trust_weight": 0.3,
        "description": "Volume spike at F&G < 30 — extreme fear accumulation signals",
    },
}

# Total: 5 V2 mutations of pumpwatch (loss-prevention focused)


# ═══════════════════════════════════════════════════════════════════════════
# RUNNER — Fetch data & execute all V2 mutations
# ═══════════════════════════════════════════════════════════════════════════

ALL_SCAN_SYMBOLS = sorted(set(PUMPWATCH_V2_SYMBOLS))


def run_all_mutations(interval: str = "1h", limit: int = 300) -> dict:
    """
    Fetch market data and run all 5 Pumpwatch V2 DNA mutations.

    Returns:
        {
            "metadata": {...},
            "picks": [...],
            "mutations_triggered": [...],
            "mutations_silent": [...]
        }
    """
    print(f"\n{'='*70}")
    print(f"DNA PUMPWATCH V2 MUTATIONS — {len(DNA_PUMPWATCH_V2_MUTATIONS)} strategies")
    print(f"Focus: Loss prevention (DOT/NVDAX/COIN pattern fixes)")
    print(f"Scanning {len(ALL_SCAN_SYMBOLS)} symbols on {interval}")
    print(f"{'='*70}\n")

    # Fetch data for all symbols
    data = {}
    for symbol in ALL_SCAN_SYMBOLS:
        df = fetch_binance_klines(symbol, interval=interval, limit=limit)
        if not df.empty and len(df) > 20:
            data[symbol] = df
            print(f"  [OK] {symbol}: {len(df)} bars")
        else:
            print(f"  [--] {symbol}: no data")

    print(f"\nFetched data for {len(data)}/{len(ALL_SCAN_SYMBOLS)} symbols\n")

    # Pre-fetch Fear & Greed for extreme fear mutation
    fg = fetch_fear_greed()
    if fg is not None:
        print(f"  Fear & Greed Index: {fg}")

    # Run all mutations
    all_picks = []
    triggered = []
    silent = []

    for name, info in DNA_PUMPWATCH_V2_MUTATIONS.items():
        try:
            fn = info["fn"]
            if name == "pump_fear_greed_filter_v2":
                picks = fn(data, fear_greed=fg)
            else:
                picks = fn(data)

            if picks:
                for p in picks:
                    p["timeframe"] = p.get("timeframe", interval)
                all_picks.extend(picks)
                triggered.append({
                    "strategy": name,
                    "parent": info["parent"],
                    "mutation": info["mutation"],
                    "picks": len(picks),
                })
                print(f"  [SIGNAL] {name}: {len(picks)} picks")
            else:
                silent.append(name)
                print(f"  [quiet] {name}: 0 picks")
        except Exception as e:
            silent.append(name)
            print(f"  [ERROR] {name}: {e}")

    # Sort by confidence
    all_picks.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    result = {
        "metadata": {
            "timestamp": _now_iso(),
            "total_mutations": len(DNA_PUMPWATCH_V2_MUTATIONS),
            "total_picks": len(all_picks),
            "mutations_triggered": len(triggered),
            "mutations_silent": len(silent),
            "symbols_scanned": len(data),
            "interval": interval,
            "system": "dna_pumpwatch_v2_mutations",
            "fear_greed": fg,
            "version": "v2",
            "focus": "loss_prevention",
        },
        "picks": all_picks,
        "mutations_triggered": triggered,
        "mutations_silent": silent,
    }

    print(f"\n{'='*70}")
    print(f"RESULTS: {len(all_picks)} picks from {len(triggered)}/{len(DNA_PUMPWATCH_V2_MUTATIONS)} mutations")
    print(f"{'='*70}\n")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DNA Pumpwatch V2 Mutations Scanner (Loss Prevention)")
    parser.add_argument("--interval", default="1h", choices=["1h", "4h", "1d"],
                        help="Kline interval (default: 1h)")
    parser.add_argument("--limit", type=int, default=300,
                        help="Number of bars to fetch (default: 300)")
    parser.add_argument("--output", default=None,
                        help="Output JSON path (default: genome/data/pumpwatch_v2_picks.json)")
    args = parser.parse_args()

    output_path = args.output or str(ROOT / "genome" / "data" / "pumpwatch_v2_picks.json")

    result = run_all_mutations(interval=args.interval, limit=args.limit)

    # Save results
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"Saved {result['metadata']['total_picks']} picks to {output_path}")

    # Summary
    if result["picks"]:
        print("\nTop 5 picks by confidence:")
        for i, p in enumerate(result["picks"][:5], 1):
            print(f"  {i}. {p['symbol']} {p['signal_type']} | "
                  f"conf={p['confidence']:.2f} | "
                  f"R:R={p['risk_reward']:.1f} | "
                  f"{p['strategy']} ({p['mutation_type']})")
