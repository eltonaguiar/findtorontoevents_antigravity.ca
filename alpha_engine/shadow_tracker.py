"""
Shadow Tracker -- Tracks what happens to signals AFTER they're blocked by gates.
Answers: "Which gates are protecting us and which are killing alpha?"

For every signal blocked by a gate, record:
- Which gate blocked it
- What the signal was (symbol, direction, entry price)
- What WOULD have happened if we traded it (track price for 24h)
- Did the gate save us (signal would have lost) or cost us (signal would have won)?

This is the highest-value research task -- it tells us which gates to tighten
and which to loosen based on actual data, not theory.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
SHADOW_FILE = DATA_DIR / "shadow_blocked.json"
MAX_SHADOW = 500  # keep last 500 blocked signals


def _load_shadow() -> List[dict]:
    """Load shadow-blocked signals from disk."""
    try:
        if SHADOW_FILE.exists():
            with open(SHADOW_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Shadow tracker load failed: {e}")
    return []


def _save_shadow(records: List[dict]) -> None:
    """Persist shadow records to disk, trimming to MAX_SHADOW."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Keep only the most recent records
        trimmed = records[-MAX_SHADOW:] if len(records) > MAX_SHADOW else records
        with open(SHADOW_FILE, "w", encoding="utf-8") as f:
            json.dump(trimmed, f, indent=1, default=str)
    except OSError as e:
        logger.error(f"Shadow tracker save failed: {e}")


def record_blocked_signal(signal: dict, gate_name: str, reason: str) -> None:
    """Record a blocked signal for shadow tracking.

    Args:
        signal: The signal dict that was blocked (must have symbol, entry_price, direction/signal_type).
        gate_name: Name of the gate that blocked it (e.g. 'RR_GATE', 'VPIN_GATE').
        reason: Human-readable reason string.
    """
    try:
        entry_price = signal.get("entry_price", 0)
        if not entry_price or entry_price <= 0:
            return  # Can't track without a valid entry price

        direction = signal.get("direction", signal.get("signal_type", "LONG")).upper()
        if direction in ("BUY",):
            direction = "LONG"
        elif direction in ("SELL",):
            direction = "SHORT"

        record = {
            "symbol": signal.get("symbol", "UNKNOWN"),
            "strategy": signal.get("strategy", ""),
            "direction": direction,
            "entry_price": float(entry_price),
            "gate_name": gate_name,
            "reason": reason,
            "blocked_at": datetime.now(timezone.utc).isoformat(),
            "take_profit": signal.get("take_profit"),
            "stop_loss": signal.get("stop_loss"),
            "elite_score": signal.get("elite_score"),
            "ml_score": signal.get("ml_score"),
            "confidence": signal.get("confidence"),
            # Outcome fields -- filled in by resolve_shadow_outcomes()
            "resolved": False,
            "outcome": None,           # "SAVED" or "KILLED_ALPHA"
            "price_after_24h": None,
            "pnl_pct_if_traded": None,  # What PnL% would have been
            "would_have_hit_tp": None,
            "would_have_hit_sl": None,
        }

        records = _load_shadow()
        records.append(record)
        _save_shadow(records)
    except Exception as e:
        logger.warning(f"Shadow tracker record failed (non-fatal): {e}")


def _fetch_current_price(symbol: str) -> Optional[float]:
    """Fetch current price for a symbol from Binance (with CoinGecko fallback)."""
    # Normalize symbol for Binance
    binance_sym = symbol.upper().replace("-USD", "USDT").replace("-", "")
    if not binance_sym.endswith("USDT") and "USD" not in binance_sym:
        binance_sym += "USDT"

    # Try Binance
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={binance_sym}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        price = float(data.get("price", 0))
        if price > 0:
            return price
    except Exception:
        pass

    # Try Binance US mirror
    try:
        url = f"https://api.binance.us/api/v3/ticker/price?symbol={binance_sym}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        price = float(data.get("price", 0))
        if price > 0:
            return price
    except Exception:
        pass

    # Try CoinGecko (for non-standard symbols)
    try:
        cg_id = symbol.lower().replace("-usd", "").replace("usdt", "")
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        if cg_id in data and "usd" in data[cg_id]:
            return float(data[cg_id]["usd"])
    except Exception:
        pass

    return None


