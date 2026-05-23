#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strong Signals Engine -- 7-filter pipeline with scoring and Kelly position sizing.

Wraps around existing smart picks to identify the highest-conviction trades.
Based on STRONG_SIGNALS_BLUEPRINT.md analysis:
  - Regime alignment is the #1 predictor (50 pts)
  - R:R 2.0-2.5 = 73.7% WR (15 pts)
  - Strategy track record doubles weight (20 pts)
  - Confidence 0.60-0.70 = 61% WR sweet spot (8 pts)
  - Stop distance 1.5-3% = optimal (7 pts)

Stdlib only: json, datetime, math, os, urllib.request, logging, pathlib.
"""
from __future__ import annotations

import json
import logging
import math
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_DATA = _DIR / "data"

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("strong_signals")

# Binance 3+ mirror failover (per API failover rule)
_SPOT_URLS = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]
_HDR = {"User-Agent": "AlphaEngine/StrongSignals/1.0"}

# ---------------------------------------------------------------------------
# Regime constants
# ---------------------------------------------------------------------------
_BULL_REGIMES = {"bullish", "leaning_bull", "strong_bull", "bull"}
_BEAR_REGIMES = {"bearish", "leaning_bear", "strong_bear", "bear"}
_NEUTRAL_REGIMES = {"choppy", "ranging", "neutral", "consolidation"}

# ---------------------------------------------------------------------------
# Filter thresholds
# ---------------------------------------------------------------------------
RR_HARD_MIN = 1.2   # Lowered from 1.5 — many good crypto/PM picks have 1.2-1.5 R:R
RR_SWEET_LOW = 1.8
RR_SWEET_HIGH = 2.5

CONF_NOISE_FLOOR = 0.55
CONF_OVERFIT_FLOOR = 0.80
CONF_SWEET_LOW = 0.60
CONF_SWEET_HIGH = 0.70

STOP_SHAKEOUT = 0.01       # 1%
STOP_OPTIMAL_LOW = 0.015   # 1.5%
STOP_OPTIMAL_HIGH = 0.03   # 3%
STOP_WIDE_MAX = 0.04       # 4%

STRAT_MIN_TRADES_HIGH = 10
STRAT_MIN_WR_HIGH = 0.45
STRAT_MIN_TRADES_LOW = 5
STRAT_MIN_WR_LOW = 0.55

# ---------------------------------------------------------------------------
# Correlation / concentration caps (Filter 6)
# ---------------------------------------------------------------------------
CORR_HIGH_THRESHOLD = 0.70
CORR_EXTREME_THRESHOLD = 0.85
MAX_PICKS_SAME_SECTOR_DIR = 2
CORR_SCORE_PENALTY = -10

# Banned strategies (auto-kill list from smart_picks_engine)
BANNED_SYSTEMS = {
    "volume_spike_backfill",
    "winner_pattern_precursor",
    "momentum_catcher",
    "hl_funding_fade",
}


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
def _http_json(url, timeout=8):
    """Fetch JSON from URL with timeout. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers=_HDR)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Regime detection (same pattern as scanner.py / smart_picks_engine.py)
# ---------------------------------------------------------------------------
def _fetch_regime():
    """Detect market regime from BTC 1h candles + Fear & Greed index.

    Returns one of: BULLISH, LEANING_BULL, NEUTRAL, LEANING_BEAR, BEARISH.
    """
    regime = "NEUTRAL"

    # 1) BTC 1h candles from Binance (with mirror failover)
    btc_change_pct = 0.0
    for mirror in _SPOT_URLS:
        data = _http_json(f"{mirror}/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=24")
        if isinstance(data, list) and len(data) >= 12:
            closes = [float(k[4]) for k in data]
            recent_avg = sum(closes[-4:]) / 4
            prior_avg = sum(closes[-12:-4]) / 8
            btc_change_pct = (recent_avg - prior_avg) / prior_avg * 100 if prior_avg else 0
            break

    # 2) Fear & Greed Index
    fear_greed = 50
    fg_data = _http_json("https://api.alternative.me/fng/?limit=1")
    if fg_data and isinstance(fg_data.get("data"), list) and fg_data["data"]:
        try:
            fear_greed = int(fg_data["data"][0]["value"])
        except (ValueError, KeyError):
            pass

    # 3) Combine signals into regime
    # BTC momentum is primary, F&G is secondary confirmation
    if btc_change_pct > 2.0 or (btc_change_pct > 1.0 and fear_greed > 60):
        regime = "BULLISH"
    elif btc_change_pct > 0.5 or fear_greed > 55:
        regime = "LEANING_BULL"
    elif btc_change_pct < -2.0 or (btc_change_pct < -1.0 and fear_greed < 40):
        regime = "BEARISH"
    elif btc_change_pct < -0.5 or fear_greed < 45:
        regime = "LEANING_BEAR"
    else:
        regime = "NEUTRAL"

    log.info("Regime detected: %s (BTC 4h/8h: %+.2f%%, F&G: %d)", regime, btc_change_pct, fear_greed)
    return regime


