#!/usr/bin/env python3
"""
Momentum Scalp Scanner — Dynamic Symbol Universe Expansion
============================================================

Scans Binance for top gainers (24h + 7d) and runs our best-performing
strategies on them to catch momentum continuation for scalp profits.

Pipeline:
  1. Fetch ALL USDT pairs from Binance 24h ticker
  2. Filter for volume > $1M, sort by 24h gain
  3. Take top 30 gainers + top 10 losers (bounce plays)
  4. Fetch 1h OHLCV for each and run signal strategies
  5. Output momentum picks to genome/data/momentum_scalp_picks.json

Strategies applied (our proven + best SANDBOX):
  - genesis_momentum_blend (PASSED backtest, +20.90%)
  - cross_agg_battleground_hybrid (PASSED backtest, 50.4% WR)
  - ema_momentum_volume (tournament winner)
  - mtf_align_mut (best SANDBOX, 39.7% WR, lowest DD)

Run: py -3.13 genome/mutation_lab/momentum_scalp_scanner.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "genome" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MIN_VOLUME_USD = 1_000_000
TOP_GAINERS = 30
TOP_LOSERS = 10
KLINE_LIMIT = 300

BINANCE_MIRRORS = [
    "https://api.binance.us",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
]

# Symbols already in our universe (skip these - already scanned)
EXISTING_UNIVERSE = {
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "AVAXUSDT", "LINKUSDT", "NEARUSDT", "SUIUSDT", "APTUSDT",
    "JUPUSDT", "INJUSDT", "FETUSDT", "TAOUSDT", "SEIUSDT",
    "DOGEUSDT", "ARBUSDT", "OPUSDT", "TIAUSDT", "FILUSDT", "LTCUSDT",
}


# ── Indicators ────────────────────────────────────────────────────────────

def sma(s, p):
    return s.rolling(p).mean()

def ema(s, p):
    return s.ewm(span=p, adjust=False).mean()

def rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)

def atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def macd(close, fast=12, slow=26, signal=9):
    ef = close.ewm(span=fast, adjust=False).mean()
    es = close.ewm(span=slow, adjust=False).mean()
    ml = ef - es
    sl = ml.ewm(span=signal, adjust=False).mean()
    return ml, sl, ml - sl


# ── Data ──────────────────────────────────────────────────────────────────

def fetch_24h_tickers():
    """Fetch all 24h tickers from Binance, return USDT pairs sorted by gain."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/ticker/24hr"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MomentumScalp/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            # Filter USDT, volume > threshold
            filtered = []
            for t in data:
                sym = t.get("symbol", "")
                if not sym.endswith("USDT"):
                    continue
                try:
                    vol_usd = float(t.get("quoteVolume", 0))
                    change = float(t.get("priceChangePercent", 0))
                    price = float(t.get("lastPrice", 0))
                except (ValueError, TypeError):
                    continue
                if vol_usd >= MIN_VOLUME_USD and price > 0:
                    filtered.append({
                        "symbol": sym,
                        "price": price,
                        "change_24h": change,
                        "volume_usd": vol_usd,
                    })

            filtered.sort(key=lambda x: x["change_24h"], reverse=True)
            return filtered
        except Exception as e:
            print(f"  Mirror {base} failed: {e}")
            continue
    return []


def fetch_klines(symbol, interval="1h", limit=KLINE_LIMIT):
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MomentumScalp/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read())
            df = pd.DataFrame(raw, columns=[
                "OpenTime", "Open", "High", "Low", "Close", "Volume",
                "CloseTime", "QuoteVol", "Trades", "TakerBuyBase", "TakerBuyQuote", "Ignore"
            ])
            for col in ("Open", "High", "Low", "Close", "Volume"):
                df[col] = df[col].astype(float)
            return df
        except Exception:
            continue
    return None


# ── Strategies ────────────────────────────────────────────────────────────

def _smart_round(v):
    if abs(v) >= 1000: return round(v, 2)
    if abs(v) >= 1: return round(v, 4)
    if abs(v) >= 0.01: return round(v, 6)
    return round(v, 8)


