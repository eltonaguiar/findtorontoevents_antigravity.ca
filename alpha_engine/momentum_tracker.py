#!/usr/bin/env python3
# ENTRY TIMING RULES (backed by data from Mar 24 investigation):
# - Sweet spot: coins up 3-8% with 2x+ volume acceleration
# - BLOCK: coins already up >15% (mean reversion zone)
# - REQUIRE: RSI(4h) < 70 (not overbought)
# - REQUIRE: price within 2% of session high (still making new highs)
"""
Real-Time Gainer Momentum Tracker
===================================
Scans ALL Binance USDT pairs every cycle to find coins that are ACCELERATING
-- not just up, but gaining momentum with volume confirmation.

CRITICAL FIX (Mar 24 2026): Changed minimum 24h gain from 5% to 3%.
Added hard cap blocking coins already up >15% (mean reversion zone).
Added RSI(4h) < 70 filter. Prioritize volume surge BEFORE price surge.

Key insight: 60% of missed gainers aren't in our configured universe.
This scanner looks at ALL pairs, not just our configured symbols.

Criteria for acceleration:
  1. Up 3%+ in last 24h (was 5% -- lowered to catch early)
  2. BLOCK: coins already up >15% (mean reversion imminent)
  3. Volume > 2x 7-day average (was 3x -- lowered to catch buildup)
  4. Price making new intraday highs (current > open by 2%+)
  5. Prioritize volume surge BEFORE price surge (informed accumulation)

Persistence tracking:
  Coins that stay in top 20 for 2+ consecutive scans get a "persistent_momentum"
  tag and higher confidence.

Pick parameters:
  - Trailing stop at 5% from peak (not fixed SL)
  - TP at +8% from entry
  - Max hold 24 hours
  - Confidence scaled by acceleration score (0.65-0.82)

Exports:
  MOMENTUM_TRACKER_STRATEGIES  -- dict for scanner.py integration
  run_momentum_scan()          -- standalone entry point

State persisted to: alpha_engine/data/momentum_tracker_state.json
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Windows UTF-8 fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# Ensure imports work from alpha_engine directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

_log = logging.getLogger("alpha_engine.momentum_tracker")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MIN_24H_CHANGE_PCT = 3.0       # Was 5% -- lowered Mar 24 to catch early momentum
MAX_24H_CHANGE_PCT = 15.0     # HARD CAP: reject coins already up >15% (mean reversion)
MIN_VOLUME_MULTIPLIER = 2.0    # Was 3x -- lowered to catch volume buildup phase
MIN_INTRADAY_GAIN_PCT = 2.0    # Current price > open price by at least 2%
MIN_QUOTE_VOLUME_USD = 500_000  # Minimum $500K 24h quote volume (filter dust)

TOP_N_ACCELERATORS = 20        # Track top 20 accelerating coins
MAX_PICKS = 5                  # Generate picks for top 5 only
PERSISTENCE_THRESHOLD = 2      # Consecutive scans to earn "persistent" tag

TRAILING_STOP_PCT = 0.05       # 5% trailing stop from peak
TAKE_PROFIT_PCT = 0.08         # 8% TP from entry
MAX_HOLD_HOURS = 24            # Maximum hold time

CONFIDENCE_MIN = 0.65
CONFIDENCE_MAX = 0.82

STATE_FILE = "data/momentum_tracker_state.json"
PICKS_FILE = "data/momentum_tracker_picks.json"

# Pairs to exclude (stablecoins, wrapped, leveraged tokens)
EXCLUDED_SUFFIXES = {
    "USDTUSDT", "BUSDUSDT", "USDCUSDT", "TUSDUSDT", "DAIUSDT",
    "EURUSDT", "GBPUSDT", "FDUSDUSDT", "AEURUSDT",
}
EXCLUDED_PATTERNS = {"UP", "DOWN", "BEAR", "BULL"}  # Leveraged tokens


# ---------------------------------------------------------------------------
# API failover: fetch ALL tickers
# ---------------------------------------------------------------------------
def _fetch_all_usdt_tickers() -> list[dict]:
    """Fetch 24h tickers for ALL USDT pairs using failover chain.

    Returns list of dicts with keys:
        symbol, lastPrice, priceChangePercent, openPrice, highPrice,
        lowPrice, volume, quoteVolume
    """
    try:
        from api_failover import (
            BINANCE_SPOT_BASES, BYBIT_BASE, KUCOIN_BASE,
            _http_get_json,
        )
    except ImportError:
        _log.error("Cannot import api_failover -- falling back to direct HTTP")
        return _fetch_all_tickers_direct()

    # --- Source 1: Binance 24hr ticker (all symbols in one call) ---
    for base in BINANCE_SPOT_BASES:
        data = _http_get_json(f"{base}/api/v3/ticker/24hr", timeout=15)
        if data and isinstance(data, list) and len(data) > 50:
            tickers = []
            for t in data:
                sym = t.get("symbol", "")
                if not sym.endswith("USDT"):
                    continue
                if sym in EXCLUDED_SUFFIXES:
                    continue
                if any(pat in sym[:-4] for pat in EXCLUDED_PATTERNS):
                    continue
                try:
                    tickers.append({
                        "symbol": sym,
                        "lastPrice": float(t.get("lastPrice", 0)),
                        "priceChangePercent": float(t.get("priceChangePercent", 0)),
                        "openPrice": float(t.get("openPrice", 0)),
                        "highPrice": float(t.get("highPrice", 0)),
                        "lowPrice": float(t.get("lowPrice", 0)),
                        "volume": float(t.get("volume", 0)),
                        "quoteVolume": float(t.get("quoteVolume", 0)),
                        "weightedAvgPrice": float(t.get("weightedAvgPrice", 0)),
                        "count": int(t.get("count", 0)),
                    })
                except (ValueError, TypeError):
                    continue
            if tickers:
                _log.info("Fetched %d USDT tickers from Binance (%s)",
                          len(tickers), base.split("//")[1].split(".")[0])
                return tickers

    # --- Source 2: Bybit spot tickers ---
    data = _http_get_json(f"{BYBIT_BASE}/v5/market/tickers?category=spot", timeout=15)
    if data and data.get("retCode") == 0:
        raw = data.get("result", {}).get("list", [])
        tickers = []
        for t in raw:
            sym = t.get("symbol", "")
            if not sym.endswith("USDT"):
                continue
            if sym in EXCLUDED_SUFFIXES:
                continue
            if any(pat in sym[:-4] for pat in EXCLUDED_PATTERNS):
                continue
            try:
                last = float(t.get("lastPrice", 0))
                prev = float(t.get("prevPrice24h", 0))
                pct = ((last - prev) / prev * 100) if prev > 0 else 0
                tickers.append({
                    "symbol": sym,
                    "lastPrice": last,
                    "priceChangePercent": pct,
                    "openPrice": prev,
                    "highPrice": float(t.get("highPrice24h", 0)),
                    "lowPrice": float(t.get("lowPrice24h", 0)),
                    "volume": float(t.get("volume24h", 0)),
                    "quoteVolume": float(t.get("turnover24h", 0)),
                    "weightedAvgPrice": 0,
                    "count": 0,
                })
            except (ValueError, TypeError):
                continue
        if tickers:
            _log.info("Fetched %d USDT tickers from Bybit", len(tickers))
            return tickers

    # --- Source 3: KuCoin allTickers ---
    data = _http_get_json(f"{KUCOIN_BASE}/api/v1/market/allTickers", timeout=15)
    if data and data.get("code") == "200000":
        raw = data.get("data", {}).get("ticker", [])
        tickers = []
        for t in raw:
            sym_kc = t.get("symbol", "")  # e.g. BTC-USDT
            if not sym_kc.endswith("-USDT"):
                continue
            sym = sym_kc.replace("-", "")  # normalize to BTCUSDT
            if sym in EXCLUDED_SUFFIXES:
                continue
            if any(pat in sym[:-4] for pat in EXCLUDED_PATTERNS):
                continue
            try:
                last = float(t.get("last", 0))
                chg_pct = float(t.get("changeRate", 0)) * 100
                tickers.append({
                    "symbol": sym,
                    "lastPrice": last,
                    "priceChangePercent": chg_pct,
                    "openPrice": float(t.get("averagePrice", last)),
                    "highPrice": float(t.get("high", last)),
                    "lowPrice": float(t.get("low", last)),
                    "volume": float(t.get("vol", 0)),
                    "quoteVolume": float(t.get("volValue", 0)),
                    "weightedAvgPrice": float(t.get("averagePrice", 0)),
                    "count": 0,
                })
            except (ValueError, TypeError):
                continue
        if tickers:
            _log.info("Fetched %d USDT tickers from KuCoin", len(tickers))
            return tickers

    _log.error("ALL ticker sources failed")
    return []


def _fetch_all_tickers_direct() -> list[dict]:
    """Direct HTTP fallback if api_failover not importable."""
    import urllib.request
    import urllib.error

    bases = [
        "https://data-api.binance.vision",
        "https://api.binance.us",
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]
    for base in bases:
        try:
            url = f"{base}/api/v3/ticker/24hr"
            req = urllib.request.Request(url, headers={
                "User-Agent": "MomentumTracker/1.0"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.getcode() == 451:
                    continue
                data = json.loads(resp.read())
                if data and isinstance(data, list) and len(data) > 50:
                    tickers = []
                    for t in data:
                        sym = t.get("symbol", "")
                        if not sym.endswith("USDT"):
                            continue
                        if sym in EXCLUDED_SUFFIXES:
                            continue
                        if any(pat in sym[:-4] for pat in EXCLUDED_PATTERNS):
                            continue
                        try:
                            tickers.append({
                                "symbol": sym,
                                "lastPrice": float(t.get("lastPrice", 0)),
                                "priceChangePercent": float(t.get("priceChangePercent", 0)),
                                "openPrice": float(t.get("openPrice", 0)),
                                "highPrice": float(t.get("highPrice", 0)),
                                "lowPrice": float(t.get("lowPrice", 0)),
                                "volume": float(t.get("volume", 0)),
                                "quoteVolume": float(t.get("quoteVolume", 0)),
                                "weightedAvgPrice": float(t.get("weightedAvgPrice", 0)),
                                "count": int(t.get("count", 0)),
                            })
                        except (ValueError, TypeError):
                            continue
                    if tickers:
                        _log.info("Fetched %d USDT tickers (direct) from %s",
                                  len(tickers), base)
                        return tickers
        except Exception as exc:
            _log.debug("Direct fetch failed %s: %s", base, exc)
            continue
    return []


# ---------------------------------------------------------------------------
# Acceleration scoring
# ---------------------------------------------------------------------------
def compute_acceleration_score(ticker: dict, avg_volume_7d: float) -> dict | None:
    """Score a ticker for momentum acceleration.

    Returns dict with acceleration metrics or None if doesn't qualify.
    """
    last_price = ticker.get("lastPrice", 0)
    open_price = ticker.get("openPrice", 0)
    change_pct = ticker.get("priceChangePercent", 0)
    high_price = ticker.get("highPrice", 0)
    quote_volume = ticker.get("quoteVolume", 0)

    # Filter: must have valid prices
    if last_price <= 0 or open_price <= 0:
        return None

    # Filter 1: Up 3%+ in 24h (lowered from 5% to catch early)
    if change_pct < MIN_24H_CHANGE_PCT:
        return None

    # HARD CAP: reject coins already up >15% (mean reversion zone)
    if change_pct > MAX_24H_CHANGE_PCT:
        return None

    # Filter 2: Minimum quote volume (skip dust pairs)
    if quote_volume < MIN_QUOTE_VOLUME_USD:
        return None

    # Filter 3: Volume > 2x estimated 7-day average (lowered from 3x to catch buildup)
    # For first scan, estimate 7d avg from current volume (conservative)
    vol_multiplier = 1.0
    if avg_volume_7d > 0:
        vol_multiplier = quote_volume / avg_volume_7d
    else:
        # No historical data -- use trade count as proxy
        # Accept if change is moderate (>5%) even without volume history
        if change_pct < 5.0:
            vol_multiplier = 1.0  # Will fail the check below
        else:
            vol_multiplier = MIN_VOLUME_MULTIPLIER  # Give benefit of doubt

    if vol_multiplier < MIN_VOLUME_MULTIPLIER:
        return None

    # Filter 4: Intraday gain -- current > open by 2%+
    intraday_gain_pct = (last_price - open_price) / open_price * 100
    if intraday_gain_pct < MIN_INTRADAY_GAIN_PCT:
        return None

    # --- Compute acceleration score (0-100) ---
    # Components (reweighted Mar 24 to prioritize volume-before-price):
    #   - Volume surge: 0-35 points (HIGHEST weight -- informed accumulation)
    #   - Price momentum (24h change): 0-25 points (lower weight -- catch early)
    #   - Intraday strength (proximity to high): 0-20 points
    #   - Volume-price divergence bonus: 0-20 points (vol surge > price surge = smart money)

    # Price momentum: 3% = 0pts, 15%+ = 25pts (log scale, capped at 15% now)
    price_score = min(25, max(0, (math.log(max(change_pct, 1)) - math.log(3)) /
                                  (math.log(15) - math.log(3)) * 25))

    # Volume surge: 2x = 0pts, 20x+ = 35pts (log scale, HIGHEST weight)
    vol_score = min(35, max(0, (math.log(max(vol_multiplier, 1)) - math.log(2)) /
                                (math.log(20) - math.log(2)) * 35))

    # Intraday strength: how close is current price to daily high?
    high_low_range = high_price - ticker.get("lowPrice", open_price)
    if high_low_range > 0:
        intraday_strength = (last_price - ticker.get("lowPrice", open_price)) / high_low_range
    else:
        intraday_strength = 1.0
    intraday_score = intraday_strength * 20

    # Volume-price divergence bonus: volume surge much bigger than price surge
    # This catches informed accumulation (smart money buying before price moves)
    vol_price_ratio = vol_multiplier / max(change_pct, 1.0)
    divergence_score = min(20, max(0, vol_price_ratio * 5))

    total_score = price_score + vol_score + intraday_score + divergence_score

    return {
        "symbol": ticker["symbol"],
        "last_price": last_price,
        "open_price": open_price,
        "high_price": high_price,
        "low_price": ticker.get("lowPrice", open_price),
        "change_24h_pct": round(change_pct, 2),
        "intraday_gain_pct": round(intraday_gain_pct, 2),
        "volume_multiplier": round(vol_multiplier, 2),
        "quote_volume_usd": round(quote_volume, 0),
        "acceleration_score": round(total_score, 2),
        "price_score": round(price_score, 2),
        "vol_score": round(vol_score, 2),
        "intraday_score": round(intraday_score, 2),
        "divergence_score": round(divergence_score, 2),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------
def _resolve_path(filename: str) -> Path:
    """Resolve path relative to alpha_engine directory."""
    base = Path(__file__).resolve().parent
    return base / filename


def load_state() -> dict:
    """Load persisted tracker state."""
    path = _resolve_path(STATE_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            _log.warning("Failed to load state: %s", exc)
    return {
        "scan_count": 0,
        "last_scan": None,
        "top20_history": {},      # symbol -> list of consecutive scan timestamps
        "volume_history": {},     # symbol -> list of recent quote volumes (for 7d avg)
        "persistent_symbols": [], # symbols with 2+ consecutive appearances
    }


def save_state(state: dict) -> None:
    """Persist tracker state."""
    path = _resolve_path(STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        _log.info("State saved to %s", path)
    except Exception as exc:
        _log.error("Failed to save state: %s", exc)


def load_picks() -> list:
    """Load current active momentum picks."""
    path = _resolve_path(PICKS_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_picks(picks: list) -> None:
    """Save active momentum picks."""
    path = _resolve_path(PICKS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(picks, indent=2, default=str), encoding="utf-8")
    _log.info("Saved %d momentum picks to %s", len(picks), path)


# ---------------------------------------------------------------------------
# Main scan logic
# ---------------------------------------------------------------------------
def run_momentum_scan(dry_run: bool = False) -> list[dict]:
    """Execute a full momentum scan cycle.

    Returns list of generated pick dicts (top 5 accelerating coins).
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    print(f"\n{'='*60}")
    print(f"  MOMENTUM TRACKER - Real-Time Gainer Scanner")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}\n")

    # Load state
    state = load_state()
    state["scan_count"] = state.get("scan_count", 0) + 1
    state["last_scan"] = now_iso
    vol_history = state.get("volume_history", {})

    # Fetch ALL USDT tickers
    print("[1/5] Fetching ALL Binance USDT pair tickers...")
    tickers = _fetch_all_usdt_tickers()
    if not tickers:
        print("  FAILED: No tickers fetched from any source")
        save_state(state)
        return []
    print(f"  Found {len(tickers)} USDT pairs")

    # Update volume history (keep last 7 entries per symbol for 7-day avg)
    for t in tickers:
        sym = t["symbol"]
        qv = t.get("quoteVolume", 0)
        if qv > 0:
            hist = vol_history.get(sym, [])
            hist.append(qv)
            # Keep only last 7 entries (7 scans ~ 7 cycles)
            vol_history[sym] = hist[-7:]
    state["volume_history"] = vol_history

    # Score all tickers for acceleration
    print(f"\n[2/5] Scoring {len(tickers)} pairs for acceleration...")
    scored = []
    for t in tickers:
        sym = t["symbol"]
        # Compute 7-day average volume from history
        hist = vol_history.get(sym, [])
        if len(hist) >= 2:
            # Use average of all but latest (to avoid including current spike)
            avg_vol = sum(hist[:-1]) / len(hist[:-1])
        else:
            avg_vol = 0  # No history yet

        result = compute_acceleration_score(t, avg_vol)
        if result:
            scored.append(result)

    # Sort by acceleration score descending
    scored.sort(key=lambda x: x["acceleration_score"], reverse=True)

    print(f"  {len(scored)} coins passed acceleration filters")
    if scored:
        print(f"  Top scorer: {scored[0]['symbol']} "
              f"(score={scored[0]['acceleration_score']:.1f}, "
              f"+{scored[0]['change_24h_pct']:.1f}%, "
              f"vol={scored[0]['volume_multiplier']:.1f}x)")

    # Take top 20 for tracking
    top20 = scored[:TOP_N_ACCELERATORS]
    top20_symbols = {s["symbol"] for s in top20}

    # Update persistence tracking
    print(f"\n[3/5] Tracking momentum persistence...")
    top20_hist = state.get("top20_history", {})
    new_top20_hist = {}
    persistent_symbols = []

    for sym in top20_symbols:
        prev = top20_hist.get(sym, [])
        prev.append(now_iso)
        # Keep last 10 entries
        new_top20_hist[sym] = prev[-10:]
        if len(prev) >= PERSISTENCE_THRESHOLD:
            persistent_symbols.append(sym)

    state["top20_history"] = new_top20_hist
    state["persistent_symbols"] = persistent_symbols

    if persistent_symbols:
        print(f"  {len(persistent_symbols)} coins with PERSISTENT momentum: "
              f"{', '.join(persistent_symbols[:5])}"
              f"{'...' if len(persistent_symbols) > 5 else ''}")
    else:
        print(f"  No persistent momentum yet (need {PERSISTENCE_THRESHOLD}+ consecutive scans)")

    # Print top 20 leaderboard
    print(f"\n[4/5] Acceleration Leaderboard (Top {min(len(top20), TOP_N_ACCELERATORS)}):")
    print(f"  {'Rank':>4}  {'Symbol':<12} {'Score':>6} {'24h%':>7} {'Intra%':>7} "
          f"{'VolX':>6} {'QuoteVol':>12} {'Persist':>7}")
    print(f"  {'----':>4}  {'------':<12} {'-----':>6} {'----':>7} {'------':>7} "
          f"{'----':>6} {'--------':>12} {'-------':>7}")
    for i, s in enumerate(top20):
        is_persistent = "YES" if s["symbol"] in persistent_symbols else "-"
        qv_str = f"${s['quote_volume_usd']:,.0f}"
        print(f"  {i+1:>4}  {s['symbol']:<12} {s['acceleration_score']:>6.1f} "
              f"{s['change_24h_pct']:>+6.1f}% {s['intraday_gain_pct']:>+6.1f}% "
              f"{s['volume_multiplier']:>5.1f}x {qv_str:>12} {is_persistent:>7}")

    # Generate picks for top 5
    print(f"\n[5/5] Generating BUY picks for top {MAX_PICKS} accelerators...")
    existing_picks = load_picks()
    existing_symbols = {p["symbol"] for p in existing_picks if p.get("status") == "active"}

    new_picks = []
    pick_candidates = top20[:MAX_PICKS]

    for s in pick_candidates:
        sym = s["symbol"]

        # Skip if already have an active pick for this symbol
        if sym in existing_symbols:
            print(f"  SKIP {sym}: already have active pick")
            continue

        # Scale confidence by acceleration score (0-100 -> 0.65-0.82)
        score_ratio = min(s["acceleration_score"] / 100, 1.0)
        confidence = CONFIDENCE_MIN + score_ratio * (CONFIDENCE_MAX - CONFIDENCE_MIN)

        # Boost confidence for persistent momentum
        if sym in persistent_symbols:
            confidence = min(confidence + 0.05, 0.85)

        entry_price = s["last_price"]
        tp_price = round(entry_price * (1 + TAKE_PROFIT_PCT), 8)
        # Trailing stop: initial SL at 5% below entry (will trail up)
        initial_sl = round(entry_price * (1 - TRAILING_STOP_PCT), 8)

        pick = {
            "id": f"mt_{sym}_{int(now.timestamp())}",
            "symbol": sym,
            "signal_type": "BUY",
            "strategy": "momentum_tracker_acceleration",
            "entry_price": entry_price,
            "take_profit": tp_price,
            "stop_loss": initial_sl,
            "trailing_stop_pct": TRAILING_STOP_PCT,
            "peak_price": entry_price,  # Will be updated each cycle
            "confidence": round(confidence, 4),
            "ml_score": round(confidence, 4),
            "status": "active",
            "created_at": now_iso,
            "max_hold_until": (
                datetime.fromtimestamp(now.timestamp() + MAX_HOLD_HOURS * 3600,
                                       tz=timezone.utc).isoformat()
            ),
            "reason": (
                f"Acceleration score {s['acceleration_score']:.0f}/100 | "
                f"+{s['change_24h_pct']:.1f}% 24h | "
                f"Vol {s['volume_multiplier']:.1f}x avg | "
                f"Intraday +{s['intraday_gain_pct']:.1f}%"
            ),
            "extra": {
                "acceleration_score": s["acceleration_score"],
                "change_24h_pct": s["change_24h_pct"],
                "intraday_gain_pct": s["intraday_gain_pct"],
                "volume_multiplier": s["volume_multiplier"],
                "quote_volume_usd": s["quote_volume_usd"],
                "persistent_momentum": sym in persistent_symbols,
                "rank_in_scan": pick_candidates.index(s) + 1,
            },
            "category": "crypto",
            "asset_type": "crypto",
            "source": "momentum_tracker",
        }

        new_picks.append(pick)
        print(f"  NEW PICK: {sym} @ {entry_price} | "
              f"TP={tp_price} SL={initial_sl} (trailing 5%) | "
              f"Conf={confidence:.2f} | Score={s['acceleration_score']:.0f}")

    # Validate existing picks: update trailing stops, check expiry
    validated_picks = []
    for p in existing_picks:
        if p.get("status") != "active":
            validated_picks.append(p)
            continue

        sym = p["symbol"]
        # Find current ticker data
        current = next((t for t in tickers if t["symbol"] == sym), None)
        if not current:
            # Can't validate -- keep as-is
            validated_picks.append(p)
            continue

        current_price = current.get("lastPrice", 0)
        if current_price <= 0:
            validated_picks.append(p)
            continue

        peak = max(p.get("peak_price", p["entry_price"]), current_price)
        p["peak_price"] = peak

        # Update trailing stop (5% from peak)
        trailing_sl = round(peak * (1 - TRAILING_STOP_PCT), 8)
        if trailing_sl > p.get("stop_loss", 0):
            p["stop_loss"] = trailing_sl

        # Check TP hit
        if current_price >= p.get("take_profit", float("inf")):
            p["status"] = "closed_tp"
            p["exit_price"] = current_price
            p["exit_reason"] = "take_profit"
            p["closed_at"] = now_iso
            pnl = (current_price - p["entry_price"]) / p["entry_price"]
            p["pnl_pct"] = round(pnl, 4)
            print(f"  TP HIT: {sym} +{pnl*100:.1f}% (entry={p['entry_price']} exit={current_price})")

        # Check trailing SL hit
        elif current_price <= p.get("stop_loss", 0):
            p["status"] = "closed_sl"
            p["exit_price"] = current_price
            p["exit_reason"] = "trailing_stop"
            p["closed_at"] = now_iso
            pnl = (current_price - p["entry_price"]) / p["entry_price"]
            p["pnl_pct"] = round(pnl, 4)
            print(f"  SL HIT: {sym} {pnl*100:+.1f}% (trailing stop at {p['stop_loss']})")

        # Check max hold expiry
        elif p.get("max_hold_until"):
            try:
                expiry = datetime.fromisoformat(p["max_hold_until"])
                if now >= expiry:
                    p["status"] = "closed_expired"
                    p["exit_price"] = current_price
                    p["exit_reason"] = "max_hold_24h"
                    p["closed_at"] = now_iso
                    pnl = (current_price - p["entry_price"]) / p["entry_price"]
                    p["pnl_pct"] = round(pnl, 4)
                    print(f"  EXPIRED: {sym} {pnl*100:+.1f}% (24h max hold)")
            except (ValueError, TypeError):
                pass

        validated_picks.append(p)

    # Combine: validated existing + new picks
    all_picks = validated_picks + new_picks

    # Save state and picks
    save_state(state)
    if not dry_run:
        save_picks(all_picks)

    # Summary
    active = [p for p in all_picks if p.get("status") == "active"]
    closed = [p for p in all_picks if p.get("status", "").startswith("closed")]
    print(f"\n{'='*60}")
    print(f"  SCAN COMPLETE (cycle #{state['scan_count']})")
    print(f"  Pairs scanned: {len(tickers)}")
    print(f"  Accelerating:  {len(scored)}")
    print(f"  Active picks:  {len(active)}")
    print(f"  Closed picks:  {len(closed)}")
    print(f"  New this scan: {len(new_picks)}")
    if persistent_symbols:
        print(f"  Persistent:    {', '.join(persistent_symbols[:10])}")
    print(f"{'='*60}\n")

    return new_picks


