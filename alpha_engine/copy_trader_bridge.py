#!/usr/bin/env python3
"""
copy_trader_bridge.py - Bridge vetted copy_trader_intel picks into Alpha Engine
===============================================================================
Reads copy_trader_intel/data/active_picks.json, drops junk copy sources
(Binance sentiment feed, Bitget, unverified clones), preserves only vetted
crypto copy picks, and tags proven traders for execution.

This module sits on scanner.py's live path. If it breaks, copy-trader picks
quietly disappear from Alpha Engine, so keep it intentionally small and strict.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Paths relative to this file (alpha_engine/)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_COPY_INTEL_DIR = os.path.join(_THIS_DIR, "..", "copy_trader_intel", "data")
_ALPHA_DATA_DIR = os.path.join(_THIS_DIR, "data")

COPY_INTEL_PICKS_FILE = os.path.join(_COPY_INTEL_DIR, "active_picks.json")
EXTRACTED_STRATEGIES_FILE = os.path.join(_COPY_INTEL_DIR, "extracted_strategies.json")
STRATEGY_PERFORMANCE_FILE = os.path.join(_ALPHA_DATA_DIR, "strategy_performance.json")

# Directional confidence thresholds
LONG_MIN_CONFIDENCE = 0.70
SHORT_MIN_CONFIDENCE = 0.75  # v100: lowered from 0.90 — was filtering ALL shorts (most have 60-70% conf)
FINAL_SCORE_THRESHOLD = 55

# Source hygiene
# 2026-05-12 exec-gate fix: import canonical BLACKLISTED_STRATEGIES from
# alpha_engine.config so kimi_signal_tracking / claude_gainer_st / etc are
# enforced at copy-trade exec — not just at intake. Prior local set was
# stale (3 entries vs 5 in config) so 2 banned strategies could copy-trade.
# Memory: feedback_gate_at_execution_not_generation.
try:
    from alpha_engine.config import BLACKLISTED_STRATEGIES as _CANONICAL_BLACKLIST
    BLACKLISTED_STRATEGIES = set(_CANONICAL_BLACKLIST) | {
        "binance_smart_money",   # 45.8% WR / -0.21% PnL — local-only retain
        "hl_funding_fade",       # 0/11 WR — consistently wrong on funding reversals
        "quan_engine_scalp",     # 0% WR / -794% total PnL zombie
    }
except Exception:
    # Defensive fallback if config import fails — preserve prior behavior
    BLACKLISTED_STRATEGIES = {"binance_smart_money", "hl_funding_fade", "quan_engine_scalp"}
BLOCKED_EXCHANGE_TAGS = ("bitget",)
PROVEN_TRADERS = {
    "copy_hl_NMTD_25M",
    "copy_hl_whale_123M_87roi",
    # v100: Added proven traders from strategy_tiers.json analysis
    "copy_hl_whale_24.5M",   # 68.8% WR, PF 3.30, 16 trades, $24.5M PnL
    "hs_lb_None",            # 57.9% WR (91.7% on shorts), dominant highscore trader
    "hs_Auros_66M",          # Auros market maker, $66M vault
    "clone_hl_copy_lb_None", # 35.7% WR but good short-side alpha
}
MIN_VERIFIED_CLOSED_TRADES = 3
MIN_VERIFIED_WIN_RATE = 0.55
MAX_ALLOWED_COPY_PF = 10.0
MIN_HISTORY_TRADES_HIGH_CERT = 10
MIN_HISTORY_WR_HIGH_CERT = 0.58
MIN_HISTORY_PF_HIGH_CERT = 1.10
CRYPTO_SYMBOL_REGEX = re.compile(r"^[A-Z0-9]+USDT$")


def _load_json(path: str) -> Any:
    """Load a JSON file, return None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None



