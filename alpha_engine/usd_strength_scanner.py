#!/usr/bin/env python3
"""
USD Strength Scanner -- Alpha Engine
=====================================
Detects USD strength/weakness regime and generates high-conviction forex picks
aligned with the dominant USD direction.

Regime Detection:
  - DXY proxy: inverse of EURUSD=X vs 20-day average
  - Risk-off breadth: AUDUSD + GBPUSD both below 5-day average
  - Safe haven confirmation: USDJPY trending up (rising 10d)

When USD STRENGTHENING:
  SELL: AUDUSD=X, NZDUSD=X, GBPUSD=X, EURUSD=X
  BUY:  USDJPY=X, USDCHF=X

Each pick includes 2:1 R:R via ATR-based TP/SL, MACD + RSI filters.

Usage:
  python alpha_engine/usd_strength_scanner.py

Author: Alpha Engine -- KIMI Rise of the Claw
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Allow standalone execution from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import yfinance as yf
except ImportError:
    print("[ERROR] yfinance not installed. Run: pip install yfinance")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# All pairs this scanner uses
USD_WEAKNESS_PAIRS = [          # SELL when USD strengthening (USD is numerator-free)
    "AUDUSD=X",
    "NZDUSD=X",
    "GBPUSD=X",
    "EURUSD=X",
]

USD_STRENGTH_PAIRS = [          # BUY when USD strengthening (USD is numerator)
    "USDJPY=X",
    "USDCHF=X",
]

ALL_PAIRS = USD_WEAKNESS_PAIRS + USD_STRENGTH_PAIRS

# DXY proxy is computed from EURUSD (EUR is 57.6% of DXY weight)
DXY_PROXY_SYMBOL = "EURUSD=X"

# Regime thresholds
DXY_SMA_SHORT = 5       # Short-term SMA period for DXY proxy
DXY_SMA_LONG  = 20      # Long-term SMA period (20-day average)
RISK_OFF_SMA  = 5       # Period for AUD/GBP risk-off check
JPY_TREND_SMA = 10      # USDJPY trend check period

# Signal generation parameters
ATR_PERIOD     = 14
ATR_SL_MULT    = 1.0    # Stop-loss = 1x ATR
ATR_TP_MULT    = 2.0    # Take-profit = 2x ATR  (2:1 R:R)
RSI_PERIOD     = 14
RSI_OB         = 70     # Overbought -- skip BUY signals
RSI_OS         = 30     # Oversold   -- skip SELL signals
MACD_FAST      = 12
MACD_SLOW      = 26
MACD_SIGNAL    = 9

MIN_CONFIDENCE = 0.50   # Minimum confidence to emit a signal


# ---------------------------------------------------------------------------
# Technical indicator helpers (self-contained, no dependency on indicators.py
# so this file is truly standalone-runnable from repo root)
# ---------------------------------------------------------------------------

def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def _macd(close: pd.Series,
          fast: int = 12, slow: int = 26,
          signal: int = 9) -> dict[str, pd.Series]:
    macd_line = _ema(close, fast) - _ema(close, slow)
    signal_line = _ema(macd_line, signal)
    return {
        "macd":      macd_line,
        "signal":    signal_line,
        "histogram": macd_line - signal_line,
    }


# ---------------------------------------------------------------------------
# Regime detection
# ---------------------------------------------------------------------------

class USDRegime:
    """Encapsulates the current USD strength/weakness regime assessment."""

    def __init__(self,
                 is_strengthening: bool,
                 confidence: float,
                 dxy_above_20sma: bool,
                 risk_off_breadth: int,   # 0–2: how many of AUD/GBP are below 5d SMA
                 jpy_trending_up: bool,
                 confirming_signals: list[str]):
        self.is_strengthening   = is_strengthening
        self.confidence         = confidence
        self.dxy_above_20sma    = dxy_above_20sma
        self.risk_off_breadth   = risk_off_breadth
        self.jpy_trending_up    = jpy_trending_up
        self.confirming_signals = confirming_signals

    def __repr__(self) -> str:
        direction = "STRENGTHENING" if self.is_strengthening else "WEAKENING/NEUTRAL"
        return (
            f"USDRegime({direction}, confidence={self.confidence:.0%}, "
            f"dxy_above_20sma={self.dxy_above_20sma}, "
            f"risk_off_breadth={self.risk_off_breadth}/2, "
            f"jpy_trending_up={self.jpy_trending_up})"
        )


def detect_usd_regime(data: dict[str, pd.DataFrame]) -> USDRegime:
    """
    Detect current USD strength/weakness regime.

    Three pillars:
      1. DXY proxy (inverse EURUSD) above its 20-day SMA
      2. Risk-off breadth: AUDUSD and GBPUSD below their 5-day SMAs
      3. JPY safe-haven: USDJPY trending up (current > 10-day SMA)

    Returns USDRegime with confidence 0–1 based on how many pillars confirm.
    """
    confirming = []
    score = 0

    # --- Pillar 1: DXY proxy ---
    dxy_above_20sma = False
    eurusd_df = data.get(DXY_PROXY_SYMBOL)
    if eurusd_df is not None and len(eurusd_df) >= DXY_SMA_LONG + 5:
        close = eurusd_df["Close"]
        # DXY proxy = 1/EURUSD. Higher = stronger USD.
        dxy_proxy = 1.0 / close
        sma20 = float(np.squeeze(_sma(dxy_proxy, DXY_SMA_LONG).iloc[-1]))
        sma5  = float(np.squeeze(_sma(dxy_proxy, DXY_SMA_SHORT).iloc[-1]))
        current_dxy = float(np.squeeze(dxy_proxy.iloc[-1]))

        if not (np.isnan(sma20) or np.isnan(sma5)):
            # Strong: current above 20d AND short SMA above long SMA
            if current_dxy > sma20 and sma5 > sma20:
                dxy_above_20sma = True
                confirming.append(
                    f"DXY proxy above 20d SMA (proxy={current_dxy:.5f} > sma20={sma20:.5f})"
                )
                score += 1
            # Moderate: just current above 20d
            elif current_dxy > sma20:
                dxy_above_20sma = True
                confirming.append(
                    f"DXY proxy above 20d SMA (proxy={current_dxy:.5f} > sma20={sma20:.5f})"
                )
                score += 0.5

    # --- Pillar 2: Risk-off breadth ---
    risk_off_breadth = 0
    risk_off_pairs = ["AUDUSD=X", "GBPUSD=X"]
    for sym in risk_off_pairs:
        df = data.get(sym)
        if df is None or len(df) < RISK_OFF_SMA + 2:
            continue
        close = df["Close"]
        sma5 = float(np.squeeze(_sma(close, RISK_OFF_SMA).iloc[-1]))
        current = float(np.squeeze(close.iloc[-1]))
        if not np.isnan(sma5) and current < sma5:
            risk_off_breadth += 1
            confirming.append(f"{sym} below 5d SMA ({current:.5f} < {sma5:.5f}) -- risk-off")

    score += risk_off_breadth * 0.5   # 0.5 per pair, max 1.0

    # --- Pillar 3: JPY safe-haven ---
    jpy_trending_up = False
    jpy_df = data.get("USDJPY=X")
    if jpy_df is not None and len(jpy_df) >= JPY_TREND_SMA + 2:
        close = jpy_df["Close"]
        sma10   = float(np.squeeze(_sma(close, JPY_TREND_SMA).iloc[-1]))
        current = float(np.squeeze(close.iloc[-1]))
        # Rising USDJPY = USD strengthening vs JPY (JPY weakening slightly, or
        # USD broadly demanded). In pure risk-off JPY actually strengthens,
        # but in USD-strength context USDJPY still rises because USD is the
        # primary driver.
        if not np.isnan(sma10) and current > sma10:
            jpy_trending_up = True
            confirming.append(
                f"USDJPY trending up ({current:.3f} > 10d SMA {sma10:.3f})"
            )
            score += 1

    # Max possible score = 3. Normalize to 0–1.
    confidence = min(1.0, score / 3.0)

    # Require at least 2 pillars (score >= 1.5) for a strengthening call
    is_strengthening = (dxy_above_20sma and score >= 1.5)

    return USDRegime(
        is_strengthening   = is_strengthening,
        confidence         = round(confidence, 3),
        dxy_above_20sma    = dxy_above_20sma,
        risk_off_breadth   = risk_off_breadth,
        jpy_trending_up    = jpy_trending_up,
        confirming_signals = confirming,
    )


# ---------------------------------------------------------------------------
# Signal generation
# ---------------------------------------------------------------------------

def _build_signal(symbol: str,
                  signal_type: str,       # "BUY" or "SELL"
                  df: pd.DataFrame,
                  confidence: float,
                  reason: str) -> Optional[dict]:
    """
    Build a single signal dict with ATR-based TP/SL and MACD/RSI filters.
    Returns None if filters reject the signal.
    """
    if df is None or len(df) < ATR_PERIOD + 5:
        return None

    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]
    entry  = float(close.iloc[-1])

    if np.isnan(entry) or entry <= 0:
        return None

    # --- ATR for TP/SL ---
    atr_series = _atr(high, low, close, ATR_PERIOD)
    atr_val = float(atr_series.iloc[-1])
    if np.isnan(atr_val) or atr_val <= 0:
        return None

    if signal_type == "SELL":
        stop_loss   = round(entry + ATR_SL_MULT * atr_val, 6)
        take_profit = round(entry - ATR_TP_MULT * atr_val, 6)
        rr = (entry - take_profit) / (stop_loss - entry) if stop_loss > entry else 0
    else:  # BUY
        stop_loss   = round(entry - ATR_SL_MULT * atr_val, 6)
        take_profit = round(entry + ATR_TP_MULT * atr_val, 6)
        rr = (take_profit - entry) / (entry - stop_loss) if entry > stop_loss else 0

    if rr < 1.8:   # Require at least ~2:1
        return None

    # --- RSI filter: avoid extreme readings ---
    rsi_val = float(_rsi(close, RSI_PERIOD).iloc[-1])
    if np.isnan(rsi_val):
        rsi_val = 50.0
    if signal_type == "SELL" and rsi_val < RSI_OS:
        return None   # Already oversold -- don't chase SELL
    if signal_type == "BUY"  and rsi_val > RSI_OB:
        return None   # Already overbought -- don't chase BUY

    # --- MACD confirmation: histogram must agree with direction ---
    macd_data = _macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    hist_now  = float(macd_data["histogram"].iloc[-1])
    hist_prev = float(macd_data["histogram"].iloc[-2]) if len(close) > 2 else 0.0

    macd_confirms = False
    macd_note = ""
    if signal_type == "SELL":
        # Bearish confirmation: histogram negative OR turning more negative
        if hist_now < 0 or hist_now < hist_prev:
            macd_confirms = True
            macd_note = f"MACD hist={hist_now:.6f} (bearish)"
    else:
        # Bullish confirmation: histogram positive OR turning more positive
        if hist_now > 0 or hist_now > hist_prev:
            macd_confirms = True
            macd_note = f"MACD hist={hist_now:.6f} (bullish)"

    # MACD disagreement reduces confidence by 20%
    if not macd_confirms:
        confidence = max(0.40, confidence - 0.20)
        macd_note = f"MACD hist={hist_now:.6f} (no confirmation)"

    full_reason = f"{reason} | RSI={rsi_val:.1f} | {macd_note}"

    return {
        "symbol":       symbol,
        "signal_type":  signal_type,
        "entry_price":  round(entry, 6),
        "take_profit":  round(take_profit, 6),
        "stop_loss":    round(stop_loss, 6),
        "confidence":   round(confidence, 3),
        "risk_reward":  round(rr, 2),
        "reason":       full_reason,
        "category":     "forex",
        "atr":          round(atr_val, 6),
        "rsi":          round(rsi_val, 1),
        "macd_hist":    round(hist_now, 6),
        "macd_confirms": macd_confirms,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
    }


def run_scan(data: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Main scan entry point. Detects USD regime and generates 5-10 forex picks.

    Args:
        data: Dict mapping yfinance symbol -> OHLCV DataFrame.
              Must include at minimum EURUSD=X, AUDUSD=X, GBPUSD=X,
              USDJPY=X, and ideally NZDUSD=X, USDCHF=X.

    Returns:
        List of signal dicts with keys:
          symbol, signal_type, entry_price, take_profit, stop_loss,
          confidence, risk_reward, reason, category, atr, rsi,
          macd_hist, macd_confirms, timestamp
    """
    regime = detect_usd_regime(data)

    if not regime.is_strengthening:
        # Still return the regime info for inspection, but no picks
        print(f"\n[USD REGIME] {regime}")
        print("  No USD-strength signals -- regime not confirmed.")
        return []

    print(f"\n[USD REGIME] {regime}")
    for sig in regime.confirming_signals:
        print(f"  + {sig}")

    signals: list[dict] = []
    base_conf = regime.confidence  # 0.5–1.0

    # --- SELL the dollar-denominated weakness pairs ---
    sell_reasons = {
        "AUDUSD=X": "AUD weakens in USD-strength regime (high beta, commodity-linked)",
        "NZDUSD=X": "NZD weakens in USD-strength regime (similar risk-on profile to AUD)",
        "GBPUSD=X": "GBP weakens in USD-strength regime (London breakout already bearish)",
        "EURUSD=X": "EUR weakens in USD-strength regime (EUR is 57.6% of DXY basket)",
    }
    for sym, base_reason in sell_reasons.items():
        df = data.get(sym)
        if df is None or len(df) < 30:
            continue

        # Boost confidence if the pair itself is below its 5d SMA (momentum aligned)
        close = df["Close"]
        sma5  = float(_sma(close, 5).iloc[-1])
        current = float(close.iloc[-1])
        pair_below_sma = (not np.isnan(sma5)) and current < sma5
        conf = base_conf + (0.08 if pair_below_sma else 0.0)
        reason = base_reason
        if pair_below_sma:
            reason += f" | Below 5d SMA ({current:.5f} < {sma5:.5f})"

        sig = _build_signal(sym, "SELL", df, min(conf, 0.95), reason)
        if sig is not None and sig["confidence"] >= MIN_CONFIDENCE:
            sig["strategy"] = "usd_strength_scanner"
            signals.append(sig)

    # --- BUY the USD-numerator strength pairs ---
    buy_reasons = {
        "USDJPY=X": "JPY safe-haven; USDJPY rises when USD broadly demanded",
        "USDCHF=X": "CHF safe-haven; USDCHF rises with broad USD strength",
    }
    for sym, base_reason in buy_reasons.items():
        df = data.get(sym)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        sma5  = float(_sma(close, 5).iloc[-1])
        current = float(close.iloc[-1])
        pair_above_sma = (not np.isnan(sma5)) and current > sma5
        conf = base_conf + (0.08 if pair_above_sma else 0.0)
        reason = base_reason
        if pair_above_sma:
            reason += f" | Above 5d SMA ({current:.5f} > {sma5:.5f})"

        sig = _build_signal(sym, "BUY", df, min(conf, 0.95), reason)
        if sig is not None and sig["confidence"] >= MIN_CONFIDENCE:
            sig["strategy"] = "usd_strength_scanner"
            signals.append(sig)

    # Sort by confidence descending
    signals.sort(key=lambda x: x["confidence"], reverse=True)
    return signals


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_data(period: str = "60d",
               interval: str = "1d") -> dict[str, pd.DataFrame]:
    """
    Download OHLCV data for all relevant forex pairs via yfinance.

    Args:
        period:   yfinance period string (e.g. "60d", "3mo")
        interval: yfinance interval string (e.g. "1d", "4h")

    Returns:
        Dict mapping symbol -> DataFrame.
    """
    print(f"Fetching {len(ALL_PAIRS)} forex pairs ({period}/{interval})...")
    data: dict[str, pd.DataFrame] = {}

    # Batch download
    tickers_str = " ".join(ALL_PAIRS)
    try:
        raw = yf.download(
            tickers_str,
            period=period,
            interval=interval,
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
    except Exception as exc:
        print(f"[ERROR] Batch download failed: {exc}")
        return data

    # yfinance multi-ticker layout varies by number of tickers
    if len(ALL_PAIRS) == 1:
        sym = ALL_PAIRS[0]
        if isinstance(raw, pd.DataFrame) and not raw.empty:
            data[sym] = raw
    else:
        for sym in ALL_PAIRS:
            try:
                if hasattr(raw.columns, "levels"):
                    # MultiIndex columns: (field, ticker)
                    df = raw.xs(sym, axis=1, level=1).dropna(how="all")
                else:
                    df = raw[sym].dropna(how="all")
                if not df.empty:
                    data[sym] = df
            except KeyError:
                pass

    # Fill any missing with single-ticker fallback
    missing = [s for s in ALL_PAIRS if s not in data or data[s].empty]
    for sym in missing:
        try:
            df = yf.download(sym, period=period, interval=interval,
                             auto_adjust=True, progress=False)
            if not df.empty:
                data[sym] = df
        except Exception:
            pass

    print(f"  Downloaded: {list(data.keys())}")
    return data


# ---------------------------------------------------------------------------
# Pretty-print results
# ---------------------------------------------------------------------------

def print_results(signals: list[dict], regime: Optional[USDRegime] = None) -> None:
    """Print a clean table of signals."""
    width = 120
    print("\n" + "=" * width)
    print("  USD STRENGTH SCANNER -- RESULTS")
    print("=" * width)

    if regime is not None:
        direction = "STRENGTHENING" if regime.is_strengthening else "WEAKENING/NEUTRAL"
        print(f"  Regime: USD {direction}   Confidence: {regime.confidence:.0%}")
        print(f"  Pillars confirmed: DXY_above_20d={regime.dxy_above_20sma}, "
              f"risk_off_breadth={regime.risk_off_breadth}/2, "
              f"jpy_up={regime.jpy_trending_up}")
        print("-" * width)

    if not signals:
        print("  No signals generated.")
        print("=" * width)
        return

    # Header
    header = (
        f"{'#':>2}  {'SYMBOL':<14} {'DIR':<5} {'ENTRY':>10} {'TP':>10} {'SL':>10} "
        f"{'RR':>5} {'CONF':>6} {'RSI':>5} {'MACD?':>6}"
    )
    print(header)
    print("-" * width)

    for i, sig in enumerate(signals, 1):
        macd_ok = "YES" if sig.get("macd_confirms") else "NO "
        row = (
            f"{i:>2}  {sig['symbol']:<14} {sig['signal_type']:<5} "
            f"{sig['entry_price']:>10.5f} {sig['take_profit']:>10.5f} {sig['stop_loss']:>10.5f} "
            f"{sig['risk_reward']:>5.2f} {sig['confidence']:>5.0%}  "
            f"{sig['rsi']:>5.1f} {macd_ok:>6}"
        )
        print(row)

    print("-" * width)
    print(f"  Total signals: {len(signals)}")
    print()

    # Detailed reasons
    print("  SIGNAL DETAILS:")
    for sig in signals:
        print(f"  [{sig['signal_type']} {sig['symbol']}] {sig['reason'][:110]}")

    print("=" * width)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("  USD STRENGTH SCANNER -- Alpha Engine")
    print(f"  Run: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # 1. Download data
    data = fetch_data(period="60d", interval="1d")

    if not data:
        print("[ERROR] No data downloaded. Check internet connection.")
        sys.exit(1)

    # 2. Detect regime
    regime = detect_usd_regime(data)
    print(f"\n[REGIME DETECTION] {regime}")
    if regime.confirming_signals:
        for s in regime.confirming_signals:
            print(f"  + {s}")
    else:
        print("  (no confirming signals)")

    # 3. Run scan
    signals = run_scan(data)

    # 4. Print results
    print_results(signals, regime)

    # 5. Summary JSON (for pipeline integration)
    import json
    output = {
        "regime": {
            "is_strengthening":   regime.is_strengthening,
            "confidence":         regime.confidence,
            "dxy_above_20sma":    regime.dxy_above_20sma,
            "risk_off_breadth":   regime.risk_off_breadth,
            "jpy_trending_up":    regime.jpy_trending_up,
            "confirming_signals": regime.confirming_signals,
        },
        "signals": signals,
        "signal_count": len(signals),
        "scan_time": datetime.now(timezone.utc).isoformat(),
    }
    out_path = Path(__file__).parent / "data" / "usd_strength_signals.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved to: {out_path}")


if __name__ == "__main__":
    main()