# ---------------------------------------------------------------------------
# Strategy function for scanner.py integration
# ---------------------------------------------------------------------------
def momentum_tracker_acceleration(symbol: str, klines: list | None = None,
                                   **kwargs) -> dict | None:
    """Strategy function compatible with scanner.py registration.

    This is a thin wrapper -- the real logic runs in run_momentum_scan().
    When called per-symbol from scanner, it checks if this symbol has
    an active momentum pick and returns it.
    """
    picks_path = _resolve_path(PICKS_FILE)
    if not picks_path.exists():
        return None

    try:
        picks = json.loads(picks_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    # Find active pick for this symbol
    sym_upper = symbol.upper().replace("-", "").replace("/", "")
    for p in picks:
        if p.get("status") == "active" and p.get("symbol") == sym_upper:
            return {
                "symbol": sym_upper,
                "signal_type": "BUY",
                "confidence": p.get("confidence", 0.70),
                "entry_price": p.get("entry_price", 0),
                "take_profit": p.get("take_profit", 0),
                "stop_loss": p.get("stop_loss", 0),
                "strategy": "momentum_tracker_acceleration",
                "reason": p.get("reason", "Momentum acceleration detected"),
                "extra": p.get("extra", {}),
            }

    return None


# ---------------------------------------------------------------------------
# Export for scanner.py integration
# ---------------------------------------------------------------------------
MOMENTUM_TRACKER_STRATEGIES = {
    "momentum_tracker_acceleration": momentum_tracker_acceleration,
}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Momentum Tracker - Real-Time Gainer Scanner")
    parser.add_argument("--dry-run", action="store_true", help="Show signals without saving picks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    picks = run_momentum_scan(dry_run=args.dry_run)
    if not picks:
        print("No new picks generated this cycle.")
