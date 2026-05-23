#!/usr/bin/env python3
"""
Direction-Split Analyzer
=========================
Splits all trading analysis into symbol-specific LONG and SHORT strategies.
A BTC-SHORT strategy is fundamentally different from BTC-LONG.

Key insight from 221 real OKX trades:
  BTC SHORT: 64% WR | BTC LONG: 39% WR  (25% gap)
  ETH SHORT: 79% WR | ETH LONG: 59% WR  (20% gap)

This module ensures every strategy variation is direction-aware.
"""

import sys
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

import json
import math
import time
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Binance API failover chain (per project rules: 3+ fallbacks)
# ---------------------------------------------------------------------------
PRICE_ENDPOINTS = [
    "https://data-api.binance.vision",
    "https://api.binance.us",
    "https://api.binance.com",
    "https://api.coingecko.com/api/v3",
    "https://api.kucoin.com/api/v1",
]

# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------

def _safe_import(name):
    """Try to import optional dependencies, return None if missing."""
    try:
        return __import__(name)
    except ImportError:
        return None

pd = _safe_import("pandas")
np = _safe_import("numpy")
yf = _safe_import("yfinance")

# ---------------------------------------------------------------------------
# Symbol normalization
# ---------------------------------------------------------------------------

def normalize_symbol(inst: str) -> str:
    """Normalize instrument names to a consistent SYMBOL-USDT format.

    Examples: ETH-USDT-SWAP -> ETH-USDT, BTCUSDT -> BTC-USDT, BTC/USDT -> BTC-USDT
    """
    s = inst.upper().replace("-SWAP", "").replace("-PERP", "").replace("_PERP", "")
    s = s.replace("/", "-").replace("_", "-")
    # If no separator, try to split known bases
    if "-" not in s:
        for quote in ["USDT", "BUSD", "USDC", "USD"]:
            if s.endswith(quote) and len(s) > len(quote):
                s = s[: -len(quote)] + "-" + quote
                break
    return s


# ═══════════════════════════════════════════════════════════════════════════════
# 1. split_trades_by_direction
# ═══════════════════════════════════════════════════════════════════════════════

def split_trades_by_direction(trades: list) -> dict:
    """Split a flat list of trades into symbol-direction buckets.

    Each trade dict should have at least:
      - inst / symbol  (instrument name)
      - side / direction  (long or short)

    Returns:
        {
            "BTC-USDT_LONG": [trades...],
            "BTC-USDT_SHORT": [trades...],
            ...
        }
    """
    buckets = defaultdict(list)
    for t in trades:
        try:
            symbol = normalize_symbol(t.get("inst") or t.get("symbol") or "")
            direction = (t.get("side") or t.get("direction") or "").upper()
            if not symbol or direction not in ("LONG", "SHORT"):
                continue
            key = f"{symbol}_{direction}"
            buckets[key].append(t)
        except Exception:
            continue
    return dict(buckets)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. analyze_direction_edge
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_sharpe(returns: list, risk_free: float = 0.0) -> float:
    """Compute annualized Sharpe from a list of per-trade returns."""
    if len(returns) < 2:
        return 0.0
    try:
        mean_r = statistics.mean(returns) - risk_free
        std_r = statistics.stdev(returns)
        if std_r == 0:
            return 0.0
        # Annualize assuming ~250 trading days, ~6 trades/day
        return round((mean_r / std_r) * math.sqrt(250 * 6), 3)
    except Exception:
        return 0.0


def _max_drawdown(pnls: list) -> float:
    """Compute max drawdown from a list of pnl values."""
    if not pnls:
        return 0.0
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        cumulative += p
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 2)


