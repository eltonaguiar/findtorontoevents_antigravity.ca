"""
Active-Feed Hygiene — shared validation for all active_picks.json writers.

P0 fix for feed contamination: zero-entry rows, resolved rows, and stale rows
must NEVER appear in any active_picks.json file.

Usage:
    from alpha_engine.feed_hygiene import sanitize_active_picks
    clean = sanitize_active_picks(raw_picks)
    json.dump(clean, f)
"""

import logging
import os
from datetime import datetime, timezone
from functools import wraps

try:
    from alpha_engine.strategy_blocklist import is_blocked_strategy, is_blocked_pick
except ImportError:  # pragma: no cover - defensive for standalone imports
    def is_blocked_strategy(_name):
        return False

    def is_blocked_pick(_pick):
        return False

# FX Kill Switch: block toxic FOREX strategies at ingest
# Rolls back if FX_KILL_SWITCH_DISABLED=1 (see alpha_engine/fx_kill_switch.py)
try:
    from alpha_engine.fx_kill_switch import is_forex_strategy, check_strategy_for_kill as _fx_check
    _HAS_FX_KILL = True
except ImportError:
    _HAS_FX_KILL = False
    def is_forex_strategy(_name):
        return False
    def _fx_check(_name, _stats=None):
        return False, "fx_kill_switch not available"

# COMMODITY Inverse Kill Switch: block inverse-COMMODITY strategies at ingest
# Rolls back if COMMODITY_INVERSE_KILL_DISABLED=1 (see alpha_engine/commodity_kill_switch.py)
try:
    from alpha_engine.commodity_kill_switch import is_commodity_strategy, is_inverse_strategy
    from alpha_engine.commodity_kill_switch import check_strategy_for_kill as _cm_check
    _HAS_CM_KILL = True
except ImportError:
    _HAS_CM_KILL = False
    def is_commodity_strategy(_name):
        return False
    def is_inverse_strategy(_name):
        return False
    def _cm_check(_name, _stats=None, asset_class=""):
        return False, "commodity_kill_switch not available"

# Polymarket Volume Spike Filter: CRYPTO LONG entry confirmation via Polymarket
# volume spikes. Smart-money crowd conviction filter.
# Rolls back if POLYMARKET_VOL_SPIKE_DISABLED=1 (see alpha_engine/polymarket_volume_filter.py)
try:
    from alpha_engine.polymarket_volume_filter import (
        is_polymarket_volume_confirmed,
        apply_confidence_boost,
    )
    _HAS_PM_VOL_FILTER = True
except ImportError:
    _HAS_PM_VOL_FILTER = False
    def is_polymarket_volume_confirmed(_symbol, _direction):
        return True, "polymarket_volume_filter not available"
    def apply_confidence_boost(_pick, conf):
        return conf, "polymarket_volume_filter not available"

logger = logging.getLogger(__name__)

_CLOSED_STATUSES = frozenset({
    "CLOSED", "RESOLVED", "STALE", "WON", "LOST",
    "TP_HIT", "SL_HIT", "TIME_EXPIRY", "EXPIRED",
    "CANCELLED", "KILLED", "ELIMINATED",
})

STALE_HOURS = 48  # picks older than this are stale

# 2026-04-20 additional-fixes audit: strategy values that are effectively
# anonymous. Picks carrying these are rejected at ingest to prevent
# attribution / blocklist / feed-replay breakdowns downstream.
_ANONYMOUS_STRATEGY_SENTINELS = frozenset({
    "", "none", "null", "unknown", "n/a", "na",
    "default", "generic", "unnamed",
})

# FOREX pnl unit heuristic: values with |pnl| < this threshold are assumed
# to be in DECIMAL form (e.g. 0.0003 = 3 bps) and will be scaled ×100 to
# percent form for consistency with the rest of the payload. Derived from
# the audit finding that multi_asset_copytrader and kimi_signal_tracking
# emit a mix of decimal (0.0003) and percent (1.28) values.
_FOREX_PNL_DECIMAL_THRESHOLD = 0.05  # below 5% in decimal ≈ below 0.05% as percent — implausible for a closed FX trade

