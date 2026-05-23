#!/usr/bin/env python3
"""
Consensus Outcome Tracker — Forward-tracks TP/SL hits for consensus picks
=========================================================================

# ATR Trailing Stop (added 2026-03-16):
# Activation: +1.5% unrealized PnL
# Trail distance: 1.5x ATR (or 2% fallback)
# Purpose: Capture 15-30% more profit in trends per Kimi research
Reads consensus picks from data/aggregated_picks.json and super signals from
cross_aggregation/data/super_signals.json, checks live prices against TP/SL
levels, and records outcomes in a JSON file for dashboard consumption.

Design:
  - Lightweight JSON-based storage (no SQLite dependency beyond what exists)
  - Reuses Binance price fetch pattern from dna_master_tracker.py
  - Handles both crypto (Binance) and equity/forex (Yahoo Finance fallback)
  - Deduplicates picks by symbol+direction+entry_price (within 0.5%)
  - Tracks: active picks, closed (WON/LOST), cumulative PnL, win rate
  - Expires stale picks after 7 days if neither TP nor SL hit

Output: cross_aggregation/data/consensus_outcomes.json

Usage:
    python -m cross_aggregation.consensus_outcome_tracker
"""

from __future__ import annotations

import json


def outcome_closure(pick: dict) -> dict:
    """Determine outcome status for a pick based on TP/SL and current price.
    This is a helper used by `check_outcomes` to annotate picks with `status`,
    `pnl_pct`, and `closed_at` fields when they hit TP, SL, or expire.
    """
    # Placeholder implementation – actual logic resides in `check_outcomes`.
    # The function simply returns the pick unchanged for now.
    return pick
import os
import pathlib
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
AGGREGATED_PICKS = REPO_ROOT / "data" / "aggregated_picks.json"
SUPER_SIGNALS = REPO_ROOT / "cross_aggregation" / "data" / "super_signals.json"
OUTCOMES_FILE = REPO_ROOT / "cross_aggregation" / "data" / "consensus_outcomes.json"

EST = timezone(timedelta(hours=-5))
STALE_HOURS = 7 * 24  # Expire picks after 7 days

# ATR trailing stop constants
TRAIL_ACTIVATION_PCT = 1.5   # Activate trailing stop at +1.5% unrealized PnL
TRAIL_ATR_MULT = 1.5         # Trail distance = 1.5x ATR
TRAIL_FALLBACK_PCT = 0.02    # 2% of price if ATR unavailable

# ---------------------------------------------------------------------------
# Price fetching (mirrors dna_master_tracker._get_binance_price)
# ---------------------------------------------------------------------------
_BINANCE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]


_UA = {"User-Agent": "ConsensusTracker/1.0"}
OUTLIER_THRESHOLD = 0.005  # 0.5% deviation from median = outlier

# CoinGecko ID mapping for common crypto symbols
_CG_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin", "SOL": "solana",
    "XRP": "ripple", "ADA": "cardano", "AVAX": "avalanche-2", "DOT": "polkadot",
    "LINK": "chainlink", "MATIC": "matic-network", "LTC": "litecoin", "DOGE": "dogecoin",
    "SHIB": "shiba-inu", "UNI": "uniswap", "AAVE": "aave", "ATOM": "cosmos",
    "NEAR": "near", "FIL": "filecoin", "ICP": "internet-computer", "TRX": "tron",
    "ETC": "ethereum-classic", "BCH": "bitcoin-cash", "ALGO": "algorand",
    "HBAR": "hedera-hashgraph", "VET": "vechain", "PEPE": "pepe", "ZEC": "zcash",
    "APT": "aptos", "OP": "optimism", "ARB": "arbitrum", "SUI": "sui",
    "SEI": "sei-network", "INJ": "injective-protocol", "FTM": "fantom",
    "RUNE": "thorchain", "GRT": "the-graph", "MKR": "maker", "STX": "blockstack",
    "FLOKI": "floki", "BONK": "bonk", "WIF": "dogwifcoin", "FET": "fetch-ai",
    "RNDR": "render-token", "IMX": "immutable-x", "TIA": "celestia",
    "TON": "toncoin", "GALA": "gala", "APE": "apecoin", "CHZ": "chiliz",
    "STRK": "starknet", "JTO": "jito-governance-token", "W": "wormhole",
    "ZRO": "layerzero", "RENDER": "render-token",
}