def resolve_shadow_outcomes() -> dict:
    """Check blocked signals whose time has passed and record what happened.

    For each unresolved shadow record older than 24h:
    - Fetch current price
    - Determine if the trade would have been profitable
    - Mark as SAVED (gate protected us) or KILLED_ALPHA (gate cost us money)

    Returns:
        Summary dict with counts of resolved, saved, killed_alpha.
    """
    records = _load_shadow()
    if not records:
        return {"resolved": 0, "saved": 0, "killed_alpha": 0}

    now = datetime.now(timezone.utc)
    resolved_count = 0
    saved_count = 0
    killed_count = 0
    price_cache: Dict[str, Optional[float]] = {}

    for rec in records:
        if rec.get("resolved", False):
            continue

        # Check if 24h have passed
        try:
            blocked_time = datetime.fromisoformat(rec["blocked_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            rec["resolved"] = True
            rec["outcome"] = "UNKNOWN"
            continue

        if now - blocked_time < timedelta(hours=24):
            continue  # Too early to resolve

        # Fetch current price (cached per symbol)
        symbol = rec.get("symbol", "")
        if symbol not in price_cache:
            price_cache[symbol] = _fetch_current_price(symbol)

        current_price = price_cache.get(symbol)
        if current_price is None:
            # If we can't get a price after 24h, mark as unresolvable
            if now - blocked_time > timedelta(hours=72):
                rec["resolved"] = True
                rec["outcome"] = "UNRESOLVABLE"
            continue

        entry = rec.get("entry_price", 0)
        if entry <= 0:
            rec["resolved"] = True
            rec["outcome"] = "INVALID"
            continue

        direction = rec.get("direction", "LONG")
        tp = rec.get("take_profit")
        sl = rec.get("stop_loss")

        # Compute PnL
        if direction == "LONG":
            pnl_pct = ((current_price - entry) / entry) * 100
        else:  # SHORT
            pnl_pct = ((entry - current_price) / entry) * 100

        # Check TP/SL
        would_hit_tp = False
        would_hit_sl = False
        if tp and entry > 0:
            if direction == "LONG":
                would_hit_tp = current_price >= tp
            else:
                would_hit_tp = current_price <= tp
        if sl and entry > 0:
            if direction == "LONG":
                would_hit_sl = current_price <= sl
            else:
                would_hit_sl = current_price >= sl

        # Determine outcome
        # SAVED = the gate protected us (trade would have lost)
        # KILLED_ALPHA = the gate cost us (trade would have won)
        if pnl_pct > 0:
            outcome = "KILLED_ALPHA"  # Gate blocked a winning trade
            killed_count += 1
        else:
            outcome = "SAVED"  # Gate saved us from a losing trade
            saved_count += 1

        rec["resolved"] = True
        rec["outcome"] = outcome
        rec["price_after_24h"] = current_price
        rec["pnl_pct_if_traded"] = round(pnl_pct, 2)
        rec["would_have_hit_tp"] = would_hit_tp
        rec["would_have_hit_sl"] = would_hit_sl
        rec["resolved_at"] = now.isoformat()
        resolved_count += 1

    _save_shadow(records)

    return {
        "resolved": resolved_count,
        "saved": saved_count,
        "killed_alpha": killed_count,
    }


def get_gate_shadow_stats() -> Dict[str, dict]:
    """Return per-gate stats: how many blocks were good (saved us) vs bad (killed alpha).

    Returns:
        Dict[gate_name, {
            "total_blocks": int,
            "resolved": int,
            "saved": int,          # Gate correctly blocked a loser
            "killed_alpha": int,    # Gate incorrectly blocked a winner
            "save_rate": float,     # saved / resolved (higher = gate is protecting us)
            "avg_pnl_if_traded": float,  # average PnL of blocked signals
        }]
    """
    records = _load_shadow()
    if not records:
        return {}

    stats: Dict[str, dict] = {}
    for rec in records:
        gate = rec.get("gate_name", "UNKNOWN")
        if gate not in stats:
            stats[gate] = {
                "total_blocks": 0,
                "resolved": 0,
                "saved": 0,
                "killed_alpha": 0,
                "pnl_sum": 0.0,
            }

        stats[gate]["total_blocks"] += 1
        if rec.get("resolved") and rec.get("outcome") in ("SAVED", "KILLED_ALPHA"):
            stats[gate]["resolved"] += 1
            if rec["outcome"] == "SAVED":
                stats[gate]["saved"] += 1
            else:
                stats[gate]["killed_alpha"] += 1
            pnl = rec.get("pnl_pct_if_traded", 0) or 0
            stats[gate]["pnl_sum"] += pnl

    # Compute derived metrics
    for gate, s in stats.items():
        if s["resolved"] > 0:
            s["save_rate"] = round(s["saved"] / s["resolved"], 3)
            s["avg_pnl_if_traded"] = round(s["pnl_sum"] / s["resolved"], 2)
        else:
            s["save_rate"] = None
            s["avg_pnl_if_traded"] = None
        del s["pnl_sum"]  # internal accumulator, not for output

    return stats
