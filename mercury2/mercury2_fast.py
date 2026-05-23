#!/usr/bin/env python3
"""
Mercury2 Fast — High Frequency Crypto Scanner (Real Data)

Uses live Binance klines via public API (no auth needed).
Runs every 4 hours via mercury2-fast-scan.yml.
Generates short-hold (2-8h) crypto signals with tight TP/SL.

Strategies:
  1. RSI Oversold Bounce — RSI<30 with price above EMA-50
  2. EMA Crossover Momentum — EMA-9 crosses above EMA-21
  3. Bollinger Squeeze Breakout — BB width contracts then price breaks upper band
  4. Volume Spike Reversal — 2x avg volume + RSI<40 (accumulation signal)
  5. MACD Histogram Reversal — Histogram crosses from negative to positive
"""

import json
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Configuration ──
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "NEARUSDT", "SUIUSDT", "ARBUSDT", "RENDERUSDT",
    "MATICUSDT", "AAVEUSDT", "OPUSDT", "FILUSDT", "APTUSDT",
]

# API endpoints — try multiple to handle geo-blocks
BINANCE_ENDPOINTS = [
    "https://api.binance.us",    # US endpoint (works from GitHub Actions)
    "https://api.binance.com",   # Global (may be geo-blocked)
    "https://api1.binance.com",  # Mirror 1
]

KLINE_INTERVAL = "1h"
KLINE_LIMIT = 100  # 100 hours of data

# Signal thresholds
MIN_SCORE = 55       # Minimum combined score to generate a signal
MAX_ACTIVE = 999     # TESTING SPRINT: was 10, uncapped
HOLD_HOURS = [4, 6, 8, 12]  # Possible hold durations


# ── Data Fetching ──

def fetch_klines(symbol: str) -> list[dict] | None:
    """Fetch 1h klines from Binance (tries multiple endpoints)."""
    for base_url in BINANCE_ENDPOINTS:
        try:
            url = f"{base_url}/api/v3/klines"
            resp = requests.get(url, params={
                "symbol": symbol,
                "interval": KLINE_INTERVAL,
                "limit": KLINE_LIMIT,
            }, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) >= 20:
                    return [
                        {
                            "timestamp": int(row[0]),
                            "open": float(row[1]),
                            "high": float(row[2]),
                            "low": float(row[3]),
                            "close": float(row[4]),
                            "volume": float(row[5]),
                        }
                        for row in data
                    ]
        except Exception:
            continue
    return None


def fetch_fear_greed() -> int | None:
    """Fetch crypto Fear & Greed index with retry."""
    import time as _time
    for attempt in range(3):
        try:
            resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            if resp.status_code == 200:
                return int(resp.json()["data"][0]["value"])
        except Exception:
            pass
        if attempt < 2:
            _time.sleep(2 * (attempt + 1))
    return None


# ── Technical Indicators ──

def compute_ema(prices: list[float], period: int) -> list[float]:
    """Exponential Moving Average."""
    if len(prices) < period:
        return prices[:]
    k = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for p in prices[period:]:
        ema.append(p * k + ema[-1] * (1 - k))
    return ema