def _is_fresh_position(pick: dict) -> bool:
    """Only copy positions opened under 24 hours ago.

    v100: Relaxed from 2h to 24h. Whale traders hold positions for hours/days.
    The 2h gate was killing every single legitimate position since the scraper
    runs every 35min and whales don't close in 2h.
    """
    opened_at = pick.get('timestamp') or pick.get('entry_date') or pick.get('open_time')
    if not opened_at:
        return False
    try:
        ts = str(opened_at).strip()
        if ts.endswith("Z"): ts = ts[:-1] + "+00:00"
        if " " in ts and "T" not in ts: ts = ts.replace(" ", "T", 1)
        import datetime
        pt = datetime.datetime.fromisoformat(ts)
        if pt.tzinfo is None:
            pt = pt.replace(tzinfo=datetime.timezone.utc)
        age_hours = (datetime.datetime.now(datetime.timezone.utc) - pt).total_seconds() / 3600
        if age_hours > 24:
            return False
        return True
    except Exception:
        return True

def _build_strategy_lookup(extracted: dict) -> Dict[str, dict]:
    """Build a lookup from strategy_id -> strategy metadata."""
    lookup: Dict[str, dict] = {}
    if not extracted or not isinstance(extracted, dict):
        return lookup
    for strat in extracted.get("strategies", []):
        sid = strat.get("strategy_id", "")
        if sid:
            lookup[sid] = strat
        label = strat.get("source_label", "")
        if label:
            lookup[label] = strat
    return lookup


def _normalize_direction(pick: dict) -> str:
    """Extract normalised direction from a pick."""
    direction = str(pick.get("direction", pick.get("signal_type", ""))).upper()
    if direction in ("BUY", "LONG"):
        return "LONG"
    if direction in ("SELL", "SHORT"):
        return "SHORT"
    return direction


def _copy_score(pick: dict, confidence: float) -> float:
    """Best-available score proxy for bridge filtering."""
    score = pick.get("elite_score")
    if score is None:
        score = pick.get("score")
    if score is None:
        score = pick.get("ml_score")
    if score is None:
        score = confidence
    score = float(score or 0)
    if score <= 1.0:
        score *= 100.0
    return score


def _avg_pnl_pct(stats: dict) -> float:
    """Normalize avg PnL across differing strategy performance schemas."""
    if stats.get("avg_pnl_pct") is not None:
        return float(stats.get("avg_pnl_pct") or 0)
    if stats.get("avg_pnl") is not None:
        return float(stats.get("avg_pnl") or 0)
    closed = int(stats.get("closed_picks", 0) or 0)
    total = float(stats.get("total_pnl_pct", 0) or 0)
    return (total / closed) if closed else 0.0


def _embedded_copy_track_record(pick: dict) -> dict:
    """Return normalized embedded history for sources not yet in local strategy stats."""
    trades = int(pick.get("history_trades", pick.get("forward_trades", 0)) or 0)
    wr = float(pick.get("history_wr", pick.get("forward_wr", 0)) or 0)
    if wr > 1.0:
        wr = wr / 100.0
    avg_pnl = pick.get("history_avg_pnl")
    if avg_pnl is None:
        avg_pnl = pick.get("avg_pnl_pct")
    avg_pnl = float(avg_pnl or 0)
    total_pnl = float(pick.get("history_total_pnl", 0) or 0)
    return {
        "trades": trades,
        "wr": wr,
        "avg_pnl": avg_pnl,
        "total_pnl": total_pnl,
        "pf": float(pick.get("history_pf", pick.get("profit_factor", 0)) or 0),
        "basis": str(pick.get("history_basis", "") or ""),
    }


def _passes_high_cert_history_gate(pick: dict, stats: dict) -> tuple[bool, str]:
    """Require a minimum consistent history before allowing live copy picks."""
    embedded = _embedded_copy_track_record(pick)
    perf_closed = int(stats.get("closed_picks", 0) or 0)
    perf_wr = float(stats.get("win_rate", 0) or 0)
    perf_pf = float(stats.get("profit_factor", 0) or 0)

    # Choose the stronger evidence source between embedded history and local perf file.
    closed = max(perf_closed, embedded["trades"])
    wr = embedded["wr"] if embedded["trades"] >= perf_closed else perf_wr
    pf = embedded["pf"] if embedded["trades"] >= perf_closed and embedded["pf"] > 0 else perf_pf

    if closed < MIN_HISTORY_TRADES_HIGH_CERT:
        return False, f"insufficient history (trades={closed})"
    if wr < MIN_HISTORY_WR_HIGH_CERT:
        return False, f"weak history wr={wr:.0%}"
    if pf > 0 and pf < MIN_HISTORY_PF_HIGH_CERT:
        return False, f"weak history pf={pf:.2f}"
    return True, f"history gate passed (trades={closed}, wr={wr:.0%}, pf={pf:.2f})"


