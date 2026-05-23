"""
ALPHA ENGINE -- Dynamic Gainer Tracker
======================================
Reverse-engineering approach: find what's ACTUALLY winning on Binance,
then check if we're tracking it. If not, auto-generate pick candidates.

Workflow:
  1. Fetch ALL Binance USDT 24h tickers
  2. Filter top 30 gainers (quoteVolume > $500K)
  3. For each, fetch 1h klines -> compute entry, RSI, volume spike
  4. Compare against our tracked symbols in config.py
  5. Auto-generate picks for untracked gainers
  6. Save to data/dynamic_gainers.json

No external dependencies -- uses only urllib.request + stdlib.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
GAINERS_PATH = DATA_DIR / "dynamic_gainers.json"

# ---------------------------------------------------------------------------
# Binance API endpoints (with fallback mirrors per API failover rule)
# ---------------------------------------------------------------------------
BINANCE_ENDPOINTS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
TOP_N = 30                    # Number of top gainers to track
MIN_QUOTE_VOLUME = 500_000    # Minimum 24h quote volume in USDT
KLINE_INTERVAL = "1h"         # Kline interval for detailed analysis
KLINE_LIMIT = 24              # Hours of klines to fetch (for RSI + volume)
RSI_PERIOD = 14               # RSI lookback
DEFAULT_TP_PCT = 5.0          # Default take-profit %
DEFAULT_SL_PCT = 3.0          # Default stop-loss %
REQUEST_TIMEOUT = 15          # Seconds per HTTP request


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def _fetch_json(url: str, timeout: int = REQUEST_TIMEOUT) -> Any:
    """Fetch JSON from URL with timeout. Returns parsed dict/list or None."""
    req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
        print(f"  [WARN] Failed to fetch {url}: {e}")
        return None


def _binance_get(path: str, params: str = "") -> Any:
    """Try Binance API with failover across mirror endpoints."""
    full_path = f"{path}?{params}" if params else path
    for base in BINANCE_ENDPOINTS:
        result = _fetch_json(f"{base}{full_path}")
        if result is not None:
            return result
    print(f"  [ERROR] All Binance endpoints failed for {path}")
    return None


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------
def compute_rsi(closes: list[float], period: int = RSI_PERIOD) -> float | None:
    """Compute RSI from a list of close prices. Returns None if insufficient data."""
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Wilder smoothing for remaining periods
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_volume_spike(volumes: list[float]) -> float:
    """Ratio of latest volume to average of prior volumes. >2.0 = spike."""
    if len(volumes) < 2:
        return 1.0
    prior = volumes[:-1]
    avg_prior = sum(prior) / len(prior) if prior else 1.0
    if avg_prior == 0:
        return 1.0
    return volumes[-1] / avg_prior


# ---------------------------------------------------------------------------
# Core: get tracked Binance symbols from config
# ---------------------------------------------------------------------------
def get_tracked_binance_symbols() -> set[str]:
    """Return set of Binance symbol strings (e.g. 'BTCUSDT') from config.py."""
    tracked = set()
    try:
        # Import config -- works whether run as module or standalone
        sys.path.insert(0, str(ENGINE_DIR))
        from config import CRYPTO_SYMBOLS
        for _key, meta in CRYPTO_SYMBOLS.items():
            binance_sym = meta.get("binance", "")
            if binance_sym:
                tracked.add(binance_sym.upper())
    except ImportError:
        print("  [WARN] Could not import config.CRYPTO_SYMBOLS, all symbols treated as untracked")
    return tracked


# ---------------------------------------------------------------------------
# Step 1 & 2: Fetch all USDT tickers, find top gainers
# ---------------------------------------------------------------------------
def fetch_top_gainers() -> list[dict]:
    """
    Fetch 24h tickers from Binance, filter USDT pairs with volume > $500K,
    sort by priceChangePercent descending, return top N.
    """
    print("[1/4] Fetching all Binance 24hr tickers...")
    tickers = _binance_get("/api/v3/ticker/24hr")
    if not tickers:
        print("  [ERROR] Could not fetch tickers")
        return []

    usdt_gainers = []
    for t in tickers:
        symbol = t.get("symbol", "")
        # Only USDT pairs, skip leveraged/down tokens
        if not symbol.endswith("USDT"):
            continue
        if any(tag in symbol for tag in ["UP", "DOWN", "BEAR", "BULL"]):
            continue

        try:
            change_pct = float(t.get("priceChangePercent", 0))
            quote_vol = float(t.get("quoteVolume", 0))
            last_price = float(t.get("lastPrice", 0))
        except (ValueError, TypeError):
            continue

        if quote_vol < MIN_QUOTE_VOLUME:
            continue
        if change_pct <= 0:
            continue
        if last_price <= 0:
            continue

        usdt_gainers.append({
            "symbol": symbol,
            "price_change_pct": round(change_pct, 2),
            "last_price": last_price,
            "quote_volume_24h": round(quote_vol, 2),
            "weighted_avg_price": float(t.get("weightedAvgPrice", 0)),
            "high_24h": float(t.get("highPrice", 0)),
            "low_24h": float(t.get("lowPrice", 0)),
        })

    # Sort by price change descending
    usdt_gainers.sort(key=lambda x: x["price_change_pct"], reverse=True)
    top = usdt_gainers[:TOP_N]
    print(f"  Found {len(usdt_gainers)} USDT gainers (vol>${MIN_QUOTE_VOLUME/1000:.0f}K), keeping top {len(top)}")
    return top


# ---------------------------------------------------------------------------
# Step 3: Fetch 1h klines for detailed analysis
# ---------------------------------------------------------------------------
def enrich_with_klines(gainer: dict) -> dict:
    """
    Fetch 1h klines for a gainer symbol and compute:
    - entry_1h_ago: price 1 hour ago
    - current_price: latest close
    - gain_1h_pct: % change in last hour
    - rsi_1h: RSI on 1h closes
    - volume_spike: latest 1h volume / avg prior 1h volume
    """
    symbol = gainer["symbol"]
    klines = _binance_get(
        "/api/v3/klines",
        f"symbol={symbol}&interval={KLINE_INTERVAL}&limit={KLINE_LIMIT}"
    )

    if not klines or len(klines) < 2:
        gainer.update({
            "entry_1h_ago": None,
            "gain_1h_pct": None,
            "rsi_1h": None,
            "volume_spike": None,
        })
        return gainer

    # Kline format: [open_time, open, high, low, close, volume, close_time, ...]
    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    current_price = closes[-1]
    entry_1h_ago = closes[-2] if len(closes) >= 2 else current_price
    gain_1h = ((current_price - entry_1h_ago) / entry_1h_ago * 100) if entry_1h_ago > 0 else 0.0

    gainer.update({
        "entry_1h_ago": entry_1h_ago,
        "current_price": current_price,
        "gain_1h_pct": round(gain_1h, 3),
        "rsi_1h": round(compute_rsi(closes), 2) if compute_rsi(closes) is not None else None,
        "volume_spike": round(compute_volume_spike(volumes), 2),
    })
    return gainer


# ---------------------------------------------------------------------------
# Step 4 & 5: Compare against tracked, generate picks for untracked
# ---------------------------------------------------------------------------
def compute_confidence(gainer: dict) -> float:
    """
    Confidence score (0.0-1.0) based on volume spike + momentum + RSI position.
    Higher volume spike + strong momentum + RSI not overbought = higher confidence.
    """
    score = 0.62  # base raised from 0.50 -- gainers have real momentum evidence, need to clear 0.60 floor

    # Volume spike bonus (capped contribution: 0-0.2)
    vs = gainer.get("volume_spike") or 1.0
    if vs >= 3.0:
        score += 0.20
    elif vs >= 2.0:
        score += 0.15
    elif vs >= 1.5:
        score += 0.10

    # 24h momentum bonus (0-0.15)
    pct = gainer.get("price_change_pct", 0)
    if pct >= 15:
        score += 0.15
    elif pct >= 10:
        score += 0.12
    elif pct >= 5:
        score += 0.08

    # RSI penalty if overbought (reduce confidence for chasing)
    rsi = gainer.get("rsi_1h")
    if rsi is not None:
        if rsi > 80:
            score -= 0.15  # Very overbought, likely to pullback
        elif rsi > 70:
            score -= 0.08
        elif 40 <= rsi <= 60:
            score += 0.05  # Mid-range RSI = room to run

    # Quote volume bonus (liquidity)
    qv = gainer.get("quote_volume_24h", 0)
    if qv > 50_000_000:
        score += 0.10
    elif qv > 10_000_000:
        score += 0.05

    return round(max(0.1, min(1.0, score)), 2)


def generate_pick(gainer: dict) -> dict:
    """
    Generate a pick dict compatible with active_picks.json format.
    """
    symbol = gainer["symbol"]
    current = gainer.get("current_price") or gainer["last_price"]
    confidence = compute_confidence(gainer)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Adjust TP/SL based on RSI -- tighter targets if overbought
    rsi = gainer.get("rsi_1h")
    tp_pct = DEFAULT_TP_PCT
    sl_pct = DEFAULT_SL_PCT
    if rsi is not None and rsi > 70:
        tp_pct = 3.0  # Tighter TP when overbought
        sl_pct = 2.0  # Tighter SL too

    tp_price = round(current * (1 + tp_pct / 100), 8)
    sl_price = round(current * (1 - sl_pct / 100), 8)
    rr = round(tp_pct / sl_pct, 2) if sl_pct > 0 else 1.67

    reason_parts = [
        f"Dynamic gainer +{gainer['price_change_pct']}% 24h",
    ]
    if gainer.get("volume_spike"):
        reason_parts.append(f"vol spike {gainer['volume_spike']}x")
    if rsi is not None:
        reason_parts.append(f"RSI {rsi}")
    if gainer.get("gain_1h_pct") is not None:
        reason_parts.append(f"1h +{gainer['gain_1h_pct']}%")

    return {
        "id": f"gainer_tracker::{symbol}::{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "strategy": "gainer_tracker",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": "BUY",
        "direction": "LONG",
        "entry_price": current,
        "entry_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": now_iso,
        "take_profit": tp_price,
        "stop_loss": sl_price,
        "confidence": confidence,
        "ml_score": None,
        "risk_reward": rr,
        "reason": " | ".join(reason_parts),
        "rsi_at_entry": rsi,
        "volume_ratio": gainer.get("volume_spike"),
        "atr_at_entry": None,
        "status": "OPEN",
        "mfe": 0,
        "mae": 0,
        "high_water_mark": current,
        "current_price": current,
        "unrealized_pnl_pct": 0.0,
        "hold_days": 0,
        "created_at": now_iso,
        "confluence_score": 0.0,
        "confluence_reason": "auto-detected gainer",
        "confluence_strategies": [],
        "ensemble_only": False,
        "forward_validated": False,
        "forward_status": "new_gainer",
        "forward_trades": 0,
        "forward_wr": 0.0,
        "last_checked": now_iso,
        "elite_score": 0,
        "elite_breakdown": {},
        "elite_grade": "U",
        # Extra fields for gainer context
        "price_change_24h_pct": gainer["price_change_pct"],
        "quote_volume_24h": gainer["quote_volume_24h"],
        "gain_1h_pct": gainer.get("gain_1h_pct"),
        "source": "gainer_tracker",
    }


def classify_gainers(
    gainers: list[dict],
    tracked_symbols: set[str],
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Split gainers into:
      - tracked: already in our universe
      - untracked: NOT in our universe (candidates for picks)
      - picks: auto-generated pick dicts for untracked gainers
    """
    tracked_list = []
    untracked_list = []
    picks = []

    for g in gainers:
        sym = g["symbol"].upper()
        if sym in tracked_symbols:
            g["tracked"] = True
            tracked_list.append(g)
        else:
            g["tracked"] = False
            untracked_list.append(g)
            picks.append(generate_pick(g))

    return tracked_list, untracked_list, picks