def _http_json(url: str, timeout: int = 10, headers: Optional[dict] = None):
    """GET JSON with error handling. Returns None on any failure."""
    hdrs = dict(_UA)
    if headers:
        hdrs.update(headers)
    try:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _get_binance_price(symbol: str) -> Optional[float]:
    """Fetch current price from Binance API with endpoint failover."""
    for base in _BINANCE_BASES:
        try:
            url = f"{base}/api/v3/ticker/price?symbol={symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "ConsensusTracker/1.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=10).read())
            return float(data["price"])
        except Exception:
            continue
    return None


def _get_bybit_price(symbol: str) -> Optional[float]:
    """Fetch current price from Bybit spot API."""
    data = _http_json(f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}", timeout=10)
    if not data or data.get("retCode") != 0:
        return None
    items = data.get("result", {}).get("list", [])
    if items and items[0].get("lastPrice"):
        try:
            return float(items[0]["lastPrice"])
        except (ValueError, TypeError):
            pass
    return None


def _get_coingecko_price(symbol: str) -> Optional[float]:
    """Fetch current price from CoinGecko for a single symbol."""
    base = symbol.replace("USDT", "").replace("BUSD", "").replace("USDC", "")
    cg_id = _CG_MAP.get(base)
    if not cg_id:
        return None
    headers = {}
    cg_key = os.environ.get("COINGECKO_API_KEY", "")
    if cg_key:
        headers["x-cg-demo-api-key"] = cg_key
    data = _http_json(
        f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd",
        timeout=15, headers=headers if headers else None,
    )
    if data and isinstance(data, dict):
        usd = data.get(cg_id, {}).get("usd")
        if usd:
            return float(usd)
    return None


def _normalize_binance_symbol(symbol: str) -> str:
    """Normalize symbol for Binance API lookup."""
    s = symbol.strip().upper().replace("-", "").replace("/", "")
    # Remove =X suffix (Yahoo forex format)
    if s.endswith("=X"):
        s = s[:-2]
    # Add USDT if it looks like bare crypto
    if s in ("BTC", "ETH", "SOL", "XRP", "ADA", "BNB", "DOGE", "AVAX",
             "LINK", "DOT", "NEAR", "FIL", "RENDER", "SUI", "ATOM", "ALGO",
             "TON", "AAVE", "FET", "INJ", "ARB", "TIA", "SHIB", "ETC",
             "BONK", "WIF", "GALA", "APE", "CHZ", "STRK", "JTO", "W", "ZRO"):
        s += "USDT"
    return s


