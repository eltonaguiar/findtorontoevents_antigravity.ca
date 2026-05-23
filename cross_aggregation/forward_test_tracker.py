#!/usr/bin/env python3
"""
Forward-Test Tracker — Captures high-score picks and tracks outcomes over time
==============================================================================

Answers: "Do top picks (score >= 75) end up winning or losing?"

Key design decisions:
  - Score threshold: confidence >= 0.75 (75 on 0-100 scale)
  - Fresh picks: age < 2h at capture time (pick was recent when we saw it)
  - Stale picks: age > 4h at capture time (pick had been floating a while)
  - Expiry: 48h with no TP/SL hit → EXPIRED
  - PnL is measured at TP price (for WON) or SL price (for LOST)
  - Score buckets: 75-80, 80-85, 85-90, 90+

Sources:
  - data/aggregated_picks.json (consensus picks, confidence field)
  - cross_aggregation/data/super_signals.json (super signals, confidence field)

Output:
  cross_aggregation/data/forward_test_results.json

Usage:
    python -m cross_aggregation.forward_test_tracker
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
AGGREGATED_PICKS = REPO_ROOT / "data" / "aggregated_picks.json"
SUPER_SIGNALS = REPO_ROOT / "cross_aggregation" / "data" / "super_signals.json"
RESULTS_FILE = REPO_ROOT / "cross_aggregation" / "data" / "forward_test_results.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCORE_THRESHOLD = 75.0        # Minimum score (confidence * 100) to capture
EXPIRE_HOURS = 48             # Hours until an unresolved pick expires
FRESH_MAX_HOURS = 2.0         # Pick age at capture <= 2h → "fresh"
STALE_MIN_HOURS = 4.0         # Pick age at capture >= 4h → "stale"
MAX_CLOSED = 300              # Keep last N closed picks to prevent unbounded growth

_UA = {"User-Agent": "ForwardTestTracker/1.0"}

# Binance endpoint failover list (mirrors consensus_outcome_tracker.py)
_BINANCE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]

# CoinGecko ID map for common crypto symbols
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


# ---------------------------------------------------------------------------
# Price fetching helpers (lightweight, no external deps)
# ---------------------------------------------------------------------------

def _http_json(url: str, timeout: int = 10) -> Optional[dict]:
    """GET JSON, return None on any failure."""
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _normalize_symbol(symbol: str) -> str:
    """Normalise symbol for Binance lookup."""
    s = symbol.strip().upper().replace("-", "").replace("/", "")
    if s.endswith("=X"):
        s = s[:-2]
    bare_cryptos = {
        "BTC", "ETH", "SOL", "XRP", "ADA", "BNB", "DOGE", "AVAX",
        "LINK", "DOT", "NEAR", "FIL", "RENDER", "SUI", "ATOM", "ALGO",
        "TON", "AAVE", "FET", "INJ", "ARB", "TIA", "SHIB", "ETC",
        "BONK", "WIF", "GALA", "APE", "CHZ", "STRK", "JTO", "W", "ZRO",
    }
    if s in bare_cryptos:
        s += "USDT"
    return s


def _is_crypto(symbol: str) -> bool:
    s = symbol.upper()
    return any(s.endswith(sfx) for sfx in ("USDT", "BUSD", "USDC", "BTC", "ETH"))


def _binance_price(symbol: str) -> Optional[float]:
    for base in _BINANCE_BASES:
        data = _http_json(f"{base}/api/v3/ticker/price?symbol={symbol}")
        if data and "price" in data:
            try:
                return float(data["price"])
            except (ValueError, TypeError):
                pass
    return None


def _coingecko_price(symbol: str) -> Optional[float]:
    base = symbol.replace("USDT", "").replace("BUSD", "").replace("USDC", "")
    cg_id = _CG_MAP.get(base)
    if not cg_id:
        return None
    headers = {"User-Agent": "ForwardTestTracker/1.0"}
    cg_key = os.environ.get("COINGECKO_API_KEY", "")
    if cg_key:
        headers["x-cg-demo-api-key"] = cg_key
    try:
        req = urllib.request.Request(
            f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        if data and isinstance(data, dict):
            usd = data.get(cg_id, {}).get("usd")
            if usd:
                return float(usd)
    except Exception:
        pass
    return None


def _yahoo_price(symbol: str) -> Optional[float]:
    try:
        req = urllib.request.Request(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d",
            headers={"User-Agent": "ForwardTestTracker/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        meta = data["chart"]["result"][0]["meta"]
        return float(meta["regularMarketPrice"])
    except Exception:
        return None


def get_current_price(symbol: str) -> Optional[float]:
    """Best-effort price fetch: Binance → CoinGecko → Yahoo."""
    sym = _normalize_symbol(symbol)
    if _is_crypto(sym):
        p = _binance_price(sym)
        if p is not None:
            return p
        p = _coingecko_price(sym)
        if p is not None:
            return p
    # Yahoo fallback (equities, forex, and crypto tickers like BTC-USD)
    return _yahoo_price(symbol)


# ---------------------------------------------------------------------------
# Score helpers
# ---------------------------------------------------------------------------

def _confidence_to_score(confidence) -> float:
    """Convert confidence field to 0-100 score."""
    try:
        v = float(confidence)
        # Values > 1 are already on 0-100 scale
        if v <= 1.0:
            return v * 100
        return v
    except (TypeError, ValueError):
        return 0.0


def _score_bucket(score: float) -> str:
    """Return the score range bucket label."""
    if score >= 90:
        return "90+"
    if score >= 85:
        return "85-90"
    if score >= 80:
        return "80-85"
    return "75-80"


# ---------------------------------------------------------------------------
# Age helpers
# ---------------------------------------------------------------------------

def _parse_dt(ts: str) -> Optional[datetime]:
    """Parse ISO datetime string → UTC datetime, or None."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _age_hours(generated_at: str, reference: Optional[datetime] = None) -> float:
    """How many hours ago was a pick generated? 0 if unknown."""
    ref = reference or datetime.now(timezone.utc)
    dt = _parse_dt(generated_at)
    if dt is None:
        return 0.0
    delta = (ref - dt).total_seconds()
    return max(0.0, delta / 3600)