# ---------------------------------------------------------------------------
# Step 6: Save results
# ---------------------------------------------------------------------------
def save_results(
    gainers: list[dict],
    tracked: list[dict],
    untracked: list[dict],
    picks: list[dict],
) -> None:
    """Save full results to dynamic_gainers.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_gainers_scanned": len(gainers),
        "tracked_count": len(tracked),
        "untracked_count": len(untracked),
        "new_picks_count": len(picks),
        "top_gainers": gainers,
        "tracked_gainers": [g["symbol"] for g in tracked],
        "untracked_gainers": [
            {"symbol": g["symbol"], "change_pct": g["price_change_pct"],
             "volume": g["quote_volume_24h"]}
            for g in untracked
        ],
        "auto_picks": picks,
    }

    with open(GAINERS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n[SAVED] {GAINERS_PATH}")


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
def run_gainer_tracker() -> list[dict]:
    """
    Full pipeline: fetch gainers -> enrich -> classify -> generate picks -> save.
    Returns list of pick dicts ready for injection into active_picks.json.
    """
    print("=" * 60)
    print("ALPHA ENGINE -- Dynamic Gainer Tracker")
    print("=" * 60)

    # Step 1-2: Fetch top gainers
    gainers = fetch_top_gainers()
    if not gainers:
        print("[DONE] No gainers found.")
        return []

    # Step 3: Enrich with 1h kline data
    print(f"\n[2/4] Enriching {len(gainers)} gainers with 1h klines...")
    for i, g in enumerate(gainers):
        enrich_with_klines(g)
        if (i + 1) % 10 == 0:
            print(f"  ...enriched {i + 1}/{len(gainers)}")
            time.sleep(0.5)  # Rate limit courtesy

    # Step 4: Get tracked symbols
    print("\n[3/4] Comparing against tracked universe...")
    tracked_symbols = get_tracked_binance_symbols()
    print(f"  Tracked symbols in config: {len(tracked_symbols)}")

    # Step 5: Classify and generate picks
    tracked, untracked, picks = classify_gainers(gainers, tracked_symbols)
    print(f"  Already tracked: {len(tracked)}")
    print(f"  NOT tracked (new candidates): {len(untracked)}")
    print(f"  Auto-generated picks: {len(picks)}")

    # Step 6: Save
    print("\n[4/4] Saving results...")
    save_results(gainers, tracked, untracked, picks)

    return picks


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    picks = run_gainer_tracker()

    if not picks:
        print("\nNo new picks generated.")
        sys.exit(0)

    print("\n" + "=" * 60)
    print(f"NEW PICK CANDIDATES ({len(picks)})")
    print("=" * 60)

    for p in picks:
        rsi_str = f"RSI={p['rsi_at_entry']}" if p['rsi_at_entry'] else "RSI=N/A"
        vol_str = f"VolSpike={p['volume_ratio']}x" if p['volume_ratio'] else "VolSpike=N/A"
        print(
            f"  {p['symbol']:>12s}  "
            f"entry={p['entry_price']:<12.6f}  "
            f"TP={p['take_profit']:<12.6f}  "
            f"SL={p['stop_loss']:<12.6f}  "
            f"conf={p['confidence']:.2f}  "
            f"{rsi_str}  {vol_str}  "
            f"+{p['price_change_24h_pct']}% 24h"
        )

    print(f"\nResults saved to: {GAINERS_PATH}")
    print("These picks can be injected into active_picks.json by the main scanner.")