def _get_yahoo_price(symbol: str) -> Optional[float]:
    """Fallback price fetch via Yahoo Finance for equities/forex."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        req = urllib.request.Request(url, headers={
            "User-Agent": "ConsensusTracker/1.0",
            "Accept": "application/json",
        })
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        meta = data["chart"]["result"][0]["meta"]
        return float(meta["regularMarketPrice"])
    except Exception:
        return None


def _is_crypto(symbol: str) -> bool:
    """Check if symbol is a crypto pair."""
    s = symbol.upper()
    return any(s.endswith(sfx) for sfx in ("USDT", "BUSD", "USDC", "BTC", "ETH"))


def _compute_consensus(prices_by_source: Dict[str, float]) -> Optional[Dict]:
    """Compute weighted consensus from multiple source prices.

    Returns dict with 'price', 'confidence', 'sources', 'outliers'.
    """
    if not prices_by_source:
        return None
    if len(prices_by_source) == 1:
        source, price = next(iter(prices_by_source.items()))
        return {'price': price, 'confidence': 0.33, 'sources': 1, 'outliers': []}

    vals = list(prices_by_source.values())
    sorted_vals = sorted(vals)
    median_price = sorted_vals[len(sorted_vals) // 2]

    # Flag outliers (>0.5% from median)
    clean = {s: p for s, p in prices_by_source.items()
             if abs(p - median_price) / median_price <= OUTLIER_THRESHOLD}
    outliers = [s for s in prices_by_source if s not in clean]

    if not clean:
        # All flagged as outliers — fall back to all prices
        clean = prices_by_source

    consensus_price = sum(clean.values()) / len(clean)
    confidence = round(len(clean) / 3, 2)  # 0.33 to 1.0

    return {
        'price': consensus_price,
        'confidence': confidence,
        'sources': len(clean),
        'outliers': outliers,
    }


def get_current_price_with_confidence(symbol: str) -> Optional[Dict]:
    """Get consensus price from all available sources.

    Returns dict with 'price', 'confidence', 'sources', 'outliers' or None.
    """
    binance_sym = _normalize_binance_symbol(symbol)
    prices_by_source: Dict[str, float] = {}

    # Try all sources
    if _is_crypto(binance_sym):
        bp = _get_binance_price(binance_sym)
        if bp is not None:
            prices_by_source['binance'] = bp

        byp = _get_bybit_price(binance_sym)
        if byp is not None:
            prices_by_source['bybit'] = byp

        cgp = _get_coingecko_price(binance_sym)
        if cgp is not None:
            prices_by_source['coingecko'] = cgp

    # Yahoo fallback (works for both crypto and equities)
    if not prices_by_source:
        yp = _get_yahoo_price(symbol)
        if yp is not None:
            prices_by_source['yahoo'] = yp

    if not prices_by_source:
        return None

    result = _compute_consensus(prices_by_source)
    if result and result['outliers']:
        print(f"  [price] OUTLIER {symbol}: {', '.join(result['outliers'])} "
              f"deviated >{OUTLIER_THRESHOLD*100}% from median")

    return result


def get_current_price(symbol: str) -> Optional[float]:
    """Backward-compatible: get consensus price as a simple float."""
    result = get_current_price_with_confidence(symbol)
    return result['price'] if result else None


# ---------------------------------------------------------------------------
# Pick key for deduplication
# ---------------------------------------------------------------------------
def _pick_key(symbol: str, direction: str, entry_price: float) -> str:
    """Generate unique key for a pick (used for dedup)."""
    return f"{symbol.upper()}__{direction.upper()}__{round(float(entry_price), 4)}"


def _is_similar_entry(existing_entry: float, new_entry: float) -> bool:
    """Check if two entry prices are within 0.5% (duplicate)."""
    if existing_entry == 0:
        return False
    return abs(existing_entry - new_entry) / existing_entry < 0.005


# ---------------------------------------------------------------------------
# Core tracker logic
# ---------------------------------------------------------------------------
def load_outcomes() -> Dict:
    """Load existing outcomes state from JSON file."""
    defaults = {
        "active": [],
        "closed": [],
        "stats": {
            "total_tracked": 0,
            "wins": 0,
            "losses": 0,
            "expired": 0,
            "win_rate": 0.0,
            "cumulative_pnl_pct": 0.0,
            "avg_pnl_pct": 0.0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "tracking_since": "",
        },
        "last_checked": "",
    }
    if OUTCOMES_FILE.exists():
        try:
            data = json.loads(OUTCOMES_FILE.read_text(encoding="utf-8"))
            # Ensure all default keys exist (prevents KeyError on missing keys)
            for key, val in defaults.items():
                if key not in data:
                    data[key] = val
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return defaults


def save_outcomes(outcomes: Dict) -> None:
    """Write outcomes state to JSON file."""
    OUTCOMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTCOMES_FILE.write_text(
        json.dumps(outcomes, indent=2, default=str),
        encoding="utf-8",
    )


def _load_consensus_picks() -> List[Dict]:
    """Load current consensus picks from aggregated_picks.json.

    Handles two formats:
      - List of picks (simple mode)
      - Dict with 'consensus_picks' key (when regime data is present)
    """
    if not AGGREGATED_PICKS.exists():
        return []
    try:
        data = json.loads(AGGREGATED_PICKS.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # When regime_data is present, aggregator wraps picks in a dict
            return data.get("consensus_picks", data.get("picks", []))
        return []
    except (json.JSONDecodeError, OSError):
        return []


def _load_super_signals() -> List[Dict]:
    """Load current super signals."""
    if not SUPER_SIGNALS.exists():
        return []
    try:
        data = json.loads(SUPER_SIGNALS.read_text(encoding="utf-8"))
        return data.get("super_signals", []) if isinstance(data, dict) else []
    except (json.JSONDecodeError, OSError):
        return []


def _normalize_pick(pick: Dict, source: str) -> Optional[Dict]:
    """Normalize a pick from either source into a standard format."""
    symbol = pick.get("symbol", "")
    direction = pick.get("direction", "")
    if not symbol or not direction:
        return None

    # Handle different field names between aggregated_picks and super_signals
    entry = float(pick.get("entry", 0) or pick.get("entry_price", 0) or 0)
    tp = float(pick.get("tp", 0) or pick.get("take_profit", 0) or 0)
    sl = float(pick.get("sl", 0) or pick.get("stop_loss", 0) or 0)

    if entry <= 0 or tp <= 0 or sl <= 0:
        return None

    return {
        "symbol": symbol.upper(),
        "direction": direction.upper(),
        "entry_price": entry,
        "tp_price": tp,
        "sl_price": sl,
        "confidence": float(pick.get("confidence", 0)),
        "agreement_count": int(pick.get("agreement_count", 0)),
        "source_systems": pick.get("source_systems", pick.get("agreeing_systems", [])),
        "consensus_tier": pick.get("consensus_tier", pick.get("signal_tier", "MODERATE")),
        "source": source,
        "generated_at": pick.get("generated_at", datetime.now(timezone.utc).isoformat()),
        "tracked_at": datetime.now(timezone.utc).isoformat(),
        "beta_score": pick.get("beta_score"),
        "beta_breakdown": pick.get("beta_breakdown"),
        "beta_qualified": pick.get("beta_qualified", False),
    }


def ingest_new_picks(outcomes: Dict) -> int:
    """Ingest new consensus picks that aren't already being tracked."""
    # Build set of active pick keys for dedup
    active_keys = set()
    for p in outcomes.get("active", []):
        active_keys.add(_pick_key(p["symbol"], p["direction"], p["entry_price"]))

    # Also check closed picks (don't re-track picks that already resolved)
    for p in outcomes.get("closed", []):
        active_keys.add(_pick_key(p["symbol"], p["direction"], p["entry_price"]))

    # Post-TP cooldown: don't re-enter same symbol within 4 hours of a TP hit
    TP_COOLDOWN_HOURS = 4
    cooldown_symbols = set()
    now = datetime.now(timezone.utc)
    for p in outcomes.get("closed", []):
        if p.get("status") == "WON":
            closed_at = p.get("closed_at", "")
            if closed_at:
                try:
                    ct = datetime.fromisoformat(closed_at)
                    if ct.tzinfo is None:
                        ct = ct.replace(tzinfo=timezone.utc)
                    if (now - ct).total_seconds() < TP_COOLDOWN_HOURS * 3600:
                        cooldown_symbols.add(p["symbol"])
                except (ValueError, TypeError):
                    pass
    if cooldown_symbols:
        print(f"  [COOLDOWN] Post-TP cooldown active for: {', '.join(cooldown_symbols)}")

    new_count = 0

    # Ingest from aggregated_picks.json
    for pick in _load_consensus_picks():
        norm = _normalize_pick(pick, "consensus")
        if norm is None:
            continue
        # Post-TP cooldown: skip symbols that recently hit TP
        if norm["symbol"] in cooldown_symbols:
            print(f"  [COOLDOWN] Skipping {norm['symbol']} — post-TP cooldown")
            continue
        # Minimum 2 system agreement for consensus picks
        if norm.get("agreement_count", 0) < 2:
            continue
        key = _pick_key(norm["symbol"], norm["direction"], norm["entry_price"])
        if key in active_keys:
            continue
        # Also check for similar entries (within 0.5%)
        is_dup = False
        for existing in outcomes["active"]:
            if (existing["symbol"] == norm["symbol"] and
                existing["direction"] == norm["direction"] and
                _is_similar_entry(existing["entry_price"], norm["entry_price"])):
                is_dup = True
                break
        if is_dup:
            continue
        outcomes["active"].append(norm)
        active_keys.add(key)
        new_count += 1

    # Ingest from super_signals.json
    for pick in _load_super_signals():
        norm = _normalize_pick(pick, "super_signal")
        if norm is None:
            continue
        # Post-TP cooldown: skip symbols that recently hit TP
        if norm["symbol"] in cooldown_symbols:
            print(f"  [COOLDOWN] Skipping {norm['symbol']} — post-TP cooldown")
            continue
        key = _pick_key(norm["symbol"], norm["direction"], norm["entry_price"])
        if key in active_keys:
            continue
        is_dup = False
        for existing in outcomes["active"]:
            if (existing["symbol"] == norm["symbol"] and
                existing["direction"] == norm["direction"] and
                _is_similar_entry(existing["entry_price"], norm["entry_price"])):
                is_dup = True
                break
        if is_dup:
            continue
        outcomes["active"].append(norm)
        active_keys.add(key)
        new_count += 1

    return new_count


