"""
Momentum Catcher -- Real-time crypto pump detector for Alpha Engine.

Detects momentum as it starts (not after) by scanning Binance Futures
for volume spikes + price acceleration, then scoring candidates.

Usage:
    python -m alpha_engine.momentum_catcher
"""

import json
import os
import time
import math
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    raise SystemExit("requests library required: pip install requests")

# Use shared api_failover for resilient multi-exchange data fetching
try:
    from alpha_engine import api_failover as _failover
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from alpha_engine import api_failover as _failover

# -- Constants ------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MOMENTUM_PICKS_PATH = os.path.join(DATA_DIR, "momentum_picks.json")
ACTIVE_PICKS_PATH = os.path.join(DATA_DIR, "active_picks.json")

MIN_DAILY_VOLUME_USD = 500_000  # $500K minimum daily volume
MAX_PICKS_PER_CYCLE = 10
MIN_SCORE = 60

TP_PCT = 0.05   # 5% take profit
SL_PCT = 0.03   # 3% stop loss

KLINE_DELAY = 0.1  # 100ms between kline fetches

# Death hours (UTC 13-16) -- low liquidity, more fakeouts
DEATH_HOURS = {13, 14, 15, 16}


def fetch_btc_4h_regime():
    """Fetch BTC 4h regime via api_failover (Binance->Bybit->KuCoin->CoinGecko->CryptoCompare).

    Returns (regime, change_pct):
      "bearish" if < -1%, "bullish" if > +1%, else "neutral".
    """
    klines = _failover.fetch_klines("BTCUSDT", interval="1h", limit=5)
    if klines and len(klines) >= 4:
        try:
            open_4h = float(klines[0][1])
            close_now = float(klines[-1][4])
            if open_4h > 0:
                change = (close_now - open_4h) / open_4h * 100
                if change < -1.0:
                    return "bearish", round(change, 2)
                elif change > 1.0:
                    return "bullish", round(change, 2)
                return "neutral", round(change, 2)
        except (ValueError, IndexError, TypeError):
            pass
    return "neutral", 0.0


# -- API helpers (using shared api_failover) ------------------------------------

def fetch_futures_tickers():
    """Fetch 24hr ticker for ALL USDT pairs via api_failover.

    Uses multi-exchange failover: Binance mirrors -> Bybit -> CoinGecko.
    """
    data = _failover.fetch_ticker_24h("")  # empty = all tickers
    if data and isinstance(data, list):
        return [t for t in data if t.get("symbol", "").endswith("USDT")]
    print("  WARNING: All ticker sources failed")
    return []


def fetch_klines(symbol, interval="1h", limit=12):
    """Fetch klines via api_failover (Binance->Bybit->KuCoin->CoinGecko->CryptoCompare)."""
    result = _failover.fetch_klines(symbol, interval=interval, limit=limit)
    return result if result else []


# -- Technical indicators -------------------------------------------------------

def compute_rsi(closes, period=14):
    """Compute RSI from a list of close prices."""
    if len(closes) < period + 1:
        # Not enough data -- use what we have
        period = max(len(closes) - 1, 1)
    if period < 1:
        return 50.0  # neutral

    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    if not gains:
        return 50.0

    # Use last `period` values
    recent_gains = gains[-period:]
    recent_losses = losses[-period:]

    avg_gain = sum(recent_gains) / period
    avg_loss = sum(recent_losses) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_bollinger_position(closes, period=20):
    """Where is current price relative to Bollinger Bands? Returns 0-1."""
    if len(closes) < period:
        return 0.5  # neutral
    window = closes[-period:]
    mean = sum(window) / len(window)
    variance = sum((x - mean) ** 2 for x in window) / len(window)
    std = math.sqrt(variance) if variance > 0 else 0.0001
    upper = mean + 2 * std
    lower = mean - 2 * std
    band_width = upper - lower
    if band_width == 0:
        return 0.5
    return max(0, min(1, (closes[-1] - lower) / band_width))


# -- Phase 1: Scan -------------------------------------------------------------