def strategy_genesis_momentum(df, symbol):
    """Genesis momentum blend — PASSED backtest (+20.90%)."""
    if len(df) < 60:
        return None
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    atr_val = float(atr(high, low, close, 14).iloc[-1])
    if atr_val <= 0 or np.isnan(atr_val):
        return None

    price = float(close.iloc[-1])
    rsi_val = float(rsi(close, 14).iloc[-1])
    adx_proxy = float(atr(high, low, close, 14).iloc[-1] / price * 100) if price > 0 else 0
    _, _, hist = macd(close)
    hist_now = float(hist.iloc[-1])

    # Supertrend proxy
    ema_10 = float(ema(close, 10).iloc[-1])
    st_bull = price > ema_10

    score = 0
    if st_bull: score += 2
    if adx_proxy > 1.5: score += 2
    if rsi_val < 55: score += 1
    if hist_now > 0: score += 1
    # Momentum bonus for gainers
    mom_5 = (price - float(close.iloc[-6])) / float(close.iloc[-6]) if len(close) > 6 else 0
    if mom_5 > 0.02: score += 2  # >2% gain in 5 bars = strong momentum
    if mom_5 > 0.05: score += 2  # >5% gain = very strong

    if score < 5:
        return None

    confidence = min(0.90, 0.50 + score * 0.05)
    tp = _smart_round(price + 2.0 * atr_val)
    sl = _smart_round(price - 1.5 * atr_val)
    rr = round((tp - price) / (price - sl), 2) if price > sl else 0

    return {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": _smart_round(price),
        "take_profit": tp,
        "stop_loss": sl,
        "risk_reward": rr,
        "confidence": round(confidence, 4),
        "strategy": "genesis_momentum_blend",
        "source": "Momentum_Scalp",
        "reason": f"Genesis score {score}/10: ST={'bull' if st_bull else 'bear'} ADX={adx_proxy:.0f} RSI={rsi_val:.0f} mom5={mom_5:.1%}",
    }


def strategy_ema_momentum(df, symbol):
    """EMA momentum with volume confirmation."""
    if len(df) < 60:
        return None
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    price = float(close.iloc[-1])
    atr_val = float(atr(high, low, close, 14).iloc[-1])
    if atr_val <= 0 or np.isnan(atr_val):
        return None

    e9 = float(ema(close, 9).iloc[-1])
    e21 = float(ema(close, 21).iloc[-1])
    e50 = float(ema(close, 50).iloc[-1])
    rsi_val = float(rsi(close, 14).iloc[-1])

    vol_now = float(volume.iloc[-1])
    vol_avg = float(volume.rolling(20).mean().iloc[-1])
    vol_ratio = vol_now / vol_avg if vol_avg > 0 else 0

    if not (e9 > e21 > e50):
        return None
    if rsi_val > 75 or rsi_val < 25:
        return None

    confidence = 0.55 + min(0.25, vol_ratio * 0.05)
    tp = _smart_round(price + 2.0 * atr_val)
    sl = _smart_round(price - 1.5 * atr_val)
    rr = round((tp - price) / (price - sl), 2) if price > sl else 0

    return {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": _smart_round(price),
        "take_profit": tp,
        "stop_loss": sl,
        "risk_reward": rr,
        "confidence": round(confidence, 4),
        "strategy": "ema_momentum_volume",
        "source": "Momentum_Scalp",
        "reason": f"EMA stack aligned (9>{e9:.4f} > 21>{e21:.4f} > 50) vol={vol_ratio:.1f}x RSI={rsi_val:.0f}",
    }