def _fetch_atr(symbol: str, period: int = 14) -> Optional[float]:
    """Fetch ATR from Binance hourly klines. Returns absolute ATR value or None."""
    binance_sym = _normalize_binance_symbol(symbol)
    for base in _BINANCE_BASES:
        try:
            url = f"{base}/api/v3/klines?symbol={binance_sym}&interval=1h&limit={period + 1}"
            req = urllib.request.Request(url, headers={"User-Agent": "ConsensusTracker/1.0"})
            data = json.loads(urllib.request.urlopen(req, timeout=5).read())
            if not data or len(data) < period + 1:
                continue
            trs = []
            for i in range(1, len(data)):
                high, low, prev_close = float(data[i][2]), float(data[i][3]), float(data[i - 1][4])
                trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
            return sum(trs[-period:]) / period
        except Exception:
            continue
    return None


def _update_trailing_stop(pick: Dict, price: float) -> Optional[str]:
    """Update ATR trailing stop for a pick. Modifies pick in-place.

    Returns 'TRAIL_SL' if trailing SL was hit, else None.
    """
    direction = pick.get("direction", "LONG").upper()
    entry = pick.get("entry_price", 0)
    if not entry:
        return None

    # Calculate unrealized PnL
    if direction == "LONG":
        pnl_pct = (price - entry) / entry * 100
    else:
        pnl_pct = (entry - price) / entry * 100

    # Track peak price
    peak = pick.get("_trail_peak_price", price)
    if direction == "LONG":
        peak = max(peak, price)
    else:
        peak = min(peak, price)
    pick["_trail_peak_price"] = peak

    # Check activation threshold
    if pnl_pct < TRAIL_ACTIVATION_PCT and not pick.get("_trail_active"):
        return None

    # Activate trailing stop if not already active
    if not pick.get("_trail_active"):
        atr = _fetch_atr(pick.get("symbol", ""))
        if atr and atr > 0:
            trail_dist = TRAIL_ATR_MULT * atr
            method = "ATR_1.5x_dynamic"
        else:
            trail_dist = TRAIL_FALLBACK_PCT * price
            method = "pct_2_fallback"
        pick["_trail_active"] = True
        pick["_trail_dist"] = trail_dist
        pick["_trail_metadata"] = {
            "method": method,
            "atr": round(atr, 6) if atr else 0,
            "trail_dist": round(trail_dist, 6),
            "activation_pnl_pct": round(pnl_pct, 2),
        }
        print(f"  TRAIL_ACTIVATED {pick.get('symbol')} dist={trail_dist:.6f} method={method}")

    trail_dist = pick.get("_trail_dist", TRAIL_FALLBACK_PCT * price)
    orig_sl = pick.get("sl_price", 0)

    # Compute new trailing SL
    if direction == "LONG":
        trail_sl = peak - trail_dist
        if orig_sl:
            trail_sl = max(trail_sl, orig_sl)
        if price <= trail_sl:
            pick["_trail_exit_peak_pnl"] = round((peak - entry) / entry * 100, 2)
            pick["_trail_exit_actual_pnl"] = round((price - entry) / entry * 100, 2)
            return "TRAIL_SL"
        pick["sl_price"] = round(trail_sl, 8)
    else:  # SHORT
        trail_sl = peak + trail_dist
        if orig_sl:
            trail_sl = min(trail_sl, orig_sl)
        if price >= trail_sl:
            pick["_trail_exit_peak_pnl"] = round((entry - peak) / entry * 100, 2)
            pick["_trail_exit_actual_pnl"] = round((entry - price) / entry * 100, 2)
            return "TRAIL_SL"
        pick["sl_price"] = round(trail_sl, 8)

    pick["peak_pnl_pct"] = round(max(pnl_pct, pick.get("peak_pnl_pct", 0)), 2)
    return None