def scan_for_pumps(tickers):
    """
    Filter tickers to find symbols showing pump characteristics:
    - Volume > $500K/day
    - Price change > 2% (significant move)
    - Higher price change = higher volume_ratio proxy (since 24h vol == wavg*vol)

    Volume ratio is computed in Phase 2 from klines (recent vs prior bars).
    Phase 1 uses price change magnitude + absolute volume as the initial filter.
    """
    pumping = []

    # Compute median volume across all qualifying pairs for relative comparison
    volumes = []
    for t in tickers:
        try:
            qv = float(t.get("quoteVolume", 0))
            if qv >= MIN_DAILY_VOLUME_USD:
                volumes.append(qv)
        except (ValueError, TypeError):
            pass
    volumes.sort()
    median_vol = volumes[len(volumes) // 2] if volumes else MIN_DAILY_VOLUME_USD

    for t in tickers:
        symbol = t["symbol"]
        try:
            quote_volume = float(t.get("quoteVolume", 0))
            price_change_pct = float(t.get("priceChangePercent", 0))
            last_price = float(t.get("lastPrice", 0))
        except (ValueError, TypeError):
            continue

        # Volume filter
        if quote_volume < MIN_DAILY_VOLUME_USD:
            continue

        # Volume ratio: this pair's volume vs median volume across all pairs
        # High relative volume = unusual interest
        volume_ratio = quote_volume / median_vol if median_vol > 0 else 1.0

        # Pump detection: significant price move + above-median volume
        is_pumping = price_change_pct > 2.0 and volume_ratio > 1.0

        if is_pumping:
            pumping.append({
                "symbol": symbol,
                "last_price": last_price,
                "price_change_pct": price_change_pct,
                "quote_volume": quote_volume,
                "volume_ratio": round(volume_ratio, 2),
            })

    # Sort by volume ratio descending -- strongest pumps first
    pumping.sort(key=lambda x: x["volume_ratio"], reverse=True)
    return pumping


# -- Phase 2: Detect Momentum --------------------------------------------------

def analyze_momentum(candidate):
    """
    Fetch 1h klines and compute momentum indicators for a candidate.
    Returns enriched candidate dict or None if data unavailable.
    """
    symbol = candidate["symbol"]
    klines = fetch_klines(symbol, interval="1h", limit=14)
    time.sleep(KLINE_DELAY)

    if not klines or len(klines) < 5:
        return None

    # Parse klines: [open_time, open, high, low, close, volume, ...]
    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    opens = [float(k[1]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]

    # RSI
    rsi = compute_rsi(closes)

    # Volume acceleration: last 3 bars vs previous 3 bars
    if len(volumes) >= 6:
        recent_vol = sum(volumes[-3:]) / 3
        prior_vol = sum(volumes[-6:-3]) / 3
        vol_acceleration = recent_vol / prior_vol if prior_vol > 0 else 1.0
    else:
        vol_acceleration = 1.0

    # Trend strength: how many of last 5 candles are green
    last_5_green = 0
    for i in range(max(0, len(closes) - 5), len(closes)):
        if closes[i] > opens[i]:
            last_5_green += 1

    # Pullback entry: is current price within 30% of the move range from the low?
    recent_high = max(highs[-5:]) if len(highs) >= 5 else max(highs)
    recent_low = min(lows[-5:]) if len(lows) >= 5 else min(lows)
    move_range = recent_high - recent_low
    if move_range > 0:
        position_in_range = (closes[-1] - recent_low) / move_range
        pullback_entry = position_in_range <= 0.3
    else:
        pullback_entry = False
        position_in_range = 0.5

    # Bollinger position
    bb_position = compute_bollinger_position(closes)

    # 1h price change (most recent candle)
    price_change_1h = 0
    if len(closes) >= 2:
        price_change_1h = ((closes[-1] - closes[-2]) / closes[-2]) * 100

    candidate.update({
        "rsi": round(rsi, 2),
        "volume_acceleration": round(vol_acceleration, 2),
        "trend_strength": last_5_green,
        "pullback_entry": pullback_entry,
        "position_in_range": round(position_in_range, 3),
        "bb_position": round(bb_position, 3),
        "price_change_1h": round(price_change_1h, 3),
        "closes": closes,
    })
    return candidate


# -- Phase 3: Score & Generate Picks -------------------------------------------

def score_candidate(c):
    """Score a momentum candidate 0-100."""
    score = 0

    # Volume ratio
    vr = c.get("volume_ratio", 0)
    if vr > 3:
        score += 30
    elif vr > 2:
        score += 20

    # Price rising (1h)
    if c.get("price_change_1h", 0) > 0.5:
        score += 15

    # RSI sweet spot (momentum but not overbought)
    rsi = c.get("rsi", 50)
    if 40 <= rsi <= 65:
        score += 15

    # Trend strength
    if c.get("trend_strength", 0) >= 3:
        score += 10

    # Volume acceleration
    if c.get("volume_acceleration", 0) > 1.5:
        score += 10

    # Pullback entry
    if c.get("pullback_entry", False):
        score += 10

    # Not in death hours
    utc_hour = datetime.now(timezone.utc).hour
    if utc_hour not in DEATH_HOURS:
        score += 10

    return score


def generate_pick(candidate, score, regime="neutral", btc_4h_change=0.0):
    """Create a pick dict matching active_picks.json format."""
    symbol = candidate["symbol"]
    entry = candidate["last_price"]
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d%H%M")
    pick_id = f"momentum_{symbol}_{ts}"

    return {
        "id": pick_id,
        "strategy": "momentum_catcher",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY",
        "direction": "LONG",
        "entry_price": entry,
        "entry_date": now.strftime("%Y-%m-%d"),
        "take_profit": round(entry * (1 + TP_PCT), 6),
        "stop_loss": round(entry * (1 - SL_PCT), 6),
        "confidence": round(score / 100, 2),
        "ml_score": None,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "high_water_mark": None,
        "status": "OPEN",
        "regime_at_entry": "momentum",
        "atr_at_entry": None,
        "rsi_at_entry": candidate.get("rsi"),
        "volume_ratio": candidate.get("volume_ratio"),
        "hold_days": None,
        "allocation": 1500.0,
        "gross_tp": round(entry * (1 + TP_PCT), 6),
        "net_tp": round(entry * (1 + TP_PCT - 0.001), 6),
        "transaction_cost_pct": 0.001,
        "cost_model": 0.001,
        "position_sizing": "fixed",
        "risk_per_trade_pct": 0.03,
        "regime_compatible": True,
        "regime_adx": None,
        "regime_volatility": None,
        "regime_trend_direction": "bullish",
        "regime_warning": None,
        "hmm_regime": None,
        "hmm_confidence": None,
        "hmm_signal": None,
        "hmm_leverage": None,
        "source_system": "alpha_engine",
        "momentum_score": score,
        "volume_acceleration": candidate.get("volume_acceleration"),
        "trend_strength": candidate.get("trend_strength"),
        "price_change_pct_24h": candidate.get("price_change_pct"),
        "price_change_pct_1h": candidate.get("price_change_1h"),
        "created_at": now.isoformat(),
        "regime_at_signal": regime,
        "btc_4h_change_at_signal": btc_4h_change,
    }


# -- Duplicate detection -------------------------------------------------------

def load_existing_symbols():
    """Load symbols already in active_picks.json to avoid duplicates."""
    existing = set()
    try:
        with open(ACTIVE_PICKS_PATH, "r") as f:
            picks = json.load(f)
        for p in picks:
            if p.get("status") == "OPEN":
                key = f"{p.get('symbol')}_{p.get('signal_type', 'BUY')}"
                existing.add(key)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Also check momentum_picks.json for recent picks
    try:
        with open(MOMENTUM_PICKS_PATH, "r") as f:
            mpicks = json.load(f)
        for p in mpicks:
            if p.get("status") == "OPEN":
                key = f"{p.get('symbol')}_{p.get('signal_type', 'BUY')}"
                existing.add(key)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return existing


# -- Main pipeline -------------------------------------------------------------

def run_momentum_scan():
    """Execute the full 3-phase momentum catcher pipeline."""
    print("=" * 60)
    print("  MOMENTUM CATCHER - Real-time Pump Detector")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    # Phase 1: Scan
    print("\n[Phase 1] Fetching all Binance Futures USDT tickers...")
    tickers = fetch_futures_tickers()
    if not tickers:
        print("  ERROR: No ticker data available from any API endpoint")
        return []

    print(f"  Found {len(tickers)} USDT pairs")
    pumping = scan_for_pumps(tickers)
    print(f"  {len(pumping)} pairs showing pump characteristics")

    if not pumping:
        print("\n  No pumps detected this cycle.")
        _save_picks([])
        return []

    # Phase 2: Analyze momentum (limit to top 30 candidates to save API calls)
    candidates = pumping[:30]
    print(f"\n[Phase 2] Analyzing momentum for top {len(candidates)} candidates...")

    analyzed = []
    for c in candidates:
        result = analyze_momentum(c)
        if result:
            analyzed.append(result)
            print(f"  {c['symbol']:15s} RSI={result['rsi']:5.1f}  "
                  f"VolAccel={result['volume_acceleration']:.2f}  "
                  f"Trend={result['trend_strength']}/5  "
                  f"1h={result['price_change_1h']:+.2f}%")

    if not analyzed:
        print("  No candidates passed momentum analysis")
        _save_picks([])
        return []

    # Phase 3: Score and generate picks
    print(f"\n[Phase 3] Scoring {len(analyzed)} candidates (min score: {MIN_SCORE})...")

    existing_symbols = load_existing_symbols()
    scored = []
    for c in analyzed:
        s = score_candidate(c)
        c["score"] = s
        dup_key = f"{c['symbol']}_BUY"
        is_dup = dup_key in existing_symbols

        status = ""
        if s < MIN_SCORE:
            status = "SKIP (low score)"
        elif is_dup:
            status = "SKIP (duplicate)"
        else:
            status = "PICK"

        print(f"  {c['symbol']:15s} score={s:3d}  {status}")

        if s >= MIN_SCORE and not is_dup:
            scored.append(c)

    # Take top picks by score
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:MAX_PICKS_PER_CYCLE]

    # === REGIME GATE: Check BTC 4h trend before generating picks ===
    btc_regime, btc_4h_change = fetch_btc_4h_regime()
    if btc_regime == "bearish":
        print(f"\n  [REGIME GATE] Bearish regime detected (BTC 4h: {btc_4h_change:+.2f}%) -- skipping all BUY picks")
        # Momentum catcher is BUY-only; in bearish regime, skip entirely
        picks = []
        _save_picks(picks)
        return picks
    elif btc_regime != "neutral":
        print(f"\n  [REGIME] BTC 4h regime: {btc_regime} ({btc_4h_change:+.2f}%)")

    picks = [generate_pick(c, c["score"], regime=btc_regime, btc_4h_change=btc_4h_change) for c in top]

    # Save
    _save_picks(picks)

    print(f"\n{'=' * 60}")
    print(f"  Scanned {len(tickers)} pairs, {len(pumping)} pumping, "
          f"{len(picks)} picks generated")
    print(f"{'=' * 60}")

    for p in picks:
        print(f"  >> {p['symbol']:15s} entry={p['entry_price']:.6f}  "
              f"TP={p['take_profit']:.6f}  SL={p['stop_loss']:.6f}  "
              f"conf={p['confidence']:.0%}")

    return picks


def _save_picks(picks):
    """Save momentum picks to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MOMENTUM_PICKS_PATH, "w") as f:
        json.dump(picks, f, indent=2, default=str)
    print(f"\n  Saved {len(picks)} picks to {MOMENTUM_PICKS_PATH}")


# -- CLI entry point -----------------------------------------------------------

def main():
    picks = run_momentum_scan()
    return picks


if __name__ == "__main__":
    main()