def strategy_momentum_pullback(df, symbol):
    """Momentum pullback: strong trend + temporary RSI dip = buy the dip."""
    if len(df) < 60:
        return None
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    price = float(close.iloc[-1])
    atr_val = float(atr(high, low, close, 14).iloc[-1])
    if atr_val <= 0 or np.isnan(atr_val):
        return None

    # Check for strong uptrend (price well above 50 EMA)
    e50 = float(ema(close, 50).iloc[-1])
    trend_strength = (price - e50) / e50 if e50 > 0 else 0

    if trend_strength < 0.03:  # Need at least 3% above 50 EMA
        return None

    # RSI pullback: was overbought, now pulling back to 40-55
    rsi_val = float(rsi(close, 14).iloc[-1])
    rsi_prev = float(rsi(close, 14).iloc[-3])  # 3 bars ago

    if not (rsi_prev > 60 and 35 < rsi_val < 55):
        return None

    # MACD still positive (trend intact)
    _, _, hist = macd(close)
    if float(hist.iloc[-1]) <= 0:
        return None

    confidence = 0.60 + min(0.20, trend_strength * 2)
    tp = _smart_round(price + 2.5 * atr_val)
    sl = _smart_round(price - 1.2 * atr_val)
    rr = round((tp - price) / (price - sl), 2) if price > sl else 0

    return {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": _smart_round(price),
        "take_profit": tp,
        "stop_loss": sl,
        "risk_reward": rr,
        "confidence": round(confidence, 4),
        "strategy": "momentum_pullback",
        "source": "Momentum_Scalp",
        "reason": f"Pullback in uptrend: {trend_strength:.1%} above EMA50, RSI dipped {rsi_prev:.0f}->{rsi_val:.0f}, MACD+",
    }


def strategy_bounce_play(df, symbol):
    """Oversold bounce on big losers: RSI extreme + volume capitulation."""
    if len(df) < 60:
        return None
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    price = float(close.iloc[-1])
    atr_val = float(atr(high, low, close, 14).iloc[-1])
    if atr_val <= 0 or np.isnan(atr_val):
        return None

    rsi_val = float(rsi(close, 14).iloc[-1])
    if rsi_val > 30:
        return None  # Need extreme oversold

    # Volume spike (capitulation)
    vol_now = float(volume.iloc[-1])
    vol_avg = float(volume.rolling(20).mean().iloc[-1])
    vol_ratio = vol_now / vol_avg if vol_avg > 0 else 0

    if vol_ratio < 1.5:
        return None  # Need volume capitulation

    # MACD turning up from negative
    _, _, hist = macd(close)
    h_now = float(hist.iloc[-1])
    h_prev = float(hist.iloc[-2]) if len(hist) > 1 else h_now
    macd_turning = h_now > h_prev  # Getting less negative

    if not macd_turning:
        return None

    confidence = 0.55 + min(0.25, (30 - rsi_val) / 30 * 0.2 + vol_ratio * 0.02)
    tp = _smart_round(price + 1.5 * atr_val)  # Tighter TP for bounce
    sl = _smart_round(price - 1.0 * atr_val)  # Tight SL
    rr = round((tp - price) / (price - sl), 2) if price > sl else 0

    return {
        "symbol": symbol,
        "direction": "LONG",
        "entry_price": _smart_round(price),
        "take_profit": tp,
        "stop_loss": sl,
        "risk_reward": rr,
        "confidence": round(confidence, 4),
        "strategy": "bounce_play",
        "source": "Momentum_Scalp",
        "reason": f"Oversold bounce: RSI={rsi_val:.0f}, vol={vol_ratio:.1f}x avg, MACD turning up",
    }


STRATEGIES = [
    ("genesis_momentum_blend", strategy_genesis_momentum),
    ("ema_momentum_volume", strategy_ema_momentum),
    ("momentum_pullback", strategy_momentum_pullback),
    ("bounce_play", strategy_bounce_play),
]


# ── Main Scanner ──────────────────────────────────────────────────────────