def check_outcomes(outcomes: Dict) -> List[Dict]:
    """Check all active picks against live prices. Returns list of exits."""
    exits = []
    still_active = []
    now = datetime.now(timezone.utc)

    for pick in outcomes["active"]:
        symbol = pick["symbol"]
        direction = pick["direction"]
        entry = pick["entry_price"]
        tp = pick["tp_price"]
        sl = pick["sl_price"]

        # Check for stale picks (older than STALE_HOURS)
        tracked_at = pick.get("tracked_at", pick.get("generated_at", ""))
        try:
            pick_time = datetime.fromisoformat(tracked_at.replace("Z", "+00:00"))
            age_hours = (now - pick_time).total_seconds() / 3600
        except (ValueError, TypeError, AttributeError):
            age_hours = 0

        if age_hours > STALE_HOURS:
            # Expire the pick
            pick["status"] = "EXPIRED"
            pick["closed_at"] = now.isoformat()
            pick["close_reason"] = f"Stale after {age_hours:.0f}h (limit: {STALE_HOURS}h)"
            pick["pnl_pct"] = 0.0
            outcomes["closed"].append(pick)
            exits.append(pick)
            continue

        # Fetch current price with confidence
        price_data = get_current_price_with_confidence(symbol)
        if price_data is None:
            still_active.append(pick)
            continue

        price = price_data['price']

        # Store last checked price and confidence metadata
        pick["last_price"] = price
        pick["last_checked"] = now.isoformat()
        pick["_price_confidence"] = price_data['confidence']
        pick["_price_sources"] = price_data['sources']
        if price_data['outliers']:
            pick["_price_outliers"] = price_data['outliers']
        if price_data['confidence'] < 0.5:
            pick["_low_confidence_note"] = "low price confidence — single source only"

        # Calculate unrealized PnL for display
        if direction == "LONG":
            pick["unrealized_pnl_pct"] = round((price / entry - 1) * 100, 4)
        else:
            pick["unrealized_pnl_pct"] = round((1 - price / entry) * 100, 4)

        # ATR trailing stop check (before fixed TP/SL)
        trail_result = _update_trailing_stop(pick, price)
        if trail_result == "TRAIL_SL":
            if direction == "LONG":
                pnl = (price / entry - 1) * 100
            else:
                pnl = (1 - price / entry) * 100
            pick["status"] = "TRAIL_SL"
            pick["exit_price"] = price
            pick["pnl_pct"] = round(pnl, 4)
            pick["closed_at"] = now.isoformat()
            pick["close_reason"] = "ATR trailing stop hit"
            pick["trail_metadata"] = pick.get("_trail_metadata", {})
            outcomes["closed"].append(pick)
            exits.append(pick)
            continue

        # Check TP/SL
        hit = None
        pnl = 0.0
        if direction == "LONG":
            if price >= tp:
                hit = "WON"
                pnl = (tp / entry - 1) * 100
            elif price <= sl:
                hit = "LOST"
                pnl = (sl / entry - 1) * 100
        else:  # SHORT
            if price <= tp:
                hit = "WON"
                pnl = (1 - tp / entry) * 100
            elif price >= sl:
                hit = "LOST"
                pnl = (1 - sl / entry) * 100

        if hit:
            pick["status"] = hit
            pick["exit_price"] = price
            pick["pnl_pct"] = round(pnl, 4)
            pick["closed_at"] = now.isoformat()
            outcomes["closed"].append(pick)
            exits.append(pick)
            # Update beta_score_tracker.json with outcomes
            try:
                import json as _json
                tracker_path = os.path.join(os.path.dirname(__file__), "data", "beta_score_tracker.json")
                if os.path.exists(tracker_path):
                    with open(tracker_path) as f:
                        tracker = _json.load(f)
                    updated = False
                    pick_symbol = pick.get("symbol", "")
                    pick_direction = pick.get("direction", "")
                    outcome_str = hit  # "WON" or "LOST"
                    for tp_entry in tracker.get("picks", []):
                        if (tp_entry.get("outcome") is None and
                            tp_entry["symbol"] == pick_symbol and
                            tp_entry["direction"] == pick_direction):
                            tp_entry["outcome"] = outcome_str
                            tp_entry["outcome_timestamp"] = datetime.now(timezone.utc).isoformat()
                            updated = True
                            break
                    if updated:
                        with open(tracker_path, "w") as f:
                            _json.dump(tracker, f, indent=2)
            except Exception as e:
                print(f"  [WARN] Beta tracker outcome update failed: {e}", file=sys.stderr)
        else:
            still_active.append(pick)

    outcomes["active"] = still_active
    return exits