def _qualify_copy_pick(pick: dict, strategy_perf: dict) -> tuple[bool, str]:
    """Return (allowed, reason) for a raw copy-trader pick."""
    strategy = str(pick.get("strategy", "") or "")
    strategy_l = strategy.lower()
    source_system = str(pick.get("source_system", "") or "").lower()

    if strategy in BLACKLISTED_STRATEGIES or strategy_l in BLACKLISTED_STRATEGIES:
        return False, "blacklisted strategy"
    if any(tag in strategy_l for tag in BLOCKED_EXCHANGE_TAGS) or any(tag in source_system for tag in BLOCKED_EXCHANGE_TAGS):
        return False, "blocked exchange/source"

    stats = strategy_perf.get(strategy, {})
    closed = int(stats.get("closed_picks", 0) or 0)
    wr = float(stats.get("win_rate", 0) or 0)
    pf = float(stats.get("profit_factor", 0) or 0)
    avg_pnl = _avg_pnl_pct(stats)

    if strategy in PROVEN_TRADERS:
        ok_hist, hist_reason = _passes_high_cert_history_gate(pick, stats)
        if not ok_hist:
            return False, f"proven trader blocked by history gate: {hist_reason}"
        return True, f"proven trader ({hist_reason})"

    if strategy_l.startswith("copy_hl_"):
        ok_hist, hist_reason = _passes_high_cert_history_gate(pick, stats)
        if not ok_hist:
            return False, f"hyperliquid history gate failed: {hist_reason}"
        if closed >= MIN_VERIFIED_CLOSED_TRADES and wr >= MIN_VERIFIED_WIN_RATE and avg_pnl > 0 and (pf == 0 or pf <= MAX_ALLOWED_COPY_PF):
            return True, f"verified hyperliquid trader ({hist_reason})"
        return False, f"hyperliquid trader unverified (closed={closed}, wr={wr:.0%}, pf={pf:.2f})"

    if strategy_l.startswith("clone_hl_"):
        return False, "clone source blocked until independently verified"

    if strategy_l.startswith("copy_pm_"):
        embedded = _embedded_copy_track_record(pick)
        eff_closed = max(closed, embedded["trades"])
        eff_wr = embedded["wr"] if embedded["trades"] >= closed else wr
        eff_avg_pnl = embedded["avg_pnl"] if embedded["trades"] >= closed else avg_pnl
        eff_total_pnl = embedded["total_pnl"]
        if (
            eff_closed >= 5
            and eff_wr >= 0.60
            and (embedded.get("pf", 0) == 0 or embedded.get("pf", 0) >= 1.10)
            and (eff_avg_pnl > 0 or eff_total_pnl > 0)
            and embedded["basis"] == "polymarket_closed_positions"
        ):
            return True, (
                f"verified Polymarket wallet (crypto closes={eff_closed}, "
                f"wr={eff_wr:.0%}, basis={embedded['basis']})"
            )
        return False, (
            f"polymarket wallet unverified (closes={eff_closed}, "
            f"wr={eff_wr:.0%}, basis={embedded['basis'] or 'missing'})"
        )

    return False, "non-vetted copy source"


