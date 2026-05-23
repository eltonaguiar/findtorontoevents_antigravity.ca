"""
Gainer Promoter -- Auto-convert top gainers to picks
====================================================
Gap #1: The system SAW DCR, PIPPIN, KITE, MORPHO as top gainers
in Feb 2026 but didn't convert them to picks. This module bridges
that gap by auto-promoting qualifying gainers.

Conservative parameters:
- TP: +8% (momentum continuation, not moonshot)
- SL: -4% (tight stop, 2:1 R:R)
- Max 5 picks per cycle
- Skip if already tracked

Uses the same Binance API failover pattern as gainer_tracker.py.
"""

from __future__ import annotations

import json
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

# ---------------------------------------------------------------------------
# Binance API endpoints (failover mirrors per API failover rule)
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
MIN_GAIN_PCT = 15.0          # Minimum 24h gain to qualify
MIN_VOLUME_USD = 2_000_000   # Minimum 24h quote volume in USDT
ILLIQUID_THRESHOLD = 1_000_000  # Skip symbols below this volume
TP_PCT = 8.0                 # Take-profit: +8% from entry
SL_PCT = 4.0                 # Stop-loss: -4% from entry
MAX_PROMOTES = 5             # Maximum picks per cycle
REQUEST_TIMEOUT = 15         # Seconds per HTTP request


# ---------------------------------------------------------------------------
# HTTP helpers (reuse pattern from gainer_tracker.py)
# ---------------------------------------------------------------------------
def _fetch_json(url: str, timeout: int = REQUEST_TIMEOUT) -> Any:
    """Fetch JSON from URL with timeout."""
    req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
        print(f"  [gainer_promoter][WARN] Failed to fetch {url}: {e}")
        return None


def _binance_get(path: str, params: str = "") -> Any:
    """Try Binance API with failover across mirror endpoints."""
    full_path = f"{path}?{params}" if params else path
    for base in BINANCE_ENDPOINTS:
        result = _fetch_json(f"{base}{full_path}")
        if result is not None:
            return result
    print(f"  [gainer_promoter][ERROR] All Binance endpoints failed for {path}")
    return None


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------
def _compute_confidence(gain_pct: float, volume_usd: float) -> float:
    """
    Confidence score (0.0-1.0) based on gain magnitude and volume.
    Higher gain + higher volume = higher confidence.
    """
    score = 0.55  # Base -- qualifies above minimum thresholds

    # Gain magnitude bonus (0-0.20)
    if gain_pct >= 50:
        score += 0.20
    elif gain_pct >= 30:
        score += 0.15
    elif gain_pct >= 20:
        score += 0.10
    elif gain_pct >= 15:
        score += 0.05

    # Volume bonus (0-0.15)
    if volume_usd >= 50_000_000:
        score += 0.15
    elif volume_usd >= 20_000_000:
        score += 0.10
    elif volume_usd >= 5_000_000:
        score += 0.05

    # Volume-to-gain ratio bonus: high volume relative to gain suggests
    # institutional interest, not just low-cap pump (0-0.10)
    vol_gain_ratio = volume_usd / max(gain_pct, 1)
    if vol_gain_ratio >= 1_000_000:
        score += 0.10
    elif vol_gain_ratio >= 500_000:
        score += 0.05

    return round(max(0.1, min(1.0, score)), 2)