def compute_stats(outcomes: Dict) -> None:
    """Recompute aggregate stats from closed picks."""
    closed = outcomes.get("closed", [])
    wins = [p for p in closed if p.get("status") in ("WON", "TRAIL_SL")]
    losses = [p for p in closed if p.get("status") == "LOST"]
    expired = [p for p in closed if p.get("status") == "EXPIRED"]

    decided = len(wins) + len(losses)  # Exclude expired from WR calc
    total_tracked = len(closed) + len(outcomes["active"])

    cum_pnl = sum(float(p.get("pnl_pct", 0) or 0) for p in closed)
    all_pnls = [float(p.get("pnl_pct", 0) or 0) for p in closed if p.get("status") in ("WON", "LOST", "TRAIL_SL")]

    # Find tracking start
    all_times = []
    for p in closed + outcomes["active"]:
        t = p.get("tracked_at", p.get("generated_at", ""))
        if t:
            all_times.append(t)
    tracking_since = min(all_times) if all_times else ""

    outcomes["stats"] = {
        "total_tracked": total_tracked,
        "active_count": len(outcomes["active"]),
        "wins": len(wins),
        "losses": len(losses),
        "expired": len(expired),
        "decided": decided,
        "win_rate": round(len(wins) / decided * 100, 1) if decided else 0.0,
        "cumulative_pnl_pct": round(cum_pnl, 2),
        "avg_pnl_pct": round(cum_pnl / decided, 2) if decided else 0.0,
        "best_trade_pct": round(max(all_pnls), 2) if all_pnls else 0.0,
        "worst_trade_pct": round(min(all_pnls), 2) if all_pnls else 0.0,
        "tracking_since": tracking_since,
    }

    # Keep closed list capped at 200 most recent (prevent unbounded growth)
    if len(outcomes["closed"]) > 200:
        outcomes["closed"] = outcomes["closed"][-200:]