# Renamed symbols and known dead symbols for feed cleanup.
# 2026-04-18: MATICUSDT alias REMOVED. Scanners emitting MATICUSDT are bugged —
# the ticker is dead on Binance. Silent remap to POLUSDT was masking the bug
# and producing 889 deterministic fee-constant losses. MATICUSDT now fails
# dead-symbol check (below) so scanners get an explicit rejection they can log.
# Any intentional Polygon exposure must name POLUSDT directly.
_SYMBOL_ALIASES = {}

_DEAD_SYMBOLS = {
    "LUNAUSDT",
    "USTUSDT",
    "FTTUSDT",
    "SRMUSDT",
    # 2026-04-18: MATICUSDT was rebranded to POLUSDT on Binance. The ticker is
    # dead but scanners kept hitting it, getting stale price 0.3794, opening
    # "trades" that all TIME_EXIT at exactly -0.15% (the fee constant). 889
    # such deterministic losses in closed_picks.json through 2026-04-18 21:47
    # UTC. Blocking at the write path so no new MATIC picks are emitted;
    # legitimate Polygon exposure should use POLUSDT. Note: _SYMBOL_ALIASES
    # above also maps MATICUSDT -> POLUSDT; that remap still happens first,
    # and this dead-list is an extra guard for any path that skips alias
    # resolution. See docs/ANALYSIS_TRADING_FORENSIC_2026_04_18.md.
    "MATICUSDT",
    "MATICUSD",
}


def has_deterministic_loss_pattern(symbol, recent_prices, threshold_stdev=0.01) -> bool:
    """Detect symbols returning stale/near-identical prices across scans.

    Catches the next MATIC-style rebrand incident where a symbol returns stale
    identical prices across scans (e.g. MATICUSDT stuck at 0.3794 post-rebrand,
    producing 889 deterministic fee-constant losses). Computes the normalized
    stdev of recent_prices; if stdev/mean < threshold_stdev, the feed is flat
    and the symbol should be rejected before a pick is emitted.
    """
    try:
        prices = [float(p) for p in (recent_prices or []) if p is not None]
    except (TypeError, ValueError):
        return False
    if len(prices) < 3:
        return False
    mean = sum(prices) / len(prices)
    if mean <= 0:
        return False
    var = sum((p - mean) ** 2 for p in prices) / len(prices)
    stdev = var ** 0.5
    return (stdev / mean) < threshold_stdev


def _normalize_symbol(symbol: str) -> str:
    s = str(symbol or "").upper().replace("-", "").replace("/", "")
    if s.endswith("USD") and not s.endswith("USDT"):
        s = s + "T"
    return _SYMBOL_ALIASES.get(s, s)