# ---------------------------------------------------------------------------
# Safe field extractors
# ---------------------------------------------------------------------------
def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pick_direction(pick):
    """Normalized direction: LONG or SHORT."""
    d = (pick.get("direction") or pick.get("signal_type") or "BUY").upper()
    return "SHORT" if d in ("SELL", "SHORT") else "LONG"


def _pick_rr(pick):
    """Compute risk:reward ratio from entry/tp/sl."""
    entry = _as_float(pick.get("entry_price"))
    tp = _as_float(pick.get("take_profit"))
    sl = _as_float(pick.get("stop_loss"))
    if entry <= 0 or tp <= 0 or sl <= 0:
        return 0.0
    direction = _pick_direction(pick)
    if direction == "LONG":
        reward = tp - entry
        risk = entry - sl
    else:
        reward = entry - tp
        risk = sl - entry
    if risk <= 0:
        return 0.0
    return round(reward / risk, 2)


def _pick_stop_distance(pick):
    """Stop distance as fraction of entry price."""
    entry = _as_float(pick.get("entry_price"))
    sl = _as_float(pick.get("stop_loss"))
    if entry <= 0 or sl <= 0:
        return 0.0
    return abs(entry - sl) / entry


def _pick_confidence(pick):
    """Confidence normalized to 0-1."""
    conf = _as_float(pick.get("confidence"))
    if conf > 1.0:
        conf = conf / 100.0
    return conf


# ---------------------------------------------------------------------------
# Strategy stats from closed picks
# ---------------------------------------------------------------------------
def compute_strategy_stats(closed_picks):
    """Compute per-strategy win rate, avg win, avg loss, closed count from closed_picks.

    Returns: {strategy_name: {total, wins, losses, wr, avg_win, avg_loss}}
    """
    if not closed_picks:
        return {}
    stats = {}
    for pick in closed_picks:
        strat = pick.get("strategy", "")
        if not strat:
            continue
        status = (pick.get("status") or "").upper()
        if status not in ("WON", "LOST"):
            continue
        if strat not in stats:
            stats[strat] = {
                "total": 0, "wins": 0, "losses": 0,
                "wr": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
                "_win_pnls": [], "_loss_pnls": [],
            }
        s = stats[strat]
        s["total"] += 1
        pnl = _as_float(pick.get("pnl_pct"))
        if status == "WON":
            s["wins"] += 1
            s["_win_pnls"].append(abs(pnl))
        else:
            s["losses"] += 1
            s["_loss_pnls"].append(abs(pnl))

    # Compute derived fields
    for s in stats.values():
        s["wr"] = s["wins"] / s["total"] if s["total"] > 0 else 0.0
        s["avg_win"] = (sum(s["_win_pnls"]) / len(s["_win_pnls"])) if s["_win_pnls"] else 0.0
        s["avg_loss"] = (sum(s["_loss_pnls"]) / len(s["_loss_pnls"])) if s["_loss_pnls"] else 0.0
        # Clean up internal fields
        del s["_win_pnls"]
        del s["_loss_pnls"]

    return stats


# ---------------------------------------------------------------------------
# 5-Filter Pipeline
# ---------------------------------------------------------------------------
def _filter1_regime(pick, regime):
    """Filter 1: Regime Alignment (Soft Gate with heavy penalty).
    LONG in BULLISH/LEANING_BULL = full score.
    SHORT in BEARISH/LEANING_BEAR = full score.
    NEUTRAL regime: both allowed, half-scored (-25 pts).
    Contra-regime: allowed but heavily penalized (-40 pts) so the STRONG
    column still shows data during prolonged bear/bull regimes instead of
    being permanently empty.
    """
    direction = _pick_direction(pick)
    r = regime.lower()

    if direction == "LONG":
        if r in _BULL_REGIMES:
            return True, "LONG aligned with bullish regime", 0
        if r in _NEUTRAL_REGIMES:
            return True, "LONG in neutral (half-scored)", -25  # half of 50 pts
        # Contra-regime: allow with heavy penalty instead of hard-block
        return True, f"LONG contra-regime in {regime} (heavy penalty)", -40
    else:
        if r in _BEAR_REGIMES:
            return True, "SHORT aligned with bearish regime", 0
        if r in _NEUTRAL_REGIMES:
            return True, "SHORT in neutral (half-scored)", -25
        # Contra-regime: allow with heavy penalty instead of hard-block
        return True, f"SHORT contra-regime in {regime} (heavy penalty)", -40