def compute_rsi(prices: list[float], period: int = 14) -> float:
    """Wilder RSI."""
    if len(prices) < period + 1:
        return 50.0
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(c, 0) for c in changes]
    losses = [max(-c, 0) for c in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_atr(candles: list[dict], period: int = 14) -> float:
    """Average True Range."""
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < period:
        return sum(trs) / len(trs) if trs else 0.0
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def compute_bb(prices: list[float], period: int = 20, std_mult: float = 2.0):
    """Bollinger Bands — returns (upper, middle, lower, width%)."""
    if len(prices) < period:
        return None
    window = prices[-period:]
    mean = sum(window) / period
    variance = sum((p - mean) ** 2 for p in window) / period
    std = variance ** 0.5
    upper = mean + std_mult * std
    lower = mean - std_mult * std
    width_pct = (upper - lower) / mean if mean > 0 else 0
    return upper, mean, lower, width_pct


def compute_macd(prices: list[float]):
    """MACD line, signal line, histogram."""
    if len(prices) < 26:
        return None
    ema12 = compute_ema(prices, 12)
    ema26 = compute_ema(prices, 26)
    # Align lengths
    min_len = min(len(ema12), len(ema26))
    macd_line = [ema12[-(min_len - i)] - ema26[-(min_len - i)] for i in range(min_len)]
    signal = compute_ema(macd_line, 9) if len(macd_line) >= 9 else macd_line
    min_len2 = min(len(macd_line), len(signal))
    hist = [macd_line[-min_len2 + i] - signal[-min_len2 + i] for i in range(min_len2)]
    return macd_line[-1] if macd_line else 0, signal[-1] if signal else 0, hist[-1] if hist else 0


# ── Strategy Signals ──

def score_rsi_bounce(closes: list[float], rsi: float, ema50: list[float]) -> tuple[int, str]:
    """Strategy 1: RSI Oversold Bounce — RSI<30 + price above EMA-50."""
    if not ema50:
        return 0, ""
    if rsi < 30 and closes[-1] > ema50[-1]:
        return 30, "RSI oversold bounce (RSI<30, above EMA50)"
    if rsi < 35 and closes[-1] > ema50[-1]:
        return 15, "RSI near oversold (RSI<35, above EMA50)"
    return 0, ""


def score_ema_crossover(ema9: list[float], ema21: list[float]) -> tuple[int, str]:
    """Strategy 2: EMA-9/21 bullish crossover."""
    if len(ema9) < 2 or len(ema21) < 2:
        return 0, ""
    # Current: 9 above 21, Previous: 9 below 21
    if ema9[-1] > ema21[-1] and ema9[-2] <= ema21[-2]:
        return 25, "EMA 9/21 bullish crossover"
    # Already above and widening
    if ema9[-1] > ema21[-1] and (ema9[-1] - ema21[-1]) > (ema9[-2] - ema21[-2]):
        return 15, "EMA 9/21 momentum widening"
    return 0, ""


def score_bb_squeeze(closes: list[float], bb_data, prev_bb_width: float) -> tuple[int, str]:
    """Strategy 3: Bollinger Squeeze Breakout."""
    if bb_data is None:
        return 0, ""
    upper, middle, lower, width = bb_data
    if prev_bb_width > 0 and width > prev_bb_width * 1.3 and closes[-1] > upper:
        return 25, "BB squeeze breakout (width expanding, price above upper band)"
    if closes[-1] > upper:
        return 10, "Price above upper Bollinger Band"
    return 0, ""


def score_volume_spike(candles: list[dict], rsi: float) -> tuple[int, str]:
    """Strategy 4: Volume Spike + Oversold = Accumulation."""
    if len(candles) < 20:
        return 0, ""
    recent_vol = candles[-1]["volume"]
    avg_vol = sum(c["volume"] for c in candles[-20:]) / 20
    if avg_vol == 0:
        return 0, ""
    vol_ratio = recent_vol / avg_vol
    if vol_ratio > 2.0 and rsi < 40:
        return 25, f"Volume spike ({vol_ratio:.1f}x avg) + RSI<40 accumulation"
    if vol_ratio > 1.5 and rsi < 35:
        return 15, f"Volume surge ({vol_ratio:.1f}x avg) + oversold"
    return 0, ""


def score_macd_reversal(macd_data) -> tuple[int, str]:
    """Strategy 5: MACD Histogram Reversal."""
    if macd_data is None:
        return 0, ""
    macd_line, signal, hist = macd_data
    if hist > 0 and macd_line > signal:
        return 20, "MACD bullish (histogram positive, MACD above signal)"
    return 0, ""


# ── Pick Resolution ──

def resolve_existing_picks(picks: list[dict], prices: dict[str, float], now: datetime) -> list[dict]:
    """Check TP/SL/expiry on existing picks, resolve those that hit."""
    active = []
    for pick in picks:
        if pick["status"] != "OPEN":
            active.append(pick)
            continue
        symbol = pick["ticker"]
        current = prices.get(symbol)
        if current is None:
            active.append(pick)
            continue

        entry = pick["entry_price"]
        direction = pick.get("action", "BUY")
        tp = pick.get("tp_price", 0)
        sl = pick.get("sl_price", 0)

        # Check expiry
        try:
            expiry = datetime.fromisoformat(pick["expiry_date"])
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if now >= expiry:
                pnl = ((current - entry) / entry * 100) if direction == "BUY" else ((entry - current) / entry * 100)
                pick["status"] = "TIME_EXIT"
                pick["resolved_at"] = now.isoformat()
                pick["resolved_price"] = current
                pick["pnl_pct"] = round(pnl, 4)
                active.append(pick)
                print(f"  TIME_EXIT {symbol}: pnl={pnl:+.2f}%")
                continue
        except (ValueError, KeyError):
            pass

        # Check TP/SL
        if direction == "BUY":
            if tp and current >= tp:
                pnl = (tp - entry) / entry * 100
                pick["status"] = "WON"
                pick["resolved_at"] = now.isoformat()
                pick["resolved_price"] = current
                pick["pnl_pct"] = round(pnl, 4)
                print(f"  TP HIT {symbol}: pnl={pnl:+.2f}%")
            elif sl and current <= sl:
                pnl = (sl - entry) / entry * 100
                pick["status"] = "LOST"
                pick["resolved_at"] = now.isoformat()
                pick["resolved_price"] = current
                pick["pnl_pct"] = round(pnl, 4)
                print(f"  SL HIT {symbol}: pnl={pnl:+.2f}%")

        active.append(pick)
    return active


# ── Feedback Loop Integration ──

def _sync_closed_to_feedback_loop(closed_picks: list[dict], now: datetime):
    """Merge mercury2_fast closed picks into data/closed_picks.json for the shared feedback loop.

    The feedback loop at ml_battleground/shared/feedback_loop.py reads from
    mercury2/data/closed_picks.json. This function merges fast-scanner closed
    picks into that file (deduped by pick ID) so the feedback loop can evaluate
    Mercury2's aggregate performance.
    """
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shared_path = data_dir / "closed_picks.json"

    # Load existing shared closed picks
    existing = []
    if shared_path.exists():
        try:
            with open(shared_path) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = []

    # Build set of existing IDs for dedup
    existing_ids = set()
    for p in existing:
        pid = p.get("id") or p.get("pick_id") or f"{p.get('symbol')}_{p.get('timestamp')}"
        existing_ids.add(pid)

    # Normalize and append new closed picks
    added = 0
    for pick in closed_picks:
        pid = pick.get("id", f"{pick.get('ticker', '')}_{pick.get('timestamp', '')}")
        if pid in existing_ids:
            continue
        # Normalize fields for feedback loop compatibility
        normalized = {
            "symbol": pick.get("ticker") or pick.get("symbol"),
            "direction": pick.get("direction", "LONG"),
            "entry_price": pick.get("entry_price"),
            "exit_price": pick.get("resolved_price"),
            "timestamp": pick.get("timestamp"),
            "exit_time": pick.get("resolved_at"),
            "status": pick.get("status"),
            "pnl_pct": pick.get("pnl_pct", 0) or 0,
            "realized_pnl_pct": pick.get("pnl_pct", 0) or 0,
            "system": "mercury2_fast",
            "strategy": pick.get("strategy", ""),
            "confidence": pick.get("confidence", 0),
            "id": pid,
        }
        existing.append(normalized)
        existing_ids.add(pid)
        added += 1

    if added > 0:
        with open(shared_path, "w") as f:
            json.dump(existing, f, indent=2, default=str)
        print(f"  Synced {added} closed picks to data/closed_picks.json for feedback loop")

    # Run feedback loop check
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from ml_battleground.shared.feedback_loop import check_and_trigger
        check_and_trigger()
        print("  Feedback loop check completed")
    except Exception as e:
        print(f"  Feedback loop check failed (non-fatal): {e}")


# ── Main Scanner ──

def run_mercury2_fast():
    """Run fast Mercury2 crypto scanner with real Binance data."""
    now = datetime.now(timezone.utc)
    print(f"Mercury2 Fast — {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Symbols: {len(SYMBOLS)} | Interval: {KLINE_INTERVAL} | Max picks: {MAX_ACTIVE}")
    print()

    # Fetch Fear & Greed
    fng = fetch_fear_greed()
    print(f"Fear & Greed Index: {fng or 'N/A'}")

    # Fetch klines for all symbols
    print("Fetching live klines from Binance...")
    symbol_data: dict[str, list[dict]] = {}
    current_prices: dict[str, float] = {}
    for symbol in SYMBOLS:
        candles = fetch_klines(symbol)
        if candles and len(candles) >= 50:
            symbol_data[symbol] = candles
            current_prices[symbol] = candles[-1]["close"]
            print(f"  {symbol}: {candles[-1]['close']:.4f} ({len(candles)} candles)")
        else:
            print(f"  {symbol}: SKIP (insufficient data)")
        time.sleep(0.1)  # Rate limit

    if not symbol_data:
        print("ERROR: No data fetched from any endpoint. Exiting.")
        return

    print(f"\nFetched {len(symbol_data)}/{len(SYMBOLS)} symbols")

    # Load existing picks
    picks_file = Path(__file__).parent / "mercury2_fast_picks.json"
    existing_picks = []
    if picks_file.exists():
        try:
            with open(picks_file) as f:
                data = json.load(f)
                existing_picks = data.get("picks", [])
        except (json.JSONDecodeError, KeyError):
            existing_picks = []

    # Resolve existing picks (TP/SL/expiry)
    print("\nResolving existing picks...")
    all_picks = resolve_existing_picks(existing_picks, current_prices, now)
    active_count = sum(1 for p in all_picks if p["status"] == "OPEN")
    print(f"  Active: {active_count} | Resolved: {len(existing_picks) - active_count}")

    # Skip new signal generation if at capacity
    if active_count >= MAX_ACTIVE:
        print(f"\nAt capacity ({active_count}/{MAX_ACTIVE}), skipping new signals.")
    else:
        # Generate new signals
        print("\nScanning for new signals...")
        candidates = []

        for symbol, candles in symbol_data.items():
            # Skip if already have an active pick for this symbol
            if any(p["ticker"] == symbol and p["status"] == "OPEN" for p in all_picks):
                continue

            closes = [c["close"] for c in candles]
            ema9 = compute_ema(closes, 9)
            ema21 = compute_ema(closes, 21)
            ema50 = compute_ema(closes, 50)
            rsi = compute_rsi(closes)
            atr = compute_atr(candles)
            bb_now = compute_bb(closes)
            bb_prev = compute_bb(closes[:-1]) if len(closes) > 20 else None
            prev_bb_width = bb_prev[3] if bb_prev else 0
            macd_data = compute_macd(closes)

            # Score all strategies
            total_score = 0
            reasons = []

            for scorer_fn, args in [
                (score_rsi_bounce, (closes, rsi, ema50)),
                (score_ema_crossover, (ema9, ema21)),
                (score_bb_squeeze, (closes, bb_now, prev_bb_width)),
                (score_volume_spike, (candles, rsi)),
                (score_macd_reversal, (macd_data,)),
            ]:
                score, reason = scorer_fn(*args)
                total_score += score
                if reason:
                    reasons.append(reason)

            # Fear & Greed bonus (contrarian: extreme fear = higher score)
            if fng is not None and fng < 25:
                total_score += 10
                reasons.append(f"Extreme fear (F&G={fng})")

            if total_score >= MIN_SCORE:
                candidates.append((total_score, symbol, rsi, atr, reasons))

        # Sort by score, take top candidates
        candidates.sort(reverse=True)
        slots = MAX_ACTIVE - active_count
        new_picks = []

        for score, symbol, rsi, atr, reasons in candidates[:slots]:
            price = current_prices[symbol]
            # ATR-based TP/SL (tight for fast variant)
            if atr > 0 and price > 0:
                tp_pct = min(0.04, (atr * 1.5) / price)  # 1.5 ATR or 4% cap
                sl_pct = min(0.025, (atr * 1.0) / price)  # 1.0 ATR or 2.5% cap
            else:
                tp_pct = 0.03
                sl_pct = 0.02

            # Direction: default LONG, SHORT if RSI > 70
            direction = "SELL" if rsi > 70 else "BUY"
            if direction == "SELL":
                tp_price = round(price * (1 - tp_pct), 8)
                sl_price = round(price * (1 + sl_pct), 8)
            else:
                tp_price = round(price * (1 + tp_pct), 8)
                sl_price = round(price * (1 - sl_pct), 8)

            hold_h = HOLD_HOURS[min(len(HOLD_HOURS) - 1, max(0, score // 25 - 2))]
            expiry = now + timedelta(hours=hold_h)

            pick = {
                "id": f"m2fast_{symbol}_{now.strftime('%Y%m%d_%H%M')}",
                "system": "mercury2_fast",
                "algorithm": "Mercury2 Fast",
                "strategy": ", ".join(reasons[:2]),
                "asset_class": "CRYPTO",
                "ticker": symbol,
                "symbol": symbol,
                "action": direction,
                "direction": "LONG" if direction == "BUY" else "SHORT",
                "entry_price": price,
                "tp_price": tp_price,
                "sl_price": sl_price,
                "tp_pct": round(tp_pct * 100, 2),
                "sl_pct": round(sl_pct * 100, 2),
                "confidence": round(min(score / 100, 0.99), 4),
                "score": score,
                "reasons": reasons,
                "rsi": round(rsi, 2),
                "fear_greed": fng,
                "timestamp": now.isoformat(),
                "generated_at": now.isoformat(),
                "expiry_date": expiry.isoformat(),
                "hold_hours_max": hold_h,
                "status": "OPEN",
                "resolved_at": None,
                "resolved_price": None,
                "resolved_reason": None,
                "pnl_pct": None,
            }
            new_picks.append(pick)
            print(f"  NEW: {direction} {symbol} @ {price:.4f} | score={score} | TP={tp_pct*100:.1f}% SL={sl_pct*100:.1f}% | {', '.join(reasons[:2])}")

        all_picks.extend(new_picks)
        print(f"\n  Generated {len(new_picks)} new signals")

    # Separate active/closed for output
    active = [p for p in all_picks if p["status"] == "OPEN"]
    closed = [p for p in all_picks if p["status"] != "OPEN"]

    # Compute stats
    won = sum(1 for p in closed if p["status"] == "WON")
    lost = sum(1 for p in closed if p["status"] == "LOST")
    total_pnl = sum(float(p.get("pnl_pct", 0) or 0) or 0 for p in closed)
    wr = (won / (won + lost) * 100) if (won + lost) > 0 else 0

    output = {
        "generated_at": now.isoformat(),
        "system": "mercury2_fast",
        "version": "2.0.0",
        "asset_class": "CRYPTO",
        "fear_greed": fng,
        "symbols_scanned": len(symbol_data),
        "stats": {
            "active": len(active),
            "closed": len(closed),
            "won": won,
            "lost": lost,
            "win_rate": round(wr, 1),
            "total_pnl_pct": round(total_pnl, 2),
        },
        "picks": all_picks,
    }

    picks_file.parent.mkdir(parents=True, exist_ok=True)
    with open(picks_file, "w") as f:
        json.dump(output, f, indent=2)

    # ── Sync closed picks to data/closed_picks.json for feedback loop ──
    _sync_closed_to_feedback_loop(closed, now)

    print(f"\nSummary: {len(active)} active | {len(closed)} closed | WR={wr:.0f}% | PnL={total_pnl:+.2f}%")
    print(f"Saved to: {picks_file}")


if __name__ == "__main__":
    run_mercury2_fast()
