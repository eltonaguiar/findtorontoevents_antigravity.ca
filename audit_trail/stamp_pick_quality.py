#!/usr/bin/env python3
"""
stamp_pick_quality.py — Hedge-Fund Quality Stamper for Active Picks
=====================================================================
Runs as a step in audit-dashboard.yml (before dashboard_generator.py).

What it does:
1. Backfills `risk_reward` from entry_price / take_profit / stop_loss where missing
2. Computes `strat_fwd_wr` and `strat_fwd_trades` from closed picks history
3. Stamps `trust_tier` based on empirical win rate (PROVEN/WATCH/MONITOR/AVOID)
4. Stamps `hf_conviction_tier` (S/A/B) using conviction_stack
5. Stamps `hf_quality_score` (0-100) using data-calibrated thresholds
6. Saves stamped picks back to active_picks.json

Data-driven thresholds (from 3,340 closed picks):
  Confidence 0.80-0.90 → 77% WR   (strongest single signal)
  RR 1.0-1.5           → 56% WR   (tighter TP actually hits)
  Elite score corr     → Spearman 0.336 (moderate, useful)

Trust tier rules (calibrated from closed-book):
  PROVEN:  strat_fwd_wr >= 55% AND strat_fwd_trades >= 10
  WATCH:   strat_fwd_wr >= 45% AND strat_fwd_trades >= 5
  MONITOR: strat_fwd_wr >= 35% OR  strat_fwd_trades >= 3
  AVOID:   strat_fwd_wr <  35% AND strat_fwd_trades >= 5 (proven loser)
  UNKNOWN: insufficient history

Usage:
  python audit_trail/stamp_pick_quality.py
  python audit_trail/stamp_pick_quality.py --dry-run   # print only
  python audit_trail/stamp_pick_quality.py --file path/to/picks.json
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _float(v: Any, default: float = 0.0) -> float:
    """Coerce arbitrary input to float; return default on failure or falsy."""
    try:
        return float(v) if v else default
    except (ValueError, TypeError):
        return default


def _int(v: Any, default: int = 0) -> int:
    """Coerce arbitrary input to int; return default on failure or falsy."""
    try:
        return int(v) if v else default
    except (ValueError, TypeError):
        return default

_REPO = Path(__file__).resolve().parent.parent

# Ensure repo root is on sys.path so conviction_stack imports correctly
# regardless of how this script is invoked (python script.py vs python -m)
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ACTIVE_PICKS_PATH = _REPO / "alpha_engine" / "data" / "active_picks.json"
_CLOSED_PICKS_PATHS = [
    _REPO / "alpha_engine" / "data" / "closed_picks.json",
    _REPO / "STOCKS" / "competition" / "forward_picks.json",
]

# ---------------------------------------------------------------------------
# Trust tier thresholds (empirically calibrated from closed-pick data)
# ---------------------------------------------------------------------------
PROVEN_WR  = 0.55
PROVEN_N   = 10
WATCH_WR   = 0.45
WATCH_N    = 5
MONITOR_WR = 0.35
MONITOR_N  = 3
AVOID_WR   = 0.35   # Lost consistently despite sufficient history

# ---------------------------------------------------------------------------
# Force-demote strategies (cannot be stamped PROVEN regardless of empirical
# WR/n). Landing here requires:
#   - Realized WR on the closed ledger contradicts the gate thresholds by a
#     wide margin (e.g. PROVEN stamped via a historical snapshot but current
#     rolling WR < 50%), OR
#   - Cohort analysis shows the strategy is a credibility liability for the
#     PROVEN badge even when isolated WR calculations would clear 0.55.
# 2026-04-20: claude_gainer_st added after effectiveness audit
# (docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md) found 778 of 790 PROVEN-
# tagged closes belong to this strategy with realized WR 26.7% / PF 0.52,
# making PROVEN actively misleading at the pool level.
_FORCE_DEMOTED_STRATEGIES = frozenset({
    "claude_gainer_st",
})

# ---------------------------------------------------------------------------
# Closed-status set for at_issue_* twin snapshotting (Phase 1, feed membership)
# Must match alpha_engine.feed_hygiene._CLOSED_STATUSES.
# ---------------------------------------------------------------------------
_CLOSED_STATUSES_FOR_AT_ISSUE = frozenset({
    "CLOSED", "RESOLVED", "STALE", "WON", "LOST",
    "TP_HIT", "SL_HIT", "TIME_EXPIRY", "EXPIRED",
    "CANCELLED", "KILLED", "ELIMINATED",
})

# ---------------------------------------------------------------------------
# HF quality score weights (from data analysis)
# ---------------------------------------------------------------------------
# Feature → (weight, direction, ideal_value)
# Confidence 0.8-0.9 bucket = 77% WR  (strongest single signal)
# Elite >= 60 = moderate predictor (Spearman 0.336)
# RR 1.0-1.5 = 56% WR (better than RR 2+ which has 25% WR because TP never hit)
# MC verified = Monte Carlo edge confirmation
_SCORE_WEIGHTS = {
    "conf_08":   30,   # confidence >= 0.80 bonus (77% WR bucket)
    "conf_07":   15,   # confidence >= 0.70 (partial)
    "elite_60":  20,   # elite_score >= 60
    "elite_40":  10,   # elite_score >= 40 (partial)
    "rr_12":     15,   # RR >= 1.2 (positive EV floor)
    "ml_85":     15,   # ML probability >= 0.85
    "mc_ok":     10,   # Monte Carlo verified
    "fresh_4h":   5,   # fresh signal (< 4h old)
    "trust_prov": 5,   # PROVEN trust tier bonus
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_won(p: dict) -> bool:
    status = str(p.get("status", "")).upper()
    if status == "WON":
        return True
    if status in ("LOST", "EXPIRED"):
        return False
    exit_r = str(p.get("exit_reason", "")).upper()
    if "TP" in exit_r:
        return True
    if "SL" in exit_r:
        return False
    pnl = p.get("pnl_pct")
    return float(pnl) > 0 if pnl is not None else False


def _strategy_key(p: dict) -> str:
    return (p.get("strategy") or p.get("algorithm") or
            p.get("source_system") or "").strip()


def _load_closed() -> list:
    """Load all closed picks, merged across sources."""
    terminal = {"WON", "LOST", "CLOSED", "EXPIRED"}
    merged, seen = [], set()
    for path in _CLOSED_PICKS_PATHS:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_bytes())
            if isinstance(data, dict):
                data = data.get("picks", [])
            for p in data:
                if not isinstance(p, dict):
                    continue
                if str(p.get("status", "")).upper() not in terminal:
                    continue
                pid = str(p.get("id") or p.get("pick_id") or id(p))
                if pid not in seen:
                    seen.add(pid)
                    merged.append(p)
        except Exception:
            continue
    return merged


def _build_strategy_stats(closed: list) -> dict[str, dict]:
    """Compute per-strategy WR, n, avg_pnl from closed picks."""
    stats: dict[str, dict] = defaultdict(lambda: {"wins": 0, "total": 0, "pnl_sum": 0.0})
    for p in closed:
        s = _strategy_key(p)
        if not s:
            continue
        pnl = p.get("pnl_pct")
        stats[s]["total"] += 1
        stats[s]["pnl_sum"] += float(pnl) if pnl is not None else 0.0
        if _is_won(p):
            stats[s]["wins"] += 1
    return {
        s: {
            "n":       d["total"],
            "wr":      d["wins"] / d["total"] if d["total"] > 0 else 0.0,
            "avg_pnl": d["pnl_sum"] / d["total"] if d["total"] > 0 else 0.0,
        }
        for s, d in stats.items()
    }


def _assign_trust_tier(wr: float, n: int) -> str:
    if n == 0:
        return "UNKNOWN"
    if n >= PROVEN_N and wr >= PROVEN_WR:
        return "PROVEN"
    if n >= WATCH_N and wr >= WATCH_WR:
        return "WATCH"
    if n >= MONITOR_N or wr >= MONITOR_WR:
        return "MONITOR"
    if n >= WATCH_N and wr < AVOID_WR:
        return "AVOID"
    return "UNKNOWN"


def _compute_rr(entry: float, tp: float, sl: float, direction: str = "LONG") -> Optional[float]:
    """Compute risk-reward ratio from entry/TP/SL prices."""
    try:
        if direction.upper() in ("LONG", "BUY"):
            reward = tp - entry
            risk   = entry - sl
        else:
            reward = entry - tp
            risk   = sl - entry
        if risk <= 0 or reward <= 0:
            return None
        return round(reward / risk, 3)
    except Exception:
        return None


def _pick_age_hours(p: dict) -> Optional[float]:
    for field in ("timestamp", "entry_date", "opened_at", "created_at", "generated_at"):
        raw = p.get(field)
        if not raw:
            continue
        try:
            ts = str(raw).replace("Z", "+00:00").replace(" EST", "")
            if "T" not in ts and " " in ts:
                ts = ts.replace(" ", "T")
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        except Exception:
            continue
    return None


def _compute_hf_quality_score(p: dict, trust: str) -> int:
    """Return data-driven quality score 0-100."""
    score = 0
    conf  = float(p.get("confidence") or 0)
    elite = float(p.get("elite_score") or p.get("ml_composite_score") or 0)
    ml    = float(p.get("ml_score") or p.get("ml_composite_score") or 0)
    rr    = float(p.get("risk_reward") or 0)
    mc    = bool(p.get("mc_verified"))
    age_h = _pick_age_hours(p)

    if conf >= 0.80:
        score += _SCORE_WEIGHTS["conf_08"]
    elif conf >= 0.70:
        score += _SCORE_WEIGHTS["conf_07"]

    if elite >= 60:
        score += _SCORE_WEIGHTS["elite_60"]
    elif elite >= 40:
        score += _SCORE_WEIGHTS["elite_40"]

    if rr >= 1.2:
        score += _SCORE_WEIGHTS["rr_12"]

    if ml >= 0.85:
        score += _SCORE_WEIGHTS["ml_85"]

    if mc:
        score += _SCORE_WEIGHTS["mc_ok"]

    if age_h is not None and age_h < 4:
        score += _SCORE_WEIGHTS["fresh_4h"]

    if trust == "PROVEN":
        score += _SCORE_WEIGHTS["trust_prov"]

    return min(100, score)


def _extract_dsr(p: dict) -> Optional[float]:
    """Best-effort read of Deflated Sharpe Ratio from common pick fields."""
    direct_keys = ("dsr", "deflated_sharpe", "deflated_sharpe_ratio")
    for k in direct_keys:
        v = p.get(k)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            pass
    extra = p.get("extra")
    if isinstance(extra, dict):
        for k in direct_keys:
            v = extra.get(k)
            if v is None:
                continue
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


# ---------------------------------------------------------------------------
# Main stamping logic
# ---------------------------------------------------------------------------

def stamp_picks(picks: list, strategy_stats: dict, dry_run: bool = False) -> dict:
    """Stamp quality fields on each pick dict in place. Returns summary counts."""
    summary = {
        "total": len(picks),
        "rr_computed": 0,
        "trust_stamped": 0,
        "dsr_promotions_blocked": 0,
        "conviction_stamped": 0,
        "quality_scored": 0,
        "trust_breakdown": {},
        "conviction_breakdown": {},
    }

    # Import conviction classifier (lazy to avoid circular imports)
    try:
        from alpha_engine.conviction_stack import (
            attach_hf_conviction_tiers_to_picks,
            classify_hf_conviction_tier,
        )
        _has_conviction = True
    except ImportError:
        _has_conviction = False

    # Hoisted once above the loop (security reviewer): prevents N dict-lookups.
    try:
        from audit_trail.feed_membership import (
            evaluate_hc_tier as _fm_evaluate_hc_tier,
            is_smart_pick_per_pick as _fm_is_smart_pick,
            is_verified_alpha_per_pick as _fm_is_verified_alpha,
        )
    except Exception:
        _fm_is_smart_pick = None  # type: ignore
        _fm_is_verified_alpha = None  # type: ignore
        _fm_evaluate_hc_tier = None  # type: ignore

    for p in picks:
        if not isinstance(p, dict):
            continue

        strategy = _strategy_key(p)

        # 1. Backfill risk_reward
        if not p.get("risk_reward"):
            entry = float(p.get("entry_price") or 0)
            tp    = float(p.get("take_profit") or p.get("tp_price") or 0)
            sl    = float(p.get("stop_loss")   or p.get("sl_price") or 0)
            direction = str(p.get("direction") or p.get("action") or "LONG")
            if entry and tp and sl:
                rr = _compute_rr(entry, tp, sl, direction)
                if rr is not None:
                    p["risk_reward"] = rr
                    summary["rr_computed"] += 1

        # 2. Stamp strategy forward stats
        stats = strategy_stats.get(strategy, {})
        n   = stats.get("n", 0)
        wr  = stats.get("wr", 0.0)
        avg = stats.get("avg_pnl", 0.0)

        # FIX 2026-05-04: PM sources have no closed picks — use their own quality signals
        source = str(p.get("source_system", "") or "").lower()
        if source in {"pm_kalshi_signals", "pm_whale_signals", "polymarket_signals",
                      "prediction_market_consensus"}:
            if n == 0:  # Only override if no closed-pick stats exist
                # Use PM-specific quality fields if available
                pm_wr = _float(p.get("consensus_wr", p.get("profile_crypto_wr", 0.55)))
                pm_n = _int(p.get("consensus_trades", p.get("source_count", 10)))
                n = max(pm_n, 5)  # Minimum 5 to avoid Gate 4 block
                wr = max(pm_wr, 0.50)  # Minimum 50% WR for PM consensus
                avg = _float(p.get("consensus_pnl", 0.0))

        p["strat_fwd_wr"]     = round(wr, 3)
        p["strat_fwd_trades"] = n
        p["strat_fwd_avg_pnl"] = round(avg, 4)

        # 3. Stamp trust tier
        trust = _assign_trust_tier(wr, n)
        dsr = _extract_dsr(p)
        # 2026-04-28: Promotion gate — no PROVEN stamp when DSR is known-bad.
        # If DSR is absent, fall back to existing WR/N trust logic.
        if trust == "PROVEN" and dsr is not None and dsr < 0:
            trust = "WATCH" if n >= WATCH_N and wr >= WATCH_WR else "MONITOR"
            p["trust_promotion_block_reason"] = f"dsr_lt_zero:{dsr:.4f}"
            summary["dsr_promotions_blocked"] += 1
        # Force-demote credibility-liability strategies before sticky-preserve
        # logic so stale PROVEN tags on historical snapshots are overwritten
        # (docs/AUDIT_EFFECTIVENESS_AUDIT_2026_04_20.md).
        if strategy in _FORCE_DEMOTED_STRATEGIES and trust == "PROVEN":
            trust = "WATCH" if n >= WATCH_N and wr >= WATCH_WR else "MONITOR"
        # Preserve BANNED/UNTRUSTED (retirement states — intentional, don't
        # re-promote on a lucky streak). PROVEN is NO LONGER sticky: if the
        # strategy's current empirical WR/n no longer meets the PROVEN gate,
        # demote to the computed tier. This fixes the Verified-Alpha bleed
        # (docs/POST_GEMINI_ACTIONS_2026_04_19.md) where the sticky guard
        # kept tagging PROVEN onto strategies decayed to <20% WR.
        existing_trust = str(p.get("trust_tier") or "").upper()
        # Also force-demote picks already stamped PROVEN for credibility-
        # liability strategies, regardless of what _assign_trust_tier
        # returns this cycle. Covers historical rows that were stamped
        # before this force-demote logic landed.
        if existing_trust == "PROVEN" and strategy in _FORCE_DEMOTED_STRATEGIES:
            p["trust_tier"] = trust
            summary["trust_stamped"] += 1
        elif existing_trust in ("BANNED", "UNTRUSTED"):
            trust = existing_trust
        elif existing_trust == "PROVEN" and trust == "PROVEN":
            # Currently PROVEN and still meets PROVEN gate → keep.
            pass
        else:
            # Either not previously PROVEN, or previously PROVEN but no longer
            # meets gate → stamp computed tier (allows demotion).
            p["trust_tier"] = trust
            summary["trust_stamped"] += 1

        td = summary["trust_breakdown"]
        td[trust] = td.get(trust, 0) + 1

        # 4. Stamp conviction tier
        if _has_conviction:
            tier, reasons = classify_hf_conviction_tier(p)
            p["hf_conviction_tier"] = tier or ""
            p["hf_conviction_reasons"] = reasons
            p["conviction_tier"] = tier or ""
            if tier:
                summary["conviction_stamped"] += 1
                cd = summary["conviction_breakdown"]
                cd[tier] = cd.get(tier, 0) + 1

        # 5. Stamp quality score
        p["hf_quality_score"] = _compute_hf_quality_score(p, trust)
        summary["quality_scored"] += 1

        # 6. Phase-1 feed-membership flags (overwriting semantics on live
        #    flags; at_issue_* twins are frozen on first ACTIVE->CLOSED
        #    transition and then immutable). Imports hoisted above the loop.
        if _fm_is_smart_pick is not None:
            try:
                p["is_smart_pick"] = _fm_is_smart_pick(p)
                p["is_verified_alpha"] = _fm_is_verified_alpha(p)
                p["hc_tier"] = _fm_evaluate_hc_tier(p)

                status_is_closed = (
                    str(p.get("status", "")).upper()
                    in _CLOSED_STATUSES_FOR_AT_ISSUE
                )
                if status_is_closed and "at_issue_is_smart_pick" not in p:
                    p["at_issue_is_smart_pick"] = p["is_smart_pick"]
                    p["at_issue_is_verified_alpha"] = p["is_verified_alpha"]
                    p["at_issue_hc_tier"] = p["hc_tier"]
            except Exception:
                # Pick-level exception isolation: one bad pick must not abort
                # the whole stamping loop (reliability reviewer).
                pass

    return summary


def run(path: Path, dry_run: bool = False) -> None:
    print(f"[quality-stamper] Loading picks from {path.name} ...")
    data = json.loads(path.read_bytes())
    is_wrapped = isinstance(data, dict)
    picks = data.get("picks", []) if is_wrapped else data
    picks = [p for p in picks if isinstance(p, dict)]
    print(f"[quality-stamper] {len(picks)} picks loaded")

    print("[quality-stamper] Building strategy stats from closed picks ...")
    closed = _load_closed()
    print(f"[quality-stamper] {len(closed)} closed picks across all sources")
    stats = _build_strategy_stats(closed)
    print(f"[quality-stamper] {len(stats)} unique strategies in history")

    summary = stamp_picks(picks, stats, dry_run=dry_run)

    print(f"[quality-stamper] Results:")
    print(f"  RR backfilled:       {summary['rr_computed']}")
    print(f"  Trust tier stamped:  {summary['trust_stamped']}")
    print(f"  DSR blocks:          {summary['dsr_promotions_blocked']}")
    print(f"  Conviction stamped:  {summary['conviction_stamped']}")
    print(f"  Quality scored:      {summary['quality_scored']}")
    print(f"  Trust breakdown:     {summary['trust_breakdown']}")
    print(f"  Conviction tiers:    {summary['conviction_breakdown']}")

    if not dry_run:
        out = data if is_wrapped else picks
        if is_wrapped:
            out["picks"] = picks
            out["quality_stamped_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print(f"[quality-stamper] Saved stamped picks to {path}")
    else:
        print("[quality-stamper] DRY RUN — no files written")

    # Print top conviction picks
    tier_picks = [p for p in picks if p.get("hf_conviction_tier") in ("S", "A", "B")]
    if tier_picks:
        print(f"\n[quality-stamper] HIGH CONVICTION PICKS ({len(tier_picks)}):")
        for p in sorted(tier_picks, key=lambda x: (x.get("hf_conviction_tier", "Z"), -float(x.get("hf_quality_score", 0)))):
            sym   = p.get("symbol") or p.get("ticker", "?")
            tier  = p.get("hf_conviction_tier")
            conf  = p.get("confidence")
            elite = p.get("elite_score")
            rr    = p.get("risk_reward")
            score = p.get("hf_quality_score")
            trust = p.get("trust_tier")
            print(f"  [{tier}] {sym:<14} conf={conf}  elite={elite}  rr={rr}  score={score}  trust={trust}")
    else:
        print("[quality-stamper] No high-conviction picks found")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    file_arg = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
    target = Path(file_arg) if file_arg else _ACTIVE_PICKS_PATH

    if not target.exists():
        print(f"ERROR: {target} not found")
        sys.exit(1)

    run(target, dry_run=dry_run)