def _filter2_rr(pick):
    """Filter 2: R:R >= 1.2 (Hard Gate).
    Block ANY pick with R:R < 1.2.
    """
    rr = _pick_rr(pick)
    if rr <= 0:
        return False, "R:R not computable (missing TP/SL)", 0
    if rr < RR_HARD_MIN:
        return False, f"R:R {rr:.2f} < {RR_HARD_MIN} (blocked)", 0
    return True, f"R:R {rr:.2f} passed", 0


def _filter3_strategy(pick, strategy_stats):
    """Filter 3: Strategy Validation (Hard Gate).
    Min 10 closed trades at >= 45% WR, or min 5 at >= 55% WR.
    Unvalidated strategies (< 5 trades) get a pass with penalty.
    """
    strat = pick.get("strategy", "")
    s = strategy_stats.get(strat)

    if not s or s["total"] == 0:
        # Unvalidated -- pass with penalty (as per spec)
        return True, f"strategy '{strat}' unvalidated (0 trades, penalty)", -10

    total, wr = s["total"], s["wr"]

    # Path 1: 10+ trades at >= 45% WR
    if total >= STRAT_MIN_TRADES_HIGH and wr >= STRAT_MIN_WR_HIGH:
        return True, f"validated: {total} trades, {wr:.0%} WR", 0

    # Path 2: 5+ trades at >= 55% WR
    if total >= STRAT_MIN_TRADES_LOW and wr >= STRAT_MIN_WR_LOW:
        return True, f"early-validated: {total} trades, {wr:.0%} WR", 0

    # Has trades but fails thresholds
    if total >= STRAT_MIN_TRADES_LOW:
        return False, f"strategy failing: {total} trades, {wr:.0%} WR", 0

    # < 5 trades -- unvalidated, pass with penalty
    return True, f"strategy unproven: {total} trades (penalty)", -5


def _filter4_confidence(pick):
    """Filter 4: Confidence 0.55-0.80 (Hard Gate).
    Below 0.55 = noise, blocked.
    Above 0.80 = overfit flag (allow but penalize score).
    """
    conf = _pick_confidence(pick)

    if conf < CONF_NOISE_FLOOR:
        return False, f"confidence {conf:.2f} < {CONF_NOISE_FLOOR} (noise)", 0

    if conf > CONF_OVERFIT_FLOOR:
        return True, f"confidence {conf:.2f} > 0.80 (overfit penalty)", -4

    return True, f"confidence {conf:.2f} in range", 0


def _filter5_stop_distance(pick):
    """Filter 5: Stop Distance 1.5-4% (Soft Gate).
    Never blocks. Penalizes or rewards.
    """
    sd = _pick_stop_distance(pick)

    if sd <= 0:
        return True, "stop distance not computable", 0

    if sd < STOP_SHAKEOUT:
        return True, f"stop {sd:.1%} < 1% (shakeout risk)", -3

    if STOP_OPTIMAL_LOW <= sd <= STOP_OPTIMAL_HIGH:
        return True, f"stop {sd:.1%} optimal (1.5-3%)", 3

    if sd > STOP_WIDE_MAX:
        return True, f"stop {sd:.1%} > 4% (poor risk mgmt)", -2

    # 1-1.5% or 3-4% -- acceptable, no bonus
    return True, f"stop {sd:.1%} acceptable", 0


# Volume-percentile liquidity thresholds
VOL_RATIO_VERY_LOW = 0.3    # below 30% of 20-period avg = dangerously illiquid
VOL_RATIO_LOW = 0.5          # below 50% of 20-period avg = low liquidity
VOL_RATIO_HIGH = 2.0         # above 200% = high volume confirmation


def _filter7_volume_liquidity(pick):
    """Filter 7: Volume Liquidity Gate (Hard + Soft Gate).

    Low volume = unreliable fills = slippage = losses.
    volume_ratio is current volume / 20-period average volume.
      < 0.3: very low liquidity -- HARD BLOCK (slippage too dangerous)
      < 0.5: low liquidity -- score penalty (-15 pts)
      > 2.0: high volume spike -- score bonus (+5 pts)
      missing: skip (don't block, no penalty)
    Also checks extra.vol_ratio as fallback field.
    Note: volume_24h / volume_usd fields are not currently populated on picks.
    """
    vr = pick.get("volume_ratio") or (pick.get("extra", {}) or {}).get("vol_ratio")
    if vr is None:
        return True, "volume_ratio not available (skip)", 0
    try:
        vr = float(vr)
    except (TypeError, ValueError):
        return True, "volume_ratio not numeric (skip)", 0

    if vr < VOL_RATIO_VERY_LOW:
        return False, f"volume_ratio {vr:.2f} < {VOL_RATIO_VERY_LOW} (BLOCKED: very low liquidity)", 0
    if vr < VOL_RATIO_LOW:
        return True, f"volume_ratio {vr:.2f} < {VOL_RATIO_LOW} (low liquidity penalty)", -15
    if vr > VOL_RATIO_HIGH:
        return True, f"volume_ratio {vr:.2f} > {VOL_RATIO_HIGH} (high volume spike bonus)", 5
    return True, f"volume_ratio {vr:.2f} normal", 0