def run() -> Dict:
    """Main entry point: ingest picks, check outcomes, update stats."""
    print("\n" + "=" * 60)
    print("  CONSENSUS OUTCOME TRACKER")
    print("=" * 60)

    outcomes = load_outcomes()

    # 1. Ingest new picks
    new_count = ingest_new_picks(outcomes)
    print(f"  New picks ingested:  {new_count}")
    print(f"  Active picks:        {len(outcomes['active'])}")

    # 2. Check TP/SL exits
    exits = check_outcomes(outcomes)
    if exits:
        print(f"\n  Exits triggered: {len(exits)}")
        for ex in exits:
            status = ex.get("status", "?")
            pnl = ex.get("pnl_pct", 0)
            icon = "WIN" if status == "WON" else "LOSS" if status == "LOST" else "EXPIRED"
            print(f"    {icon}: {ex['symbol']} {ex['direction']} -> {pnl:+.2f}%")
    else:
        print(f"\n  No exits triggered")

    # 3. Recompute stats
    compute_stats(outcomes)
    stats = outcomes["stats"]
    print(f"\n  --- Cumulative Stats ---")
    print(f"  Total tracked:  {stats['total_tracked']}")
    print(f"  Active:         {stats['active_count']}")
    print(f"  Decided:        {stats['decided']} (W: {stats['wins']} / L: {stats['losses']})")
    print(f"  Win rate:       {stats['win_rate']:.1f}%")
    print(f"  Cum PnL:        {stats['cumulative_pnl_pct']:+.2f}%")
    if stats["decided"] > 0:
        print(f"  Avg PnL/trade:  {stats['avg_pnl_pct']:+.2f}%")
        print(f"  Best trade:     {stats['best_trade_pct']:+.2f}%")
        print(f"  Worst trade:    {stats['worst_trade_pct']:+.2f}%")
    print(f"  Expired:        {stats['expired']}")

    # 4. Save
    outcomes["last_checked"] = datetime.now(timezone.utc).isoformat()
    save_outcomes(outcomes)
    print(f"\n  Output: {OUTCOMES_FILE}")
    print("=" * 60 + "\n")

    return outcomes