def is_valid_active_pick(pick: dict) -> bool:
    """Return True if pick belongs in active_picks.json."""
    if not isinstance(pick, dict):
        return False

    # 1. Must have valid entry_price > 0 (UNLESS it's an exempt pick type)
    is_classifier = pick.get("regime") is not None and pick.get("signal") in ["LONG", "SHORT", "NEUTRAL"]
    is_aggregated = pick.get("source_system") == "aggregated_picks" or pick.get("strategy") == "SignalAggregator"
    is_research = "KIMI_CLAW" in str(pick.get("source_file", "")) or pick.get("paper_only") is True

    try:
        entry = float(pick.get("entry_price") or 0)
    except (TypeError, ValueError):
        entry = 0.0

    if entry <= 0 and not (is_classifier or is_aggregated or is_research):
        return False

    # 2. Must NOT be resolved/closed
    status = str(pick.get("status", "")).upper().strip()
    if status in _CLOSED_STATUSES:
        return False

    # 3. Must NOT have exit indicators
    try:
        exit_px = float(pick.get("exit_price") or 0)
    except (TypeError, ValueError):
        exit_px = 0.0
    if exit_px > 0:
        return False

    if pick.get("resolved_at") or pick.get("closed_at") or pick.get("exit_time"):
        return False

    # 4. Must have a symbol
    if not pick.get("symbol"):
        return False

    # 4a. Must have a non-anonymous strategy name (2026-04-20 additional-fixes
    # audit: 211 closed picks had strategy == "", "unknown", or mirrored the
    # source_system, which breaks per-strategy attribution, blocklist checks,
    # and Smart Picks/HC filter replay. Reject at ingest so those slip paths
    # are closed at the source rather than papered over downstream.)
    strat_raw = str(pick.get("strategy") or "").strip()
    if not strat_raw or strat_raw.lower() in _ANONYMOUS_STRATEGY_SENTINELS:
        return False
    sys_raw = str(pick.get("source_system") or "").strip()
    if strat_raw.lower() == sys_raw.lower() and strat_raw != "":
        # Self-named strategy (strategy == source_system) — anonymous by convention.
        return False

    # 5. Retired-strategy blocklist (checks both strategy name and composite
    #    (source_system, strategy) pairs — e.g. kimi_signal_tracking/default on FX)
    if is_blocked_pick(pick):
        return False

    # 5a. FX Kill Switch — block toxic FOREX strategies at ingest.
    # Checks known-toxic hard-blocks (7 strategies) and dynamic decay/PF/WR kills.
    # Rollback: FX_KILL_SWITCH_DISABLED=1
    if _HAS_FX_KILL:
        strat = str(pick.get("strategy") or "").strip()
        asset_class = str(pick.get("asset_class") or "").upper().strip()
        symbol = str(pick.get("symbol") or "").upper().strip()
        if asset_class == "FOREX" or is_forex_strategy(strat):
            should_kill, reason = _fx_check(strat)
            if should_kill:
                logger.info(
                    "[feed_hygiene] FX kill switch: blocking %s (%s) — %s",
                    strat, symbol, reason,
                )
                return False

    # 5b. COMMODITY Inverse Kill Switch — block inverse-COMMODITY strategies at ingest.
    # All 3 swarm engines (DeepSeek, xAI, Cerebras) agree: inverse commodity strategies
    # destroy value. Checks: known-toxic hard-blocks, COMMODITY+inverse naming,
    # and dynamic PF/WR/decay kills.
    # Rollback: COMMODITY_INVERSE_KILL_DISABLED=1
    if _HAS_CM_KILL:
        strat = str(pick.get("strategy") or "").strip()
        asset_class = str(pick.get("asset_class") or "").upper().strip()
        symbol = str(pick.get("symbol") or "").upper().strip()
        if asset_class == "COMMODITY" or is_commodity_strategy(strat):
            should_kill, reason = _cm_check(strat, asset_class=asset_class)
            if should_kill:
                logger.info(
                    "[feed_hygiene] COMMODITY inverse kill switch: blocking %s (%s) — %s",
                    strat, symbol, reason,
                )
                return False

    # 5c. Polymarket Volume Spike Filter v2 — CRYPTO LONG entry confirmation.
    # v2 (2026-05-08, swarm #4): scoped per drag-cohort to avoid over-blocking
    # 40-60% of CRYPTO LONG volume. Rules:
    #   - Drag cohort (alpha_engine_fast, kimi_signal_tracking): always require
    #     Polymarket spike for any LONG. These two have PF 0.62 / 0.26 — Polymarket
    #     momentum confirmation gates the bleed cohort.
    #   - HIGH_CONVICTION tier elsewhere: require Polymarket spike (extra rigor for
    #     bigger sizes only).
    #   - All others (MEDIUM/LOW conviction non-drag): pass through (boost on spike
    #     hit, no block on miss).
    # Rollback: POLYMARKET_VOL_SPIKE_DISABLED=1
    # Full disable of v2 scoping (revert to v1 universal gate): POLYMARKET_VOL_SPIKE_V2_DISABLED=1
    _PM_DRAG_COHORT = {"alpha_engine_fast", "kimi_signal_tracking"}
    if _HAS_PM_VOL_FILTER:
        symbol = str(pick.get("symbol") or "").upper().strip()
        direction = str(pick.get("direction") or pick.get("signal_type") or "").upper().strip()
        # Only gate LONG entries (SHORT and non-crypto pass through)
        if symbol.endswith("USDT") and direction in ("LONG", "BUY"):
            v2_disabled = os.environ.get("POLYMARKET_VOL_SPIKE_V2_DISABLED", "").strip() in ("1", "true", "TRUE")
            src_lc = (str(pick.get("source_system") or pick.get("source") or "").lower().strip())
            strat_lc = str(pick.get("strategy") or "").lower().strip()
            in_drag_cohort = src_lc in _PM_DRAG_COHORT or strat_lc in _PM_DRAG_COHORT
            tier = str(
                pick.get("hf_conviction_tier")
                or pick.get("trust_tier")
                or pick.get("conviction_tier")
                or ""
            ).upper().strip()
            is_high_conv = tier in ("HIGH", "HIGH_CONVICTION", "PROVEN", "ELITE")

            should_gate = v2_disabled or in_drag_cohort or is_high_conv
            confirmed, reason = is_polymarket_volume_confirmed(symbol, direction)
            if should_gate and not confirmed:
                logger.info(
                    "[feed_hygiene] Polymarket vol spike filter v2: blocking %s (%s) — drag=%s high_conv=%s reason=%s",
                    pick.get("strategy", "?"), symbol, in_drag_cohort, is_high_conv, reason,
                )
                return False
            # Apply confidence boost if spike confirmed (always, regardless of gate scope)
            if confirmed:
                current_conf = float(pick.get("confidence", 0) or 0)
                new_conf, boost_reason = apply_confidence_boost(pick, current_conf)
                if new_conf != current_conf:
                    pick["confidence"] = new_conf
                    pick["_pm_vol_spike_boost"] = boost_reason

    # 6. Deterministic-loss guard (only if caller provides price history)
    recent = pick.get("price_history") or pick.get("recent_prices")
    if recent and has_deterministic_loss_pattern(pick.get("symbol"), recent):
        return False

    return True