def _load_correlation_matrix():
    """Load correlation matrix from data/correlation_report.json.

    Returns dict-of-dicts: {symbol: {symbol: corr_float, ...}, ...}.
    Returns empty dict if file is missing or unreadable.
    """
    path = _DATA / "correlation_report.json"
    if not path.exists():
        log.info("correlation_report.json not found -- skipping correlation filter")
        return {}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        matrix = report.get("correlation_matrix", {})
        if isinstance(matrix, dict):
            return matrix
    except Exception as e:
        log.warning("Failed to load correlation_report.json: %s", e)
    return {}


def _filter6_correlation_concentration(candidates, correlation_matrix):
    """Filter 6: Correlation & Concentration Caps.

    Iterates candidates sorted by strong_score descending.  For each candidate:
      - Duplicate symbol already accepted -> HARD BLOCK
      - Extreme correlation (>0.85) with any accepted pick -> HARD BLOCK
      - High correlation (>0.70) with any accepted pick -> PASS with penalty & flag
      - More than MAX_PICKS_SAME_SECTOR_DIR in same sector+direction -> penalty

    Mutates candidate dicts in-place (adds flags, adjusts strong_score).
    Returns (accepted, blocked_count).
    """
    # Sort by score descending so best picks get priority
    candidates.sort(key=lambda c: c.get("strong_score", 0), reverse=True)

    accepted = []
    blocked_count = 0
    # Track sector+direction counts among accepted picks
    sector_dir_counts = {}  # (sector, direction) -> count

    for pick in candidates:
        symbol = (pick.get("symbol") or "").upper()
        direction = _pick_direction(pick)
        sector = (pick.get("category") or pick.get("asset_class") or "crypto").lower()
        sector_dir_key = (sector, direction)

        # --- Duplicate symbol check ---
        accepted_symbols = {(p.get("symbol") or "").upper() for p in accepted}
        if symbol in accepted_symbols:
            pick["_corr_blocked"] = True
            pick["_corr_reason"] = f"duplicate symbol {symbol}"
            blocked_count += 1
            continue

        # --- Extreme correlation check ---
        extreme_blocked = False
        high_corr_flag = False
        if correlation_matrix and symbol in correlation_matrix:
            sym_corrs = correlation_matrix[symbol]
            for acc in accepted:
                acc_sym = (acc.get("symbol") or "").upper()
                corr_val = abs(_as_float(sym_corrs.get(acc_sym, 0.0)))
                if corr_val > CORR_EXTREME_THRESHOLD:
                    pick["_corr_blocked"] = True
                    pick["_corr_reason"] = (
                        f"extreme correlation {corr_val:.2f} with {acc_sym}"
                    )
                    blocked_count += 1
                    extreme_blocked = True
                    break
                if corr_val > CORR_HIGH_THRESHOLD:
                    high_corr_flag = True

        if extreme_blocked:
            continue

        # --- High correlation penalty ---
        if high_corr_flag:
            pick["correlated_risk"] = True
            pick["strong_score"] = max(0, pick.get("strong_score", 0) + CORR_SCORE_PENALTY)

        # --- Sector + direction concentration ---
        count = sector_dir_counts.get(sector_dir_key, 0)
        if count >= MAX_PICKS_SAME_SECTOR_DIR:
            pick["sector_overflow"] = True
            pick["strong_score"] = max(0, pick.get("strong_score", 0) + CORR_SCORE_PENALTY)

        # Accept this pick
        accepted.append(pick)
        sector_dir_counts[sector_dir_key] = count + 1

    return accepted, blocked_count