def sync_outcomes_to_mysql(outcomes: Dict) -> int:
    """Sync closed outcomes back to at_consensus_picks in MySQL."""
    try:
        import pymysql
    except ImportError:
        print("  pymysql not installed, skipping MySQL sync")
        return 0

    import os
    try:
        conn = pymysql.connect(
            host=os.getenv("AUDIT_DB_HOST", "mysql.50webs.com"),
            port=int(os.getenv("AUDIT_DB_PORT", "3306")),
            user=os.getenv("AUDIT_DB_USER", "ejaguiar1_stocks"),
            password=os.getenv("AUDIT_DB_PASS", "stocks"),
            database=os.getenv("AUDIT_DB_NAME", "ejaguiar1_stocks"),
            connect_timeout=10, charset="utf8mb4", autocommit=True,
        )
    except Exception as e:
        print(f"  MySQL connection failed: {e}")
        return 0

    cur = conn.cursor()
    updated = 0
    for pick in outcomes.get("closed", []):
        status = pick.get("status", "")
        if status not in ("WON", "LOST", "EXPIRED"):
            continue
        symbol = pick.get("symbol", "")
        direction = pick.get("direction", "")
        entry = pick.get("entry_price", 0)
        exit_p = pick.get("exit_price", entry)
        pnl = pick.get("pnl_pct", 0)
        closed_at = pick.get("closed_at", "")
        if "T" in str(closed_at):
            try:
                closed_at = datetime.fromisoformat(closed_at.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                closed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        reason = "TP_HIT" if status == "WON" else "SL_HIT" if status == "LOST" else "EXPIRED"
        try:
            cur.execute(
                """UPDATE at_consensus_picks
                   SET status=%s, exit_price=%s, exit_reason=%s, pnl_pct=%s, closed_at=%s
                   WHERE symbol=%s AND direction=%s
                     AND ABS(entry_price - %s) / entry_price < 0.005
                     AND status='OPEN'
                   LIMIT 1""",
                (status, exit_p, reason, pnl, closed_at, symbol, direction, entry),
            )
            if cur.rowcount > 0:
                updated += 1
        except Exception as e:
            print(f"  MySQL update error for {symbol}: {e}")

    conn.close()
    return updated


if __name__ == "__main__":
    outcomes = run()
    updated = sync_outcomes_to_mysql(outcomes)
    if updated:
        print(f"  MySQL: Updated {updated} consensus picks with outcomes")