def ensure_entry_time(pick: dict) -> dict:
    """Return a copy of pick with entry_time populated if missing.

    Falls back to `timestamp` → `created_at` → `opened_at` → `generated_at`.
    Idempotent: returns pick unchanged if entry_time already non-empty.
    Added 2026-04-20 after active-pick staleness detection found 14/37
    active picks missing entry_time, blocking freshness checks.
    """
    if not isinstance(pick, dict):
        return pick
    if str(pick.get("entry_time") or "").strip():
        return pick
    out = dict(pick)
    for fallback in ("timestamp", "created_at", "opened_at", "generated_at"):
        val = pick.get(fallback)
        if val and str(val).strip():
            out["entry_time"] = val
            break
    return out


def _is_forex_symbol(symbol: str) -> bool:
    s = (symbol or "").upper().strip()
    return s.endswith("=X")


def normalize_forex_pnl(pick: dict) -> dict:
    """Return a copy of pick with `pnl_pct` normalized to percent form for
    FOREX rows. Decimal-form pnl (|v| < 0.05) is rescaled ×100. No change
    for non-FOREX picks or percent-form values already in range.

    2026-04-20 additional-fixes audit: multi_asset_copytrader and
    kimi_signal_tracking emit a mix of decimal (0.0003) and percent
    (1.28) values in the same payload, making FOREX aggregates
    uninterpretable. Normalize at ingest so downstream analytics
    compare apples to apples.
    """
    if not isinstance(pick, dict):
        return pick
    if not _is_forex_symbol(pick.get("symbol", "")):
        return pick
    raw = pick.get("pnl_pct")
    if raw is None:
        return pick
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return pick
    if 0 < abs(v) < _FOREX_PNL_DECIMAL_THRESHOLD:
        out = dict(pick)
        out["pnl_pct"] = round(v * 100.0, 6)
        out["_pnl_pct_unit_normalized"] = "decimal_to_percent"
        return out
    return pick


# ---------------------------------------------------------------------------
# Schema validation (2026-05-02)
#
# Tier-1 (HARD) fields are already enforced by is_valid_active_pick() above:
# symbol, entry_price, strategy, source_system. The decorator below adds two
# orthogonal checks that the existing gates do NOT cover:
#
#   1. Look-ahead guard — picks with timestamp > now are dropped (feature
#      leakage from back-tests bleeding into the active feed).
#   2. Soft-fill — back-fills downstream-required fields (ml_score,
#      hf_conviction_tier, va_cohort_id) with sentinels rather than dropping
#      the pick. This keeps gates that read those fields from raising
#      KeyError / silently treating None as 0 in different ways.
#
# Wire-up: validate_pick_schema() is called from sanitize_active_picks() below,
# so every existing caller of sanitize_active_picks (copy_trader_bridge,
# dashboard_generator, smart_picks_engine, etc.) picks it up automatically.
# ---------------------------------------------------------------------------