def _widen_whale_tp_sl(enriched: dict) -> None:
    """Give proven whales more room instead of forcing retail-tight stops."""
    strategy = str(enriched.get("strategy", "") or "")
    if strategy not in PROVEN_TRADERS:
        return

    entry = float(enriched.get("entry_price") or 0)
    tp = float(enriched.get("take_profit") or 0)
    sl = float(enriched.get("stop_loss") or 0)
    if entry <= 0 or tp <= 0 or sl <= 0:
        return

    direction = str(enriched.get("direction", "") or "").upper()
    widened = False
    if direction == "LONG":
        tp_pct = (tp - entry) / entry
        sl_pct = (entry - sl) / entry
        if tp_pct < 0.08:
            enriched["take_profit"] = round(entry * 1.08, 8)
            widened = True
        if sl_pct < 0.04:
            enriched["stop_loss"] = round(entry * 0.96, 8)
            widened = True
    elif direction == "SHORT":
        tp_pct = (entry - tp) / entry
        sl_pct = (sl - entry) / entry
        if tp_pct < 0.08:
            enriched["take_profit"] = round(entry * 0.92, 8)
            widened = True
        if sl_pct < 0.04:
            enriched["stop_loss"] = round(entry * 1.04, 8)
            widened = True

    if widened:
        enriched["_widened_whale_tp_sl"] = "8/4"