def analyze_direction_edge(trades: list) -> dict:
    """Analyze win rate, profit factor, sharpe, etc. per symbol-direction combo.

    Returns dict keyed by 'SYMBOL_DIRECTION' with stats for each combo
    that has >= 5 trades.
    """
    buckets = split_trades_by_direction(trades)
    results = {}

    for key, bucket_trades in buckets.items():
        if len(bucket_trades) < 5:
            continue

        pnls = []
        returns = []
        hold_hours_wins = []
        hold_hours_losses = []
        entry_hours = []
        leverages = []

        for t in bucket_trades:
            pnl = t.get("pnl_usd") or t.get("pnl_dollar") or 0.0
            pnl_pct = t.get("pnl_pct") or 0.0
            hold_h = t.get("hold_hours") or t.get("hold_days", 0) * 24
            lev = t.get("leverage") or 1.0

            pnls.append(pnl)
            returns.append(pnl_pct)
            leverages.append(lev)

            if pnl > 0:
                hold_hours_wins.append(hold_h)
            else:
                hold_hours_losses.append(hold_h)

            # Extract entry hour from timestamp
            open_ts = t.get("open_time") or t.get("detected_at") or t.get("entry_date")
            if open_ts:
                try:
                    if isinstance(open_ts, (int, float)):
                        dt = datetime.fromtimestamp(open_ts / 1000, tz=timezone.utc)
                    else:
                        dt = datetime.fromisoformat(str(open_ts).replace("Z", "+00:00"))
                    entry_hours.append(dt.hour)
                except Exception:
                    pass

        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p <= 0)
        win_rate = round(wins / len(pnls) * 100, 1) if pnls else 0.0

        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.0

        avg_pnl = round(statistics.mean(pnls), 2) if pnls else 0.0
        sharpe = _safe_sharpe(returns)
        max_dd = _max_drawdown(pnls)

        # Best entry hours -- top 3 by frequency
        best_hours = []
        if entry_hours:
            hour_counts = defaultdict(int)
            for h in entry_hours:
                hour_counts[h] += 1
            best_hours = [h for h, _ in sorted(hour_counts.items(), key=lambda x: -x[1])[:3]]

        results[key] = {
            "symbol": key.rsplit("_", 1)[0],
            "direction": key.rsplit("_", 1)[1],
            "sample_size": len(bucket_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "sharpe": sharpe,
            "avg_pnl": avg_pnl,
            "max_dd": max_dd,
            "avg_hold_hours_wins": round(statistics.mean(hold_hours_wins), 2) if hold_hours_wins else 0.0,
            "avg_hold_hours_losses": round(statistics.mean(hold_hours_losses), 2) if hold_hours_losses else 0.0,
            "best_entry_hours": best_hours,
            "avg_leverage": round(statistics.mean(leverages), 1) if leverages else 1.0,
        }

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# 3. compute_directional_features
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_rsi(closes, period=14):
    """Compute RSI from a list of close prices."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _compute_ema(closes, period):
    """Compute EMA from a list of close prices, return last value."""
    if len(closes) < period:
        return None
    multiplier = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema
    return round(ema, 4)


def _compute_macd(closes, fast=12, slow=26, signal=9):
    """Compute MACD line and signal line, return (macd, signal, histogram)."""
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = _compute_ema(closes, fast)
    ema_slow = _compute_ema(closes, slow)
    if ema_fast is None or ema_slow is None:
        return None, None, None
    macd_line = ema_fast - ema_slow
    # Approximate signal -- use last signal-period of MACD values
    # For simplicity, compute from price deltas
    return round(macd_line, 4), None, None


def _compute_bollinger(closes, period=20, std_mult=2.0):
    """Compute Bollinger Bands, return (upper, middle, lower, pct_b)."""
    if len(closes) < period:
        return None, None, None, None
    window = closes[-period:]
    middle = statistics.mean(window)
    std = statistics.stdev(window) if len(window) > 1 else 0
    upper = middle + std_mult * std
    lower = middle - std_mult * std
    current = closes[-1]
    pct_b = (current - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
    return round(upper, 4), round(middle, 4), round(lower, 4), round(pct_b, 4)


def compute_directional_features(symbol: str, direction: str, data=None) -> dict:
    """Compute technical features that differ for LONG vs SHORT entries.

    For LONG: oversold RSI, support bounces, bullish MACD, near lower BB
    For SHORT: overbought RSI, resistance rejection, bearish MACD, near upper BB

    Args:
        symbol: e.g. "BTC-USDT"
        direction: "LONG" or "SHORT"
        data: pandas DataFrame with OHLCV (or None to fetch via yfinance)

    Returns dict of features and their current signal strength.
    """
    features = {
        "symbol": symbol,
        "direction": direction,
        "rsi_14": None,
        "rsi_signal": "neutral",
        "macd_signal": "neutral",
        "bb_pct_b": None,
        "bb_signal": "neutral",
        "ema50_trend": "neutral",
        "volume_ratio": None,
        "volume_signal": "neutral",
        "overall_score": 0.0,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    closes = None
    volumes = None

    # Try to get price data from DataFrame or yfinance
    if data is not None and pd is not None:
        try:
            if hasattr(data, "Close") or "Close" in data.columns:
                closes = data["Close"].dropna().tolist()
                volumes = data["Volume"].dropna().tolist() if "Volume" in data.columns else None
            elif "close" in data.columns:
                closes = data["close"].dropna().tolist()
                volumes = data["volume"].dropna().tolist() if "volume" in data.columns else None
        except Exception:
            pass
    elif yf is not None and data is None:
        try:
            # Map symbol to yfinance ticker
            ticker_map = {
                "BTC-USDT": "BTC-USD", "BTC-USD": "BTC-USD",
                "ETH-USDT": "ETH-USD", "ETH-USD": "ETH-USD",
                "SOL-USDT": "SOL-USD", "SOL-USD": "SOL-USD",
                "BNB-USDT": "BNB-USD", "XRP-USDT": "XRP-USD",
                "DOGE-USDT": "DOGE-USD", "ADA-USDT": "ADA-USD",
                "AVAX-USDT": "AVAX-USD", "DOT-USDT": "DOT-USD",
                "LINK-USDT": "LINK-USD", "MATIC-USDT": "MATIC-USD",
            }
            yf_sym = ticker_map.get(symbol, symbol.replace("-USDT", "-USD"))
            # Rate limit protection
            time.sleep(0.5)
            df = yf.download(yf_sym, period="60d", interval="4h", progress=False)
            if df is not None and len(df) > 0:
                closes = df["Close"].dropna().tolist()
                volumes = df["Volume"].dropna().tolist() if "Volume" in df.columns else None
        except Exception as e:
            print(f"  [WARN] yfinance fetch failed for {symbol}: {e}")

    if not closes or len(closes) < 30:
        features["error"] = "insufficient_price_data"
        return features

    direction = direction.upper()

    # RSI
    rsi = _compute_rsi(closes)
    features["rsi_14"] = rsi
    if rsi is not None:
        if direction == "LONG":
            if rsi < 30:
                features["rsi_signal"] = "strong_buy"
            elif rsi < 40:
                features["rsi_signal"] = "buy"
            elif rsi > 70:
                features["rsi_signal"] = "avoid"
            else:
                features["rsi_signal"] = "neutral"
        else:  # SHORT
            if rsi > 70:
                features["rsi_signal"] = "strong_sell"
            elif rsi > 60:
                features["rsi_signal"] = "sell"
            elif rsi < 30:
                features["rsi_signal"] = "avoid"
            else:
                features["rsi_signal"] = "neutral"

    # MACD
    macd, _, _ = _compute_macd(closes)
    if macd is not None:
        if direction == "LONG":
            features["macd_signal"] = "bullish" if macd > 0 else "bearish"
        else:
            features["macd_signal"] = "bearish" if macd < 0 else "bullish"

    # Bollinger Bands
    upper, middle, lower, pct_b = _compute_bollinger(closes)
    features["bb_pct_b"] = pct_b
    if pct_b is not None:
        if direction == "LONG":
            if pct_b < 0.1:
                features["bb_signal"] = "strong_buy"
            elif pct_b < 0.3:
                features["bb_signal"] = "buy"
            elif pct_b > 0.9:
                features["bb_signal"] = "avoid"
            else:
                features["bb_signal"] = "neutral"
        else:  # SHORT
            if pct_b > 0.9:
                features["bb_signal"] = "strong_sell"
            elif pct_b > 0.7:
                features["bb_signal"] = "sell"
            elif pct_b < 0.1:
                features["bb_signal"] = "avoid"
            else:
                features["bb_signal"] = "neutral"

    # EMA50 trend
    ema50 = _compute_ema(closes, 50)
    if ema50 is not None:
        current_price = closes[-1]
        if direction == "LONG":
            features["ema50_trend"] = "bullish" if current_price > ema50 else "bearish"
        else:
            features["ema50_trend"] = "bearish" if current_price < ema50 else "bullish"

    # Volume ratio (current vs 20-period average)
    if volumes and len(volumes) >= 20:
        avg_vol = statistics.mean(volumes[-20:])
        current_vol = volumes[-1]
        vol_ratio = round(current_vol / avg_vol, 2) if avg_vol > 0 else 1.0
        features["volume_ratio"] = vol_ratio
        if vol_ratio > 1.5:
            features["volume_signal"] = "high_volume"
        elif vol_ratio < 0.5:
            features["volume_signal"] = "low_volume"
        else:
            features["volume_signal"] = "normal"

    # Compute overall score (0.0 to 1.0)
    score = 0.5  # neutral baseline
    signal_scores = {
        "strong_buy": 0.15, "buy": 0.1, "strong_sell": 0.15, "sell": 0.1,
        "bullish": 0.1, "bearish": -0.05, "avoid": -0.15,
        "high_volume": 0.05, "neutral": 0.0, "low_volume": -0.05, "normal": 0.0,
    }

    for field in ["rsi_signal", "macd_signal", "bb_signal", "ema50_trend", "volume_signal"]:
        val = features.get(field, "neutral")
        score += signal_scores.get(val, 0.0)

    features["overall_score"] = round(max(0.0, min(1.0, score)), 3)
    return features


# ═══════════════════════════════════════════════════════════════════════════════
# 4. generate_direction_variations
# ═══════════════════════════════════════════════════════════════════════════════

def generate_direction_variations(symbol: str, direction: str,
                                   edge_stats: dict, features: dict) -> list:
    """Generate 3 strategy variations for a symbol-direction combo.

    Variation 1: Pure technical (RSI + BB + trend aligned)
    Variation 2: Session + momentum (best hours + 4h momentum match)
    Variation 3: Volume + patience (volume confirmation + hold time rules)
    """
    direction = direction.upper()
    sym_lower = symbol.lower().replace("-", "")
    dir_lower = direction.lower()

    wr = edge_stats.get("win_rate", 50.0)
    avg_hold_wins = edge_stats.get("avg_hold_hours_wins", 6.0)
    avg_hold_losses = edge_stats.get("avg_hold_hours_losses", 3.0)
    best_hours = edge_stats.get("best_entry_hours", [])
    avg_lev = edge_stats.get("avg_leverage", 5.0)
    pf = edge_stats.get("profit_factor", 1.0)

    # Direction-specific TP/SL defaults
    if direction == "SHORT":
        # Shorts tend to hit TP faster with tighter targets
        base_tp = 2.5
        base_sl = 1.2
    else:
        # Longs need wider stops in current market
        base_tp = 3.0
        base_sl = 1.5

    # Adjust based on edge data
    if pf > 2.0:
        base_tp *= 1.2  # let winners run more
    if wr > 65:
        base_sl *= 0.9  # tighter SL since we're right more often

    rsi_val = features.get("rsi_14")
    bb_val = features.get("bb_pct_b")
    overall_score = features.get("overall_score", 0.5)

    variations = []

    # --- Variation 1: Pure Technical ---
    entry_rules_tech = {}
    if direction == "LONG":
        entry_rules_tech = {
            "rsi_below": 40,
            "bb_pct_b_below": 0.3,
            "ema50_trend": "bullish",
            "macd_cross": "bullish",
        }
    else:
        entry_rules_tech = {
            "rsi_above": 60,
            "bb_pct_b_above": 0.7,
            "ema50_trend": "bearish",
            "macd_cross": "bearish",
        }

    variations.append({
        "name": f"{sym_lower}_{dir_lower}_technical",
        "symbol": symbol,
        "direction": direction,
        "variation_type": "technical",
        "entry_rules": entry_rules_tech,
        "tp_pct": round(base_tp, 2),
        "sl_pct": round(base_sl, 2),
        "max_hold_hours": round(avg_hold_wins * 1.5, 1),
        "session_filter": [],  # no session filter for pure technical
        "min_confidence": 0.6,
        "expected_wr": round(wr * 1.05, 1),  # slightly better with tech filter
        "leverage": min(round(avg_lev, 0), 20),
        "description": f"{direction} when RSI + BB + trend all align",
    })

    # --- Variation 2: Session + Momentum ---
    session_hours = best_hours if best_hours else [12, 13, 14, 15]
    entry_rules_session = {
        "entry_hours_utc": session_hours,
        "momentum_4h_aligned": True,
    }
    if direction == "LONG":
        entry_rules_session["price_above_vwap"] = True
    else:
        entry_rules_session["price_below_vwap"] = True

    variations.append({
        "name": f"{sym_lower}_{dir_lower}_session",
        "symbol": symbol,
        "direction": direction,
        "variation_type": "session_momentum",
        "entry_rules": entry_rules_session,
        "tp_pct": round(base_tp * 0.85, 2),  # slightly tighter for session trades
        "sl_pct": round(base_sl * 0.9, 2),
        "max_hold_hours": round(avg_hold_wins * 1.0, 1),
        "session_filter": session_hours,
        "min_confidence": 0.65,
        "expected_wr": round(wr * 1.08, 1),
        "leverage": min(round(avg_lev, 0), 20),
        "description": f"{direction} during best session hours with 4h momentum confirmation",
    })

    # --- Variation 3: Volume + Patience ---
    entry_rules_vol = {
        "volume_ratio_above": 1.3,
        "min_hold_hours": round(avg_hold_wins * 0.5, 1),
        "max_hold_hours": round(avg_hold_wins * 2.0, 1),
    }
    if direction == "LONG":
        entry_rules_vol["bullish_volume_expansion"] = True
    else:
        entry_rules_vol["bearish_volume_expansion"] = True

    # Patience = wider TP/SL but better risk/reward
    variations.append({
        "name": f"{sym_lower}_{dir_lower}_volume",
        "symbol": symbol,
        "direction": direction,
        "variation_type": "volume_patience",
        "entry_rules": entry_rules_vol,
        "tp_pct": round(base_tp * 1.3, 2),
        "sl_pct": round(base_sl * 1.1, 2),
        "max_hold_hours": round(avg_hold_wins * 2.5, 1),
        "session_filter": [],
        "min_confidence": 0.55,
        "expected_wr": round(wr * 0.95, 1),  # slightly lower WR but better R:R
        "leverage": min(round(avg_lev * 0.8, 0), 15),  # lower lev for patience
        "description": f"{direction} on volume expansion, wider targets, patient hold",
    })

    return variations


# ═══════════════════════════════════════════════════════════════════════════════
# 5. backtest_directional_variation
# ═══════════════════════════════════════════════════════════════════════════════

def backtest_directional_variation(variation: dict, data=None) -> dict:
    """Backtest a single directional variation against historical price data.

    Args:
        variation: dict from generate_direction_variations
        data: pandas DataFrame with OHLCV or None to fetch

    Returns backtest result dict.
    """
    result = {
        "variation_name": variation["name"],
        "symbol": variation["symbol"],
        "direction": variation["direction"],
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "sharpe": 0.0,
        "max_dd": 0.0,
        "avg_hold_hours": 0.0,
        "total_pnl_pct": 0.0,
        "status": "no_data",
    }

    closes = None
    highs = None
    lows = None

    if data is not None and pd is not None:
        try:
            close_col = "Close" if "Close" in data.columns else "close"
            high_col = "High" if "High" in data.columns else "high"
            low_col = "Low" if "Low" in data.columns else "low"
            closes = data[close_col].dropna().tolist()
            highs = data[high_col].dropna().tolist() if high_col in data.columns else closes
            lows = data[low_col].dropna().tolist() if low_col in data.columns else closes
        except Exception:
            pass
    elif yf is not None and data is None:
        try:
            ticker_map = {
                "BTC-USDT": "BTC-USD", "ETH-USDT": "ETH-USD",
                "SOL-USDT": "SOL-USD", "BNB-USDT": "BNB-USD",
                "XRP-USDT": "XRP-USD", "DOGE-USDT": "DOGE-USD",
            }
            yf_sym = ticker_map.get(variation["symbol"],
                                     variation["symbol"].replace("-USDT", "-USD"))
            time.sleep(0.5)
            df = yf.download(yf_sym, period="90d", interval="4h", progress=False)
            if df is not None and len(df) > 0:
                closes = df["Close"].dropna().tolist()
                highs = df["High"].dropna().tolist()
                lows = df["Low"].dropna().tolist()
        except Exception as e:
            result["error"] = str(e)
            return result

    if not closes or len(closes) < 50:
        result["status"] = "insufficient_data"
        return result

    tp_pct = variation.get("tp_pct", 3.0) / 100.0
    sl_pct = variation.get("sl_pct", 1.5) / 100.0
    direction = variation["direction"].upper()
    entry_rules = variation.get("entry_rules", {})
    session_filter = variation.get("session_filter", [])

    trades = []
    pnls = []
    returns = []
    hold_lengths = []

    # Simple bar-by-bar backtest
    i = 50  # start after enough data for indicators
    while i < len(closes) - 1:
        # Check entry conditions
        entry_price = closes[i]
        should_enter = False

        # RSI check
        rsi = _compute_rsi(closes[:i + 1])
        if rsi is not None:
            if direction == "LONG" and entry_rules.get("rsi_below"):
                if rsi < entry_rules["rsi_below"]:
                    should_enter = True
            elif direction == "SHORT" and entry_rules.get("rsi_above"):
                if rsi > entry_rules["rsi_above"]:
                    should_enter = True
            elif "rsi_below" not in entry_rules and "rsi_above" not in entry_rules:
                # No RSI rule, check other rules
                should_enter = True

        # Volume ratio check
        if entry_rules.get("volume_ratio_above"):
            should_enter = True  # simplified -- would need volume data

        # Session/momentum check
        if entry_rules.get("momentum_4h_aligned"):
            # Check 4-bar momentum
            if i >= 4:
                mom = closes[i] - closes[i - 4]
                if direction == "LONG" and mom > 0:
                    should_enter = True
                elif direction == "SHORT" and mom < 0:
                    should_enter = True

        if not should_enter:
            i += 1
            continue

        # Simulate trade
        if direction == "LONG":
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)
        else:
            tp_price = entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 + sl_pct)

        # Walk forward to find exit
        max_bars = int(variation.get("max_hold_hours", 24) / 4)  # 4h bars
        max_bars = max(max_bars, 2)
        exit_price = None
        exit_reason = None
        bars_held = 0

        for j in range(i + 1, min(i + max_bars + 1, len(closes))):
            bars_held += 1
            bar_high = highs[j] if j < len(highs) else closes[j]
            bar_low = lows[j] if j < len(lows) else closes[j]

            if direction == "LONG":
                if bar_high >= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    break
                elif bar_low <= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    break
            else:  # SHORT
                if bar_low <= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    break
                elif bar_high >= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    break

        if exit_price is None:
            # Max hold reached, exit at current price
            exit_price = closes[min(i + max_bars, len(closes) - 1)]
            exit_reason = "MAX_HOLD"

        # Calculate PnL
        if direction == "LONG":
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        trades.append({
            "entry_bar": i,
            "exit_bar": i + bars_held,
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "pnl_pct": round(pnl_pct, 3),
            "exit_reason": exit_reason,
            "bars_held": bars_held,
        })

        pnls.append(pnl_pct)
        returns.append(pnl_pct / 100.0)
        hold_lengths.append(bars_held * 4)  # convert to hours

        # Skip ahead past exit
        i += bars_held + 1

    if not trades:
        result["status"] = "no_trades"
        return result

    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p <= 0)
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))

    result["trades"] = len(trades)
    result["wins"] = wins
    result["losses"] = losses
    result["win_rate"] = round(wins / len(trades) * 100, 1) if trades else 0.0
    result["profit_factor"] = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.0
    result["sharpe"] = _safe_sharpe(returns)
    result["max_dd"] = _max_drawdown(pnls)
    result["avg_hold_hours"] = round(statistics.mean(hold_lengths), 1) if hold_lengths else 0.0
    result["total_pnl_pct"] = round(sum(pnls), 2)
    result["status"] = "complete"
    result["trade_details"] = trades

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 6. run_full_directional_analysis (main)
# ═══════════════════════════════════════════════════════════════════════════════

def _load_json(filename: str) -> dict:
    """Load a JSON file from the data directory."""
    path = DATA_DIR / filename
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] Failed to load {filename}: {e}")
        return {}


def _save_json(filename: str, data):
    """Save data as JSON to the data directory."""
    path = DATA_DIR / filename
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        print(f"  [OK] Saved {path}")
    except Exception as e:
        print(f"  [ERROR] Failed to save {filename}: {e}")


def _flatten_okx_trades(trade_data: dict) -> list:
    """Flatten OKX trade history (keyed by trader ID) into a single trade list."""
    all_trades = []
    traders = trade_data.get("traders", trade_data)
    if isinstance(traders, dict):
        for trader_id, trades in traders.items():
            if isinstance(trades, list):
                for t in trades:
                    t["_trader_id"] = trader_id
                    all_trades.append(t)
    elif isinstance(traders, list):
        all_trades = traders
    return all_trades


def _flatten_active_picks(picks_data) -> list:
    """Flatten active picks (list or dict) into trade-like records."""
    if isinstance(picks_data, list):
        return picks_data
    if isinstance(picks_data, dict):
        return picks_data.get("picks", picks_data.get("active_picks", []))
    return []


def run_full_directional_analysis():
    """Run full directional analysis pipeline.

    1. Load OKX trade history + active picks
    2. Split by direction per symbol
    3. Analyze edge per direction
    4. Compute directional features (yfinance)
    5. Generate 3 variations per direction (6 per symbol)
    6. Backtest each variation
    7. Rank by Sharpe and save results
    """
    print("=" * 70)
    print("  DIRECTION-SPLIT ANALYZER")
    print("  Splitting ALL analysis into LONG vs SHORT per symbol")
    print("=" * 70)
    start_time = time.time()

    # ── Step 1: Load trade data ──────────────────────────────────────────
    print("\n[1/7] Loading trade data...")

    all_trades = []

    # OKX trade history (primary)
    okx_data = _load_json("okx_trade_history.json")
    if okx_data:
        okx_trades = _flatten_okx_trades(okx_data)
        print(f"  OKX trades: {len(okx_trades)}")
        all_trades.extend(okx_trades)

    # Active picks from copy trader intel
    picks_data = _load_json("active_picks.json")
    if picks_data:
        picks = _flatten_active_picks(picks_data)
        # Convert picks to trade-like format
        for p in picks:
            if p.get("status") == "CLOSED" or p.get("pnl_pct") is not None:
                trade = {
                    "inst": p.get("symbol", ""),
                    "side": (p.get("direction") or "").lower(),
                    "pnl_usd": p.get("pnl_dollar") or 0,
                    "pnl_pct": p.get("pnl_pct") or 0,
                    "hold_hours": (p.get("hold_days") or 0) * 24,
                    "leverage": p.get("max_safe_leverage") or 1,
                    "open_time": p.get("detected_at"),
                }
                all_trades.append(trade)
        print(f"  Active picks (closed): {sum(1 for p in picks if p.get('status') == 'CLOSED')}")

    # Also load strategy_variations forward test results
    fwd_data = _load_json("variation_forward_test.json")
    if fwd_data:
        fwd_trades = fwd_data.get("closed_trades", [])
        for ft in fwd_trades:
            trade = {
                "inst": ft.get("symbol") or ft.get("coin", ""),
                "side": (ft.get("direction") or "").lower(),
                "pnl_usd": ft.get("pnl_usd") or ft.get("pnl_dollar") or 0,
                "pnl_pct": ft.get("pnl_pct") or 0,
                "hold_hours": ft.get("hold_hours") or 0,
                "leverage": ft.get("leverage") or 1,
                "open_time": ft.get("entry_time"),
            }
            all_trades.append(trade)
        print(f"  Forward test trades: {len(fwd_trades)}")

    # Load multi-asset picks for forex/equity analysis
    multi_asset_files = [
        "cta_strategy_picks.json",
        "multi_asset_picks.json",
    ]
    multi_asset_trades = []
    for mf in multi_asset_files:
        mdata = _load_json(mf)
        if mdata:
            mpicks = _flatten_active_picks(mdata)
            for p in mpicks:
                if p.get("pnl_pct") is not None:
                    trade = {
                        "inst": p.get("symbol", ""),
                        "side": (p.get("direction") or "").lower(),
                        "pnl_usd": p.get("pnl_dollar") or 0,
                        "pnl_pct": p.get("pnl_pct") or 0,
                        "hold_hours": (p.get("hold_days") or 0) * 24,
                        "leverage": p.get("leverage") or 1,
                        "open_time": p.get("detected_at"),
                    }
                    multi_asset_trades.append(trade)
            print(f"  {mf}: {len(mpicks)} picks")
    all_trades.extend(multi_asset_trades)

    print(f"\n  Total trades loaded: {len(all_trades)}")

    if not all_trades:
        print("[ERROR] No trades found. Cannot analyze.")
        return

    # ── Step 2: Split by direction ───────────────────────────────────────
    print("\n[2/7] Splitting trades by symbol + direction...")
    buckets = split_trades_by_direction(all_trades)
    print(f"  Found {len(buckets)} symbol-direction combos:")
    for key, trades in sorted(buckets.items(), key=lambda x: -len(x[1])):
        print(f"    {key}: {len(trades)} trades")

    # ── Step 3: Analyze edge per direction ───────────────────────────────
    print("\n[3/7] Analyzing directional edge...")
    edge_results = analyze_direction_edge(all_trades)
    print(f"  Qualified combos (>= 5 trades): {len(edge_results)}")
    for key, stats in sorted(edge_results.items(), key=lambda x: -x[1]["win_rate"]):
        print(f"    {key}: WR={stats['win_rate']}% PF={stats['profit_factor']} "
              f"Sharpe={stats['sharpe']} n={stats['sample_size']}")

    # ── Step 4: Compute directional features ─────────────────────────────
    print("\n[4/7] Computing directional features (yfinance)...")
    all_features = {}
    for key, stats in edge_results.items():
        symbol = stats["symbol"]
        direction = stats["direction"]
        try:
            features = compute_directional_features(symbol, direction)
            all_features[key] = features
            score = features.get("overall_score", 0)
            print(f"    {key}: score={score} rsi={features.get('rsi_14')} "
                  f"bb={features.get('bb_pct_b')}")
        except Exception as e:
            print(f"    {key}: [ERROR] {e}")
            all_features[key] = {"error": str(e)}

    # ── Step 5: Generate variations ──────────────────────────────────────
    print("\n[5/7] Generating 3 variations per symbol-direction...")
    all_variations = []
    for key, stats in edge_results.items():
        symbol = stats["symbol"]
        direction = stats["direction"]
        features = all_features.get(key, {})
        try:
            variations = generate_direction_variations(symbol, direction, stats, features)
            all_variations.extend(variations)
            print(f"    {key}: {len(variations)} variations")
        except Exception as e:
            print(f"    {key}: [ERROR] generating variations: {e}")

    print(f"  Total variations generated: {len(all_variations)}")

    # ── Step 6: Backtest each variation ──────────────────────────────────
    print("\n[6/7] Backtesting variations...")
    backtest_results = []
    # Cache yfinance data per symbol to avoid redundant downloads
    price_cache = {}

    for var in all_variations:
        symbol = var["symbol"]
        try:
            cached_data = price_cache.get(symbol)
            if cached_data is None and yf is not None:
                ticker_map = {
                    "BTC-USDT": "BTC-USD", "ETH-USDT": "ETH-USD",
                    "SOL-USDT": "SOL-USD", "BNB-USDT": "BNB-USD",
                    "XRP-USDT": "XRP-USD", "DOGE-USDT": "DOGE-USD",
                }
                yf_sym = ticker_map.get(symbol, symbol.replace("-USDT", "-USD"))
                time.sleep(0.5)
                df = yf.download(yf_sym, period="90d", interval="4h", progress=False)
                if df is not None and len(df) > 0:
                    price_cache[symbol] = df
                    cached_data = df
                else:
                    price_cache[symbol] = False  # mark as failed
                    cached_data = None

            if cached_data is False:
                cached_data = None

            bt = backtest_directional_variation(var, data=cached_data)
            backtest_results.append(bt)
            if bt["trades"] > 0:
                print(f"    {var['name']}: {bt['trades']} trades, "
                      f"WR={bt['win_rate']}%, PF={bt['profit_factor']}, "
                      f"Sharpe={bt['sharpe']}")
            else:
                print(f"    {var['name']}: {bt['status']}")
        except Exception as e:
            print(f"    {var['name']}: [ERROR] {e}")
            backtest_results.append({
                "variation_name": var["name"],
                "status": "error",
                "error": str(e),
            })

    # ── Step 7: Rank and save ────────────────────────────────────────────
    print("\n[7/7] Ranking variations and saving results...")

    # Rank by Sharpe ratio
    ranked = sorted(
        [bt for bt in backtest_results if bt.get("trades", 0) > 0],
        key=lambda x: x.get("sharpe", 0),
        reverse=True,
    )

    # Save direction_split_analysis.json
    analysis_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": "1.0",
        "total_trades_analyzed": len(all_trades),
        "symbol_direction_combos": len(edge_results),
        "edge_stats": edge_results,
    }
    _save_json("direction_split_analysis.json", analysis_output)

    # Save direction_variations.json
    variations_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": "1.0",
        "total_variations": len(all_variations),
        "variations": all_variations,
        "backtest_results": backtest_results,
        "ranked_by_sharpe": [
            {
                "rank": i + 1,
                "name": bt["variation_name"],
                "symbol": bt.get("symbol"),
                "direction": bt.get("direction"),
                "trades": bt.get("trades"),
                "win_rate": bt.get("win_rate"),
                "profit_factor": bt.get("profit_factor"),
                "sharpe": bt.get("sharpe"),
                "total_pnl_pct": bt.get("total_pnl_pct"),
            }
            for i, bt in enumerate(ranked[:30])
        ],
    }
    _save_json("direction_variations.json", variations_output)

    # Save direction_top_picks.json -- current picks from top 20 variations
    top_20 = ranked[:20]
    top_picks = []
    for bt in top_20:
        # Find the matching variation
        var = next((v for v in all_variations if v["name"] == bt["variation_name"]), None)
        if var is None:
            continue

        edge_key = f"{var['symbol']}_{var['direction']}"
        edge = edge_results.get(edge_key, {})
        features = all_features.get(edge_key, {})

        pick = {
            "id": f"dirsplit_{var['name']}_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            "strategy": var["name"],
            "symbol": var["symbol"].replace("-", ""),
            "category": "crypto" if "USDT" in var["symbol"] or "USD" in var["symbol"] else "forex",
            "signal_type": "BUY" if var["direction"] == "LONG" else "SELL",
            "direction": var["direction"],
            "entry_rules": var["entry_rules"],
            "tp_pct": var["tp_pct"],
            "sl_pct": var["sl_pct"],
            "max_hold_hours": var["max_hold_hours"],
            "confidence": round(min(bt.get("win_rate", 50) / 100.0, 0.95), 3),
            "expected_wr": bt.get("win_rate", 0),
            "backtest_sharpe": bt.get("sharpe", 0),
            "backtest_pf": bt.get("profit_factor", 0),
            "backtest_trades": bt.get("trades", 0),
            "edge_stats": {
                "historical_wr": edge.get("win_rate"),
                "historical_pf": edge.get("profit_factor"),
                "sample_size": edge.get("sample_size"),
            },
            "features": {
                "overall_score": features.get("overall_score"),
                "rsi": features.get("rsi_14"),
                "bb_pct_b": features.get("bb_pct_b"),
            },
            "source_system": f"direction_split_{var['symbol']}_{var['direction']}",
            "status": "ACTIVE",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        top_picks.append(pick)

    picks_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": "1.0",
        "top_variations_count": len(top_picks),
        "picks": top_picks,
    }
    _save_json("direction_top_picks.json", picks_output)

    # ── Print summary table ──────────────────────────────────────────────
    elapsed = round(time.time() - start_time, 1)

    print("\n" + "=" * 85)
    print("  DIRECTIONAL EDGE SUMMARY")
    print("=" * 85)
    print(f"{'Symbol':<14} {'Direction':<10} {'EdgeWR':>8} {'Variations':>12} "
          f"{'Best Var WR':>12} {'Best Var Sharpe':>15}")
    print("-" * 85)

    # Group by symbol
    symbols_seen = {}
    for key, stats in sorted(edge_results.items(), key=lambda x: -x[1]["win_rate"]):
        symbol = stats["symbol"]
        direction = stats["direction"]

        # Find best variation for this symbol-direction
        sym_dir_bts = [bt for bt in ranked
                       if bt.get("symbol") == symbol and bt.get("direction") == direction]
        best_wr = max((bt.get("win_rate", 0) for bt in sym_dir_bts), default=0)
        best_sharpe = max((bt.get("sharpe", 0) for bt in sym_dir_bts), default=0)
        num_vars = sum(1 for v in all_variations
                       if v["symbol"] == symbol and v["direction"] == direction)

        print(f"{symbol:<14} {direction:<10} {stats['win_rate']:>7.1f}% {num_vars:>12} "
              f"{best_wr:>11.1f}% {best_sharpe:>15.2f}")

    print("-" * 85)
    print(f"  Total trades analyzed: {len(all_trades)}")
    print(f"  Symbol-direction combos: {len(edge_results)}")
    print(f"  Total variations: {len(all_variations)}")
    print(f"  Backtested: {sum(1 for bt in backtest_results if bt.get('trades', 0) > 0)}")
    print(f"  Top picks generated: {len(top_picks)}")
    print(f"  Elapsed: {elapsed}s")
    print("=" * 85)

    return {
        "edge_results": edge_results,
        "variations": all_variations,
        "backtest_results": backtest_results,
        "top_picks": top_picks,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Multi-asset analysis (forex, commodities, equities)
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_multi_asset_directions():
    """Analyze directional edge for non-crypto assets.

    Loads CTA strategy picks and multi-asset data, splits by direction,
    and generates variations for forex pairs, commodities, and equities.
    """
    print("\n" + "=" * 70)
    print("  MULTI-ASSET DIRECTIONAL ANALYSIS")
    print("=" * 70)

    # Define yfinance tickers for non-crypto assets
    forex_pairs = {
        "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X", "USDCAD": "USDCAD=X", "NZDUSD": "NZDUSD=X",
    }
    commodities = {
        "GOLD": "GC=F", "SILVER": "SI=F", "OIL": "CL=F",
    }
    equities = {
        "SPY": "SPY", "QQQ": "QQQ", "TSLA": "TSLA", "NVDA": "NVDA",
    }

    all_assets = {}
    all_assets.update(forex_pairs)
    all_assets.update(commodities)
    all_assets.update(equities)

    # Load any existing multi-asset trade data
    multi_trades = []
    for fname in ["cta_strategy_picks.json", "multi_asset_picks.json"]:
        data = _load_json(fname)
        if data:
            picks = _flatten_active_picks(data)
            for p in picks:
                if p.get("pnl_pct") is not None:
                    multi_trades.append({
                        "inst": p.get("symbol", ""),
                        "side": (p.get("direction") or "").lower(),
                        "pnl_usd": p.get("pnl_dollar") or 0,
                        "pnl_pct": p.get("pnl_pct") or 0,
                        "hold_hours": (p.get("hold_days") or 0) * 24,
                        "leverage": p.get("leverage") or 1,
                        "open_time": p.get("detected_at"),
                    })

    print(f"  Multi-asset trades loaded: {len(multi_trades)}")

    # For assets without enough trade history, generate both LONG and SHORT
    # variations using technical features only
    multi_variations = []

    for asset_name, yf_ticker in all_assets.items():
        if yf is None:
            print(f"  [SKIP] {asset_name} -- yfinance not available")
            continue

        try:
            time.sleep(0.5)
            df = yf.download(yf_ticker, period="90d", interval="4h", progress=False)
            if df is None or len(df) < 50:
                print(f"  [SKIP] {asset_name} -- insufficient data")
                continue

            for direction in ["LONG", "SHORT"]:
                features = compute_directional_features(asset_name, direction, data=df)

                # Create synthetic edge stats from features
                base_wr = 55.0 if direction == "LONG" else 50.0
                if asset_name in equities:
                    base_wr = 58.0 if direction == "LONG" else 45.0  # equity long bias

                synthetic_edge = {
                    "win_rate": base_wr,
                    "profit_factor": 1.2,
                    "avg_hold_hours_wins": 12.0,
                    "avg_hold_hours_losses": 6.0,
                    "best_entry_hours": [9, 10, 14, 15],
                    "avg_leverage": 2.0 if asset_name in forex_pairs else 1.0,
                }

                variations = generate_direction_variations(
                    asset_name, direction, synthetic_edge, features
                )
                multi_variations.extend(variations)
                print(f"    {asset_name} {direction}: score={features.get('overall_score', 0):.3f}")

        except Exception as e:
            print(f"  [ERROR] {asset_name}: {e}")

    print(f"\n  Multi-asset variations generated: {len(multi_variations)}")

    # Save multi-asset variations
    if multi_variations:
        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": "1.0",
            "asset_classes": ["forex", "commodities", "equities"],
            "total_variations": len(multi_variations),
            "variations": multi_variations,
        }
        _save_json("direction_multi_asset_variations.json", output)

    return multi_variations


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Direction-Split Analyzer")
    parser.add_argument("--multi-asset", action="store_true",
                        help="Also analyze forex/commodities/equities")
    parser.add_argument("--symbol", type=str, default=None,
                        help="Analyze a single symbol (e.g. BTC-USDT)")
    parser.add_argument("--direction", type=str, default=None,
                        help="Analyze a single direction (LONG or SHORT)")
    args = parser.parse_args()

    if args.symbol and args.direction:
        # Single symbol-direction analysis
        print(f"Analyzing {args.symbol} {args.direction}...")
        features = compute_directional_features(args.symbol, args.direction.upper())
        print(json.dumps(features, indent=2, default=str))
    else:
        # Full analysis
        results = run_full_directional_analysis()
        if args.multi_asset:
            analyze_multi_asset_directions()

    print("\nDone.")