# Soft-fill defaults. Missing fields are filled, not rejected.
# ml_score=0.0 is the sentinel for "no ML score populated" — NOT a real model output.
# A probability model never outputs exactly 0.0 for a real pick.
# M-037 gate in quality_gates.py treats ml_score <= 0 as "not populated" (fail-open).
# Do NOT change this to None — sig.get("ml_score", 0.0) calls would return None instead
# of the expected numeric default, breaking math in confluence_engine and similar.
_SCHEMA_SOFT_DEFAULTS = {
    "ml_score": 0.0,
    "hf_conviction_tier": "UNKNOWN",
    "va_cohort_id": "none",
    "asset_class": "CRYPTO",
}


# M-081: known symbol→asset_class mismatches. Format: symbol_prefix → expected class.
# Whitelist approach — only flag obvious mismatches, not exotic/unusual instruments.
_FOREX_PAIR_SUFFIXES = ("=X",)  # Yahoo Finance FOREX suffix (USDJPY=X, EURUSD=X, etc.)
_FOREX_CLASSES = {"FOREX"}
_SYMBOL_CLASS_MISMATCH_CHECKS = (
    # (predicate, correct_class, description)
    (lambda sym, ac: sym.endswith("=X") and ac not in _FOREX_CLASSES,
     "FOREX", "Yahoo FOREX pair tagged as non-FOREX"),
)


def _check_symbol_class_consistency(pick: dict) -> None:
    """Log a warning when symbol format clearly contradicts the declared asset_class.

    Never rejects — data-quality signal only. The artifact that triggered this
    (USDJPY=X tagged as BOND from cta_replicator/cta_fx_multifactor, 2026-05-17 AN)
    had null pick_id and null timestamps, indicating a legacy entry. This guard
    catches future occurrences early so they appear in logs before reaching
    money_ready_verdict or the dashboard.
    """
    sym = str(pick.get("symbol") or "")
    ac = str(pick.get("asset_class") or "").upper()
    for predicate, correct_class, description in _SYMBOL_CLASS_MISMATCH_CHECKS:
        if predicate(sym, ac):
            logger.warning(
                "[feed_hygiene] symbol/class mismatch: symbol=%s asset_class=%s "
                "(expected %s) strategy=%s — %s",
                sym, ac, correct_class,
                pick.get("strategy") or pick.get("source_system"),
                description,
            )


def validate_pick_schema(pick: dict) -> dict | None:
    """Apply schema-level validation BEFORE the existing is_valid_active_pick
    business-rule gate.

    Returns a (possibly enriched) pick on success, or None to reject.

    Rejections (return None):
      * non-dict input
      * timestamp parses as a future datetime (look-ahead leakage)

    Soft-fills (mutates a copy of the pick):
      * any field in _SCHEMA_SOFT_DEFAULTS that is missing or None/empty
    """
    if not isinstance(pick, dict):
        return None

    # 1. Look-ahead guard. Tolerate non-ISO/empty timestamps — other gates
    #    catch staleness; this only rejects clearly future timestamps.
    ts = pick.get("timestamp")
    if isinstance(ts, str) and ts.strip():
        try:
            pick_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if pick_ts.tzinfo is None:
                pick_ts = pick_ts.replace(tzinfo=timezone.utc)
            # 60-second clock-skew tolerance.
            if (pick_ts - datetime.now(timezone.utc)).total_seconds() > 60:
                logger.warning(
                    "[feed_hygiene] future-timestamp drop: symbol=%s ts=%s",
                    pick.get("symbol"), ts,
                )
                return None
        except ValueError:
            pass

    # 2. Symbol/asset_class consistency check (log-only, never rejects).
    _check_symbol_class_consistency(pick)

    # 3. Soft-fill missing downstream-required fields.
    out = pick
    for field, default in _SCHEMA_SOFT_DEFAULTS.items():
        v = pick.get(field)
        if v is None or v == "":
            if out is pick:
                out = dict(pick)
            out[field] = default
    return out