def _enrich_pick(pick: dict, strategy_meta: Optional[dict], verified: bool, reason: str) -> dict:
    """Return a new pick dict in alpha_engine active_picks format."""
    direction = _normalize_direction(pick)
    confidence = float(pick.get("confidence", 0) or 0)
    strategy = pick.get("strategy", "")

    enriched = {
        "id": pick.get("id", ""),
        "strategy": strategy,
        "symbol": pick.get("symbol", ""),
        "category": pick.get("category", "crypto"),
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": pick.get("entry_price"),
        "entry_date": pick.get("entry_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "take_profit": pick.get("take_profit"),
        "stop_loss": pick.get("stop_loss"),
        "confidence": confidence,
        "ml_score": pick.get("ml_score"),
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "status": pick.get("status", "OPEN"),
        "hold_days": None,
        "allocation": float(pick.get("allocation", 150) or 150),
        "position_sizing": "copy_trader",
        "risk_per_trade_pct": float(pick.get("risk_per_trade_pct", 0.02) or 0.02),
        # Proven traders should be allowed to compete for execution; everyone
        # else stays paper-only until their history clears the bridge.
        "forward_test_only": not verified,
        "copy_trader_verified": verified,
        "copy_trader_bridge_reason": reason,
        "source": "copy_trader_intel_bridge",
        "source_system": pick.get("source_system", "copy_trader_intel"),
        "elite_score": pick.get("elite_score", int(confidence * 100)),
        "elite_grade": pick.get("elite_grade", ""),
        "consensus_count": pick.get("consensus_count", 1),
        "consensus_sources": pick.get("consensus_sources", []),
        "cross_exchange_consensus": pick.get("cross_exchange_consensus", False),
        "trader_address": pick.get("trader_address", ""),
        "trader_pnl": pick.get("trader_pnl"),
        "forward_trades": pick.get("forward_trades"),
        "forward_wr": pick.get("forward_wr"),
        "forward_validated": pick.get("forward_validated", False),
        "reason": pick.get("reason", ""),
        "max_safe_leverage": pick.get("max_safe_leverage", 1.0),
        "timestamp": pick.get("timestamp", datetime.now(timezone.utc).isoformat()),
    }

    if strategy_meta:
        rules = strategy_meta.get("rules", {})
        perf = strategy_meta.get("expected_performance", {})
        enriched["strategy_meta"] = {
            "strategy_id": strategy_meta.get("strategy_id", ""),
            "description": strategy_meta.get("description", ""),
            "tp_pct": rules.get("tp_pct"),
            "sl_pct": rules.get("sl_pct"),
            "max_leverage": rules.get("max_leverage"),
            "typical_hold_hours": rules.get("typical_hold_hours"),
            "expected_wr": perf.get("win_rate"),
            "profit_factor": perf.get("profit_factor"),
        }

    _widen_whale_tp_sl(enriched)
    return enriched


def get_copy_trader_picks() -> List[dict]:
    """
    Return vetted copy-trader picks from the copy_trader_intel pipeline.

    Filters:
      - OPEN only
      - crypto-only symbols
      - valid entry/TP/SL
      - directional confidence floor
      - score proxy >= 55
      - no Binance sentiment / Bitget / unverified clone sources
      - only proven or verified Hyperliquid traders pass through
    """
    raw_picks = _load_json(COPY_INTEL_PICKS_FILE)
    if not raw_picks or not isinstance(raw_picks, list):
        print("  [COPY TRADER BRIDGE] No picks found in copy_trader_intel/data/active_picks.json")
        return []

    extracted = _load_json(EXTRACTED_STRATEGIES_FILE) or {}
    strategy_perf = _load_json(STRATEGY_PERFORMANCE_FILE) or {}
    strat_lookup = _build_strategy_lookup(extracted)

    filtered: List[dict] = []
    skipped = {
        "low_conf_long": 0,
        "low_conf_short": 0,
        "incomplete": 0,
        "non_crypto": 0,
        "low_score": 0,
        "blocked_source": 0,
    }

    for pick in raw_picks:
        if not isinstance(pick, dict):
            continue

        if str(pick.get("status", "")).upper() != "OPEN":
            continue

        entry = float(pick.get("entry_price") or 0)
        tp = float(pick.get("take_profit") or 0)
        sl = float(pick.get("stop_loss") or 0)
        if entry <= 0 or tp <= 0 or sl <= 0:
            skipped["incomplete"] += 1
            continue

        symbol = str(pick.get("symbol", "") or "").upper()
        category = str(pick.get("category", "crypto") or "crypto").lower()
        if category != "crypto" or not CRYPTO_SYMBOL_REGEX.match(symbol):
            skipped["non_crypto"] += 1
            continue

        direction = _normalize_direction(pick)
        confidence = float(pick.get("confidence", 0) or 0)
        if direction == "LONG" and confidence < LONG_MIN_CONFIDENCE:
            skipped["low_conf_long"] += 1
            continue
        if direction == "SHORT" and confidence < SHORT_MIN_CONFIDENCE:
            skipped["low_conf_short"] += 1
            continue
        if direction not in ("LONG", "SHORT"):
            skipped["incomplete"] += 1
            continue

        if _copy_score(pick, confidence) < FINAL_SCORE_THRESHOLD:
            skipped["low_score"] += 1
            continue

        
        if not _is_fresh_position(pick):
            skipped["stale_position"] = skipped.get("stale_position", 0) + 1
            continue

        allowed, reason = _qualify_copy_pick(pick, strategy_perf)
        if not allowed:
            skipped["blocked_source"] += 1
            continue

        strategy_name = pick.get("strategy", "")
        strat_meta = strat_lookup.get(strategy_name)
        if not strat_meta:
            for prefix in ("copy_hl_", "copy_hl_lb_", "copy_okx_", "copy_bybit_", "copy_bitget_", "copy_bingx_"):
                if strategy_name.startswith(prefix):
                    strat_meta = strat_lookup.get(strategy_name[len(prefix):])
                    if strat_meta:
                        break

        verified = strategy_name in PROVEN_TRADERS
        enriched = _enrich_pick(pick, strat_meta, verified=verified, reason=reason)
        filtered.append(enriched)

    print(
        f"  [COPY TRADER BRIDGE] {len(filtered)} vetted picks "
        f"(from {len(raw_picks)} total | "
        f"blocked: {skipped['blocked_source']} source, {skipped['low_score']} low-score, "
        f"{skipped['low_conf_long']} low-conf LONG, {skipped['low_conf_short']} low-conf SHORT, "
        f"{skipped['non_crypto']} non-crypto, {skipped['incomplete']} incomplete, {skipped.get('stale_position', 0)} stale)"
    )
    return filtered


if __name__ == "__main__":
    picks = get_copy_trader_picks()
    print(f"\nTotal bridged picks: {len(picks)}")
    for p in picks[:10]:
        print(
            f"  {p['symbol']:12s} {p['direction']:5s} "
            f"verified={p['copy_trader_verified']} "
            f"forward_test_only={p['forward_test_only']} "
            f"strategy={p['strategy']}"
        )