def _freshness_label(age_at_capture: float) -> str:
    """Return 'fresh', 'stale', or 'mid' based on age at capture."""
    if age_at_capture <= FRESH_MAX_HOURS:
        return "fresh"
    if age_at_capture >= STALE_MIN_HOURS:
        return "stale"
    return "mid"


# ---------------------------------------------------------------------------
# Deduplication key
# ---------------------------------------------------------------------------

def _pick_key(symbol: str, direction: str, entry: float) -> str:
    return f"{symbol.upper()}__{direction.upper()}__{round(float(entry), 4)}"


def _similar_entry(a: float, b: float) -> bool:
    if a == 0 or b == 0:
        return False
    return abs(a - b) / max(abs(a), abs(b)) < 0.005


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------

def _load_results() -> Dict:
    """Load existing forward test results, or return empty scaffold."""
    if RESULTS_FILE.exists():
        try:
            return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "tracked_picks": [],
        "stats": {
            "total": 0,
            "active": 0,
            "resolved": 0,
            "won": 0,
            "lost": 0,
            "expired": 0,
            "wr_overall": None,
            "wr_fresh": None,
            "wr_stale": None,
            "wr_by_score": {
                "75-80": None,
                "80-85": None,
                "85-90": None,
                "90+": None,
            },
            "avg_pnl_fresh": None,
            "avg_pnl_stale": None,
            "avg_pnl_overall": None,
            "tracking_since": None,
        },
        "last_updated": None,
    }


def _save_results(data: Dict) -> None:
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Ingest picks
# ---------------------------------------------------------------------------