def require_fields(soft: dict | None = None):
    """Decorator factory: drop picks whose timestamp is in the future and
    soft-fill missing fields from `soft` (defaults to _SCHEMA_SOFT_DEFAULTS).

    The wrapped callable must accept a pick dict as its first argument and
    return either an (optionally enriched) pick or None.
    """
    fill = dict(_SCHEMA_SOFT_DEFAULTS)
    if soft:
        fill.update(soft)

    def deco(fn):
        @wraps(fn)
        def wrapper(pick, *args, **kwargs):
            if not isinstance(pick, dict):
                return None
            ts = pick.get("timestamp")
            if isinstance(ts, str) and ts.strip():
                try:
                    pick_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if pick_ts.tzinfo is None:
                        pick_ts = pick_ts.replace(tzinfo=timezone.utc)
                    if (pick_ts - datetime.now(timezone.utc)).total_seconds() > 60:
                        return None
                except ValueError:
                    pass
            out = pick
            for field, default in fill.items():
                v = pick.get(field)
                if v is None or v == "":
                    if out is pick:
                        out = dict(pick)
                    out[field] = default
            return fn(out, *args, **kwargs)
        return wrapper
    return deco


def sanitize_active_picks(picks: list, source_label: str = "unknown") -> list:
    """Filter a list of picks, returning only valid active ones.

    Logs rejected picks for audit trail.
    """
    if not isinstance(picks, list):
        logger.warning("[feed_hygiene] %s: expected list, got %s", source_label, type(picks).__name__)
        return []

    valid = []
    rejected = {
        "no_entry": 0,
        "closed": 0,
        "has_exit": 0,
        "no_symbol": 0,
        "dead_symbol": 0,
        "duplicate": 0,
        "future_ts": 0,
        "other": 0,
    }
    seen_keys = set()

    for p in picks:
        if not isinstance(p, dict):
            rejected["other"] += 1
            continue

        symbol = _normalize_symbol(p.get("symbol", ""))
        p_norm = dict(p)
        if symbol:
            p_norm["symbol"] = symbol

        # Normalize: default entry_time from timestamp/created_at/opened_at
        # and rescale FOREX decimal pnl to percent form. Both are no-ops when
        # the input is already well-formed.
        p_norm = ensure_entry_time(p_norm)
        p_norm = normalize_forex_pnl(p_norm)

        # Schema validation: reject look-ahead timestamps + soft-fill the
        # downstream-required fields (ml_score, hf_conviction_tier, etc.)
        validated = validate_pick_schema(p_norm)
        if validated is None:
            rejected["future_ts"] += 1
            continue
        p_norm = validated

        if symbol in _DEAD_SYMBOLS:
            rejected["dead_symbol"] += 1
            continue

        direction = str(p_norm.get("direction", p_norm.get("signal_type", ""))).upper().strip()
        dedupe_key = (
            p_norm.get("strategy", ""),
            symbol,
            direction,
            p_norm.get("source_system", ""),
        )
        if symbol and direction and dedupe_key in seen_keys:
            rejected["duplicate"] += 1
            continue

        if is_valid_active_pick(p_norm):
            valid.append(p_norm)
            if symbol and direction:
                seen_keys.add(dedupe_key)
        else:
            # Categorize rejection
            entry = 0
            try:
                entry = float(p_norm.get("entry_price") or 0)
            except (TypeError, ValueError):
                pass
            status = str(p_norm.get("status", "")).upper()

            if entry <= 0:
                rejected["no_entry"] += 1
            elif status in _CLOSED_STATUSES:
                rejected["closed"] += 1
            elif p_norm.get("exit_price") or p_norm.get("resolved_at"):
                rejected["has_exit"] += 1
            elif not p_norm.get("symbol"):
                rejected["no_symbol"] += 1
            else:
                rejected["other"] += 1

    total_rejected = sum(rejected.values())
    if total_rejected > 0:
        logger.info(
            "[feed_hygiene] %s: %d valid, %d rejected (no_entry=%d, closed=%d, has_exit=%d, no_symbol=%d, dead_symbol=%d, duplicate=%d, future_ts=%d, other=%d)",
            source_label, len(valid), total_rejected,
            rejected["no_entry"], rejected["closed"], rejected["has_exit"],
            rejected["no_symbol"], rejected["dead_symbol"], rejected["duplicate"],
            rejected["future_ts"], rejected["other"],
        )

    return valid