def filter_strong_signals(picks, regime, closed_picks):
    """7-filter pipeline. Returns only picks that pass ALL hard gates.

    Filter 1: Regime Alignment (Hard Gate)
      - LONG only in BULLISH/LEANING_BULL
      - SHORT only in BEARISH/LEANING_BEAR
      - NEUTRAL regime: both allowed but half-scored

    Filter 2: R:R >= 1.5 (Hard Gate)
      - Block ANY pick with R:R < 1.5
      - Compute R:R from entry/tp/sl

    Filter 3: Strategy Validation (Hard Gate)
      - Compute WR per strategy from closed_picks
      - Min 10 closed trades at >= 45% WR
      - Or min 5 trades at >= 55% WR
      - Unvalidated strategies (< 5 trades) get a pass with penalty

    Filter 4: Confidence 0.55-0.80 (Hard Gate)
      - Below 0.55 = noise, blocked
      - Above 0.80 = overfit flag (allow but penalize score)

    Filter 5: Stop Distance 1.5-4% (Soft Gate)
      - Optimal: 1.5-3% (bonus)
      - < 1% = shakeout risk (penalize)
      - > 4% = poor risk management (penalize)

    Filter 6: Correlation & Concentration (Hard/Soft Gate)
      - Duplicate symbol -> HARD BLOCK
      - Extreme correlation >0.85 with accepted -> HARD BLOCK
      - High correlation >0.70 -> pass with penalty & correlated_risk flag
      - Max 2 same sector+direction -> penalize overflow

    Filter 7: Volume Liquidity Gate (Hard + Soft)
      - volume_ratio < 0.3: HARD BLOCK (slippage too dangerous)
      - volume_ratio < 0.5: -15 score penalty
      - volume_ratio > 2.0: +5 score bonus
      - Missing volume data: skip (no block, no penalty)
    """
    strategy_stats = compute_strategy_stats(closed_picks)
    correlation_matrix = _load_correlation_matrix()

    filter_counts = {
        "input": len(picks),
        "regime_blocked": 0,
        "regime_penalized": 0,
        "rr_blocked": 0,
        "strategy_blocked": 0,
        "confidence_blocked": 0,
        "banned_blocked": 0,
        "volume_blocked": 0,
        "volume_penalized": 0,
        "correlation_blocked": 0,
        "passed": 0,
    }

    survivors = []

    for pick in picks:
        # Skip banned systems
        strat = (pick.get("strategy") or "").lower().strip()
        if strat in BANNED_SYSTEMS:
            filter_counts["banned_blocked"] += 1
            continue

        # Skip non-active picks
        status = (pick.get("status") or "").upper()
        if status and status not in ("OPEN", "ACTIVE", "PENDING", "LIVE"):
            continue

        filters_passed = []
        blocked = False
        score_adj = 0  # cumulative score adjustment from filter penalties

        # Filter 1: Regime (soft gate -- penalizes but never blocks)
        passed, reason, adj = _filter1_regime(pick, regime)
        filters_passed.append({"filter": "regime_alignment", "passed": passed, "reason": reason})
        score_adj += adj
        if adj <= -30:
            filter_counts["regime_penalized"] += 1  # track contra-regime picks
        if not passed:
            filter_counts["regime_blocked"] += 1
            blocked = True

        # Filter 2: R:R
        if not blocked:
            passed, reason, adj2 = _filter2_rr(pick)
            filters_passed.append({"filter": "risk_reward", "passed": passed, "reason": reason})
            score_adj += adj2
            if not passed:
                filter_counts["rr_blocked"] += 1
                blocked = True

        # Filter 3: Strategy validation
        if not blocked:
            passed, reason, adj3 = _filter3_strategy(pick, strategy_stats)
            filters_passed.append({"filter": "strategy_validation", "passed": passed, "reason": reason})
            score_adj += adj3
            if not passed:
                filter_counts["strategy_blocked"] += 1
                blocked = True

        # Filter 4: Confidence
        if not blocked:
            passed, reason, adj4 = _filter4_confidence(pick)
            filters_passed.append({"filter": "confidence", "passed": passed, "reason": reason})
            score_adj += adj4
            if not passed:
                filter_counts["confidence_blocked"] += 1
                blocked = True

        # Filter 5: Stop distance (soft gate -- never blocks)
        if not blocked:
            passed, reason, adj5 = _filter5_stop_distance(pick)
            filters_passed.append({"filter": "stop_distance", "passed": passed, "reason": reason})
            score_adj += adj5

        # Filter 7: Volume liquidity (hard block < 0.3, penalty < 0.5, bonus > 2.0)
        if not blocked:
            passed, reason, adj7 = _filter7_volume_liquidity(pick)
            filters_passed.append({"filter": "volume_liquidity", "passed": passed, "reason": reason})
            score_adj += adj7
            if not passed:
                filter_counts["volume_blocked"] += 1
                blocked = True
            elif adj7 < 0:
                filter_counts["volume_penalized"] += 1

        if not blocked:
            pick["_score_adj"] = score_adj  # carry forward for scoring step
            filter_counts["passed"] += 1
            survivors.append((pick, filters_passed, strategy_stats))

    log.info(
        "7-filter: %d input -> %d passed | blocked: regime=%d rr=%d strat=%d conf=%d banned=%d vol=%d | vol_penalized=%d",
        filter_counts["input"], filter_counts["passed"],
        filter_counts["regime_blocked"], filter_counts["rr_blocked"],
        filter_counts["strategy_blocked"], filter_counts["confidence_blocked"],
        filter_counts["banned_blocked"], filter_counts["volume_blocked"],
        filter_counts["volume_penalized"],
    )

    # --- Filter 6: Correlation & Concentration (post-scoring pass) ---
    # We need scored picks first so filter6 can sort by score; score them now.
    pre_f6_picks = []
    for pick, filter_details, _ in survivors:
        strong_score = score_strong_signal(pick, regime, strategy_stats)
        # Apply cumulative filter penalty/bonus (regime contra-penalty, etc.)
        score_adj = pick.pop("_score_adj", 0)
        strong_score = max(0, strong_score + score_adj)
        pick["strong_score"] = strong_score
        pick["_filter_details_pre6"] = filter_details
        pre_f6_picks.append(pick)

    accepted_picks, corr_blocked = _filter6_correlation_concentration(
        pre_f6_picks, correlation_matrix
    )
    filter_counts["correlation_blocked"] = corr_blocked
    filter_counts["passed"] = len(accepted_picks)

    log.info(
        "6-filter: %d after F1-F5 -> %d after F6 (corr_blocked=%d)",
        len(pre_f6_picks), len(accepted_picks), corr_blocked,
    )

    # Rebuild survivors list in the expected format
    final_survivors = []
    for pick in accepted_picks:
        fd = pick.pop("_filter_details_pre6", [])
        fd.append({
            "filter": "correlation_concentration",
            "passed": True,
            "reason": pick.get("_corr_reason", "passed correlation check"),
        })
        final_survivors.append((pick, fd, strategy_stats))

    return final_survivors, filter_counts, strategy_stats