def _load_raw_consensus() -> List[Dict]:
    if not AGGREGATED_PICKS.exists():
        return []
    try:
        raw = json.loads(AGGREGATED_PICKS.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return raw.get("consensus_picks", raw.get("picks", []))
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _load_raw_super() -> List[Dict]:
    if not SUPER_SIGNALS.exists():
        return []
    try:
        raw = json.loads(SUPER_SIGNALS.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw.get("super_signals", [])
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _normalize_raw(pick: Dict, source: str) -> Optional[Dict]:
    """Normalise pick from either source into a common dict."""
    symbol = pick.get("symbol", "")
    direction = pick.get("direction", "")
    if not symbol or not direction:
        return None

    # Handle field name differences between aggregated_picks and super_signals
    entry = float(pick.get("entry", 0) or pick.get("entry_price", 0) or 0)
    tp = float(pick.get("tp", 0) or pick.get("take_profit", 0) or 0)
    sl = float(pick.get("sl", 0) or pick.get("stop_loss", 0) or 0)

    if entry <= 0 or tp <= 0 or sl <= 0:
        return None

    confidence_raw = pick.get("confidence", 0)
    score = _confidence_to_score(confidence_raw)

    if score < SCORE_THRESHOLD:
        return None  # Below minimum quality gate

    generated_at = pick.get("generated_at", "")

    return {
        "symbol": symbol.upper(),
        "direction": direction.upper(),
        "entry_price": entry,
        "tp_price": tp,
        "sl_price": sl,
        "score": round(score, 1),
        "score_bucket": _score_bucket(score),
        "confidence_raw": round(float(confidence_raw), 4),
        "agreement_count": int(pick.get("agreement_count", 0)),
        "source_systems": pick.get("source_systems", pick.get("agreeing_systems", [])),
        "consensus_tier": pick.get("consensus_tier", pick.get("signal_tier", "MODERATE")),
        "source": source,
        "generated_at": generated_at,
    }


def ingest_new_picks(results: Dict) -> int:
    """Capture high-score picks not already being tracked."""
    now = datetime.now(timezone.utc)

    # Build dedup set from existing tracked picks
    existing_keys: set = set()
    for p in results["tracked_picks"]:
        existing_keys.add(_pick_key(p["symbol"], p["direction"], p["entry_price"]))

    new_count = 0
    candidates = []

    for raw, source_label in [
        (_load_raw_consensus(), "consensus"),
        (_load_raw_super(), "super_signal"),
    ]:
        for raw_pick in raw:
            norm = _normalize_raw(raw_pick, source_label)
            if norm is None:
                continue
            candidates.append(norm)

    for norm in candidates:
        key = _pick_key(norm["symbol"], norm["direction"], norm["entry_price"])
        if key in existing_keys:
            continue

        # Fuzzy dedup: same symbol+direction within 0.5% entry
        is_dup = False
        for ep in results["tracked_picks"]:
            if (ep["symbol"] == norm["symbol"] and
                    ep["direction"] == norm["direction"] and
                    _similar_entry(ep["entry_price"], norm["entry_price"])):
                is_dup = True
                break
        if is_dup:
            continue

        # Compute age at capture
        age_h = _age_hours(norm["generated_at"], reference=now)

        # Capture snapshot
        captured = dict(norm)
        captured["status"] = "OPEN"
        captured["captured_at"] = now.isoformat()
        captured["age_at_capture_hours"] = round(age_h, 2)
        captured["freshness"] = _freshness_label(age_h)

        # Best-effort: fetch live price at capture moment
        live_price = get_current_price(norm["symbol"])
        captured["price_at_capture"] = live_price

        results["tracked_picks"].append(captured)
        existing_keys.add(key)
        new_count += 1
        print(f"  CAPTURED  {norm['symbol']} {norm['direction']} "
              f"score={norm['score']} age={age_h:.1f}h freshness={captured['freshness']}")

    return new_count


# ---------------------------------------------------------------------------
# Check outcomes
# ---------------------------------------------------------------------------

def check_outcomes(results: Dict) -> List[Dict]:
    """Check all OPEN picks against live prices. Returns closed picks."""
    now = datetime.now(timezone.utc)
    closed_this_run = []
    still_open = []

    for pick in results["tracked_picks"]:
        if pick.get("status") != "OPEN":
            continue  # Already resolved — skip

        symbol = pick["symbol"]
        direction = pick["direction"]
        entry = pick["entry_price"]
        tp = pick["tp_price"]
        sl = pick["sl_price"]

        # --- Expiry check ---
        captured_dt = _parse_dt(pick.get("captured_at", ""))
        if captured_dt is not None:
            age_since_capture = (now - captured_dt).total_seconds() / 3600
        else:
            age_since_capture = 0.0

        if age_since_capture > EXPIRE_HOURS:
            pick["status"] = "EXPIRED"
            pick["resolved_at"] = now.isoformat()
            pick["pnl_pct"] = 0.0
            pick["close_reason"] = f"Expired after {age_since_capture:.0f}h (limit: {EXPIRE_HOURS}h)"
            closed_this_run.append(pick)
            print(f"  EXPIRED   {symbol} {direction} after {age_since_capture:.0f}h")
            continue

        # --- Price check ---
        price = get_current_price(symbol)
        if price is None:
            still_open.append(pick)
            continue

        pick["last_price"] = price
        pick["last_checked"] = now.isoformat()

        # Unrealized PnL for display
        if direction == "LONG":
            pick["unrealized_pnl_pct"] = round((price / entry - 1) * 100, 4)
        else:
            pick["unrealized_pnl_pct"] = round((1 - price / entry) * 100, 4)

        # --- TP / SL check ---
        outcome: Optional[str] = None
        pnl = 0.0

        if direction == "LONG":
            if price >= tp:
                outcome = "WON"
                pnl = (tp / entry - 1) * 100
            elif price <= sl:
                outcome = "LOST"
                pnl = (sl / entry - 1) * 100
        else:  # SHORT
            if price <= tp:
                outcome = "WON"
                pnl = (1 - tp / entry) * 100
            elif price >= sl:
                outcome = "LOST"
                pnl = (1 - sl / entry) * 100

        if outcome:
            pick["status"] = outcome
            pick["exit_price"] = price
            pick["pnl_pct"] = round(pnl, 4)
            pick["resolved_at"] = now.isoformat()
            closed_this_run.append(pick)
            icon = "WIN" if outcome == "WON" else "LOSS"
            print(f"  {icon:<8}  {symbol} {direction} -> pnl={pnl:+.2f}% "
                  f"(freshness={pick.get('freshness','?')} score={pick.get('score','?')})")
        else:
            still_open.append(pick)

    # Re-assemble: open picks first, resolved ones stay in place (they are in-place mutated)
    # The full list is results["tracked_picks"], which includes already-closed picks.
    # We only need to update the OPEN ones that are still open.
    # closed_this_run are already mutated in place; just make sure still_open is accurate.
    # We do nothing else — the full list stays intact (closed picks have status != OPEN).

    return closed_this_run


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def _wr(picks: List[Dict]) -> Optional[float]:
    """Win rate for a list of resolved (WON/LOST) picks. None if empty."""
    decided = [p for p in picks if p.get("status") in ("WON", "LOST")]
    if not decided:
        return None
    won = sum(1 for p in decided if p.get("status") == "WON")
    return round(won / len(decided) * 100, 1)


def _avg_pnl(picks: List[Dict]) -> Optional[float]:
    """Average PnL % across WON/LOST picks. None if empty."""
    decided = [p for p in picks if p.get("status") in ("WON", "LOST")]
    if not decided:
        return None
    return round(sum(float(p.get("pnl_pct", 0) or 0) for p in decided) / len(decided), 2)


def compute_stats(results: Dict) -> None:
    """Recompute all statistics from tracked_picks."""
    all_picks = results["tracked_picks"]

    open_picks = [p for p in all_picks if p.get("status") == "OPEN"]
    won_picks = [p for p in all_picks if p.get("status") == "WON"]
    lost_picks = [p for p in all_picks if p.get("status") == "LOST"]
    expired_picks = [p for p in all_picks if p.get("status") == "EXPIRED"]
    resolved = won_picks + lost_picks

    # Overall WR
    wr_overall = _wr(resolved) if resolved else None

    # Freshness split
    fresh = [p for p in all_picks if p.get("freshness") == "fresh"]
    stale = [p for p in all_picks if p.get("freshness") == "stale"]
    wr_fresh = _wr(fresh)
    wr_stale = _wr(stale)
    avg_pnl_fresh = _avg_pnl(fresh)
    avg_pnl_stale = _avg_pnl(stale)

    # Score bucket WR
    buckets = {"75-80": [], "80-85": [], "85-90": [], "90+": []}
    for p in all_picks:
        b = p.get("score_bucket", "75-80")
        if b in buckets:
            buckets[b].append(p)
    wr_by_score = {b: _wr(picks) for b, picks in buckets.items()}

    # Tracking since
    all_times = [p.get("captured_at", "") for p in all_picks if p.get("captured_at")]
    tracking_since = min(all_times) if all_times else None

    results["stats"] = {
        "total": len(all_picks),
        "active": len(open_picks),
        "resolved": len(resolved),
        "won": len(won_picks),
        "lost": len(lost_picks),
        "expired": len(expired_picks),
        "wr_overall": wr_overall,
        "wr_fresh": wr_fresh,
        "wr_stale": wr_stale,
        "wr_by_score": wr_by_score,
        "avg_pnl_fresh": avg_pnl_fresh,
        "avg_pnl_stale": avg_pnl_stale,
        "avg_pnl_overall": _avg_pnl(resolved),
        "tracking_since": tracking_since,
        # Counts by freshness for context
        "count_fresh": len(fresh),
        "count_stale": len(stale),
        "count_mid": len([p for p in all_picks if p.get("freshness") == "mid"]),
        # Counts by score bucket
        "count_by_score": {b: len(picks) for b, picks in buckets.items()},
    }

    # Cap tracked_picks to prevent unbounded growth (keep most recent MAX_CLOSED resolved)
    resolved_sorted = sorted(
        [p for p in all_picks if p.get("status") != "OPEN"],
        key=lambda p: p.get("resolved_at", p.get("captured_at", "")),
    )
    if len(resolved_sorted) > MAX_CLOSED:
        resolved_sorted = resolved_sorted[-MAX_CLOSED:]

    results["tracked_picks"] = open_picks + resolved_sorted


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run() -> Dict:
    print("\n" + "=" * 60)
    print("  FORWARD-TEST TRACKER")
    print("=" * 60)

    results = _load_results()

    # Step 1: Ingest new high-score picks
    new_count = ingest_new_picks(results)
    open_count = sum(1 for p in results["tracked_picks"] if p.get("status") == "OPEN")
    print(f"\n  New captured:   {new_count}")
    print(f"  Open/tracked:   {open_count}")

    # Step 2: Check outcomes for all open picks
    print("\n  Checking outcomes...")
    exits = check_outcomes(results)
    if exits:
        print(f"  Exits this run: {len(exits)}")
    else:
        print("  No exits triggered")

    # Step 3: Compute stats
    compute_stats(results)
    s = results["stats"]
    print(f"\n  --- Stats ---")
    print(f"  Total tracked: {s['total']}  Active: {s['active']}")
    print(f"  Won: {s['won']}  Lost: {s['lost']}  Expired: {s['expired']}")
    if s["wr_overall"] is not None:
        print(f"  Overall WR: {s['wr_overall']}%")
    if s["wr_fresh"] is not None:
        print(f"  Fresh WR:   {s['wr_fresh']}%  (n={s['count_fresh']})")
    if s["wr_stale"] is not None:
        print(f"  Stale WR:   {s['wr_stale']}%  (n={s['count_stale']})")
    print(f"  WR by score: {s['wr_by_score']}")

    # Step 4: Save
    results["last_updated"] = datetime.now(timezone.utc).isoformat()
    _save_results(results)
    print(f"\n  Output: {RESULTS_FILE}")
    print("=" * 60 + "\n")

    return results


if __name__ == "__main__":
    run()