# ---------------------------------------------------------------------------
# Core: promote top gainers to picks
# ---------------------------------------------------------------------------
def promote_top_gainers(
    data: dict | None = None,
    existing_symbols: set[str] | None = None,
) -> list[dict]:
    """
    Fetch Binance 24h tickers, filter qualifying gainers, and generate
    BUY picks with conservative TP/SL parameters.

    Args:
        data: Price dataframes dict from scanner (used to check symbol coverage).
              Can be None -- we fetch directly from Binance API.
        existing_symbols: Set of symbols already in active picks (to skip dupes).

    Returns:
        List of pick dicts ready for injection into all_signals.
    """
    if existing_symbols is None:
        existing_symbols = set()

    # Normalize existing symbols to uppercase for comparison
    existing_upper = {s.upper() for s in existing_symbols}

    print("  [gainer_promoter] Fetching Binance 24h tickers...")
    tickers = _binance_get("/api/v3/ticker/24hr")
    if not tickers:
        print("  [gainer_promoter] Could not fetch tickers, skipping")
        return []

    # Filter qualifying gainers
    candidates = []
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

        # Must meet minimum thresholds
        if change_pct < MIN_GAIN_PCT:
            continue
        if quote_vol < MIN_VOLUME_USD:
            continue
        if last_price <= 0:
            continue

        # Skip illiquid
        if quote_vol < ILLIQUID_THRESHOLD:
            continue

        # Skip symbols already in active picks
        if symbol.upper() in existing_upper:
            continue

        # Also skip if the base symbol (without USDT) is already tracked
        base_symbol = symbol.replace("USDT", "")
        if base_symbol in existing_upper or f"{base_symbol}USDT" in existing_upper:
            continue

        candidates.append({
            "symbol": symbol,
            "price": last_price,
            "change_pct": round(change_pct, 2),
            "volume_usd": round(quote_vol, 2),
            "high_24h": float(t.get("highPrice", 0)),
            "low_24h": float(t.get("lowPrice", 0)),
        })

    if not candidates:
        print("  [gainer_promoter] No qualifying gainers found")
        return []

    # Sort by gain % descending, take top N
    candidates.sort(key=lambda x: x["change_pct"], reverse=True)
    candidates = candidates[:MAX_PROMOTES]

    print(f"  [gainer_promoter] Found {len(candidates)} qualifying gainer(s) above {MIN_GAIN_PCT}%")

    # Generate picks
    picks = []
    now_iso = datetime.now(timezone.utc).isoformat()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for c in candidates:
        entry = c["price"]
        tp = round(entry * (1 + TP_PCT / 100), 8)
        sl = round(entry * (1 - SL_PCT / 100), 8)
        confidence = _compute_confidence(c["change_pct"], c["volume_usd"])
        rr = round(TP_PCT / SL_PCT, 2)

        volume_millions = c["volume_usd"] / 1_000_000

        pick = {
            "id": f"gainer_auto_promote::{c['symbol']}::{today_str}",
            "strategy": "gainer_auto_promote",
            "symbol": c["symbol"],
            "category": "crypto",
            "signal_type": "BUY",
            "direction": "LONG",
            "entry_price": entry,
            "entry_date": today_str,
            "timestamp": now_iso,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "ml_score": None,
            "risk_reward": rr,
            "reason": (
                f"Auto-promoted gainer: +{c['change_pct']}% 24h, "
                f"${volume_millions:.1f}M vol, "
                f"TP +{TP_PCT}% / SL -{SL_PCT}% (2:1 R:R)"
            ),
            "rsi_at_entry": None,
            "volume_ratio": None,
            "atr_at_entry": None,
            "status": "OPEN",
            "mfe": 0,
            "mae": 0,
            "high_water_mark": entry,
            "current_price": entry,
            "unrealized_pnl_pct": 0.0,
            "hold_days": 0,
            "created_at": now_iso,
            "confluence_score": 0.0,
            "confluence_reason": "auto-promoted top gainer",
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
            # Extra context fields
            "price_change_24h_pct": c["change_pct"],
            "quote_volume_24h": c["volume_usd"],
            "high_24h": c["high_24h"],
            "low_24h": c["low_24h"],
            "source": "gainer_auto_promote",
        }
        picks.append(pick)

        print(
            f"    PROMOTE {c['symbol']:>12s}  "
            f"+{c['change_pct']}% 24h  "
            f"${volume_millions:.1f}M vol  "
            f"entry={entry}  TP={tp}  SL={sl}  "
            f"conf={confidence}"
        )

    return picks


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    picks = promote_top_gainers()
    if picks:
        print(f"\n[gainer_promoter] Generated {len(picks)} pick(s)")
        # Save to a standalone file for inspection
        out_path = DATA_DIR / "gainer_promoted_picks.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(picks, f, indent=2, default=str)
        print(f"[gainer_promoter] Saved to {out_path}")
    else:
        print("\n[gainer_promoter] No picks generated this cycle.")