def main():
    now = datetime.now(timezone.utc)
    print("=" * 70)
    print("  MOMENTUM SCALP SCANNER -- Dynamic Symbol Universe Expansion")
    print(f"  {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # 1. Fetch 24h tickers
    print("\n  Fetching Binance 24h tickers...")
    tickers = fetch_24h_tickers()
    if not tickers:
        print("  FATAL: No ticker data. Aborting.")
        return

    print(f"  Found {len(tickers)} USDT pairs with >${MIN_VOLUME_USD/1e6:.0f}M volume")

    # 2. Separate gainers and losers
    gainers = [t for t in tickers[:TOP_GAINERS] if t["symbol"] not in EXISTING_UNIVERSE]
    losers = [t for t in tickers[-TOP_LOSERS:] if t["symbol"] not in EXISTING_UNIVERSE]

    # Also include existing universe gainers for comparison
    existing_in_top = [t for t in tickers[:TOP_GAINERS] if t["symbol"] in EXISTING_UNIVERSE]

    print(f"\n  TOP GAINERS (new symbols only, excluding existing universe):")
    print(f"  {'Symbol':18s} {'24h%':>8s} {'Volume':>14s} {'Price':>12s}")
    print(f"  {'-'*54}")
    for t in gainers[:15]:
        print(f"  {t['symbol']:18s} {t['change_24h']:>+7.2f}% ${t['volume_usd']/1e6:>10.1f}M {t['price']:>12.6f}")

    if existing_in_top:
        print(f"\n  (Already in universe, also gaining: {', '.join(t['symbol'] for t in existing_in_top)})")

    print(f"\n  TOP LOSERS (bounce candidates):")
    for t in losers[:5]:
        print(f"  {t['symbol']:18s} {t['change_24h']:>+7.2f}% ${t['volume_usd']/1e6:>10.1f}M")

    # 3. Fetch OHLCV and run strategies
    scan_symbols = gainers + losers
    print(f"\n  Scanning {len(scan_symbols)} momentum symbols...")

    all_picks = []
    symbol_data = {}

    for t in scan_symbols:
        sym = t["symbol"]
        df = fetch_klines(sym)
        if df is None or len(df) < 60:
            continue
        symbol_data[sym] = t
        time.sleep(0.15)

        for strat_name, strat_fn in STRATEGIES:
            pick = strat_fn(df, sym)
            if pick:
                pick["change_24h"] = t["change_24h"]
                pick["volume_usd"] = t["volume_usd"]
                pick["timestamp"] = now.isoformat()
                pick["status"] = "ACTIVE"
                pick["outcome"] = "PENDING"
                pick["pnl_pct"] = 0.0
                pick["scanner"] = "momentum_scalp"
                all_picks.append(pick)
                print(f"  [SIGNAL] {strat_name} -> {sym} {pick['direction']} "
                      f"@ {pick['entry_price']} conf={pick['confidence']:.2f} "
                      f"(24h: {t['change_24h']:+.1f}%)")

    # Sort by confidence
    all_picks.sort(key=lambda p: p["confidence"], reverse=True)

    print(f"\n{'='*70}")
    print(f"  TOTAL: {len(all_picks)} momentum picks from {len(scan_symbols)} new symbols")
    print(f"{'='*70}")

    # 4. Save output
    output = {
        "generated_at": now.isoformat(),
        "scanner": "momentum_scalp",
        "symbols_scanned": len(scan_symbols),
        "new_symbols_found": len(gainers),
        "bounce_candidates": len(losers),
        "picks_generated": len(all_picks),
        "top_gainers": gainers[:15],
        "top_losers": losers[:5],
        "picks": all_picks,
    }

    json_path = DATA_DIR / "momentum_scalp_picks.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved to {json_path}")

    # 5. Generate CHATWITHIT entry
    if all_picks:
        md_lines = [
            f"### Momentum Scalp Scanner ({now.strftime('%Y-%m-%d %H:%M UTC')})",
            "",
            f"**New symbols scanned:** {len(gainers)} gainers + {len(losers)} bounce candidates",
            f"**Picks generated:** {len(all_picks)}",
            "",
            "| # | Symbol | Dir | Entry | TP | SL | R:R | Conf | Strategy | 24h% | Reason |",
            "|---|--------|-----|-------|----|----|-----|------|----------|------|--------|",
        ]
        for i, p in enumerate(all_picks[:15], 1):
            md_lines.append(
                f"| {i} | {p['symbol']} | {p['direction']} | {p['entry_price']} | "
                f"{p['take_profit']} | {p['stop_loss']} | {p['risk_reward']} | "
                f"{p['confidence']:.0%} | `{p['strategy']}` | {p['change_24h']:+.1f}% | "
                f"{p['reason'][:60]} |"
            )
        md_text = "\n".join(md_lines)

        md_path = DATA_DIR / "momentum_scalp_chatwithit_entry.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_text)
        print(f"Saved CHATWITHIT entry to {md_path}")

    return all_picks


if __name__ == "__main__":
    main()