# ---------------------------------------------------------------------------
# Scoring (0-100)
# ---------------------------------------------------------------------------
def score_strong_signal(pick, regime, strategy_stats):
    """Score 0-100 for picks that passed all hard gates.

    Components:
    - Regime match: 50 pts max (up from 40)
    - R:R quality: 15 pts max (2.0-2.5 = max)
    - Strategy track record: 20 pts max (WR * closed_count weighted)
    - Confidence sweet spot: 8 pts max (0.60-0.70 = max)
    - Stop distance: 7 pts max (1.5-3% = max)
    - Volume liquidity: -15 to +5 pts (hard block <0.3, penalty <0.5, bonus >2.0)
    """
    score = 0
    direction = _pick_direction(pick)
    r = regime.lower()

    # 1. Regime match (50 pts max)
    if direction == "LONG" and r in _BULL_REGIMES:
        score += 50
    elif direction == "SHORT" and r in _BEAR_REGIMES:
        score += 50
    elif r in _NEUTRAL_REGIMES:
        score += 25  # half
    # else: 0 (shouldn't reach here if filter passed, but safe)

    # 2. R:R quality (15 pts max)
    rr = _pick_rr(pick)
    if RR_SWEET_LOW <= rr <= RR_SWEET_HIGH:
        score += 15  # sweet spot
    elif rr >= RR_HARD_MIN and rr < RR_SWEET_LOW:
        # Linear scale: 1.5 -> 8 pts, approaching 2.0 -> 14 pts
        score += 8 + int((rr - RR_HARD_MIN) / (RR_SWEET_LOW - RR_HARD_MIN) * 6)
    elif rr > RR_SWEET_HIGH:
        # Diminishing: TP may be unreachable
        score += 10
    # rr < 1.5 shouldn't get here (filtered), but gives 0

    # 3. Strategy track record (20 pts max)
    strat = pick.get("strategy", "")
    s = strategy_stats.get(strat)
    if s and s["total"] > 0:
        wr = s["wr"]
        total = s["total"]
        # WR component: 0-12 pts
        if wr >= 0.60:
            wr_pts = 12
        elif wr >= 0.55:
            wr_pts = 10
        elif wr >= 0.50:
            wr_pts = 8
        elif wr >= 0.45:
            wr_pts = 5
        else:
            wr_pts = 0
        # Volume component: 0-8 pts (more trades = more confidence in WR)
        if total >= 50:
            vol_pts = 8
        elif total >= 20:
            vol_pts = 6
        elif total >= 10:
            vol_pts = 4
        elif total >= 5:
            vol_pts = 2
        else:
            vol_pts = 0
        score += wr_pts + vol_pts
    else:
        # Unvalidated: baseline 5 pts (not penalized to 0)
        score += 5

    # 4. Confidence sweet spot (8 pts max)
    conf = _pick_confidence(pick)
    if CONF_SWEET_LOW <= conf <= CONF_SWEET_HIGH:
        score += 8  # 0.60-0.70 = 61% WR best
    elif 0.70 < conf <= 0.80:
        score += 6
    elif 0.55 <= conf < 0.60:
        score += 4
    elif conf > 0.80:
        score += 2  # overconfidence penalty
    # < 0.55 shouldn't get here (filtered), 0 pts

    # 5. Stop distance (7 pts max)
    sd = _pick_stop_distance(pick)
    if sd <= 0:
        score += 3  # can't compute, neutral
    elif STOP_OPTIMAL_LOW <= sd <= STOP_OPTIMAL_HIGH:
        score += 7  # 1.5-3% optimal
    elif STOP_SHAKEOUT < sd < STOP_OPTIMAL_LOW:
        score += 4  # tight but ok
    elif STOP_OPTIMAL_HIGH < sd <= STOP_WIDE_MAX:
        score += 3  # slightly wide
    elif sd <= STOP_SHAKEOUT:
        score += 1  # shakeout risk
    else:
        score += 1  # > 4% poor risk mgmt

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Position sizing: Half-Kelly with volatility scaling
# ---------------------------------------------------------------------------
def size_position_kelly(pick, strategy_stats, portfolio_value=10000):
    """Half-Kelly with volatility scaling and correlation penalty.

    Returns: dict with dollar_amount, position_pct, kelly_fraction.
    """
    strat = pick.get("strategy", "")
    s = strategy_stats.get(strat)

    # Default Kelly fraction for unvalidated strategies
    if not s or s["total"] < 5:
        return {
            "dollar_amount": round(portfolio_value * 0.02, 2),
            "position_pct": 2.0,
            "kelly_fraction": 0.0,
        }

    wr = s["wr"]
    avg_win = s["avg_win"] if s["avg_win"] > 0 else 3.0   # default 3% if missing
    avg_loss = s["avg_loss"] if s["avg_loss"] > 0 else 2.0  # default 2% if missing

    # Kelly % = (W * avg_win - L * avg_loss) / avg_win
    # where W = win rate, L = 1 - W
    edge = (wr * avg_win) - ((1 - wr) * avg_loss)
    kelly_pct = edge / avg_win if avg_win > 0 else 0.0

    # Half-Kelly (conservative)
    half_kelly = kelly_pct * 0.5

    # Volatility scaling: use stop distance as proxy for volatility
    # Target vol ~2% stop = 1.0 scalar
    sd = _pick_stop_distance(pick)
    target_sd = 0.02
    if sd > 0:
        vol_scalar = min(target_sd / sd, 2.0)  # cap at 2x
    else:
        vol_scalar = 1.0

    # Simple correlation penalty: crypto-to-crypto = correlated
    # (Full correlation matrix would need live data; proxy with asset class)
    category = (pick.get("category") or pick.get("asset_class") or "").lower()
    if category in ("crypto", "meme"):
        corr_scalar = 0.75  # crypto is correlated to BTC
    else:
        corr_scalar = 1.0

    # Final position size as fraction of portfolio
    position_frac = half_kelly * vol_scalar * corr_scalar

    # Hard caps: 1% min, 10% max
    position_frac = max(0.01, min(0.10, position_frac))

    # If Kelly is negative (negative edge), use minimum
    if kelly_pct <= 0:
        position_frac = 0.01

    dollar_amount = round(portfolio_value * position_frac, 2)

    return {
        "dollar_amount": dollar_amount,
        "position_pct": round(position_frac * 100, 2),
        "kelly_fraction": round(half_kelly, 4),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def generate_strong_picks(active_picks_path=None, closed_picks_path=None, regime=None):
    """Main entry point. Loads picks, runs 5-filter pipeline, scores survivors,
    returns sorted list with position sizes. Also saves to data/strong_signals.json
    with metadata: filter_stats (how many blocked at each stage), regime, timestamp.
    """
    now = datetime.now(timezone.utc)

    # Resolve paths
    if active_picks_path is None:
        active_picks_path = _DATA / "active_picks.json"
    else:
        active_picks_path = Path(active_picks_path)

    if closed_picks_path is None:
        closed_picks_path = _DATA / "closed_picks.json"
    else:
        closed_picks_path = Path(closed_picks_path)

    # Load active picks
    if not active_picks_path.exists():
        log.error("Active picks not found: %s", active_picks_path)
        return {"error": "active_picks.json not found", "picks": []}

    try:
        active_picks = json.loads(active_picks_path.read_text(encoding="utf-8"))
        if not isinstance(active_picks, list):
            active_picks = []
    except Exception as e:
        log.error("Failed to load active picks: %s", e)
        return {"error": str(e), "picks": []}

    # Load closed picks
    closed_picks = []
    if closed_picks_path.exists():
        try:
            closed_picks = json.loads(closed_picks_path.read_text(encoding="utf-8"))
            if not isinstance(closed_picks, list):
                closed_picks = []
        except Exception:
            closed_picks = []

    log.info("Loaded %d active picks, %d closed picks", len(active_picks), len(closed_picks))

    # Detect regime if not provided
    if regime is None:
        # Try loading cached regime from disk first
        regime_path = _DATA / "fast_regime.json"
        if regime_path.exists():
            try:
                rd = json.loads(regime_path.read_text(encoding="utf-8"))
                regime = rd.get("regime", "").upper()
                if regime:
                    log.info("Using cached regime: %s", regime)
            except Exception:
                pass
        if not regime:
            # Also check HMM regime state
            hmm_path = _DATA / "hmm_regime_state.json"
            if hmm_path.exists():
                try:
                    rd = json.loads(hmm_path.read_text(encoding="utf-8"))
                    regime = rd.get("aggregate", {}).get("market_regime", "").upper()
                    if regime:
                        log.info("Using HMM regime: %s", regime)
                except Exception:
                    pass
        if not regime:
            # Fetch live from Binance + Fear & Greed
            regime = _fetch_regime()

    regime = regime.upper()
    log.info("Regime for filtering: %s", regime)

    # Run 6-filter pipeline (includes scoring for filter 6 sort order)
    survivors, filter_counts, strategy_stats = filter_strong_signals(
        active_picks, regime, closed_picks
    )

    # Size each survivor (score already computed by filter pipeline + filter 6 penalties)
    scored_picks = []
    for pick, filter_details, _ in survivors:
        # strong_score already set by filter pipeline (with F6 penalties applied)
        strong_score = pick.get("strong_score", score_strong_signal(pick, regime, strategy_stats))
        sizing = size_position_kelly(pick, strategy_stats)

        # Build output pick in same format as active_picks.json + extra fields
        out = {}
        # Copy all original fields
        for k, v in pick.items():
            out[k] = v
        # Add strong signal fields
        out["strong_score"] = strong_score
        out["strong_filters_passed"] = [f["filter"] for f in filter_details]
        out["position_size_pct"] = sizing["position_pct"]
        out["kelly_fraction"] = sizing["kelly_fraction"]
        out["position_dollar"] = sizing["dollar_amount"]
        out["risk_reward"] = _pick_rr(pick)
        out["stop_distance_pct"] = round(_pick_stop_distance(pick) * 100, 2)
        out["confidence_norm"] = round(_pick_confidence(pick), 3)
        out["_filter_details"] = filter_details

        scored_picks.append(out)

    # Sort by strong_score descending
    scored_picks.sort(key=lambda x: x["strong_score"], reverse=True)

    # Build output payload
    output = {
        "generated_at": now.isoformat(),
        "regime": regime,
        "version": "1.0",
        "filter_system": "strong_signals_6filter_v1",
        "filter_stats": filter_counts,
        "strategy_stats_summary": {
            strat: {"total": s["total"], "wr": round(s["wr"], 3)}
            for strat, s in strategy_stats.items()
            if s["total"] >= 5  # only show strategies with meaningful data
        },
        "total_strong": len(scored_picks),
        "picks": _sanitize_for_json(scored_picks),
    }

    # Save to data/strong_signals.json
    _DATA.mkdir(parents=True, exist_ok=True)
    out_path = _DATA / "strong_signals.json"
    try:
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("Saved %d strong signals to %s", len(scored_picks), out_path)
    except Exception as e:
        log.error("Failed to save strong_signals.json: %s", e)

    return output


def _sanitize_for_json(obj):
    """Remove NaN/Inf values that would break JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    result = generate_strong_picks()
    if not result or result.get("error"):
        print(f"ERROR: {result.get('error', 'unknown')}")
        sys.exit(1)

    picks = result.get("picks", [])
    stats = result.get("filter_stats", {})

    print(f"\n{'='*65}")
    print(f"STRONG SIGNALS | Regime: {result['regime']} | {len(picks)} picks passed")
    print(f"{'='*65}")
    print(f"Filter stats: {stats}")
    print()

    for i, p in enumerate(picks[:15], 1):
        sym = p.get("symbol", "?")
        direction = _pick_direction(p)
        score = p.get("strong_score", 0)
        rr = p.get("risk_reward", 0)
        pos_pct = p.get("position_size_pct", 0)
        kelly = p.get("kelly_fraction", 0)
        conf = p.get("confidence_norm", 0)
        sd = p.get("stop_distance_pct", 0)
        strat = p.get("strategy", "?")

        print(f"  #{i:2d}  {sym:<14s} {direction:<5s}  Score: {score}/100  R:R: {rr:.2f}x")
        print(f"       Strategy: {strat}  Conf: {conf:.2f}  Stop: {sd:.1f}%")
        print(f"       Position: {pos_pct:.1f}% (Kelly: {kelly:.4f})")
        print()

    print(f"Total strong: {len(picks)} / {stats.get('input', 0)} input")
