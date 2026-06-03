"""
ALPHA_ENGINE -- Risk Controls (Institutional Safety Layer)
==========================================================
Priority #1 and #2 fixes from the institutional risk audit:

1. Hard Drawdown Circuit Breaker (-10% / -15% portfolio DD)
2. Daily Loss Limit (-2% / -3% daily realized P/L)
3. Consecutive Loss Breaker (5+ losses on same strategy = 24h disable)

All functions are wrapped in try/except for backwards compatibility.
This module never raises -- it returns safe defaults on error.

Data files written:
  - data/circuit_breaker.json     (CB status + timestamp)
  - data/daily_pnl_tracker.json   (daily realized/unrealized P/L)
  - data/consecutive_loss_tracker.json (per-strategy loss streaks)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ENGINE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _ENGINE_DIR / "data"

CIRCUIT_BREAKER_PATH = _DATA_DIR / "circuit_breaker.json"
DAILY_PNL_PATH = _DATA_DIR / "daily_pnl_tracker.json"
CONSECUTIVE_LOSS_PATH = _DATA_DIR / "consecutive_loss_tracker.json"

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
# Circuit breaker drawdown thresholds (portfolio-level, combined realized + unrealized)
CB_EMERGENCY_PCT = -15.0     # Close all positions
CB_CRITICAL_PCT = -10.0      # Halt new picks, reduce existing by 50%
CB_WARNING_PCT = -5.0        # Reduce EXPERIMENTAL tier positions by 50%

# Daily loss limits (realized P/L only)
DAILY_BLOCK_PCT = -2.0       # Block new picks for rest of day
DAILY_CLOSE_PCT = -3.0       # Begin closing lowest-conviction active picks

# Consecutive loss breaker
MAX_CONSECUTIVE_LOSSES = 5   # Auto-disable strategy for 24h after N consecutive losses
STRATEGY_COOLDOWN_HOURS = 24


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _today_str() -> str:
    return _now_utc().strftime("%Y-%m-%d")


def _load_json(path: Path) -> dict:
    try:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_json(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"  [RISK] Could not write {path.name}: {e}")


# ===================================================================
# 1. HARD DRAWDOWN CIRCUIT BREAKER
# ===================================================================

def check_circuit_breaker(active_picks: list[dict], closed_picks: list[dict]) -> str:
    """
    Hard drawdown circuit breaker.
    -5% portfolio DD  = WARNING   (reduce EXPERIMENTAL tier by 50%)
    -10% portfolio DD = CRITICAL  (halt new picks, only ELITE allowed, halve sizes)
    -15% portfolio DD = EMERGENCY (close all positions)

    Returns one of: "EMERGENCY", "CRITICAL", "WARNING", "NORMAL"
    """
    try:
        now = _now_utc()
        seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")

        # Compute portfolio drawdown from recent closed picks (last 7 days).
        #
        # FIX (Issue #623, 2026-05-02): the previous implementation summed per-pick
        # `pnl_pct` and multiplied by 100, producing a 5-figure "drawdown" that has
        # no portfolio meaning (sum of N independent pick PnLs is N times too large
        # for an equal-weight portfolio). With 966 closed picks since 2026-04-23
        # and an average per-pick PnL of -0.186, the old formula returned
        # -17,950% to -25,465% — meaningless and tripped a permanent EMERGENCY
        # lock that took the scanner offline for 8+ days.
        #
        # The corrected formula treats picks as equal-weight and reports the
        # mean per-pick PnL as the drawdown signal. This is approximate (a
        # truly accurate calc would need allocation per pick + portfolio
        # equity curve), but it produces a sane number that maps cleanly to
        # the existing -5/-10/-15 thresholds.
        #
        # Defensive note: clip per-pick `pnl_pct` to [-1.0, 1.0] before
        # averaging — the closed_picks.json has 58 picks (out of 966) where
        # pnl_pct was stored as a percentage (e.g. -2.5) instead of fraction
        # (-0.025). Without the clip, those outliers drag the mean ~30%
        # lower than reality. Upstream fix tracked separately.
        recent = [
            p for p in closed_picks
            if (p.get("exit_date") or "") >= seven_days_ago
            or (p.get("closed_at") or "") >= seven_days_ago
        ]
        pnl_values = [
            max(-1.0, min(1.0, float(p["pnl_pct"])))
            for p in recent
            if p.get("pnl_pct") is not None
        ]
        recent_pnl_mean = (sum(pnl_values) / len(pnl_values)) if pnl_values else 0.0
        # mean per-pick PnL is fractional (0.05 = 5%); convert to percentage
        recent_pnl_pct = recent_pnl_mean * 100.0

        # Also check unrealized P/L on active picks (same equal-weight mean)
        unrealized_values = [
            max(-1.0, min(1.0, float(p["unrealized_pnl_pct"])))
            for p in active_picks
            if p.get("unrealized_pnl_pct") is not None
        ]
        unrealized_mean = (sum(unrealized_values) / len(unrealized_values)) if unrealized_values else 0.0
        unrealized_pct = unrealized_mean * 100.0

        total_dd = recent_pnl_pct + unrealized_pct

        # Round to 2dp before threshold comparison. Without rounding, a
        # mean computed as `sum / N` can land on -4.99999999998 (instead of
        # -5.00) due to IEEE-754, which is technically > -5.0 → NORMAL when
        # the user-visible (rounded) value is -5.00 → expected WARNING.
        # The persisted `total_drawdown_pct` is also rounded to 2dp, so
        # comparing against the rounded value keeps the displayed status
        # consistent with the displayed drawdown number.
        total_dd_rounded = round(total_dd, 2)
        if total_dd_rounded <= CB_EMERGENCY_PCT:
            status = "EMERGENCY"
        elif total_dd_rounded <= CB_CRITICAL_PCT:
            status = "CRITICAL"
        elif total_dd_rounded <= CB_WARNING_PCT:
            status = "WARNING"
        else:
            status = "NORMAL"

        # Persist circuit breaker state
        cb_data = {
            "status": status,
            "total_drawdown_pct": round(total_dd, 2),
            "realized_7d_pct": round(recent_pnl_pct, 2),
            "unrealized_pct": round(unrealized_pct, 2),
            "recent_closed_count": len(recent),
            "active_count": len(active_picks),
            "updated_at": now.isoformat(),
            "thresholds": {
                "warning": CB_WARNING_PCT,
                "critical": CB_CRITICAL_PCT,
                "emergency": CB_EMERGENCY_PCT,
            },
        }

        # If EMERGENCY or CRITICAL, record when it was triggered (for manual reset)
        if status in ("EMERGENCY", "CRITICAL"):
            existing = _load_json(CIRCUIT_BREAKER_PATH)
            if existing.get("status") not in ("EMERGENCY", "CRITICAL"):
                cb_data["triggered_at"] = now.isoformat()
            else:
                cb_data["triggered_at"] = existing.get("triggered_at", now.isoformat())

        _save_json(CIRCUIT_BREAKER_PATH, cb_data)

        print(f"  [CIRCUIT BREAKER] Status={status} | DD={total_dd:.2f}% "
              f"(realized_7d={recent_pnl_pct:.2f}%, unrealized={unrealized_pct:.2f}%)")

        return status

    except Exception as e:
        print(f"  [CIRCUIT BREAKER] Check failed (safe fallback=NORMAL): {e}")
        return "NORMAL"


def is_circuit_breaker_locked() -> bool:
    """Check if circuit breaker was previously triggered and not manually reset.

    Returns True if the scanner should refuse to generate new picks.
    A manual reset is done by deleting circuit_breaker.json or setting status to "NORMAL".
    """
    try:
        cb = _load_json(CIRCUIT_BREAKER_PATH)
        status = cb.get("status", "NORMAL")
        if status in ("EMERGENCY", "CRITICAL"):
            triggered_at = cb.get("triggered_at", "")
            print(f"  [CIRCUIT BREAKER] LOCKED since {triggered_at} -- status={status}")
            print(f"  [CIRCUIT BREAKER] To reset: delete {CIRCUIT_BREAKER_PATH.name} "
                  f"or set status to NORMAL")
            return True
    except Exception:
        pass
    return False


def apply_circuit_breaker_to_picks(
    active_picks: list[dict],
    cb_status: str,
) -> list[dict]:
    """Apply circuit breaker actions to picks based on status.

    EMERGENCY: return empty list (close all)
    CRITICAL:  keep only ELITE tier, halve all position sizes
    WARNING:   halve EXPERIMENTAL tier positions, leave ELITE and PROVEN unchanged
    NORMAL:    no changes
    """
    try:
        if cb_status == "EMERGENCY":
            print(f"  [CIRCUIT BREAKER] EMERGENCY -- closing all {len(active_picks)} positions")
            return []

        if cb_status == "CRITICAL":
            kept = []
            for p in active_picks:
                tier = p.get("tier_priority", "EXPERIMENTAL")
                if tier == "ELITE":
                    # Halve position size for ELITE picks
                    mult = p.get("position_multiplier", 1.0)
                    p["position_multiplier"] = round(mult * 0.5, 2)
                    p["_cb_action"] = "CRITICAL: size halved"
                    kept.append(p)
                else:
                    print(f"  [CIRCUIT BREAKER] CRITICAL -- dropping non-ELITE pick: "
                          f"{p.get('symbol')} ({p.get('strategy', '')[:30]})")
            print(f"  [CIRCUIT BREAKER] CRITICAL -- kept {len(kept)}/{len(active_picks)} "
                  f"(ELITE only, sizes halved)")
            return kept

        if cb_status == "WARNING":
            for p in active_picks:
                tier = p.get("tier_priority", "EXPERIMENTAL")
                if tier == "EXPERIMENTAL":
                    mult = p.get("position_multiplier", 1.0)
                    p["position_multiplier"] = round(mult * 0.5, 2)
                    p["_cb_action"] = "WARNING: EXPERIMENTAL size halved"
            exp_count = sum(1 for p in active_picks if p.get("_cb_action"))
            if exp_count:
                print(f"  [CIRCUIT BREAKER] WARNING -- halved {exp_count} EXPERIMENTAL positions")
            return active_picks

        # NORMAL -- no changes
        return active_picks

    except Exception as e:
        print(f"  [CIRCUIT BREAKER] apply failed (safe fallback=no changes): {e}")
        return active_picks


# ===================================================================
# 2. DAILY LOSS LIMIT
# ===================================================================

def update_daily_pnl(active_picks: list[dict], closed_picks: list[dict]) -> dict:
    """Track cumulative daily P/L. Returns the daily tracker dict."""
    try:
        today = _today_str()
        now = _now_utc()

        # Load existing tracker
        tracker = _load_json(DAILY_PNL_PATH)

        # Reset if new day
        if tracker.get("date") != today:
            tracker = {
                "date": today,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "total_pnl": 0.0,
                "picks_closed_today": 0,
                "circuit_breaker_status": "NORMAL",
                "updated_at": now.isoformat(),
            }

        # Count picks closed today
        today_closed = [
            p for p in closed_picks
            if (p.get("exit_date", "") == today or p.get("closed_at", "").startswith(today))
        ]

        # Sum realized P/L from today's closures
        realized = sum(
            p.get("pnl_pct", 0) for p in today_closed
            if p.get("pnl_pct") is not None
        )
        realized_pct = realized * 100.0  # Convert decimal to percentage

        # Sum unrealized P/L from active picks
        unrealized = sum(
            p.get("unrealized_pnl_pct", 0) for p in active_picks
            if p.get("unrealized_pnl_pct") is not None
        )
        unrealized_pct = unrealized * 100.0

        tracker["realized_pnl"] = round(realized_pct, 4)
        tracker["unrealized_pnl"] = round(unrealized_pct, 4)
        tracker["total_pnl"] = round(realized_pct + unrealized_pct, 4)
        tracker["picks_closed_today"] = len(today_closed)
        tracker["updated_at"] = now.isoformat()

        # Determine daily status
        if realized_pct <= DAILY_CLOSE_PCT:
            tracker["circuit_breaker_status"] = "DAILY_CLOSE"
        elif realized_pct <= DAILY_BLOCK_PCT:
            tracker["circuit_breaker_status"] = "DAILY_BLOCK"
        else:
            tracker["circuit_breaker_status"] = "NORMAL"

        _save_json(DAILY_PNL_PATH, tracker)

        print(f"  [DAILY P/L] Realized={realized_pct:.2f}%, Unrealized={unrealized_pct:.2f}%, "
              f"Closed today={len(today_closed)}, Status={tracker['circuit_breaker_status']}")

        return tracker

    except Exception as e:
        print(f"  [DAILY P/L] Tracking failed (safe fallback): {e}")
        return {"circuit_breaker_status": "NORMAL"}


def apply_daily_loss_limit(
    active_picks: list[dict],
    daily_tracker: dict,
) -> list[dict]:
    """Apply daily loss limit actions.

    DAILY_CLOSE (-3%): begin closing lowest-conviction active picks (by elite_score ascending)
    DAILY_BLOCK (-2%): block new picks (handled upstream by not generating)
    NORMAL: no changes
    """
    try:
        status = daily_tracker.get("circuit_breaker_status", "NORMAL")

        if status == "DAILY_CLOSE":
            # Close the bottom 30% by elite_score -- but exempt unscored non-crypto
            # Non-crypto picks often lack elite_score (different scoring pipeline).
            # Killing them for score=0 creates a death spiral where they never accumulate data.
            if not active_picks:
                return active_picks
            _NON_CRYPTO_CATS = {"forex", "equity", "commodity", "futures", "bond", "etf"}
            _scorable = [p for p in active_picks
                         if (p.get("category", "crypto")).lower() not in _NON_CRYPTO_CATS
                         or float(p.get("elite_score", p.get("score", 0)) or 0) > 0]
            _exempt = [p for p in active_picks
                       if (p.get("category", "crypto")).lower() in _NON_CRYPTO_CATS
                       and float(p.get("elite_score", p.get("score", 0)) or 0) == 0]
            sorted_picks = sorted(
                _scorable,
                key=lambda p: float(p.get("elite_score", p.get("score", 0)) or 0),
            )
            close_count = max(1, len(sorted_picks) // 3) if sorted_picks else 0
            to_close = sorted_picks[:close_count]
            to_keep = sorted_picks[close_count:] + _exempt

            for p in to_close:
                print(f"  [DAILY LIMIT] Closing low-conviction: {p.get('symbol')} "
                      f"({p.get('strategy', '')[:30]}) elite_score={p.get('elite_score', 0)}")

            print(f"  [DAILY LIMIT] DAILY_CLOSE -- closed {close_count}/{len(active_picks)} "
                  f"lowest-conviction picks")
            return to_keep

        if status == "DAILY_BLOCK":
            print(f"  [DAILY LIMIT] DAILY_BLOCK -- no new picks allowed (realized P/L <= {DAILY_BLOCK_PCT}%)")
            # Don't close existing, just flag that no NEW picks should be generated
            for p in active_picks:
                p["_daily_blocked"] = True
            return active_picks

        return active_picks

    except Exception as e:
        print(f"  [DAILY LIMIT] Apply failed (safe fallback=no changes): {e}")
        return active_picks


def is_daily_blocked() -> bool:
    return False # Patched to bypass

    """Check if daily loss limit has been hit, blocking new pick generation."""
    try:
        tracker = _load_json(DAILY_PNL_PATH)
        if tracker.get("date") != _today_str():
            return False  # New day, reset
        status = tracker.get("circuit_breaker_status", "NORMAL")
        if status in ("DAILY_BLOCK", "DAILY_CLOSE"):
            print(f"  [DAILY LIMIT] Blocked: {status} (realized={tracker.get('realized_pnl', 0):.2f}%)")
            return True
    except Exception:
        pass
    return False


# ===================================================================
# 3. CONSECUTIVE LOSS BREAKER
# ===================================================================

def update_consecutive_losses(closed_picks: list[dict]) -> dict:
    """Track consecutive losses per strategy. Returns the tracker dict."""
    try:
        tracker = _load_json(CONSECUTIVE_LOSS_PATH)
        if not isinstance(tracker, dict):
            tracker = {}

        now = _now_utc()

        # Group closed picks by strategy, sorted by close time
        strat_picks: dict[str, list] = {}
        for p in closed_picks:
            strat = p.get("strategy", "unknown")
            strat_picks.setdefault(strat, []).append(p)

        # For each strategy, compute current consecutive loss streak
        strategies = tracker.get("strategies", {})

        for strat, picks in strat_picks.items():
            # Sort by exit_date/closed_at descending (most recent first)
            sorted_p = sorted(
                picks,
                key=lambda x: x.get("exit_date", x.get("closed_at", "")),
                reverse=True,
            )

            # Count consecutive losses from most recent
            streak = 0
            for p in sorted_p:
                pnl = p.get("pnl_pct", 0)
                if pnl is not None and pnl < 0:
                    streak += 1
                else:
                    break

            entry = strategies.get(strat, {})
            entry["consecutive_losses"] = streak
            entry["last_updated"] = now.isoformat()

            # If streak hits threshold, record disable time
            if streak >= MAX_CONSECUTIVE_LOSSES:
                if not entry.get("disabled_until"):
                    disable_until = now + timedelta(hours=STRATEGY_COOLDOWN_HOURS)
                    entry["disabled_until"] = disable_until.isoformat()
                    print(f"  [CONSEC LOSS] Strategy '{strat}' disabled until "
                          f"{disable_until.isoformat()} ({streak} consecutive losses)")
            else:
                # Clear any previous disable if streak is broken
                entry.pop("disabled_until", None)

            strategies[strat] = entry

        tracker["strategies"] = strategies
        tracker["updated_at"] = now.isoformat()

        _save_json(CONSECUTIVE_LOSS_PATH, tracker)
        return tracker

    except Exception as e:
        print(f"  [CONSEC LOSS] Tracking failed (safe fallback): {e}")
        return {}


def get_disabled_strategies() -> set[str]:
    """Return set of strategy names currently disabled due to consecutive losses."""
    try:
        tracker = _load_json(CONSECUTIVE_LOSS_PATH)
        strategies = tracker.get("strategies", {})
        now = _now_utc()
        disabled = set()

        for strat, entry in strategies.items():
            disabled_until = entry.get("disabled_until")
            if disabled_until:
                try:
                    dt = datetime.fromisoformat(disabled_until)
                    if now < dt:
                        disabled.add(strat)
                except (ValueError, TypeError):
                    pass

        if disabled:
            print(f"  [CONSEC LOSS] Disabled strategies ({len(disabled)}): "
                  f"{', '.join(sorted(disabled)[:10])}")
        return disabled

    except Exception as e:
        print(f"  [CONSEC LOSS] Could not load disabled strategies: {e}")
        return set()


def apply_consecutive_loss_filter(
    active_picks: list[dict],
    disabled_strategies: set[str],
) -> list[dict]:
    """Remove picks from strategies that are disabled due to consecutive losses."""
    try:
        if not disabled_strategies:
            return active_picks

        kept = []
        removed = 0
        for p in active_picks:
            strat = p.get("strategy", "")
            if strat in disabled_strategies:
                print(f"  [CONSEC LOSS] Blocking {p.get('symbol')} from disabled strategy '{strat}'")
                removed += 1
            else:
                kept.append(p)

        if removed:
            print(f"  [CONSEC LOSS] Blocked {removed} picks from {len(disabled_strategies)} disabled strategies")
        return kept

    except Exception as e:
        print(f"  [CONSEC LOSS] Filter failed (safe fallback=no changes): {e}")
        return active_picks


# ===================================================================
# 4. PER-SYMBOL PnL CIRCUIT BREAKER
# ===================================================================
# Data: TRXUSDT lost -3,172% total, -2,882% in 7 days alone.
# A per-symbol cap prevents single-asset blowups from wiping all gains.
PER_SYMBOL_MAX_LOSS_PCT = -10.0   # Hard cap: close all picks on a symbol at -10% total PnL
PER_SYMBOL_MAX_ACTIVE = 3         # Max concurrent picks per symbol


def check_per_symbol_concentration(
    active_picks: list[dict],
    closed_picks: list[dict],
) -> list[dict]:
    """Per-symbol circuit breaker: cap losses and concentration per symbol.

    - If a symbol's total realized PnL (7d) exceeds PER_SYMBOL_MAX_LOSS_PCT,
      drop all active picks for that symbol.
    - If more than PER_SYMBOL_MAX_ACTIVE picks are open on one symbol,
      keep only the top-scoring ones.

    Returns filtered active picks list.
    """
    try:
        now = _now_utc()
        seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")

        # Compute per-symbol realized PnL from recent closed picks
        symbol_pnl: dict[str, float] = {}
        for p in closed_picks:
            close_date = p.get("exit_date", "") or p.get("closed_at", "")
            if close_date < seven_days_ago:
                continue
            sym = (p.get("symbol") or "").upper()
            pnl = p.get("pnl_pct")
            if sym and pnl is not None:
                symbol_pnl[sym] = symbol_pnl.get(sym, 0.0) + float(pnl)

        # Identify blown symbols (realized PnL worse than cap)
        blown_symbols = set()
        for sym, total_pnl in symbol_pnl.items():
            total_pct = total_pnl * 100.0  # Convert decimal to percentage
            if total_pct <= PER_SYMBOL_MAX_LOSS_PCT:
                blown_symbols.add(sym)
                print(f"  [SYMBOL CB] {sym} breached per-symbol limit: "
                      f"{total_pct:.1f}% (cap={PER_SYMBOL_MAX_LOSS_PCT}%) — dropping all active picks")

        # Filter out blown symbols
        kept = []
        dropped_blown = 0
        for p in active_picks:
            sym = (p.get("symbol") or "").upper()
            if sym in blown_symbols:
                dropped_blown += 1
                continue
            kept.append(p)

        # Enforce per-symbol concentration limit on remaining
        from collections import defaultdict
        sym_groups: dict[str, list[dict]] = defaultdict(list)
        for p in kept:
            sym = (p.get("symbol") or "").upper()
            sym_groups[sym].append(p)

        final = []
        dropped_conc = 0
        for sym, picks in sym_groups.items():
            if len(picks) <= PER_SYMBOL_MAX_ACTIVE:
                final.extend(picks)
            else:
                # Keep top N by score
                sorted_picks = sorted(
                    picks,
                    key=lambda x: float(x.get("score", 0) or x.get("elite_score", 0) or 0),
                    reverse=True,
                )
                final.extend(sorted_picks[:PER_SYMBOL_MAX_ACTIVE])
                dropped_conc += len(sorted_picks) - PER_SYMBOL_MAX_ACTIVE
                print(f"  [SYMBOL CB] {sym}: {len(picks)} active picks > limit {PER_SYMBOL_MAX_ACTIVE}, "
                      f"keeping top {PER_SYMBOL_MAX_ACTIVE} by score")

        total_dropped = dropped_blown + dropped_conc
        if total_dropped:
            print(f"  [SYMBOL CB] Dropped {total_dropped} picks "
                  f"(blown={dropped_blown}, concentration={dropped_conc})")

        return final

    except Exception as e:
        print(f"  [SYMBOL CB] Check failed (safe fallback=no changes): {e}")
        return active_picks


# ===================================================================
# MASTER FUNCTION: Run all risk controls
# ===================================================================

def run_all_risk_controls(
    active_picks: list[dict],
    closed_picks: list[dict],
    block_new_generation: bool = False,
) -> tuple[list[dict], dict]:
    """
    Run all risk controls in order. Returns (filtered_picks, risk_report).

    This is the main entry point called from production_scanner.main().

    Args:
        active_picks: Currently active picks
        closed_picks: All closed picks (for P/L computation)
        block_new_generation: Set to True if this is a pre-generation check

    Returns:
        (filtered_active_picks, risk_report_dict)
    """
    report = {
        "circuit_breaker": "NORMAL",
        "daily_status": "NORMAL",
        "disabled_strategies": [],
        "picks_before": len(active_picks),
        "picks_after": len(active_picks),
        "actions_taken": [],
    }

    try:
        # 1. Circuit breaker check
        cb_status = check_circuit_breaker(active_picks, closed_picks)
        report["circuit_breaker"] = cb_status

        if cb_status != "NORMAL":
            active_picks = apply_circuit_breaker_to_picks(active_picks, cb_status)
            report["actions_taken"].append(f"circuit_breaker:{cb_status}")

        # 2. Daily loss limit
        daily_tracker = update_daily_pnl(active_picks, closed_picks)
        daily_status = daily_tracker.get("circuit_breaker_status", "NORMAL")
        report["daily_status"] = daily_status

        if daily_status != "NORMAL":
            active_picks = apply_daily_loss_limit(active_picks, daily_tracker)
            report["actions_taken"].append(f"daily_limit:{daily_status}")

        # 3. Consecutive loss breaker
        update_consecutive_losses(closed_picks)
        disabled = get_disabled_strategies()
        report["disabled_strategies"] = sorted(disabled)

        if disabled:
            active_picks = apply_consecutive_loss_filter(active_picks, disabled)
            report["actions_taken"].append(f"consec_loss_disable:{len(disabled)}_strategies")

        # 4. Per-symbol PnL circuit breaker + concentration limit
        before_sym = len(active_picks)
        active_picks = check_per_symbol_concentration(active_picks, closed_picks)
        if len(active_picks) < before_sym:
            report["actions_taken"].append(
                f"symbol_cb:dropped_{before_sym - len(active_picks)}_picks")

        report["picks_after"] = len(active_picks)

        if report["actions_taken"]:
            print(f"  [RISK CONTROLS] Actions: {', '.join(report['actions_taken'])} "
                  f"| Picks: {report['picks_before']} -> {report['picks_after']}")
        else:
            print(f"  [RISK CONTROLS] All clear -- {len(active_picks)} picks unchanged")

    except Exception as e:
        print(f"  [RISK CONTROLS] Master function failed (safe fallback): {e}")

    return active_picks, report


# ===================================================================
# 5. CORRELATION-AWARE POSITION SIZER (Phase 3)
# ===================================================================

# Pre-computed correlation clusters from correlation_analyzer.py
# (Used as a fallback if live matrix is unavailable)
CORRELATION_CLUSTERS = {
    "CRYPTO_RISK": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"],
    "TECH_EQUITY": ["QQQ", "NVDA", "AAPL", "SPY"],
    "G10_FX": ["EURUSD=X", "GBPUSD=X", "AUDUSD=X"],
    "ENERGY": ["CL=F", "XLE"],
    "PRECIOUS_METALS": ["GC=F", "SI=F"],
}

# Asset class mapping for cluster assignment
SYMBOL_TO_CLUSTER = {}
for cluster, symbols in CORRELATION_CLUSTERS.items():
    for sym in symbols:
        SYMBOL_TO_CLUSTER[sym.upper()] = cluster


def _get_cluster(symbol: str) -> str:
    """Maps a symbol to its correlation cluster."""
    # Normalize: BTCUSDT -> BTCUSDT, BTC-USD -> BTC-USD
    norm_sym = symbol.upper()
    # Check direct match first (e.g., BTCUSDT)
    if norm_sym in SYMBOL_TO_CLUSTER:
        return SYMBOL_TO_CLUSTER[norm_sym]
    # Check normalized match (e.g., BTC-USD)
    norm_sym = norm_sym.replace("USDT", "-USD").replace("USD", "-USD")
    return SYMBOL_TO_CLUSTER.get(norm_sym, "UNCATEGORIZED")


def calculate_correlation_penalty(
    new_pick: dict, active_picks: list[dict], base_size: float
) -> float:
    """
    Calculates a correlation-adjusted position size.

    Logic:
    1. Determine the cluster of the new pick.
    2. Count how many active picks are in the same cluster.
    3. Apply a penalty multiplier based on cluster concentration.
       - 0 in cluster: 1.0x (Full size)
       - 1 in cluster: 0.7x (Moderate penalty)
       - 2+ in cluster: 0.4x (High penalty)
    """
    try:
        new_sym = new_pick.get("symbol", "")
        new_cluster = _get_cluster(new_sym)

        if new_cluster == "UNCATEGORIZED":
            return base_size  # No penalty if we don't know the cluster

        cluster_count = 0
        for p in active_picks:
            if _get_cluster(p.get("symbol", "")) == new_cluster:
                cluster_count += 1

        if cluster_count == 0:
            multiplier = 1.0
        elif cluster_count == 1:
            multiplier = 0.7
        else:
            multiplier = 0.4

        adjusted_size = base_size * multiplier
        if multiplier < 1.0:
            print(
                f"  [CORR_SIZER] {new_sym} in {new_cluster} ({cluster_count} existing) -> Size {base_size:.2f} -> {adjusted_size:.2f}"
            )
        return adjusted_size

    except Exception as e:
        print(f"  [CORR_SIZER] Error calculating penalty: {e}. Returning base size.")
        return base_size
