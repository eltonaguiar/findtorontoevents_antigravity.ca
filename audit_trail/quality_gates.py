"""
Quality Gates for Audit Dashboard Picks

This module implements the filtering logic to ensure only high-quality,
tradeable picks appear on findtorontoevents.ca/audit

Usage:
    from audit_trail.quality_gates import passes_active_gate, passes_smart_gate

    if passes_active_gate(pick):
        active_picks.append(pick)

Optional strict data-quality mode (off by default): set environment variable
``AUDIT_PICK_SANITY_GATE=1`` to reject picks that fail ``audit_trail.pick_sanity``
after normal trade-geometry checks. Prediction-market rows are exempt (same as
geometry skip list).

    if passes_smart_gate(pick):
        smart_picks.append(pick)
"""

import json
import logging
import os
import re
import sys
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timezone

# Pair-level exception carve-out registry (B19)
try:
    from alpha_engine.pair_exceptions import should_pair_exception_pass
    _PAIR_EXCEPTIONS_AVAILABLE = True
except ImportError:
    _PAIR_EXCEPTIONS_AVAILABLE = False

    def should_pair_exception_pass(_pick: "Dict[str, Any]") -> bool:  # type: ignore[misc]
        return False

# Mutation filter — enforce symbol-lock and direction-filter constraints
# for CANDIDATE strategies derived from banned parents
try:
    from alpha_engine.strategy_mutations import (
        check_mutation_filter,
        get_mutation_for_parent,
        ALL_MUTATIONS,
        SYMBOL_LOCKED_VARIANTS,
        DIRECTION_FILTERED_VARIANTS,
    )

    _MUTATIONS_AVAILABLE = True
except ImportError:
    _MUTATIONS_AVAILABLE = False
    ALL_MUTATIONS = {}
    SYMBOL_LOCKED_VARIANTS = {}
    DIRECTION_FILTERED_VARIANTS = {}

try:
    from audit_trail.hf_policy_thresholds import (
        decay_hard_gate_triggers,
        normalize_wr_percent,
    )
except ImportError:

    def decay_hard_gate_triggers(bt_wr, fwd_wr, n_closed, gap_pp=15.0, min_closed=20):
        return False

    def normalize_wr_percent(value):
        return None


try:
    from audit_trail.forward_degradation_tracker import _is_rehab_variant_strategy
except ImportError:

    def _is_rehab_variant_strategy(strategy_name: str) -> bool:
        return False

# Anti-overfit validator (CPCV/PBO + DSR) — OPT-IN wire-in.
# Flag default-OFF (Kimi P1 wire-up 2026-05-12). Flip
# ``ANTI_OVERFIT_VALIDATOR_ENABLED=1`` to engage. When engaged, picks whose
# strategy history returns DSR < 0.95 OR PBO > 0.50 are rejected from Smart.
try:
    from alpha_engine.anti_overfit_validator import (
        evaluate_strategy as _anti_overfit_evaluate,
    )
    _ANTI_OVERFIT_AVAILABLE = True
except Exception:  # pragma: no cover - missing optional deps
    _ANTI_OVERFIT_AVAILABLE = False

    def _anti_overfit_evaluate(_history, n_trials=1, n_candidates=2):  # type: ignore[misc]
        return {"dsr": float("nan"), "pbo": float("nan")}


# Optional: per_class_trainer ML quality predictor (shadow mode, 30-day data collection)
try:
    from ml_gatekeeper.per_class_trainer import predict_quality as _pct_predict_fn
    _PCT_TRAINER_AVAILABLE = True
except Exception:
    _pct_predict_fn = None
    _PCT_TRAINER_AVAILABLE = False


_STRATEGY_RETURNS_CACHE: "dict[str, list[float]] | None" = None


def _load_strategy_returns_cache() -> "dict[str, list[float]]":
    """Lazily build strategy→[pnl_pct, ...] map from closed_picks.json."""
    global _STRATEGY_RETURNS_CACHE
    if _STRATEGY_RETURNS_CACHE is not None:
        return _STRATEGY_RETURNS_CACHE
    cache: "dict[str, list[float]]" = {}
    try:
        import json as _json
        from pathlib import Path as _Path
        cp = _Path(__file__).resolve().parent.parent / "alpha_engine" / "data" / "closed_picks.json"
        if cp.exists():
            raw = _json.loads(cp.read_text(encoding="utf-8"))
            picks = raw if isinstance(raw, list) else raw.get("picks", [])
            for p in picks:
                strat = str(p.get("strategy") or p.get("source") or "")
                pnl = p.get("pnl_pct")
                if strat and pnl is not None:
                    try:
                        cache.setdefault(strat, []).append(float(pnl))
                    except (TypeError, ValueError):
                        pass
    except Exception:
        pass
    _STRATEGY_RETURNS_CACHE = cache
    return cache


def _anti_overfit_reject(pick: Dict[str, Any]) -> bool:
    """Return True iff opt-in anti-overfit validator says reject.

    Default-ON as of 2026-05-13 (post-soak verification, swarm-cleared).
    Set ``ANTI_OVERFIT_VALIDATOR_ENABLED=0`` to bypass. Reads the
    strategy's per-period return history from ``pick`` keys
    ``returns_history`` / ``strategy_returns`` / ``forward_returns``.
    Falls back to closed_picks.json cache for strategies with >=20 closed trades.
    Missing/short history => no opinion (False, falls through to legacy gate).
    """
    if os.environ.get("ANTI_OVERFIT_VALIDATOR_ENABLED", "1") != "1":
        return False
    if not _ANTI_OVERFIT_AVAILABLE:
        return False
    history = (
        pick.get("returns_history")
        or pick.get("strategy_returns")
        or pick.get("forward_returns")
    )
    if not history:
        strat = str(pick.get("strategy") or pick.get("source") or "")
        history = _load_strategy_returns_cache().get(strat, [])
    history = history or []
    try:
        history_list = [float(x) for x in history]
    except (TypeError, ValueError):
        return False
    if len(history_list) < 20:
        return False
    try:
        result = _anti_overfit_evaluate(history_list)
    except Exception:
        return False
    dsr = result.get("dsr")
    pbo = result.get("pbo")
    # NaN comparisons are False -- treated as "no evidence" => no reject.
    try:
        if dsr is not None and dsr == dsr and float(dsr) < 0.95:
            logger.debug(
                "Smart gate: anti_overfit DSR %.3f < 0.95 (n=%d)",
                float(dsr), len(history_list),
            )
            return True
        if pbo is not None and pbo == pbo and float(pbo) > 0.50:
            logger.debug(
                "Smart gate: anti_overfit PBO %.3f > 0.50 (n=%d)",
                float(pbo), len(history_list),
            )
            return True
    except (TypeError, ValueError):
        return False
    return False


try:
    from audit_trail.pick_sanity import passes_pick_sanity as _PICK_SANITY_PASS
except ImportError:
    _PICK_SANITY_PASS = None

try:
    from alpha_engine.matrix_symbol_gates import matrix_symbol_gate_blocks
except ImportError:

    def matrix_symbol_gate_blocks(pick):  # type: ignore
        return False, ""


try:
    from alpha_engine.sandbox_mutation_experiments import (
        apply_sandbox_experiment_relabels,
    )
except ImportError:

    def apply_sandbox_experiment_relabels(pick):  # type: ignore
        pass

# Trade geometry validation for ALL asset classes (fixes non-crypto bypass bug)
try:
    from audit_trail.trade_geometry import has_valid_trade_geometry
    _TRADE_GEOMETRY_AVAILABLE = True
except ImportError:
    _TRADE_GEOMETRY_AVAILABLE = False



logger = logging.getLogger(__name__)
_TECH_ALIGN_RE = re.compile(
    r"(?P<aligned>\d+)\s*/\s*(?P<total>\d+)\s*(?P<bias>BUY|SELL)", re.I
)
# ── SUPER STRATEGY: Multi-symbol robustness tiers (cached at module load) ──
# A strategy that profits across many symbols is more trustworthy than one
# that only works on a single symbol. This is the 'super strategy' concept:
#   ALL_SYMBOL (10+ profitable symbols) = highest trust
#   MULTI_SYMBOL (5-9) = high trust
#   FEW_SYMBOL (3-4) = moderate trust
#   SINGLE_SYMBOL = lowest trust (curve-fit risk)
_SYMBOL_STRENGTH_TIERS: Dict[str, Any] = {}


def _load_symbol_strength_tiers() -> Dict[str, Any]:
    """Load symbol_strength_tiers.json once at module level. Cached."""
    global _SYMBOL_STRENGTH_TIERS
    if _SYMBOL_STRENGTH_TIERS:
        return _SYMBOL_STRENGTH_TIERS
    _tiers_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "alpha_engine",
        "data",
        "ab_test_portfolios",
        "symbol_strength_tiers.json",
    )
    try:
        with open(_tiers_path, "r", encoding="utf-8") as f:
            _SYMBOL_STRENGTH_TIERS = json.load(f)
        logger.info(
            "Loaded symbol_strength_tiers.json: %d strategies",
            len(_SYMBOL_STRENGTH_TIERS.get("details", {})),
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load symbol_strength_tiers.json: %s", exc)
        _SYMBOL_STRENGTH_TIERS = {}
    return _SYMBOL_STRENGTH_TIERS


# ── Q12 STREAK MOMENTUM: module-level cache of per-strategy win/loss streaks ──
_STREAK_CACHE: Dict[str, int] = {}  # strategy -> signed streak (+N wins, -N losses)


def _load_streak_cache() -> Dict[str, int]:
    """Load closed_picks.json, compute trailing win/loss streak per strategy."""
    cache: Dict[str, int] = {}
    _path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "alpha_engine",
        "data",
        "closed_picks.json",
    )
    try:
        with open(_path, "r", encoding="utf-8") as f:
            picks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return cache
    from collections import defaultdict

    grouped: Dict[str, list] = defaultdict(list)
    for p in picks:
        strat = p.get("strategy") or ""
        ts = p.get("closed_at") or p.get("exit_time") or p.get("entry_time") or ""
        if strat and ts:
            grouped[strat].append((ts, p.get("pnl_pct", 0)))
    for strat, entries in grouped.items():
        entries.sort(key=lambda x: x[0], reverse=True)  # newest first
        streak = 0
        for _, pnl in entries:
            won = (pnl or 0) > 0
            if streak == 0:
                streak = 1 if won else -1
            elif won and streak > 0:
                streak += 1
            elif not won and streak < 0:
                streak -= 1
            else:
                break
        cache[strat] = streak
    return cache


_STREAK_CACHE = _load_streak_cache()


# Active-picks snapshot cache (30s TTL) used by the concentration_cap
# wire-up in `passes_active_gate`. Per swarm round 2026-05-13: raw disk
# reads per gate call would degrade dashboard build time (HIGH I/O). TTL
# of 30s mirrors hourly dashboard refresh cadence while shielding hot
# loops from repeated disk reads.
_ACTIVE_PICKS_CACHE: Dict[str, Any] = {"ts": 0.0, "picks": []}
_ACTIVE_PICKS_CACHE_TTL_SEC = 30.0

# M-004: system concentration cache — loaded from audit_trail/data/system_concentration.json
# written by dashboard_generator. Refreshed every 5 minutes. Fail-open (empty if file absent).
_SYSTEM_CONCENTRATION_CACHE: Dict[str, Any] = {"ts": 0.0, "by_class": {}}
_SYSTEM_CONCENTRATION_CACHE_TTL_SEC = 300.0

# M-049: safety_status verdict cache — checked at most once per 60s to avoid
# calling get_safety_status() on every pick (it reads dashboard_data.json).
_SAFETY_STATUS_CACHE: Dict[str, Any] = {"ts": 0.0, "verdict": None}
_SAFETY_STATUS_CACHE_TTL_SEC = 60.0


def _get_safety_status_verdict() -> str | None:
    """Return safety_status verdict ('GO'/'CAUTION'/'STOP'), cached 60s. Fail-open → None."""
    import time as _time_ss
    now = _time_ss.time()
    if (now - _SAFETY_STATUS_CACHE["ts"]) < _SAFETY_STATUS_CACHE_TTL_SEC:
        return _SAFETY_STATUS_CACHE.get("verdict")
    try:
        from audit_trail.safety_status import get_safety_status as _gss
        _SAFETY_STATUS_CACHE["verdict"] = _gss().get("verdict")
        _SAFETY_STATUS_CACHE["ts"] = now
        return _SAFETY_STATUS_CACHE["verdict"]
    except Exception:
        return None  # fail-open: never block picks on safety_status import error


def _cached_active_picks_snapshot() -> list:
    """Return active picks list, refreshing once per TTL window."""
    import time as _time
    now = _time.time()
    if (now - _ACTIVE_PICKS_CACHE["ts"]) < _ACTIVE_PICKS_CACHE_TTL_SEC:
        cached = _ACTIVE_PICKS_CACHE.get("picks")
        if isinstance(cached, list):
            return cached
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "alpha_engine",
        "data",
        "active_picks.json",
    )
    picks: list = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, list):
            picks = [p for p in d if isinstance(p, dict)]
        elif isinstance(d, dict):
            cand = d.get("picks") or d.get("active") or []
            if isinstance(cand, list):
                picks = [p for p in cand if isinstance(p, dict)]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        picks = []
    _ACTIVE_PICKS_CACHE["ts"] = now
    _ACTIVE_PICKS_CACHE["picks"] = picks
    return picks


def _reset_active_picks_cache() -> None:
    """Force the next call to re-read disk. Test helper."""
    _ACTIVE_PICKS_CACHE["ts"] = 0.0
    _ACTIVE_PICKS_CACHE["picks"] = []


def _cached_system_concentration() -> dict:
    """Return {asset_class: {system_name: {pf, vol_pct, resolved_n}}}, TTL 5min.

    M-004: written by dashboard_generator to audit_trail/data/system_concentration.json.
    Fail-open: returns {} if file missing or unparseable.
    """
    import time as _time_sc
    now = _time_sc.time()
    if (now - _SYSTEM_CONCENTRATION_CACHE["ts"]) < _SYSTEM_CONCENTRATION_CACHE_TTL_SEC:
        return _SYSTEM_CONCENTRATION_CACHE.get("by_class") or {}
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "system_concentration.json",
    )
    by_class: dict = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        by_class = d.get("by_class", {}) or {}
    except Exception:
        pass  # fail-open: empty dict if file missing
    _SYSTEM_CONCENTRATION_CACHE["ts"] = now
    _SYSTEM_CONCENTRATION_CACHE["by_class"] = by_class
    return by_class


def _reset_system_concentration_cache() -> None:
    """Force the next call to re-read disk. Test helper."""
    _SYSTEM_CONCENTRATION_CACHE["ts"] = 0.0
    _SYSTEM_CONCENTRATION_CACHE["by_class"] = {}


# Quality thresholds
# =============================================================================
# ⚠ THRESHOLD FREEZE — 2026-05-20 to 2026-08-18 (90 days)
# Per Kimi Renaissance Review: all score thresholds frozen to stop data snooping.
# DO NOT modify any SMART_PICKS_MIN_SCORE_* value until 2026-08-18 without
# operator approval + documented justification in updates/.
# Frozen values (as of 2026-05-20):
#   CRYPTO:     60 (was 70→65→60)
#   EQUITY:     50
#   FOREX:      40 (was 55→40)
#   COMMODITY:  30 (was 60→30)
#   FUTURES:    45 (was 65→45)
#   BOND:       35 (was 60→35)
#   ETF:        35 (was 40→35)
#   ASSET_CLASS_SMART_THRESHOLDS: frozen as-is below
# =============================================================================

import os as _os

_THRESHOLD_FREEZE_ENV = _os.environ.get("THRESHOLD_FREEZE", "1")  # Default ON
_THRESHOLD_FREEZE_UNTIL = "2026-08-18"

if _THRESHOLD_FREEZE_ENV == "1":
    import logging as _freeze_log
    _freeze_log.getLogger("quality_gates").warning(
        "THRESHOLD FREEZE ACTIVE until %s — score floors locked. "
        "Set THRESHOLD_FREEZE=0 to override (NOT RECOMMENDED).",
        _THRESHOLD_FREEZE_UNTIL,
    )

ACTIVE_PICKS_MIN_SCORE = 0  # REVERTED: let ALL picks through, sort by score. Hiding picks starves the dashboard.
SMART_PICKS_MIN_SCORE = 60  # FROZEN 2026-05-20 to 2026-08-18
# 5+ agent consensus (Kimi/Codex/claude-dash-fix/antigrav-scoring-review/me):
# At threshold=70, ZERO active picks qualify (max live score=60).
# At threshold=60, 1 pick qualifies; at 50, 7 qualify.
# Penalty stacking (Sunday -6, LONG_OVERCONF -25, direction_conflict -12
# applied to 65pct of picks) is destroying genuine signals.
# My earlier raise to 70 was based on closed-pick H1 vs H2 chrono-split,
# but LIVE book has different dynamics — score IS predictive, but
# current calibration floors most picks before they reach 70. Lowering to
# 60 until underlying scoring recalibration lands. Codex closed-pick
# analysis: score 60-69 = 62.7pct WR PF 12.90 (strong edge).
# v1 rationale (superseded): Chrono-split on 2662 closed crypto showed forward-decay
# floor=60 H1=81%WR -> H2=50%WR. Raised to 70, but scoring recalibration gaps
# prevented live picks from reaching 70. Lowering back until recalibration lands.
SMART_PICKS_MIN_SCORE_EQUITY = (
    50  # FROZEN 2026-05-20 to 2026-08-18
)
# vs old floor=30 recent-third: 40%WR PF 1.06 (stale calibration).
# Chrono-stable: H1 67%WR PF 2.69 / H2 64%WR PF 2.91.
# 2026-04-21: FOREX score floor RAISED 40→55 for hedge fund performance.
# The 40 threshold allowed too many low-quality picks (25% WR).
# Raise to 55 to focus on proven strategies with forward WR ≥45%
# - FwdWR≥50 is the correct forex gate (PF 1.62 on n=466), already added in PR #191
# - Score≥55 filters to top-tier forex strategies only
# - Proven strategies (forex_rsi2_mean_reversion, myfxbook_retail_contrarian) score 30-45
    #   Connors & Alvarez (2008) = 68% WR academic baseline. Re-evaluate after resolver fix.
#   but must now pass additional quality gates beyond score
# - The FwdWR≥50 gate (added in PR #191) provides the real quality filtering for forex
SMART_PICKS_MIN_SCORE_FOREX = 40  # FROZEN 2026-05-20 to 2026-08-18
SMART_PICKS_MIN_SCORE_COMMODITY = 30  # FROZEN 2026-05-20 to 2026-08-18
# Antigravity P2 diagnosis. Floor=60 was unreachable: commodity strategies
# can't accumulate score booster enrichment (score_booster has crypto-only
# guards in MTF + ensemble gates), so achievable score range is ~30-55.
# Floor=60 = silent zero picks. Lowering to 40 (matching ETF/BOND/FOREX)
# is safe because downstream filters fortified: BLOCKED_STRATEGIES,
# BLOCKED_ASSET_STRATEGY_PAIRS, _is_valid_resolved_pick (commit 19b8eda365),
# and hc_filter per-class WR/score floors at 40 (commit 8e97a8500d).
SMART_PICKS_MIN_SCORE_BOND = (
    35  # FROZEN 2026-05-20 to 2026-08-18
)
SMART_PICKS_MIN_SCORE_FUTURES = 45  # FROZEN 2026-05-20 to 2026-08-18
# Note: futures_momentum was the winner in that window but has since been
# KILLED (0% WR on 56 closed, PF 0.00 — added 2026-05-06).
# Score floor override remains for other futures strategies.
SMART_PICKS_MIN_SCORE_ETF = (
    35  # FROZEN 2026-05-20 to 2026-08-18
)
ASSET_CLASS_SMART_THRESHOLDS = {
    "CRYPTO": {"min_score": 65.0, "min_fwr": 0.62, "min_trades": 10},
    "EQUITY": {"min_score": 40.0, "min_fwr": 0.50, "min_trades": 5},
    "FOREX": {"min_score": 40.0, "min_fwr": 0.46, "min_trades": 3},
    "COMMODITY": {"min_score": 30.0, "min_fwr": 0.50, "min_trades": 0},
    "FUTURES": {"min_score": 45.0, "min_fwr": 0.50, "min_trades": 0},
    "BOND": {"min_score": 35.0, "min_fwr": 0.50, "min_trades": 0},
    "ETF": {"min_score": 35.0, "min_fwr": 0.50, "min_trades": 0},
}
SMART_PICKS_MIN_CONFIDENCE = 0.60  # FROZEN 2026-05-20 to 2026-08-18
# ML score gate is currently DISABLED — ml_score is not reliably populated upstream,
# so enforcing a floor rejects large fractions of otherwise-valid picks.
# Historical target was 0.60 (IC=+0.33 on decile test; <0.50 was the 22% WR kill zone).
# Re-enable only after validating ml_score fill rate on live picks.
# Canonical value is the single assignment further below (SMART_PICKS_MIN_ML_SCORE = 0.0).

# =========================================================================
# Strategy-specific score overrides (Phase 3: FOREX_COMMODITIES_BONDS.MD)
# Proven strategies get lower floors — they earn trust through track record,
# not score booster enrichment that doesn't exist for non-crypto yet.
# =========================================================================
STRATEGY_SCORE_OVERRIDES: dict[str, int] = {
    # FOREX — proven strategies scoring 30-45
    # "forex_rsi2_mean_reversion": 30,  # KILLED 2026-05-06: 43.3% WR, PF 0.37, n=593 — large-n bleeder
    "myfxbook_retail_contrarian": 30,
    "forex_bollinger_squeeze": 35,
    "forex_session_momentum": 35,
    # ETF — academically-backed rotation strategies
    "etf_dual_momentum": 30,
    "etf_sector_momentum": 30,
    "etf_risk_on_off": 30,
    "etf_trend_following": 35,
    "etf_rsi2_pullback": 30,  # Short-term RSI2 mean-reversion (2-5 day hold)
    # 2026-05-28 baby-strat ships — lower floor for shadow/monitor accumulation:
    "etf_dual_momentum_rotation": 28,  # DIA WR 58.8%, PF 2.64
    "equity_sector_rotation_momentum": 30,  # sector rotation with dual mom
    # BOND — conservative strategies, lower natural scores
    "bond_yield_momentum": 28,
    "bond_duration_rotation": 28,
    "bond_mean_reversion": 30,
    "bond_credit_spread": 30,
    # 2026-05-28 baby-strat ships:
    "bond_yield_curve_momentum": 28,  # yield-curve duration momentum
    # COMMODITY — CTA and seasonal
    "cta_golden_cross_200": 35,
    "cot_positioning": 35,
    "commodity_seasonal": 30,
    # 2026-05-28 baby-strat ships:
    "copper_platinum_cot_momentum": 35,  # COT-proxy for HG=F, PL=F
    # FUTURES
    "futures_bb_mean_reversion": 35,
    # 2026-05-28 baby-strat ships:
    "futures_session_breakout_cot": 35,  # ES=F WR 61.5%, PF 1.39
    # CRYPTO — 2026-05-28 baby-strat ships:
    "crypto_atr_ratio_expansion_long": 30,  # ATR compression/expansion breakout
}

def get_effective_min_score(strategy_name: str, asset_class: str) -> int:
    """Return the effective minimum score for a pick, considering strategy overrides.

    Proven strategies with track records get lower floors.
    Unproven strategies use the class default.
    """
    if strategy_name in STRATEGY_SCORE_OVERRIDES:
        return STRATEGY_SCORE_OVERRIDES[strategy_name]
    # Fall back to class defaults
    _class_floors = {
        "CRYPTO": SMART_PICKS_MIN_SCORE,
        "FOREX": SMART_PICKS_MIN_SCORE_FOREX,
        "COMMODITY": SMART_PICKS_MIN_SCORE_COMMODITY,
        "FUTURES": SMART_PICKS_MIN_SCORE_FUTURES,
        "BOND": SMART_PICKS_MIN_SCORE_BOND,
        "ETF": SMART_PICKS_MIN_SCORE_ETF,
        "EQUITY": SMART_PICKS_MIN_SCORE_EQUITY,
    }
    return _class_floors.get(asset_class.upper(), SMART_PICKS_MIN_SCORE)


# Prior duplicate assignment removed 2026-04-19 per code review (Finding 2).

# ── PREFERRED STRATEGY-SYMBOL PAIRS (HF-P0 ┬º2.4, 2026-04-05 claude-noncrypto-drilldown) ──
# Whitelist of empirically vetted (asset_class, strategy, symbol, timeframe) combos from
# cross_asset_edge_finder.py scan (Sharpe>=1.8, WR>=60%, PF>=1.8, n>=13 trades, live yfinance data).
# Matching picks receive PREFERRED_PAIR_BONUS (+10) in _apply_score_penalties.
# Refresh cadence: regenerate cross_asset_edge_finder_results.json monthly OR after regime shift.
# Fail-safe: if file missing or malformed, returns empty dict — bonus silently not applied.
PREFERRED_PAIR_BONUS = 10
_PREFERRED_PAIRS_CACHE: Optional[Set[Tuple[str, str, str]]] = None


def _normalize_asset_class(asset_class: Any) -> str:
    ac = str(asset_class or "").upper().strip()
    return {"COMMODITIES": "COMMODITY", "BONDS": "BOND", "ETFS": "ETF"}.get(ac, ac)


def _load_preferred_pairs() -> Set[Tuple[str, str, str]]:
    """Lazy-load cross-asset edge-finder recommended combos as (asset_class, strategy_fragment, symbol_root) set.

    Format in JSON: 'ASSET|STRATEGY|SYMBOL|TIMEFRAME' keys.
    We match fuzzy on symbol_root (GC=F -> GC, EURUSD=X -> EURUSD).
    Strategy matched as substring since strategy names vary across the pipeline.
    """
    global _PREFERRED_PAIRS_CACHE
    if _PREFERRED_PAIRS_CACHE is not None:
        return _PREFERRED_PAIRS_CACHE
    import json as _json
    from pathlib import Path as _Path

    result: Set[Tuple[str, str, str]] = set()
    try:
        _path = _Path(__file__).parent.parent / "cross_asset_edge_finder_results.json"
        if not _path.exists():
            _PREFERRED_PAIRS_CACHE = result
            return result
        with open(_path, "r", encoding="utf-8") as _f:
            _data = _json.load(_f)
        _rec = _data.get("recommended", {}) or {}
        for _key in _rec.keys():
            _parts = _key.split("|")
            if len(_parts) < 3:
                continue
            _asset = _parts[0].strip().upper()
            _strat = _parts[1].strip().upper()
            _sym = (
                _parts[2]
                .strip()
                .upper()
                .replace("=F", "")
                .replace("=X", "")
                .replace("^", "")
            )
            result.add((_asset, _strat, _sym))
    except (OSError, ValueError, KeyError):
        pass  # Fail-safe: empty whitelist
    _PREFERRED_PAIRS_CACHE = result
    return result


def _matches_preferred_pair(pick: Dict[str, Any]) -> bool:
    """Check if pick matches any whitelisted preferred pair (fuzzy match)."""
    pairs = _load_preferred_pairs()
    if not pairs:
        return False
    _ac = str(pick.get("asset_class", "") or "").upper()
    # Asset aliases: ETF_LEVERAGED -> ETF, INDEX -> FUTURES (per cursor-audit-quant convention)
    if _ac == "ETF_LEVERAGED":
        _ac = "ETF"
    elif _ac == "INDEX":
        _ac = "FUTURES"
    _strat = str(pick.get("strategy", "") or "").upper()
    _sym = (
        str(pick.get("symbol", "") or "")
        .upper()
        .replace("=F", "")
        .replace("=X", "")
        .replace("^", "")
    )
    # Also strip USDT/USD suffix for crypto-equivalent matching (BTCUSDT <-> BTC)
    _sym_stripped = _sym
    for suffix in ("USDT", "USDC", "BUSD", "USD"):
        if _sym_stripped.endswith(suffix) and len(_sym_stripped) > len(suffix):
            _sym_stripped = _sym_stripped[: -len(suffix)]
            break
    for _p_ac, _p_strat_frag, _p_sym in pairs:
        if _p_ac != _ac:
            continue
        if _p_sym not in (_sym, _sym_stripped):
            continue
        # Strategy substring match in either direction (pipeline names vary)
        _strat_key = _strat.replace("_", "").replace("-", "")
        _p_key = _p_strat_frag.replace("_", "").replace("-", "")
        if _p_key in _strat_key or _strat_key in _p_key:
            return True
        # Also allow fragment-level match (e.g., "SUPERTREND" in both)
        for _frag in _p_strat_frag.split("_"):
            if len(_frag) >= 5 and _frag in _strat_key:
                return True
    return False


# ── CROSS-ASSET CONFLUENCE BONUS (HF-┬ºextra, 2026-04-05) ──
# Deferred follow-on from commit 30832eba08 (score floors) and 823d253a1e (preferred pairs).
# When the same underlying asset has aligned directional signals across 2+ DIFFERENT
# asset classes (e.g., BTCUSDT LONG in CRYPTO + BITO LONG in ETF + BTC1! LONG in FUTURES),
# that confluence is a strong institutional signal more robust than a single pipeline.
# Each matching pick receives CROSS_ASSET_CONFLUENCE_BONUS (+8) in _apply_score_penalties.
# Smaller than +10 preferred_pair bonus because confluence counting is noisier.
# Fail-safe: missing asset_class or normalization failure => no match, no bonus.
# Idempotent: _cross_asset_confluence field is set once per pick and checked before bonus.
CROSS_ASSET_CONFLUENCE_BONUS = 8

# ETF ÔåÆ underlying asset root mapping (so ETF picks can align with crypto/commodity/equity)
_ETF_UNDERLYING_MAP = {
    "BITO": "BTC",
    "BITI": "BTC",
    "BTF": "BTC",
    "GBTC": "BTC",
    "IBIT": "BTC",
    "FBTC": "BTC",
    "ETHE": "ETH",
    "ETHA": "ETH",
    "FETH": "ETH",
    "ETH": "ETH",
    "GLD": "GC",
    "IAU": "GC",
    "GLDM": "GC",
    "SLV": "SI",
    "SIVR": "SI",
    "USO": "CL",
    "UCO": "CL",
    "SCO": "CL",
    "UNG": "NG",
    "BOIL": "NG",
    "KOLD": "NG",
    "SPY": "ES",
    "VOO": "ES",
    "IVV": "ES",
    "QQQ": "NQ",
    "QQQM": "NQ",
    "DIA": "YM",
    "IWM": "RTY",
}


def _normalize_symbol_root(symbol: str, asset_class: str) -> Optional[str]:
    """Normalize a symbol to its underlying asset root for cross-class matching.

    Returns None if normalization fails or asset_class is unrecognized for cross-class linking.
    Equities are returned as-is (they generally don't link to other asset classes).
    """
    if not symbol:
        return None
    sym = str(symbol).upper().strip()
    ac = str(asset_class or "").upper().strip()
    if ac == "ETF_LEVERAGED":
        ac = "ETF"
    elif ac == "INDEX":
        ac = "FUTURES"
    try:
        if ac == "CRYPTO":
            # BTCUSDT -> BTC, ETHUSDC -> ETH
            for suffix in ("USDT", "USDC", "BUSD", "USD"):
                if sym.endswith(suffix) and len(sym) > len(suffix):
                    return sym[: -len(suffix)]
            return sym
        if ac == "FUTURES":
            # GC=F -> GC, BTC1! -> BTC, ES1! -> ES
            root = sym.replace("=F", "")
            # Strip trailing "!" month codes like 1!, 2!, !, etc.
            root = re.sub(r"\d*!$", "", root)
            return root or None
        if ac == "FOREX":
            # EURUSD=X -> EURUSD
            return sym.replace("=X", "")
        if ac == "COMMODITY":
            return sym.replace("=F", "")
        if ac == "ETF":
            return _ETF_UNDERLYING_MAP.get(sym, sym)
        if ac == "BOND":
            return sym.replace("=X", "").replace("=F", "")
        if ac == "EQUITY":
            # Equities don't generally link cross-class; keep as-is (will only match same class)
            return sym
        return sym or None
    except (AttributeError, TypeError):
        return None


def _normalize_direction(direction: str) -> Optional[str]:
    """Collapse direction variants to LONG/SHORT."""
    if not direction:
        return None
    d = str(direction).upper().strip()
    if d in ("LONG", "BUY", "BULLISH"):
        return "LONG"
    if d in ("SHORT", "SELL", "BEARISH"):
        return "SHORT"
    return None


def _compute_cross_asset_confluence(all_picks: List[Dict[str, Any]]) -> Dict[str, int]:
    """Compute cross-asset confluence counts across all picks.

    Groups picks by (normalized_root, direction) and counts the number of DISTINCT
    asset_class values present in each group. Returns a map of pick_id -> confluence_count
    where confluence_count is the number of distinct asset classes aligning on that
    root+direction (>=2 means cross-asset confluence exists).

    Side-effect: stamps each matching pick with pick["_cross_asset_confluence"] = count
    (idempotent: only set once, skipped if already present).

    Fail-safe: picks with missing symbol/direction/asset_class are silently skipped.
    """
    confluence_map: Dict[str, int] = {}
    if not all_picks:
        return confluence_map
    # Build groups: (root, direction) -> set of asset_classes and list of pick refs
    groups: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for pick in all_picks:
        try:
            ac_raw = str(pick.get("asset_class", "") or "").upper().strip()
            if not ac_raw:
                continue
            ac_norm = (
                "ETF"
                if ac_raw == "ETF_LEVERAGED"
                else ("FUTURES" if ac_raw == "INDEX" else ac_raw)
            )
            root = _normalize_symbol_root(pick.get("symbol", ""), ac_raw)
            direction = _normalize_direction(pick.get("direction", ""))
            if not root or not direction:
                continue
            key = (root, direction)
            entry = groups.setdefault(key, {"asset_classes": set(), "picks": []})
            entry["asset_classes"].add(ac_norm)
            entry["picks"].append(pick)
        except (AttributeError, TypeError, KeyError):
            continue  # Fail-safe: skip malformed picks
    # Assign counts
    for key, entry in groups.items():
        count = len(entry["asset_classes"])
        if count < 2:
            continue
        for pick in entry["picks"]:
            pid = str(pick.get("id", "") or "").strip()
            # Idempotency: only set if not already present
            if "_cross_asset_confluence" not in pick:
                pick["_cross_asset_confluence"] = count
            if pid:
                confluence_map[pid] = count
    return confluence_map


SMART_PICKS_MAX_CONFIDENCE = 0.95  # Cap overconfident picks
ACTIVE_PICKS_MIN_RR = 1.0
SMART_PICKS_MIN_RR = 1.5
SMART_PICKS_MAX_RR = 3.5  # R:R ceiling — widened: docstring golden combo is R:R 2.0-3.0, old 1.75 was too narrow
SMART_PICKS_MIN_ML_SCORE = 0.0  # Disabled - ML scores not currently populated
# 2026-04-14 edge-filter audit (all-picks, no cherry-picking):
# Trust≥3 outperforms Trust≥5 for crypto (PF 1.98 on n=689 vs PF 1.96 on n=348)
# and equity (PF 2.62 on n=119 vs PF 2.09 on n=201). Lowering from 5ÔåÆ3 widens
# the net while retaining edge. PF CI lower bound > 1.5 for both at Trust≥3.
# For forex, trust filter hurts — FwdWR≥50 is the correct forex gate.
SMART_PICKS_MIN_TRUST_SCORE = 3  # LOWERED 5ÔåÆ3 (2026-04-14): wider net, PF still >1.9
# Active picks (non-crypto): reject when 0 < trust_score < MIN (same floor as smart picks).
# Product note (2026-04-15): passes_active_gate previously used a hard-coded "< 4", which
# rejected trust_score==3 while SMART_PICKS_MIN_TRUST_SCORE was already 3. Using this
# constant aligns active gate with smart picks (2026-04-14 edge audit: Trust>=3 keeps PF edge).
# Forex still uses FwdWR in passes_smart_gate, not trust alone.
ACTIVE_NON_CRYPTO_MIN_TRUST_SCORE = 3  # LOWERED 5ÔåÆ3 to match smart picks

# 2026-04-14 edge-filter convergence (Claude + Cursor + Mercury):
# CRYPTO SHORT picks had PF 1.54 vs LONG 1.91 in the last-7d validation window
# (dashboard ledger, ghost-filtered, n=2,060 baseline PF 1.69). Combined with
# LONG + Score>=50 + Trust>=3 the filter pushes to PF 5.48 on n=438 (Wilson
# WR_LB 64.9%). The LONG-only constraint on CRYPTO is the single net-new
# hard-filter addition vs the existing Smart Picks gate (MIN_SCORE=60,
# MIN_TRUST_SCORE=5). Non-crypto assets are unaffected — they already have
# per-asset thresholds calibrated separately. Keep the flag so we can flip
# it off instantly if live performance diverges from backtest.
#
# Caveat: trust_score is re-computed at dashboard generation time via
# enrich_picks_with_trust_score(recent_closed) — historical trust_score
# values reflect later strategy performance (partial lookahead in backtest).
# For LIVE picks the filter is forward-clean because trust_score is read from
# the strategy_performance snapshot available AT pick creation time.
SMART_PICKS_CRYPTO_LONG_ONLY = True

# ── PSI (Population Stability Index) drift gate (task J / handoff P1) ──
# PSI measures feature distribution drift between training and production.
# Industry convention: PSI < 0.10 stable, 0.10-0.25 moderate, > 0.25 = material
# drift — models/rules keyed on that feature become unreliable. When any feature
# in alpha_engine/data/feature_health_report.json exceeds this threshold, the
# pick pipeline is in a drifted regime. Currently SHADOW-mode: we log and tag
# but do not actually reject, because we have no per-strategy ÔåÆ per-feature
# ownership map yet (global drift would kill the book). Remove shadow after
# 48h of forward observation + decision to hard-enforce, per handoff guidance.
PSI_BLOCK_THRESHOLD = 0.25
_PSI_REPORT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "alpha_engine", "data", "feature_health_report.json",
)
_PSI_CACHE: Dict[str, Any] = {"mtime": 0.0, "max_psi": 0.0, "drifted": []}

# ── KS concept-drift auto-pause gate (swarm master synthesis 2026-05-14) ──
# Reads hf_stats.concept_drift from dashboard_data.json. When KS_D exceeds
# DRIFT_PAUSE_RATIO × critical threshold, new CRYPTO and FOREX picks are
# paused at the admission gate (fail-open: any read error = pass through).
# KS_D = 0.312576, critical = 0.047292 → ratio = 6.6× at 2026-05-14 (SEVERE).
# Kill-switch: env DRIFT_PAUSE_GATE_ENABLED=0. Ratio threshold: DRIFT_PAUSE_RATIO
# (default 3.0 — a 3× overshoot means the feature distribution has shifted enough
# that ML scores are unreliable directional signals).
_DRIFT_PAUSE_RATIO = float(os.environ.get("DRIFT_PAUSE_RATIO", "3.0"))
_DRIFT_DASHBOARD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "audit_dashboard", "data", "dashboard_data.json",
)
_DRIFT_CACHE: Dict[str, Any] = {"ts": 0.0, "ks_d": 0.0, "critical": 1.0, "alert": False}
_DRIFT_CACHE_TTL = 300.0  # re-read at most every 5 minutes


def _get_concept_drift_ratio() -> float:
    """Return KS_D / critical from dashboard_data.json::hf_stats.concept_drift.
    Cached for _DRIFT_CACHE_TTL seconds. Returns 0.0 on any error (fail-open)."""
    import time as _time
    now = _time.monotonic()
    if now - _DRIFT_CACHE["ts"] < _DRIFT_CACHE_TTL:
        crit = _DRIFT_CACHE["critical"]
        return _DRIFT_CACHE["ks_d"] / crit if crit > 0 else 0.0
    try:
        with open(_DRIFT_DASHBOARD_PATH, "r", encoding="utf-8") as _f:
            _dd = json.load(_f)
        _cd = (_dd.get("hf_stats") or {}).get("concept_drift") or {}
        # dashboard_data.json keys: "ks_D" / "ks_critical_05" (verified 2026-05-14)
        _ks_d = float(_cd.get("ks_D") or _cd.get("KS_D") or 0)
        _crit = float(_cd.get("ks_critical_05") or _cd.get("critical") or 1)
        _alert = bool(_cd.get("drift_alert", False))
        _DRIFT_CACHE.update(ts=now, ks_d=_ks_d, critical=_crit, alert=_alert)
        return _ks_d / _crit if _crit > 0 else 0.0
    except Exception as _e:
        logger.debug("Drift cache load failed: %s", _e)
        _DRIFT_CACHE["ts"] = now
        return 0.0


def _get_max_psi() -> Tuple[float, List[str]]:
    """Return (max_psi, drifted_feature_names) from the cached feature health
    report. Cheap: reads the JSON only when its mtime changes. Returns (0.0, [])
    on any error so the gate never breaks admission.
    """
    try:
        st = os.stat(_PSI_REPORT_PATH)
    except OSError:
        return 0.0, []
    if st.st_mtime == _PSI_CACHE["mtime"]:
        return _PSI_CACHE["max_psi"], _PSI_CACHE["drifted"]
    try:
        with open(_PSI_REPORT_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)
        psi_scores = report.get("psi_scores", {}) or {}
        if not isinstance(psi_scores, dict) or not psi_scores:
            _PSI_CACHE.update(mtime=st.st_mtime, max_psi=0.0, drifted=[])
            return 0.0, []
        max_psi = 0.0
        drifted: List[str] = []
        for fname, val in psi_scores.items():
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            if v > max_psi:
                max_psi = v
            if v > PSI_BLOCK_THRESHOLD:
                drifted.append(str(fname))
        _PSI_CACHE.update(mtime=st.st_mtime, max_psi=max_psi, drifted=drifted)
        return max_psi, drifted
    except Exception as e:
        logger.debug("PSI cache load failed: %s", e)
        _PSI_CACHE.update(mtime=st.st_mtime, max_psi=0.0, drifted=[])
        return 0.0, []


# ── CRYPTO SHORT regime-gate (Phase 2-A panel 7/8, 2026-04-29) ────────────
# Phase 2-A CRYPTO panel finding: CRYPTO SHORT picks n=448 PF 1.000 (perfectly
# break-even). Panel recommendation 7/8: "disable or regime-gate SHORT direction".
#
# Implemented as TWO opt-in env-flags (both default-off, no behavior regression):
#   - CRYPTO_SHORT_DISABLED=1: kill-switch, blocks ALL crypto SHORTs
#   - CRYPTO_SHORT_REGIME_GATE_ENABLED=1: blocks crypto SHORTs only in BULL regime
#
# Bull-regime detection prefers existing `alpha_engine/data/regime_report.json`
# (BULL/BEAR/CHOPPY produced by alpha_engine/regime_router.py + multi_asset
# _test_portfolios.py pipeline) — falls back to BTC 50d-MA proxy if missing.
# Phase 4 will replace this with the HMM regime detector (Gate 1 P1).
_REGIME_REPORT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "alpha_engine", "data", "regime_report.json",
)
_REGIME_CACHE: Dict[str, Any] = {"mtime": 0.0, "is_bull": True}

# Regime labels considered "bull" (block SHORTs when regime-gate is on).
# Anything NOT in this set (BEAR, BEARISH, CHOPPY, RANGING, NEUTRAL, etc.) is
# treated as a permissive regime where SHORTs are allowed.
_BULL_REGIME_LABELS = frozenset({"BULL", "BULLISH", "TRENDING_UP", "STRONG_BULL"})


def _is_crypto_bull_regime() -> bool:
    """Return True if BTC/crypto is in a confirmed bull regime.

    Reading priority:
      1. alpha_engine/data/regime_report.json["regime"] (canonical source,
         updated hourly by regime_router.py / multi_asset_test_portfolios.py)
      2. BTC trend proxy via regime_report["btc_trend"] == "UP"
         (fallback if regime label is missing/unknown)
      3. Conservative default: True (preserves "block SHORTs" behavior when
         regime-gate is on but data is missing — matches operator intent of a
         cautious gate that errs on the side of NOT shorting)

    Cached per-mtime so we don't re-read the file on every pick.
    """
    try:
        st = os.stat(_REGIME_REPORT_PATH)
    except (OSError, FileNotFoundError):
        # No regime artifact — conservative default: assume bull (block SHORTs)
        return True
    if st.st_mtime == _REGIME_CACHE.get("mtime"):
        return bool(_REGIME_CACHE.get("is_bull", True))
    try:
        with open(_REGIME_REPORT_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        regime_label = str(data.get("regime", "") or "").upper().strip()
        btc_trend = str(data.get("btc_trend", "") or "").upper().strip()
        if regime_label in _BULL_REGIME_LABELS:
            is_bull = True
        elif regime_label:
            # Known non-bull label (BEAR, CHOPPY, RANGING, NEUTRAL, FLAT, ...)
            is_bull = False
        elif btc_trend in ("UP", "BULLISH"):
            is_bull = True
        else:
            # Unknown regime + non-bullish trend ÔåÆ allow SHORTs (not bull)
            is_bull = False
        _REGIME_CACHE.update(mtime=st.st_mtime, is_bull=is_bull)
        return is_bull
    except Exception as e:  # pragma: no cover - defensive
        logger.debug("Regime cache load failed: %s", e)
        _REGIME_CACHE.update(mtime=st.st_mtime, is_bull=True)
        return True


def _is_probation_symbol(symbol: str) -> bool:
    """Return True if the symbol is currently in the 3-stage PROBATION stage."""
    return symbol in PROBATION_STATUS


def _crypto_short_gate_block_reason(pick: Dict[str, Any]) -> Optional[str]:
    """Return a block-reason string if this CRYPTO SHORT pick should be
    blocked under the Phase 2-A regime-gate flags, or None to pass through.

    Both flags default-off ÔåÆ returns None ÔåÆ no behavior change.
    """
    asset_class = str(pick.get("asset_class", "") or "").upper()
    if asset_class != "CRYPTO":
        return None
    direction = str(
        pick.get("direction") or pick.get("signal_type") or ""
    ).upper()
    if direction not in ("SHORT", "SELL"):
        return None
    # Kill-switch (most aggressive — wins over regime-gate)
    if os.environ.get("CRYPTO_SHORT_DISABLED", "0") == "1":
        return "crypto_short_killed_globally"
    # Regime-gate (moderate). Default ON as of 2026-05-13:
    # 4/4 swarm consensus + verified 14d CRYPTO LONG 53.6%/PF 2.06 vs
    # SHORT 31.0%/PF 0.55 (22.6pp asymmetry). Only blocks SHORTs when
    # BTC regime is bull. Current state (CHOPPY) = no-op until regime flips.
    # Override: CRYPTO_SHORT_REGIME_GATE_ENABLED=0.
    if (
        os.environ.get("CRYPTO_SHORT_REGIME_GATE_ENABLED", "1") == "1"
        and _is_crypto_bull_regime()
    ):
        return "crypto_short_blocked_in_bull_regime"
    return None


# ── Concept-drift auto-pause gate (P0 2026-05-14) ────────────────────────────
# Reads audit_dashboard/data/dashboard_data.json::hf_stats.concept_drift.
# Pauses NEW sizing on a class when its drift exceeds the effect-size threshold.
# Threshold per 3/3 swarm consensus (deepseek + xai + kilo, 2026-05-14T23:31Z,
# swarm_runs/second-opinion-20260514T233053Z): D > 2 * ks_critical_05.
# Per-asset-class when by_asset_class metrics available; otherwise system-wide
# only fires at D > 3 * ks_critical_05 (avoids killing productive classes).
# Fail-open on payload absent or stale (> 36h) — no behavior change without data.
# Disable: DRIFT_AUTO_PAUSE_DISABLED=1.
_DRIFT_PAYLOAD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "audit_dashboard", "data", "dashboard_data.json",
)
_DRIFT_CACHE: Dict[str, Any] = {
    "mtime": 0.0,
    "system_breached": False,
    "system_severe": False,
    "by_class_breached": {},  # CLASS -> True if D > 2*critical
    "payload_age_hours": None,
}
_DRIFT_THRESHOLD_MULT = 2.0
_DRIFT_SYSTEM_WIDE_MULT = 3.0
_DRIFT_MAX_PAYLOAD_AGE_HOURS = 36.0


def _load_drift_state() -> Dict[str, Any]:
    """Refresh drift cache when payload mtime changes. Always fail-open."""
    try:
        st = os.stat(_DRIFT_PAYLOAD_PATH)
    except (OSError, FileNotFoundError):
        return _DRIFT_CACHE  # no payload -> permissive
    if st.st_mtime == _DRIFT_CACHE.get("mtime"):
        return _DRIFT_CACHE
    try:
        with open(_DRIFT_PAYLOAD_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:  # noqa: BLE001 — any parse error is permissive
        _DRIFT_CACHE.update(mtime=st.st_mtime)
        return _DRIFT_CACHE
    hf = (data or {}).get("hf_stats") or {}
    cd = hf.get("concept_drift") or {}
    # Stale-payload check: fail open if older than threshold.
    age_h = None
    try:
        gen = hf.get("generated_at")
        if gen:
            gen_dt = datetime.fromisoformat(str(gen).replace("Z", "+00:00"))
            if gen_dt.tzinfo is None:
                gen_dt = gen_dt.replace(tzinfo=timezone.utc)
            age_h = (datetime.now(timezone.utc) - gen_dt).total_seconds() / 3600.0
    except Exception:  # noqa: BLE001
        age_h = None
    if age_h is not None and age_h > _DRIFT_MAX_PAYLOAD_AGE_HOURS:
        # Stale snapshot -> ignore. Real-money safety prefers fail-open over
        # acting on weeks-old drift numbers.
        _DRIFT_CACHE.update(
            mtime=st.st_mtime,
            system_breached=False,
            system_severe=False,
            by_class_breached={},
            payload_age_hours=age_h,
        )
        return _DRIFT_CACHE
    d_sys = cd.get("ks_D")
    crit_sys = cd.get("ks_critical_05")
    sys_breached = False
    sys_severe = False
    if isinstance(d_sys, (int, float)) and isinstance(crit_sys, (int, float)) and crit_sys > 0:
        sys_breached = d_sys > _DRIFT_THRESHOLD_MULT * crit_sys
        sys_severe = d_sys > _DRIFT_SYSTEM_WIDE_MULT * crit_sys
    # Per-class drift (when available). Schema: hf_stats.by_asset_class[CLASS].concept_drift.{ks_D, ks_critical_05}
    by_class = {}
    bac = hf.get("by_asset_class") or {}
    if isinstance(bac, dict):
        for cls, m in bac.items():
            if not isinstance(m, dict):
                continue
            ccd = m.get("concept_drift") or {}
            d_c = ccd.get("ks_D")
            crit_c = ccd.get("ks_critical_05")
            if isinstance(d_c, (int, float)) and isinstance(crit_c, (int, float)) and crit_c > 0:
                by_class[str(cls).upper()] = d_c > _DRIFT_THRESHOLD_MULT * crit_c
    _DRIFT_CACHE.update(
        mtime=st.st_mtime,
        system_breached=sys_breached,
        system_severe=sys_severe,
        by_class_breached=by_class,
        payload_age_hours=age_h,
    )
    return _DRIFT_CACHE


def _passes_drift_auto_pause_gate(pick: Dict[str, Any]) -> Optional[str]:
    """Return block-reason string when concept-drift gate should pause this
    pick. Default-ON but fails open on missing/stale payload.

    Block rules:
      - per-class breach (D > 2 * critical_05 in that class's slice) -> block
        only picks of that class
      - system-wide severe (D > 3 * critical_05 system-wide) -> block all classes
      - system-wide moderate (D > 2 * critical_05 but < 3x) -> warn only, no block
    """
    if os.environ.get("DRIFT_AUTO_PAUSE_DISABLED", "0") == "1":
        return None
    state = _load_drift_state()
    asset_class = str(pick.get("asset_class", "") or "").upper()
    if state.get("system_severe"):
        return "drift_auto_pause_system_severe"
    if asset_class and state.get("by_class_breached", {}).get(asset_class):
        return f"drift_auto_pause_class_{asset_class.lower()}"
    return None


# ── M-016: Live-vs-backtest WR drift circuit breaker ─────────────────────────
# Reads fwd_vs_bt_divergence rows from dashboard_data.json (same payload as
# _load_drift_state). Strategies with wr_z < BT_WR_DRIFT_Z_THRESHOLD (default
# -3.5, ~99.9th percentile decay) are blocked when gate is ON.
#
# Default: OFF (BT_WR_DRIFT_GATE_ENABLED=0) — shadow mode first, then promote.
# Kill-switch: BT_WR_DRIFT_GATE_ENABLED=0  → no block (fail-open).
# Override threshold: BT_WR_DRIFT_Z_THRESHOLD=<float>  (more negative = stricter).
# ─────────────────────────────────────────────────────────────────────────────

BT_WR_DRIFT_Z_THRESHOLD: float = -3.5
_BT_WR_DRIFT_CACHE: Dict[str, Any] = {"mtime": 0.0, "blocked_strategies": frozenset()}
_DASHBOARD_DATA_PATH_QG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "audit_dashboard", "data", "dashboard_data.json",
)


def _load_bt_wr_drift_state() -> frozenset:
    """Return frozenset of strategy names whose live WR breaches the Z threshold.

    Reads fwd_vs_bt_divergence.rows from dashboard_data.json. Caches on mtime.
    Fails open (returns empty set) on any error.
    """
    try:
        mtime = os.path.getmtime(_DASHBOARD_DATA_PATH_QG)
        if mtime == _BT_WR_DRIFT_CACHE["mtime"]:
            return _BT_WR_DRIFT_CACHE["blocked_strategies"]
        threshold = float(os.environ.get("BT_WR_DRIFT_Z_THRESHOLD", str(BT_WR_DRIFT_Z_THRESHOLD)))
        import json as _json_bwd
        with open(_DASHBOARD_DATA_PATH_QG, "r", encoding="utf-8") as _f:
            dd = _json_bwd.load(_f)
        rows = (dd.get("fwd_vs_bt_divergence") or {}).get("rows") or []
        blocked: frozenset = frozenset(
            str(r.get("strategy", "")).lower()
            for r in rows
            if isinstance(r.get("wr_z"), (int, float)) and r["wr_z"] < threshold
        )
        _BT_WR_DRIFT_CACHE.update(mtime=mtime, blocked_strategies=blocked)
        return blocked
    except Exception:
        _BT_WR_DRIFT_CACHE.update(mtime=0.0, blocked_strategies=frozenset())
        return frozenset()


def _passes_bt_wr_drift_gate(pick: Dict[str, Any]) -> Optional[str]:
    """Return block-reason string when strategy's live WR has decayed beyond threshold.

    Default OFF (BT_WR_DRIFT_GATE_ENABLED env var). Fail-open on missing data.
    """
    if os.environ.get("BT_WR_DRIFT_GATE_ENABLED", "0") not in ("1", "true", "TRUE"):
        return None
    strategy = str(pick.get("strategy", "") or "").lower()
    if not strategy:
        return None
    blocked = _load_bt_wr_drift_state()
    if strategy in blocked:
        return f"m016_bt_wr_drift_blocked:{strategy}"
    return None


# ── CRYPTO dynamic quarantine cache (2026-05-15 swarm review fix) ──
# Cached at module load + invalidated on file-mtime change to avoid hot-path
# file I/O. passes_active_gate() is called per-pick; with n=8k CRYPTO picks,
# per-call json.load() was adding ~8k file opens per dashboard regen cycle.
_CRYPTO_QUARANTINE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "audit_dashboard", "data", "crypto_quarantine.json",
)
_CRYPTO_QUARANTINE_CACHE: dict = {"strategies": frozenset(), "mtime": -1.0}


def _get_crypto_quarantine_strategies() -> frozenset:
    """Return cached set of quarantined strategy names (lower-cased). Reloads on mtime change."""
    try:
        mtime = os.path.getmtime(_CRYPTO_QUARANTINE_PATH)
        if mtime != _CRYPTO_QUARANTINE_CACHE["mtime"]:
            import json as _json_cq
            with open(_CRYPTO_QUARANTINE_PATH, "r", encoding="utf-8") as _f:
                data = _json_cq.load(_f)
            _CRYPTO_QUARANTINE_CACHE["strategies"] = frozenset(
                str(s).lower() for s in data.get("quarantined", [])
            )
            _CRYPTO_QUARANTINE_CACHE["mtime"] = mtime
    except Exception:
        pass  # fail-open: return cached (possibly empty) set
    return _CRYPTO_QUARANTINE_CACHE["strategies"]


# M-004: Source-system-level auto-quarantine warn cache (60s TTL).
# Reads audit_dashboard/data/dashboard_data.json leaderboard to aggregate
# per-(source_system, asset_class) PF, WR, and volume share.  Only CRYPTO.
# Env flag: SOURCE_QUARANTINE_WARN_ENABLED=1 (default OFF — observational).
_SOURCE_QUARANTINE_STATS_CACHE: dict = {"ts": 0.0, "stats": {}}
_SOURCE_QUARANTINE_STATS_TTL_SEC = 60.0
_DASHBOARD_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "audit_dashboard", "data", "dashboard_data.json",
)


def _get_source_quarantine_stats() -> dict:
    """Return per-(source_system, asset_class) stats dict, cached 60s. Fail-open → {}.

    Structure: {(source_system_lower, asset_class_upper): {"pf": float, "wr": float,
    "n": int, "vol_share": float}}  — vol_share is fraction of class total n.
    """
    import time as _t_sqw
    now = _t_sqw.time()
    if (now - _SOURCE_QUARANTINE_STATS_CACHE["ts"]) < _SOURCE_QUARANTINE_STATS_TTL_SEC:
        return _SOURCE_QUARANTINE_STATS_CACHE["stats"]
    try:
        import json as _json_sqw
        with open(_DASHBOARD_DATA_PATH, "r", encoding="utf-8") as _f_sqw:
            _dd = _json_sqw.load(_f_sqw)
        leaderboard = _dd.get("leaderboard") or []
        # Aggregate n, weighted PF numerator/denominator, wins per (source, class)
        _agg: dict = {}  # (src, cls) -> {n, gross_win, gross_loss, wins}
        for _row in leaderboard:
            _src = str(_row.get("source_system") or "").strip().lower()
            _cls = str(_row.get("asset_class") or "").strip().upper()
            if not _src or not _cls:
                continue
            try:
                _n = int(_row.get("fwd_trades") or 0)
                _wr = float(_row.get("fwd_wr") or 0)
                _pf = float(_row.get("fwd_pf") or 1.0)
            except (TypeError, ValueError):
                continue
            if _n <= 0:
                continue
            _wins = int(round(_wr / 100.0 * _n))
            _losses = _n - _wins
            # avg_win / avg_loss not available per-strategy; use PF as gross ratio proxy
            # gross_win / gross_loss = PF  →  gross_win = PF * gross_loss
            # We store wins/losses counts for class-wide WR, and n for volume share.
            _key = (_src, _cls)
            if _key not in _agg:
                _agg[_key] = {"n": 0, "wins": 0, "losses": 0, "pf_num": 0.0, "pf_den": 0.0}
            _agg[_key]["n"] += _n
            _agg[_key]["wins"] += _wins
            _agg[_key]["losses"] += _losses
            # weight PF by n for a volume-weighted composite
            _agg[_key]["pf_num"] += _pf * _n
            _agg[_key]["pf_den"] += _n
        # Class totals for volume share
        _class_n: dict = {}
        for (_src, _cls), _v in _agg.items():
            _class_n[_cls] = _class_n.get(_cls, 0) + _v["n"]
        # Build final stats dict
        _stats: dict = {}
        for (_src, _cls), _v in _agg.items():
            _tot_n = _v["n"]
            _pf_composite = (_v["pf_num"] / _v["pf_den"]) if _v["pf_den"] > 0 else 1.0
            _wr_composite = ((_v["wins"] / _tot_n) * 100.0) if _tot_n > 0 else 0.0
            _vol_share = (_tot_n / _class_n[_cls]) if _class_n.get(_cls, 0) > 0 else 0.0
            _stats[(_src, _cls)] = {
                "pf": round(_pf_composite, 4),
                "wr": round(_wr_composite, 2),
                "n": _tot_n,
                "vol_share": round(_vol_share, 4),
            }
        _SOURCE_QUARANTINE_STATS_CACHE["stats"] = _stats
        _SOURCE_QUARANTINE_STATS_CACHE["ts"] = now
        return _stats
    except Exception:
        return {}  # fail-open: never block picks if dashboard_data.json is missing/stale


BLOCKED_ACTIVE_TRUST_LABELS = {"AVOID", "BANNED"}
# UNTRUSTED added: client-side already blocked BANNED+UNTRUSTED; server-side must match.
# 7 UNTRUSTED picks from kimi_riseoftheclaw were leaking through with score=120 (2026-04-04).
BLOCKED_ACTIVE_TRUST_TIERS = {"BANNED", "AVOID", "UNTRUSTED"}

# Per Gate 1 Q4 = A (5/5 UNANIMOUS panel + 8-stream consensus 2026-04-29):
# Trust-tier model is calibrated for CRYPTO. Verified inverted on EQUITY:
#   EQUITY UNTRUSTED n=185 +$246 (TOP); RELIABLE n=26 -$10 (LOSING)
#   CRYPTO RELIABLE  n=716 +$107;       BANNED   n=157 -$57 (NORMAL)
# Therefore: bypass trust-tier gate by default for ALL non-CRYPTO classes.
# Each class can be force-re-enabled via TRUST_TIER_GATE_FORCE_<CLASS>_ENABLED=1
# if research validates a class-specific trust model.
NON_CRYPTO_TRUST_EXEMPT_CLASSES = frozenset(
    {"EQUITY", "FOREX", "COMMODITY", "ETF", "BOND", "FUTURES"}
)
AUDITED_PM_MIN_HISTORY_WR = 0.65
AUDITED_PM_MIN_HISTORY_TRADES = 20
AUDITED_PM_MIN_SOURCE_COUNT = 2
AUDITED_PM_SCORE_BONUS = 10
SMART_CONCENTRATION_MODERATE_PENALTY = 8
SMART_CONCENTRATION_HIGH_PENALTY = 15

# Age limits (hours)
CRYPTO_MAX_AGE_HOURS = 168  # RELAXED: 7 days (was 72h)
NON_CRYPTO_MAX_AGE_HOURS = 240  # 10 days for forex/equity

# Source tiers that are allowed (exclude EXPERIMENTAL)
ALLOWED_SOURCE_TIERS = {"TOP_TIER", "PROVEN", "WATCH"}

# Permanently killed strategies (from TODO analysis)
PERMANENTLY_KILLED_STRATEGIES = {
    # Copy-trader sentiment (not real copy trading)
    "binance_smart_money",
    # Proven losers
    "hl_funding_fade",
    # 2026-05-01: claude_gainer_st = 778/790 PROVEN picks, 26.5% WR, -355% total PnL
    # Drives trust-tier inversion (PROVEN cohort 26.7% WR = worst tier)
    "claude_gainer_st",
    "cta_tsmom_blend",
    "yahoo_analyst_consensus",
    "winner_pattern_precursor",
    "inverse_winner_pattern_precursor",
    # Rapid Fire now_picks.json banned strategies (2026-04-02 leak fix: 183/500 picks were from these)
    "macd_crossover",  # 25-31% WR LONG/SHORT, 139 leaked picks
    "rsi_overbought",  # 29% WR SHORT, -17.1% PnL, 44 leaked picks
    # 0% WR strategies ( bleeding capital, identified 2026-03-26)
    "stoch-rsi-crypto",  # 0% WR, -$4,000
    "keltner_compression_expansion_doge",  # 2.2% WR, -$57
    "keltner_compression_expansion_doge_v1",  # 0% WR baseline
    "macd-momentum",  # 0% WR, -$28,340
    # "MeanReversionBB",  # REHABBED 2026-04-05 claude-bus-setup: 77.8% WR +25.4% PnL n=18
    #   on closed picks, PF=4.17, bootstrap 95% CI [+0.88, +2.65]% avgPnL, perm p=0.002.
    #   Only LINK-USD loses (33% WR, -2.3%). See TESTING_PROTOCOL ┬ºStage 1.
    #   Block added to BLOCKED_STRATEGY_SYMBOL_PAIRS.
    "battleground_vwap_1h_mut",  # 0% WR, -$24,000
    "vwap_deviation_reversion_doge",  # 0% WR
    "st_multi_day_momentum",  # 0% rolling WR
    "hh-hl-scout",  # 0% rolling WR
    # "claude_ml_moderate_mut",  # REHABBED 2026-04-05 claude-bus-setup: 52% WR +12.2% PnL n=25.
    #   Passes TESTING_PROTOCOL Stage 1: 2 qualifying symbols (SEI 100% WR n=5, JUP 60% WR n=5,
    #   both PF>=1.2). Loser symbols (IMX, TIA) added to BLOCKED_STRATEGY_SYMBOL_PAIRS.
    # crypto_soc family - extensive 0% WR bleeders
    "crypto_soc_delta_divergence_a03_v1",
    "crypto_soc_dynamic_risk_heat_a02_v1",
    "crypto_soc_dynamic_risk_heat_a03_v1",
    "crypto_soc_dynamic_risk_heat_a06_v1",
    "crypto_soc_dynamic_risk_heat_a07_v1",
    "crypto_soc_dynamic_risk_heat_a08_v1",
    "crypto_soc_dynamic_risk_heat_a09_v1",
    "crypto_soc_dynamic_risk_heat_a10_v1",
    "crypto_soc_mtf_orb_pivots_a02_v1",
    "crypto_soc_mtf_orb_pivots_a03_v1",
    "crypto_soc_mtf_orb_pivots_a04_v1",
    "crypto_soc_mtf_orb_pivots_a06_v1",
    "crypto_soc_mtf_orb_pivots_a07_v1",
    "crypto_soc_mtf_orb_pivots_a08_v1",
    "crypto_soc_mtf_orb_pivots_a09_v1",
    "crypto_soc_mtf_orb_pivots_a10_v1",
    "crypto_soc_proxy_decoupling_a03_v1",
    "crypto_soc_proxy_decoupling_a06_v1",
    "crypto_soc_regime_filters_a01_v1",
    "crypto_soc_regime_filters_a02_v1",
    "crypto_soc_regime_filters_a03_v1",
    "crypto_soc_regime_filters_a06_v1",
    "crypto_soc_regime_filters_a07_v1",
    "crypto_soc_regime_filters_a08_v1",
    "crypto_soc_regime_filters_a10_v1",
    "crypto_soc_vol_expansion_index_a08_v1",
    # Additional 0% WR strategies from kill list analysis
    "kimi_lgbm_features",  # 0% WR, -$43,420
    "stocktwits:QuietZonePlayers",  # 0% WR, -$36,000
    # "ttm_squeeze",                              # REMOVED 2026-04-04: unfairly tested (3/5 grade-gated,
    #                                              # only 2 real trades). John Carter's BB-inside-KC squeeze
    #                                              # has documented 60-75% WR on equities. Needs 50+ trades
    #                                              # across equities/forex/crypto before kill decision.
    "irb_hoffman",  # 0% WR, -$35,500
    "corr_kama_adaptive",  # 0% WR, -$32,000
    "Meta Learner",  # 0% WR, -$32,000
    "multi_timeframe_ema_stack",  # 0% WR, -$29,040
    "GPX_Gen10_2a4b0b",  # 0% WR, -$24,000
    "lower_wick_absorption",  # 13% WR, -$24,000
    # Anti-predictive ML timeframes
    # (block all 15m models, keep 1h/4h/1d)
    # Portfolio optimization kills (2026-03-29 analysis)
    # Data: quan_engine_position 0% WR, 13/13 SL exits, TAOUSDT only
    "quan_engine_scalp",  # 25% WR, 1793 trades, -352.88% PnL — worst strategy by total loss
    # Investigation doc: reports/quan_engine_scalp_investigation_2026-05-17.md
    # SCHEDULED AUTOPSY 2026-05-24: full family autopsy (quan_engine base + position) after MySQL
    # ghost-row purge completes (655k stale rows — PA console action pending). Fresh data needed
    # for valid resolved_n computation. Current closed_picks.json coverage: 0 rows post-purge.
    "quan_engine",           # 2026-05-06 P0-B: 0 closed + 0 active — proactively blocked
    "quan_engine_position",  # 0% WR, -$995, 100% SL exits
    # M-095 (2026-05-17): cot_positioning — COT-publication LOOK-AHEAD
    # LEAKAGE. Headline 77-78% WR / PF 4.6 is an artifact: ~85% of its 134
    # picks are CT=F (cotton); the COT signal uses CFTC data not available at
    # decision time. Deduped + ex-CT=F: n=20 / WR 30% / PF 0.51 — a loser.
    # Data-integrity kill (leakage cannot be mutated away). Verified by 5
    # agents. Removes the false COMMODITY signal from asset_class_health /
    # pf_registry aggregates. COT_DEDUP_SYSTEMS handles re-emissions; this
    # handles the strategy. MASTER_ACTION_PLAN sec 27. Rollback: remove line.
    "cot_positioning",
    # Data: maplestax 12% WR, -4.98% avg PnL, score=1
    "maplestax_vwap_cbc_flip",  # 12% WR, avg score=1, -4.98% avg PnL
    # Data: flash-crash-reversal 0% WR on 6 active, -3.65% avg PnL
    "flash-crash-reversal",  # 0% WR active, -3.65% avg PnL
    # 2026-05-06 P1-E: futures_momentum 0% WR on 56 closed, PF 0.00 — KILLED
    # 2026-05-18 OPERATOR DECISION: moved to MONITORED_FUTURES_STRATEGIES (shadow/stats mode).
    # User directive: "futures strategies should be moved from blocked to monitor — we still
    # need the stats ran so we can optimize if needed." (n=201 WR=2.0% at time of unblock)
    # "futures_momentum",  # unblocked 2026-05-18 — see MONITORED_FUTURES_STRATEGIES below
    # Day-2 audit kills (2026-05-06): Large-n bleeders at PF < 1.0
    "combined_confidence",   # 52.2% WR, PF 0.28, n=23 — wins-it-all-loses-it pattern
    "forex_rsi2_mean_reversion",  # RE-BLOCKED 2026-05-13 (post-resolver-v2): n=84 trailing-14d, WR 7.1%, PF 0.09, avg PnL -0.42%. Largest FOREX drag: removing lifts FOREX 14d WR 23.2->46.6%, PF 0.67->1.71. Connors & Alvarez RSI(2) failed empirically on majors post-resolver-v2.
    "cta_commodity_momentum_term",  # 36.2% WR, PF 0.02, n=47 — total bleed (confirms SLV/USO cancel)
    "smart_money_accumulation",  # 20.0% WR, PF 0.20, n=5 — structural loser
    # 2026-04-05: REMOVED from killed — consensus variants producing +2.2% to +4.6% winners on EQUITY class
    # (NFLX, ARM, GOOG, LIN, UNH, LLY, IBM, GOOGL, GS, PFE). Historical crypto WR was poor but EQUITY
    # application is working. Move to mutation/rehabilitation track per mutate-before-kill policy.
    # "goldmine_1x_consensus",  # was 24% crypto WR, now +3-4% EQUITY winners
    # "goldmine_2x_consensus",  # was 29% crypto WR, now +2.5% EQUITY winners
    # "goldmine_3x_consensus",  # was 12% crypto WR, now +2.2% EQUITY winners
    # 2026-04-02: Closed pick analysis — worst strategy+direction combos
    "st_rsi_momentum_confluence",  # 10% WR LONG (10W/95L, -296.5% PnL!) — WORST in entire system
    "crypto_roc_acceleration_trend_v1",  # 20% WR LONG (1W/4L)
    "crypto_drawdown_convexity_recovery_v1",  # 25% WR SHORT (2W/6L)
    "futures_ema_stack_momentum",  # 0/4=0% WR, 7 active zombie picks — killed 2026-04-02
    # 2026-04-04: MUTATION CANDIDATES — NOT killed, moved to inverse/symbol-lock pipeline
    # Per user policy: oppose killing strategies, prefer inverse/DNA mutation/symbol-lock/TP-SL tweak
    # "claude_gainer_1h",         # 14.3% WR LONG ÔåÆ inverse_claude_gainer_1h = 85.7% WR (VALIDATED)
    # "enhanced_ml_A_xgboost",   # 30.8% WR LONG ÔåÆ symbol-lock SEI/ALGO/JTO = 67%+ WR; drop TRX(0%)
    # "widened_tp_momentum_carry",# 22.2% WR ÔåÆ try tighter TP/SL or inverse
    # "Extreme Fear Contrarian Buy",# 20% WR ÔåÆ distinct from st_fear_greed_contrarian(87.7%!), try inverse
    # "crypto_adx_pullback_trendresume_v1", # 14.3% WR ÔåÆ try inverse or different symbols
    # 2026-04-04: ml_crypto_predictor LONG killed per copilot-quant-audit (responsible for -15238% cum PnL)
    # ONLY LONG direction killed — SHORT variants work (100% WR combos on FETUSDT, SUIUSDT already in _100WR_COMBOS)
    # Per mutate-before-kill: the SHORT signal has edge, LONG does not. Use ml_crypto_predictor_short_only mutation.
    "ml_crypto_predictor",  # LONG 0% WR, 41 trades, contributes -15238% — SHORT variants retained
    # 2026-04-11 leaderboard cull (peer e81e7ee5a6 verified on dashboard_data.json):
    # Conservative criteria: fwd_trades>=30, fwd_wr<=35, fwd_pf<=0.7, fwd_total_pnl<=-20
    "Value + Quality",           # n=51 WR 7.8% PF 0.15 PnL -251.27 (leaderboard cull)
    "volume_spike_breakout",     # n=189 WR 33.9% PF 0.49 PnL -158.35
    "Consecutive Beats",         # n=59 WR 20.3% PF 0.43 PnL -136.86
    "Earnings Drift",            # n=31 WR 12.9% PF 0.25 PnL -102.54
    "st_bb_squeeze_expansion",   # n=104 WR 31.7% PF 0.33 PnL -43.27
    "ML Ranker",                 # n=46 WR 30.4% PF 0.57 PnL -39.27
    # 2026-04-11 user-flagged non-crypto drain fix:
    "Dividend Aristocrats",      # n=8 WR 0.0% PnL -49.6 — EQUITY drain
    "futures_mean_reversion",    # n=2 catastrophic -88.8% single-pick tail risk
    # 2026-04-12: ETF/FUTURES drain strategies identified by per-asset-class audit
    "extreme_oversold_bounce",   # ETF: n=6 0% WR -15.5% PnL; FUTURES: n=2 0% WR — zero wins across all asset classes
    "vix_reversal",              # ETF: n=6 WR 33% -1.7% PnL; FUTURES: n=4 WR 0% -0.4% PnL; overall drain
    # 2026-04-21 HF-grade audit: Strategies with WR<35% on 15+ non-flat trades (statistically significant)
    # Each is confirmed negative-edge by dashboard_payload.json closed-pick analysis.
    "atr_regime_rsi",            # 17.2% WR, 29 trades, -10.4% PnL — anti-predictive
    "st_atr_vol_breakout",       # 22.2% WR, 27 trades, -21.5% PnL
    "st_obv_support_divergence", # 23.8% WR, 84 trades, -78.5% PnL — massive sample confirms
    "carry-trade-momentum",      # 26.7% WR, 15 trades, -2.2% PnL
    "copy_hl_lb_None",           # 32.0% WR, 278 trades, -806.4% PnL — 2nd worst strategy by total loss
    "copy_hl_lb_none",           # lowercase variant of above

    # 2026-05-24 Institutional Readiness P0 — BOND kill (0% WR across all 9 closed picks).
    # All 3 BOND strategies show consistent negative edge. See
    # reports/audit_benchmark_analysis_2026-05-24.md.
    "bond_mean_reversion",       # n=5, 0% WR, all losses
    "bond_yield_momentum",       # n=3, 0% WR, all losses
    "bond_yield_curve_slope",    # n=1, 0% WR
    # PR5 (2026-05-27): Kill antigravity_bond — 0% WR on n=9, PF 0.00.
    "antigravity_bond",          # n=9, 0% WR, Sharpe -2.465
}

# FIX: Case-insensitive kill check. Picks arrive as lowercase but kill list has mixed case.
# Codebuff audit found 33 active picks leaking through (24 from enhanced_ml_A_xgboost alone).
_KILLED_STRATEGIES_LOWER = {s.lower() for s in PERMANENTLY_KILLED_STRATEGIES}

# ── PF_REGISTRY_POLICY_EXCLUDED: sources excluded from by_asset_class_policy_clean_net view ──
# These are NOT new gate blocks — the strategies listed here are already blocked at pick
# admission (via BLOCKED_DIRECTION_TRIPLES or BLOCKED_ASSET_STRATEGY_PAIRS). Adding them
# here fixes the pf_registry canonical view so it reflects forward-state picks only
# (not historical losers that can never be admitted again).
# Used by tools/build_pf_registry.py::_load_policy_excluded() alongside BLOCKED_SOURCE_SYSTEMS.
PF_REGISTRY_POLICY_EXCLUDED: set = {
    # cta_commodity_momentum_term: LONG+SHORT blocked 2026-05-17 (n=11 WR=0%).
    # Kept here (vs BLOCKED_DIRECTION_TRIPLES only) because it also appears as
    # source_system in some COMMODITY rows.
    "cta_commodity_momentum_term",
    # futures_connors_rsi2: FUTURES picks stored pnl_pct in dollar scale (YM=F/ES=F/NQ=F
    # raw point values ≈ 140k% per pick). build_pf_registry.py now auto-drops pnl_pct > 100%
    # (DOLLAR_SCALE_ARTIFACT_THRESHOLD). Belt-and-suspenders exclusion until source is fixed.
    # Artifact discovered 2026-05-19 (Session CU): gross_profit=19,081,667, PF=613,777.
    "futures_connors_rsi2",
    # cta_replicator REMOVED 2026-05-18 (M-110): COMMODITY picks blocked by
    # BLOCKED_DIRECTION_TRIPLES (cta_cross_asset_tsmom COMMODITY LONG+SHORT).
    # FOREX cta_cross_asset_tsmom SHORT (n=120, WR=66%, PF=2.8) is T1-grade
    # and must not be flat-excluded by source_system name.
    # cta_cross_asset_tsmom REMOVED 2026-05-18 (M-110): same reason.
    # All directional blocks now handled by build_pf_registry.py direction-aware filter.
}

# Direction-specific penalties: strategies that lose in one direction but win in another
# Data: rsi_overbought SHORT = 29% WR (4W/10L) but overall 76% WR
# The strategy works for LONG but NOT for SHORT — penalize SHORT picks from it
DIRECTION_SPECIFIC_LOSERS = {
    ("rsi_overbought", "SHORT"): -15,  # 29% WR, -17.1% PnL on SHORTs
    ("macd_crossover", "LONG"): -15,  # 31% WR on LONGs
    ("macd_crossover", "SHORT"): -10,  # 25% WR on SHORTs
    ("luxalgo_confluence", "LONG"): -10,  # 35% WR on LONGs
    ("crypto_mtf_ema_slope_alignment_v1", "SHORT"): -12,  # 12% WR on SHORTs
}

# Energy stocks consistently lose — block from equity portfolios
# CVX SHADOW 2026-05-16: post-block n=12, WR=75.0%, PF=3.48 (MySQL). Removed from EQUITY_BLOCKED_SYMBOLS.
#   Tracking continues in PENDING_UNBLOCK_REVIEW (SHADOW stage — no live picks until n>=20).
#   The prior comment said "promoted to PROBATION" — this was incorrect. CVX is SHADOW (n<20).
#   Review date 2026-07-01 — if MySQL confirms n>=20, WR>=52%, PF>=1.3: promote to PROBATION_STATUS.
#   See audit_trail/symbol_reviews/CVX_review_20260519.json for full audit trail.
# XOM review 2026-07-01: post-dedup MySQL (2026-05-19) n=3 resolved (all WON), 97 OPEN.
#   Pre-dedup n=15/WR=60%/PF=1.33 was inflated. Real resolved data insufficient. PF undefined.
#   Keep blocked until n>=10 for SHADOW or n>=20 + WR>=52% + PF>=1.3 for PROBATION.
#   See audit_trail/symbol_reviews/XOM_review_20260519.json.
EQUITY_BLOCKED_SYMBOLS = {"XLE", "XOM"}  # CVX removed 2026-05-16 (SHADOW in PENDING_UNBLOCK_REVIEW)

# Per Phase 2-C FOREX panel (6/7 unanimous, 2026-04-29):
# JPY-cross pairs (CADJPY/EURJPY/NZDJPY/GBPJPY/AUDJPY) BUY-direction picks
# drove ~-45% sum_pnl on the 30d cohort. LONG and SHORT sub-cohorts are
# profitable (LONG n=102 +5.66%, SHORT n=158 +3.74%). Kill BUY-direction
# surgically; preserve LONG/SHORT.
#
# USDJPY=X excluded from kill set (panel: n=64 PF 9.50 — keep).
# Default-on. Rollback: JPY_CROSS_BUY_KILL_DISABLED=1
# 2026-05-08: TEMP DISABLED via JPY_CROSS_BUY_KILL_DISABLED=1 default.
# The -45.43% 30d loss was on phantom-expired data. Re-evaluate after resolver fix.
# See reports/HFPA_PHASE-2-findings-FOREX-2026-04-29.md
# See docs/PERFORMANCE_DEEP_DIVE_MAY82026.md (Section 7.4)
JPY_CROSS_PAIRS = frozenset({
    "CADJPY=X", "EURJPY=X", "NZDJPY=X",
    "GBPJPY=X", "AUDJPY=X",
})

# ─────────────────────────────────────────────────────────────────────
# ETF symbol blacklist (Phase 2-E ETF panel verdict 2026-04-29)
# ─────────────────────────────────────────────────────────────────────
# Per Phase 2-E ETF panel
# (reports/HFPA_PHASE-2-findings-ETF-2026-04-29.md), 6/6 UNANIMOUS:
#
#   ETF 30d: Tier 1 CANDIDATE (4/6 TIER_1, 2/6 CANDIDATE) — n=38 (under
#   PROVEN floor of 200) — but IWM and GLD are NEGATIVE-edge symbols
#   dragging the sector ETF (XLK/XLE/QQQ/SOXX) edge.
#
#   Per-symbol verification (audit_dashboard/data/dashboard_data.json
#   recent_closed, 2026-04-29; n>=3):
#       IWM (small-cap):   n= 16  WR 43.8%  sum -11.67%  KILL (panel 6/6)
#       GLD (gold):        n= 11  WR 36.4%  sum  -6.23%  KILL (panel 6/6)
#       XLF:               n=  3  WR 33.3%  sum  -1.54%  KEEP (small n)
#       SPY (broad):       n= 10  WR 50.0%  sum  -0.09%  KEEP (flat, not bad)
#       QQQ (broad-tech):  n= 13  WR 61.5%  sum  +5.24%  KEEP
#       XLE (energy):      n= 16  WR 56.2%  sum  +7.91%  KEEP
#       XLK (tech):        n=  7  WR 71.4%  sum +14.55%  KEEP
#
# Net effect: removes the two clear drags (sum -17.90%) while preserving
# the sector ETF + broad-market edge driver.
#
# Default-on. Rollback: ETF_IWM_GLD_KILL_DISABLED=1
#
# 2026-05-16 extension: SLV (Silver ETF) added via quant-analyst ETF PF audit.
#   Re-verification (dashboard_data.json 2026-05-16T02:47Z, recent_closed n=107):
#       SLV (silver):      n=  2  WR  0.0%  sum -15.74%  KILL
#       IWM (small-cap):   n= 19  WR 37.0%  sum -14.82%  already blocked
#       GLD (gold):        n= 11  WR 36.0%  sum  -6.23%  already blocked
#   SLV: both picks are kimi_riseoftheclaw SL_HIT (-10.30%, -5.44%).
#   Impact: adding SLV lifts ETF PF from 1.320 → 1.532 (Tier-2 ≥1.5 threshold).
#   WR impact: 57.1% → 58.3% (Tier-1 floor preserved).
#   SLV is a commodity-proxy ETF with no sector-rotation edge in this system.
ETF_BLACKLIST = frozenset({
    "IWM",  # Small-cap (Russell 2000): n=16 sum -11.67% (Phase 2-E 2026-04-29)
    "GLD",  # Gold ETF: n=11 WR 36.4% sum -6.23% (Phase 2-E 2026-04-29)
    "SLV",  # Silver ETF: n=2 WR 0.0% sum -15.74% (2026-05-16 audit)
})

# ─────────────────────────────────────────────────────────────────────
# ETF Sector Rotation — Approach B (macro-regime veto)
# ─────────────────────────────────────────────────────────────────────
# Defensive sector ETFs that underperform the broad market in high-VIX
# (risk-off) environments per academic literature (Fama-French sector
# rotation, SPDR sector factor analysis 2000-2024):
#   XLU (Utilities): mean-reverts below SPY in volatility spikes.
#   XLP (Consumer Staples): flight-to-safety narrative breaks down;
#         real earnings don't outperform once VIX >30 (Invesco 2023).
#   XLV (Health Care): defensive, but sector picks in this system showed
#         negative realized edge when VIX > 30 (post-phase-2-E review).
#
# Approach B: soft -10 score penalty when VIX > 30 AND ETF_MACRO_VETO=1.
# Soft penalty (not hard block) — we don't have enough n yet (n=105).
# Default OFF. Enable with ETF_MACRO_VETO=1 when n >= 150.
#
# Wiring: _apply_score_penalties() in this file (see VIX+YC REGIME section).
DEFENSIVE_SECTOR_ETFS: frozenset = frozenset({"XLU", "XLP", "XLV"})

# ─────────────────────────────────────────────────────────────────────
# COMMODITY sub-class blacklist (Phase 2-D panel verdict 2026-04-29)
# ─────────────────────────────────────────────────────────────────────
# Per Phase 2-D COMMODITY panel:
#   - COMMODITY 7/7 BELOW Tier 3 all windows
#   - Sub-class verified locally vs recent_closed:
#       HG=F (copper) n=168 WR 47.0% sum +6.64% KEEP
#       PL=F (platinum) n=138 WR 44.9% sum +5.15% KEEP
#       GC=F (gold) n=91 WR 39.6% sum -0.52% KILL (safety)
#       SI=F (silver) n=181 WR 44.2% sum -4.47% KILL
#       CL=F (crude) n=6 WR 16.7% sum -5.25% KILL
#       CT=F (cotton) n=12 WR 8.3% sum -8.41% KILL
#       KC=F (coffee) n=12 WR 8.3% sum -6.02% KILL
# Net: COMMODITY universe restricted to HG=F + PL=F.
# Default-on. Rollback: COMMODITY_SUBCLASS_KILL_DISABLED=1
COMMODITY_BLACKLIST = frozenset({
    # Energy
    "CL=F", "BZ=F", "HO=F", "RB=F", "NG=F",
    # Agro
    "ZC=F", "ZS=F", "ZW=F", "LE=F", "HE=F", "KC=F",
    # CT=F removed 2026-05-16 — PROBATION (n=43, WR 81.4%, PF 6.33); see PENDING_UNBLOCK_REVIEW
    # Silver + Gold
    "SI=F", "GC=F",
})

# ─────────────────────────────────────────────────────────────────────
# WIN-RATE TRAP blacklist (xai swarm blind spot, 2026-05-09)
# ─────────────────────────────────────────────────────────────────────
# Symbols where WR>=50% but sum_pnl<0 over 90d — the classic "small wins,
# catastrophic losses" asymmetry. xai swarm 1/4 flagged (others missed it
# but the data confirms when run as a separate query).
#
# Verified 2026-05-09 vs trading_picks (forex excluded, ±50% pnl clamp):
#
#   symbol     n   WR     avg_win   avg_loss   sum_pnl
#   ETHUSDT   68  51.5%   +3.82%    -5.18%     -37.2%
#   INJUSDT   90  50.0%   +0.17%    -0.69%     -23.3%
#   DYDXUSDT  67  70.1%   +0.07%    -1.25%     -21.6%   ← worst PF
#   FETUSDT   88  56.8%   +0.30%    -0.57%      -6.4%
#   STRKUSDT  58  69.0%   +0.01%    -0.20%      -3.1%
#   ETCUSDT   12  50.0%   +0.71%    -0.86%      -0.9%
#
# DYDXUSDT especially: 70% WR but losses are 17x bigger than wins. The
# system clusters wins around tight TPs but lets losses run.
#
# This is a SYMBOL-level surgical kill. Asymmetry is structural to these
# tickers (often illiquid alts with frequent fakeouts), not a strategy
# bug. Per docs/MUTATION_THREE_AXIS_PROTOCOL.md the symbol-axis kill is
# the right axis when DIRECTION + STRATEGY axes don't isolate the bleed
# — and they don't here (50%+ WR across both directions).
#    # NOTE (2026-05-17 audit): WIN_RATE_TRAP_BLACKLIST is NOW CHECKED in passes_active_gate
    # (wired 2026-05-27 EAGLE P2-02). Default-off via WIN_RATE_TRAP_GATE_ENABLED=1 — symbols
    # may already be caught by score/trust gates; this is belt-and-suspenders.
#   - ETHUSDT quan_engine (143 picks, WR=33.6%): blocked via score gates (passes_active_gate=False)
#   - INJUSDT, FETUSDT: appear OK in current data (PF>1 with very small PnL values)
#   - STRKUSDT: still shows trap pattern but blocked by score gates
# Do NOT wire this list into the gate without re-verifying each symbol's current state.
# Rollback: WIN_RATE_TRAP_KILL_DISABLED=1 (no-op — gate was never wired)
WIN_RATE_TRAP_BLACKLIST = frozenset({
    "DYDXUSDT", "ETHUSDT", "INJUSDT", "FETUSDT", "STRKUSDT", "ETCUSDT",
    "NIO",       # equity bleed: n=11 WR 27% sum -48.9% (not a trap, just
                 # a loser — but lumped here for unified symbol-block)
    "BCH-USD",   # equity-tagged BCH bleed: n=4 sum -17.3% (yahoo-style;
                 # complements PR #884 category inference)
})

# Asset-class-level blocks — temporarily disable entire classes with systemic issues
# FUTURES: score penalty (not an active-list hard ban) per kilo-audit-agent + bus (2026-04-04):
#   - Closed book showed 0% WR / heavy loss on Connors/hyperopt lane (sample n small)
#   - Separate: symbol format mismatches (/ES vs ES=F) — keep penalty until paths verified
#   - Active visibility still uses passes_active_gate (e.g. GC=F entry sanity was blocking gold)
# ETF: same -60 penalty plus **hard ban** in passes_active_gate (PLAN_FIX_LOWPICKSCOUNT Phase 1:
#   thin closed book, systemic drain — no new ETF actives until forward validation justifies).
BLOCKED_ASSET_CLASSES: set = {"FOREX", "COMMODITY", "FUTURES", "BOND"}
# FOREX: 2026-05-28 Tier-0 freeze, 90d policy-clean PF 0.39 / WR 15.4% / n=13. 15,720 picks → 0 high-conviction.
#        Bypass route: external MyFXBook replication gate (Tier 5 fix plan).
# BOND: 2026-06-03 freeze. Live PF 0.37 (CLASS_DEGRADED per quant_monitor 2026-06-03), money_ready_verdict.json
#        2026-05-24 records n=8 INSUFF-N / PF 0. EAGLE_JUNE2 + mimo session-summary item #4 (depromote until
#        admissibility pipeline passes). Bypass: paper-only 60d on HYG/LQD credit-spread strategies +
#        bond_credit_mom lab-side validation (currently PF 1.41 in lab, not live).
# COMMODITY: 2026-06-02 EAGLE-2 Pillar 1 freeze. Live policy-clean PF 0.31 / WR 11% / n=28; CT=F 57% concentration;
#        cot_positioning PF dropped 4.6 → 0.51 post-dedup (grok consult 2026-05-25, 75-85% leakage probability).
#        Bypass: 3-day COT publication lag enforced at signal receipt + CT=F removed from universe + 60d post-fix
#        live test. See EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD Pillar 1 action #2.
# FUTURES: 2026-06-02 EAGLE-2 Pillar 1 freeze. n=2 is not a class. futures_momentum killed 2026-05-06 (56 closed,
#        0% WR). Micro-contract slippage not modeled. Bypass: COT lag fix + slippage-adjusted backtest on 2y data
#        + 50 paper trades OOS. See EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD Pillar 1 action #3.
# Mechanism: -60 score penalty + SMART_PICKS_MIN_SCORE_{CLASS}=40 floor → smart_picks fails. passes_active_gate
# does NOT read this set, so active book stays visible for audit.
# Historical: was {"FUTURES"} until 2026-04-16; -60 penalty caused data starvation, removed. Re-frozen 2026-06-02
# after live policy-clean revealed n=2 with no credible lab strategy.

# Non-crypto raw-score floor bypass: audited *backtest* history is not enough; require
# a minimum **forward** lane sample so low dashboard scores cannot ride history alone.
NC_RAW_SCORE_BYPASS_MIN_FORWARD_TRADES = 10
NC_RAW_SCORE_BYPASS_MIN_FORWARD_WR = 0.55

# Large-sample active-feed floors by asset class. These are stricter than
# ranking penalties but looser than Smart Picks: once a cohort has enough
# forward history to be statistically meaningful, obviously weak strategies
# should not remain visible in the main active book.
ACTIVE_CRYPTO_MIN_FORWARD_TRADES = 50
ACTIVE_CRYPTO_MIN_FORWARD_WR = 0.40
ACTIVE_NON_CRYPTO_MIN_FORWARD_TRADES = 20
ACTIVE_NON_CRYPTO_MIN_FORWARD_WR = 0.45


def active_non_crypto_forward_wr_floor(asset_class: str) -> float:
    """Minimum forward win-rate (0–1) for the large-sample active gate (#288).

    The single global ``ACTIVE_NON_CRYPTO_MIN_FORWARD_WR`` (0.45) was calibrated
    on mixed non-crypto cohorts. In production it zeroed the live **EQUITY** book:
    many legitimate scanners sit at ~41–44% forward WR with n≥20 while still
    contributing positive ``recent_closed`` expectancy. ``FOREX`` / ``COMMODITY``
    keep the stricter 0.45 default; ``BOND`` uses a lower bar because the forward
    book is tiny and we still need visibility to build history.

    See ``docs/ACTIVE_PICKS_ASSET_CLASS_DIAGNOSIS_2026_04_22.md``.
    """
    ac = (asset_class or "").upper().strip()
    _floors: dict[str, float] = {
        "EQUITY": 0.40,
        "ETF": 0.40,
        "BOND": 0.35,
        "COMMODITY": 0.35,  # LOWERED 0.45->0.35 (2026-05-03): Cyclical, COT-lagged, lower vol
        "FOREX": 0.38,  # LOWERED 0.45->0.38 (2026-05-03): Mean-reversion friendly, lower vol than crypto
        "FUTURES": 0.35,  # LOWERED 0.45->0.35 (2026-05-03): Thinner market, same as commodity
    }
    return _floors.get(ac, ACTIVE_NON_CRYPTO_MIN_FORWARD_WR)


# Asset-class trust bonuses. The 2026-04-04 attribution (EQUITY 67.2% WR) was
# reversed by the 2026-04-11 per-asset-class edge report (peer claude-opus-4.6-hyro,
# updates/2026-04-11-per-asset-class-edge-report.md): EQUITY n=572 cum -395%, with
# 61% of that drain from ONE strategy (Value + Quality). The +8 bonus was actively
# amplifying losses on a bleeding asset class. Neutralized to 0 — we still WANT
# to keep running equity picks and build forward history (per user directive:
# don't fully block, keep building history), but without the score tailwind.
#
# FOREX also neutralized after 2026-04-12 forensic investigation (peer cursor,
# updates/2026-04-11-forex-data-integrity-spot-check.md): the +4 bonus was
# originally justified by PF 2.09 +211% on 570 trades, BUT forensic spot-check
# found the reported FOREX edge was 94% driven by 4 anomalous rows from
# `kimi_signal_tracking` with confidence=9.9999 (broken data) and +40-95%
# single-pick "gains" that are physically impossible for unleveraged spot FX.
# Root cause: bulk outcome-resolver double-stamp bug on 2026-04-10 22:42Z that
# wrote a second WON row for 3 picks already resolved as LOST. After dedup,
# clean FOREX is n=567 PnL +12% PF 1.06 — marginal, not edge. The +4 bonus
# was baked into a data artifact. Neutralized to 0 until forward data justifies.
#
# Small-n classes (BOND n=8, ETF n=4) also zeroed until n ≥ 50 gives real signal.
ASSET_CLASS_BONUSES = {
    "EQUITY": 3,  # PARTIAL RESTORE 0→+3 (2026-05-16): OOS WR=66.1%, 100% fold consistency.
    # April-11 drain (-395% cum) was driven by Value+Quality, Consecutive Beats, Earnings Drift,
    # Dividend Aristocrats strategies — all 4 now individually blocked in BLOCKED_STRATEGIES.
    # Clean post-block EQUITY (n=393) has PF=1.65, WR=53.2%. Modest +3 restores routing weight.
    "BOND": 0,  # was +5; n=8 too small to justify bonus
    "ETF": 3,  # PARTIAL RESTORE 0→+3 (2026-05-16): WR=66.7%, PF=2.25, n=75. Tier-1 profile.
    # n=4 ban lifted: now at 75 picks with 66.7% WR. Same rationale as EQUITY restore.
    "FOREX": 0,  # was +4; reversed 2026-04-12 per cursor forex integrity report
                 # (bulk-resolver bug inflated 3 rows by +203%; clean PF 1.06)
    "CRYPTO": 0,  # 49.8% WR baseline
    "COMMODITY": 0,  # was -3; neutral — let forward history decide
    # FUTURES handled by BLOCKED_ASSET_CLASSES (-60)
}

# Broken/delisted symbols generating phantom trades — HARD BLOCK (2026-04-03 data mining)
# NOTE: This set is referenced by both the penalty scorer AND the pick filter.
# There is NO separate BLOCKED_SYMBOLS below — all symbol blocks go HERE.
BLOCKED_SYMBOLS = {
    "MATICUSDT",  # 424 trades, 0% WR, -63.60% total PnL — delisted, phantom TIME_EXIT trades
    "UUSDT",  # 14 trades, 0% WR — broken symbol
    "XMR",  # 23 trades, 0% WR, -115% PnL — most destructive symbol (codebuff confirmed)
    "XMRUSDT",  # alias for XMR — same 0% WR, -115% PnL data
    "ENAUSDT",  # 8 trades, 12.5% WR, -15.6% PnL
    "IMXUSDT",  # 7 trades, 0% WR, -12.6% PnL
    "KASUSDT",  # 12% WR, 25 trades — P1 kill
    # Data quality / redenomination blocks (merged from second definition)
    "KATUSDT",  # Token redenomination: entry 0.0108 -> live 0.1408 (13x jump)
    "TRXUSDT",  # -10,064% PnL (103% of ALL negative crypto PnL). Blacklisted 2026-04-02.
    # 2026-04-11 EQUITY drain symbols — identified by pattern-mining on 1,371
    # non-crypto closed picks in dashboard_data.json. Our mean-reversion strategies
    # are shorting uptrending enterprise-software/tech mega-caps at the wrong times.
    # See updates/2026-04-11-non-crypto-pattern-mining.md (Finding 3).
    # Combined drain across these 6 symbols: ~-315% PnL across 82 closed picks.
    "ADBE",  # n=18, 5.6% WR, -85.5% PnL (Software) — single largest equity drain
    "CRM",   # n=10, 0.0% WR, -66.7% PnL (Software) — zero wins
    "ACN",   # n=11, 0.0% WR, -56.7% PnL (Consulting) — zero wins
    "MSFT",  # n=16, 18.8% WR, -48.0% PnL (Software)
    "PLTR",  # n=12, 16.7% WR, -33.3% PnL (Software)
    "TSLA",  # n=15, 26.7% WR, -24.4% PnL (Auto/tech)
    # T1-C bottom-symbol blocklist (2026-04-15) - structural anti-edge regardless of strategy
    # Evidence: 3,500-pick closed ledger, n >= 20, WR < 35%
    "JTOUSDT",    # n=33, 18.2% WR, PF 0.38, -34.1% PnL
    "XLMUSDT",    # n=26, 19.2% WR, PF 0.81, -1.7% PnL
    "ICPUSDT",    # n=53, 22.6% WR, PF 0.65, -6.7% PnL
    "RENDERUSDT", # n=45, 31.1% WR, PF 0.40, -33.8% PnL
    "NVDA",        # n=21, 33.3% WR, PF 0.77, -6.3% PnL (equity)
    # 2026-04-18 Codex equity-drain attribution — verified independently against
    # current dashboard_data.json (693 closed equity rows). These 3 complete the
    # 6-symbol toxic cluster identified by ChatGPT Codex; the other 3 (ADBE,
    # CRM, ACN) are already blocked above. Excluding all 6 lifts equity PF
    # 0.834 → 1.071 with total PnL flipping to +90.65%.
    # See: updates/2026-04-18-non-crypto-synthesis-and-action-plan.md (P4.3)
    "NKE",   # n=8,  0.0% WR, -66.78% PnL (Consumer/Apparel)
    "PG",    # n=8,  0.0% WR, -44.97% PnL (Consumer Staples)
    "HD",    # n=10, 10.0% WR, PF 0.005, -35.00% PnL (Retail)
    # 2026-05-17 AU audit: data artifact symbols — source_system=None, near-zero PnL, outcome=None
    # These generate artificially inflated WR/PF in money_ready_verdict. Blocked from live
    # picks by score/trust gates; adding here excludes historical artifact rows from stats.
    "DYDXUSDT",  # n=33 closed_picks ALL source_system=None, avg_win=+0.02%, avg_loss=-0.02%
                 # WR=90.9% PF=11.33 are arithmetic artifacts of near-zero PnL, not real alpha.
                 # In PENDING_UNBLOCK_REVIEW — re-review 2026-06-30 if source traced.
}

# ─────────────────────────────────────────────────────────────────────
# Corrupted outcome rows (bulk-resolver double-stamp bug 2026-04-10 22:42Z)
# ─────────────────────────────────────────────────────────────────────
# On 2026-04-10 22:42Z a bulk outcome resolver wrote a second WON row for
# 3 kimi_signal_tracking FOREX picks already resolved as LOST. The fake
# rows have id=MISSING, confidence=9.9999 (should be [0,1]), empty strategy
# field, and PnL physically impossible for unleveraged spot FX.
# They inflate reported FOREX aggregate from clean PF 1.06 to fake PF 2.04.
#
# Root cause: missing uniqueness constraint on outcome ledger + suspected
# unit-conversion bug in resolver. See the resolver investigation notes:
#   make_pick_id() at audit_trail/universal_pick_resolver.py:372-376 does NOT
#   include entry_price in its composite key, allowing retry loops to
#   re-resolve the same physical pick as a new row.
#
# Forensic reports:
#   updates/2026-04-11-forex-data-integrity-spot-check.md   (peer cursor)
#   updates/2026-04-11-non-crypto-pattern-mining.md         (findings)
#
# Client-side mirror: audit_dashboard/template.html::_CORRUPTED_OUTCOME_ROWS
# (PR #87 merged 2026-04-12).
#
# Tuple key: (symbol, timestamp, entry_price, direction, source_system, pnl_pct)
# The underlying rows are NOT deleted from dashboard_data.json — reversible quarantine only.
CORRUPTED_OUTCOME_ROWS = frozenset({
    ("USDCAD=X", "2026-03-24 16:54:37", 1.37709, "BUY", "kimi_signal_tracking", 40.45),
    ("EURUSD=X", "2026-03-13 19:07:51", 1.14338, "BUY", "kimi_signal_tracking", 66.76),
    ("AUDUSD=X", "2026-03-13 16:16:18", 0.70028, "BUY", "kimi_signal_tracking", 95.58),
})


def is_corrupted_outcome_row(pick: dict) -> bool:
    """Return True if pick matches a known-corrupted outcome row.

    Used by display/aggregation layers to drop picks that should have been
    deduplicated at outcome resolution time. Matches on the composite
    (symbol, timestamp, entry_price, direction, source_system, pnl_pct) key.

    Callers: audit_trail/outcome_aggregator.py, any stat computation path.
    """
    try:
        key = (
            pick.get("symbol"),
            pick.get("timestamp"),
            float(pick.get("entry_price")) if pick.get("entry_price") is not None else None,
            pick.get("direction"),
            pick.get("source_system"),
            float(pick.get("pnl_pct")) if pick.get("pnl_pct") is not None else None,
        )
        return key in CORRUPTED_OUTCOME_ROWS
    except (TypeError, ValueError):
        return False

# ── Dashboard Visibility Filters: Hard-rejects that suppress picks ──

# BLOCKED_SOURCE_SYSTEMS: Statistically proven losers (10+ trades, negative PnL, PF < 1.0)
# These systems are HARD-BLOCKED - their picks are completely hidden from all views.
# Sync with template.html's BLOCKED_SYSTEMS.
#
# Before ADDING new entries: read docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md — prefer
# DNA mutation, inverse, regime grid, and cross-asset checks (TESTING_PROTOCOL ┬º7). Losers
# often rehab or invert to winners; hard block only after documented investigation.
BLOCKED_SOURCE_SYSTEMS = {
    # EAGLE2 Phase 0 (2026-06-02): false consensus + 14d CRYPTO 66% concentration.
    "incubator_gainer",
    "mercury2_fast",  # already scored; reinforce global block (EAGLE2 Phase 0)
    # 2026-04-05: RE-BLOCKED per user data verification (re-audit 2026-04-05):
    # stocks_competition: 33.5% WR, -304.2% cum PnL on n=281 closed - BLEEDING
    # fast_stocks_competition: 14.3% WR, -41.0% cum on n=21
    # Prior 2026-04-04 unblock was based on crypto-filtered stats that missed the
    # actual equity-side losses. Full-population data shows clear negative edge.
    "stocks_competition",
    "fast_stocks_competition",
    # "kimi_signal_tracking" UNBLOCKED 2026-05-16: was n=22, WR=18.2%, PF=0.20 (old).
    # validated_resolved_picks 2026-05-16 now shows n=368, WR=76.6%, PF=7.70, AvgPnL=+2.13%.
    # Massive recovery — 2nd best source system behind aggregated_picks. UNBLOCKED.
    "ml_bg_system_a",  # 19 trades, 10.5% WR, -50% PnL, PF 0.14
    "ml_bg_system_b",  # 19 trades, 5.6% WR, -55% PnL, PF 0.02
    "ml_crypto_pred_v12",  # 117 trades, 36.8% WR, -32% PnL, PF 0.55
    "crypto_winners",  # 48 trades, 39.6% WR, PF 0.30
    "ml_bg_system_c",  # 5 trades, 0% WR
    "ml_bg_ensemble",  # 8 trades, 0% WR, -33% PnL
    # "signal_validation",  # UNBANNED 2026-04-13/14: stale ban comment was "10 trades, 0% WR, -18.4% PnL".
    # Canonical data now shows n=139 (universal_resolved_picks.json) / n=140 (dashboard cross-check),
    # WR 57.6%/57.1%, PF 2.16/2.11, Wilson 95% CI [49.2%, 65.5%], +108-110% cum PnL on universal.
    # Internal consistency: line 2863 _SOURCE_SYSTEM_SCORES already scored this strategy +10 with
    # comment "56.6% WR, +0.86% avg PnL" — same file contradicted itself. Verified independently by
    # Cursor + Claude on the same file (see docs/CURSOR_CLAUDE_AGREEMENT_2026-04-14.md).
    # The ban reflected an ancient state (n=10) before the strategy accumulated 130+ additional
    # profitable trades. FOREX-specific variant remains blocked via BLOCKED_ASSET_SOURCE_PAIRS
    # (line ~970) — conservative carve-out kept since forex subset may behave differently.
    # RE-BLOCK TRIGGER: if WR drops below 40% on n >= 50 forward-test trades, add this back.
    "ml_bg_system_f",  # 7 trades, 0% WR, -37.8% PnL
    # 2026-05-14 MMR audit (PR #986) §4 draggers:
    "breakout_b_ml",         # n=44, 0% WR, PF 0.00 — zero-win placeholder pattern
    "kimi_claw_research",    # n=50, 0% WR, PF 0.00 — zero-win placeholder, 3 asset classes
    "rocket_scanner",  # 2026-04-05: 5 active picks, 0% WR, -0.81% avg — kimi + noncrypto-drilldown live audit
    # 2026-04-28: copy_trader_highscore — Hyperliquid leaderboard SHORT replay system.
    # System aggregate (audit_dashboard/data/dashboard_data.json):
    #   resolved=234, WR 31.6%, avg -0.34%, sum -78.41%, PF 0.74, MaxDD 106.5%.
    # Mutation three-axis autopsy (reports/mutation_analysis_copy_trader_highscore_2026_04_28.txt,
    # n=283 from universal_resolved_picks.json):
    #   - DIRECTION axis: hs_lb_None SHORT 32.4% WR / -68.82% sum on n=253 (90% of system
    #     volume), LONG 80% WR but n=5 — well below the n>=30 statistical floor for any
    #     mutation save (per docs/MUTATION_THREE_AXIS_PROTOCOL.md §5).
    #   - SYMBOL axis: 6 symbols show 100% WR with identical +3.50% TP_HIT pnl on
    #     5-7 SHORT trades each — same placeholder-stat artifact flagged in
    #     feedback_clone_hl_placeholder_stats.md (2026-04-22). Not realized edge.
    #   - TIMEFRAME axis: no flips above 5pp threshold.
    # No axis shows PF>1.2 with n>=30. Last signal 2026-04-19 (already dormant).
    # Convergent kill recommendation from GitHub Cloud agent (Sonnet 4.6) deep-dive
    # + Cursor convergent finding c720b66d6b. See reports/zombie_kill_protocol_2026_04_28.md.
    "copy_trader_highscore",
    # 2026-04-28: goldmine_stocks — equity 6x-consensus zombie. Active-emitter (last
    # signal 2026-04-27, 80 active picks generated continuously).
    # System aggregate: resolved=24, WR 12.5% (3W/21L), sum -70.37%, PF 0.03, MaxDD 70.4%
    # (closed_picks=434 with 410 awaiting resolver — but the resolved sample is unambiguous).
    # Mutation three-axis autopsy (reports/mutation_analysis_goldmine_stocks_2026_04_28.txt):
    #   - DIRECTION axis: 24/24 LONG, no SHORT data — no inverse mutation testable.
    #   - SYMBOL axis: every symbol with n>=2 is 0% WR (JNJ 0/5, ABBV 0/3, XOM 0/3,
    #     MRK 0/2, CVX 0/2). Only n=1 wins. No symbol-allowlist subset >= n=10.
    #   - STRATEGY axis: goldmine_6x_consensus dominant variant is 0/17 = 0% WR /
    #     -58.71% sum (deterministic-loser fast-path candidate per Kimi feedback).
    #     goldmine_5x_consensus 3W/2L on n=5 is below the n>=30 floor and sum is
    #     net negative (-0.31%); cannot save the source.
    # No axis shows PF>1.2 with n>=30. Convergent finding from EQUITY-class team
    # (a30df0ac) + GitHub Cloud agent. See reports/zombie_kill_protocol_2026_04_28.md.
    "goldmine_stocks",
    # 2026-04-04: MUTATION CANDIDATES — NOT blocked, moved to inverse pipeline
    # "claude_gainer",        # 14.3% WR ÔåÆ inverse_claude_gainer = 85.7% WR (VALIDATED)
    # "aggregated_picks",     # 16.7% WR ÔåÆ needs confluence filter + symbol-lock mutation
    "multi_asset",  # 231 trades, 45.5% WR, -161% PnL, PF 0.32 (Money-Maker-Ready P0 2026-05-14)

    # FREEBUFF P0 blocklist additions (2026-05-17):
    # quan_engine_scalp: 25% WR, 1793 trades, -352.88% PnL — worst strategy by total loss.
    # Already in PERMANENTLY_KILLED_STRATEGIES; adding source-system-level block for
    # defense-in-depth (pipeline checks source_system, not just strategy name).
    "quan_engine_scalp",
    # cot_positioning: COT-publication LOOK-AHEAD LEAKAGE. Headline 77-78% WR / PF 4.6 is
    # an artifact: ~85% of its 134 picks are CT=F (cotton); COT signal uses CFTC data not
    # available at decision time. Deduped + ex-CT=F: n=20 / WR 30% / PF 0.51 — a loser.
    # Also in PERMANENTLY_KILLED_STRATEGIES (M-095). Source-system-level block adds
    # defense-in-depth against any pipeline path that reads source_system directly.
    "cot_positioning",
    # futures_momentum: 0% WR on 56 closed, PF 0.00 — KILLED 2026-05-06. Already in
    # PERMANENTLY_KILLED_STRATEGIES. Source-system-level block for defense-in-depth.
    "futures_momentum",
    # Phase-5 retirement 2026-05-31 — Phase-4 SUSPECT-PF forensic audit (PR #180,
    # reports/peer_claude-phase4-suspect-pf-audit_result_2026-05-31.md) confirmed
    # both PFs below are RESOLVER ARTIFACTS, not real edge:
    #
    # cta_golden_cross_200 (COMMODITY): reported PF 44 / WR 96% on n=25. Reality:
    # 24/24 winners are HG=F LONG with exit_reason = PRICE_RESOLVED* and exit_price
    # overshooting TP by up to 286 bps. The resolver walks daily closes forward N
    # days and stamps the first profitable close as exit, never checking intrabar
    # SL. RETIRE from money_ready_verdict + dashboards.
    "cta_golden_cross_200",
    # prediction_market_consensus (CRYPTO): reported PF 24.5 / WR 90% on n=89.
    # PF inflated by (a) 23 DOGEUSDT SHORT rows tagged SL_HIT_RESOLVED
    # [PRICE_MISMATCH] with POSITIVE pnl (exit_reason vs pnl-sign contradiction =
    # data corruption), (b) one XRPUSDT row literally tagged SL_HIT
    # (REPAIRED_PNL_CONTRADIC) worth +80.37%. RETIRE.
    "prediction_market_consensus",
}

# ── REQUIRES_WALKAHEAD_AUDIT (set): Systems flagged for mandatory walk-forward before live use ──
# These systems have suspicious headline metrics that may be artifacts (over-emission,
# data leakage, single-symbol concentration, look-ahead bias). They require a clean
# walk-forward split (train on pre-2025, test on 2025+) before graduating to paper/live.
# Per Money-Maker-Ready protocol: systems here are excluded from Smart Picks / High Conviction
# until walk-forward audit confirms OOS performance.
# 2026-05-14: seeded from Money-Maker-Ready audit findings.
REQUIRES_WALKAHEAD_AUDIT = {
    # multi_asset_cot (2026-05-14): PF=21.86 from 102 trades on only 5 unique CFTC weekly releases.
    # Over-emission artifact (20:1 ratio). After 1-pick-per-cycle dedup: WR=40%, PF=0.17, PnL=-2.
    # See reports/cot_pipeline_audit_20260514.md and reports/multi_asset_cot_audit_20260514.md.
    "multi_asset_cot",
}

# ── 3-Stage Unblock Protocol (SHADOW → PROBATION → FULL) ──
# SHADOW:    Symbol under passive monitoring. n>=10, WR>=50%, PF>=1.3.
#            No live picks emitted; metrics tracked in PENDING_UNBLOCK_REVIEW.
# PROBATION: Symbol approved for reduced-size live picks (typically 50% sizing).
#            n>=20, WR>=52%, PF>=1.3. Tracked in PROBATION_STATUS.
#            Reblock triggers are enforced (e.g., WR < 50% on n >= 20).
# FULL:      Symbol fully unblocked from all asset-class blacklists.
#            n>=30, WR>=52% (Wilson 95% LB>=45%), PF>=1.5, MDD<=25%,
#            7d trailing slope positive, regime-safe, gates-pass.
PROBATION_STATUS: Dict[str, Dict[str, Any]] = {
    "CT=F": {
        "promoted_at": "2026-05-16",
        "stage": "FULL",  # 2026-05-18: promoted PROBATION→FULL. n=77, WR=78%, PF=4.73, Wilson LB≈68% (>45% floor)
        "metrics_at_promotion": {
            "n": 43,
            "wr": 0.814,
            "pf": 6.33,
            "wilson_lb": 0.70,
        },
        "metrics_at_full": {
            "n": 77,
            "wr": 0.779,
            "pf": 4.73,
            "wilson_lb": 0.68,  # 95% Wilson CI lower bound
        },
        "review_date": "2026-06-30",
        "reblock_trigger": "WR < 50% on n >= 20 OR n stagnates (< 5 new picks in 14 days)",
    },
}

# ── PENDING_UNBLOCK_REVIEW: symbols blocked ≥30 days ago, due for data-driven review ──
# These are NOT unblocked — they require a human + agent audit against the criteria in
# reports/edge_improvement_analysis_20260516.md §3 before any change to BLOCKED_SYMBOLS.
# Format: symbol -> ISO date when review is due (or overdue).
# Dashboard generator can surface these as "due for review" cards.
# Unblock criteria: n≥30 post-block, WR≥52% (Wilson 95% LB≥45%), PF≥1.50 (bootstrap
# 2.5th-pct CI>1.0), MDD≤25%, 7d trailing slope positive, regime-safe, gates-pass,
# documented in updates/YYYY-MM-DD-symbol-rehab-<SYMBOL>.md.
PENDING_UNBLOCK_REVIEW: dict[str, str] = {
    # Original batch — 30d elapsed since block
    "NVDA":       "2026-08-01",  # blocked 2026-04-15 (n=21, WR 33.3%, PF 0.77). AU audit: still sub-threshold. Quarterly re-review.
    "JTOUSDT":    "2026-08-01",  # blocked 2026-04-15; AU audit WR=30.6%/PF=0.35 (n=18) — well below 52%/1.3 criteria. Quarterly re-review.
    "XLMUSDT":    "2026-08-01",  # blocked 2026-04-15; AU audit WR=38.3%/PF=0.64 (n=47) — below criteria. Quarterly re-review.
    "ICPUSDT":    "2026-08-01",  # blocked 2026-04-15; AU audit WR=30.6%/PF=0.40 (n=36) — below criteria. Quarterly re-review.
    "RENDERUSDT": "2026-08-01",  # blocked 2026-04-15; AU audit WR=31.1%/PF=0.40 (n=45) — below criteria. Quarterly re-review.
    # 2026-05-16 live analyzer results (tools/analyze_symbol_rehab_candidates.py):
    # Stage PROBATION — n>=20, WR>=52%, PF>=1.3 (needs n>=30 + 14d+ for full unblock)
    "IMXUSDT": "2026-06-06",  # CRYPTO: post-dedup MySQL (2026-05-19): n=0 resolved (1 OPEN). Prior
                              # n=29/WR=62.1%/PF=2.54 were duplicates invalidated by dedup. Stage RESET.
                              # Blocked 2026-04-15. Q-001 sync issue; organic picks must re-accumulate.
                              # At 2026-06-06: if n>=10/WR>=50%/PF>=1.3 → SHADOW; n>=20 → PROBATION.
                              # See audit_trail/symbol_reviews/IMXUSDT_review_20260519.json.
    # Stage SHADOW — n>=10, WR>=50%, PF>=1.3 (needs n>=20 for PROBATION)
    "DYDXUSDT": "2026-06-30",  # CRYPTO: DATA ARTIFACT — DO NOT PROMOTE (2026-05-17 AU audit).
                               # n=33 in closed_picks; ALL from source_system='?' (unknown source).
                               # avg_win=+0.02%, avg_loss=-0.02% — near-zero PnL, not real trading edge.
                               # WR=90.9%/PF=11.33 are arithmetic artifacts of tiny PnL values, not alpha.
                               # Remains blocked. Re-review only if source_system='?' entries are traced.
    "TRXUSDT":  "2026-06-30",  # CRYPTO: post-dedup MySQL (2026-05-19): n=31, WR=22.6%, PF=0.046. KEEP_BLOCKED.
                               # Pre-dedup claimed n=24/WR=50%/PF=2.42 were inflated duplicates. Real data
                               # shows WR=22.6% — decisively below 52% PROBATION floor. Was -10,064% PnL
                               # (2026-04-02 block). If WR<40% at 2026-06-30 review with n>=50, consider kill.
                               # See audit_trail/symbol_reviews/TRXUSDT_review_20260519.json.
    "CVX":      "2026-07-01",  # EQUITY: post n=12, WR 75.0%, PF 3.48 — SHADOW (MySQL). NOT in
                               # EQUITY_BLOCKED_SYMBOLS (removed 2026-05-16). Local data n=4, WR=25%, PF=0.32.
                               # Date extended from 2026-05-30 (2026-05-19 audit). Needs MySQL confirmation
                               # of n>=20 before PROBATION. See audit_trail/symbol_reviews/CVX_review_20260519.json.
    "XOM":      "2026-07-01",  # EQUITY: post-dedup MySQL (2026-05-19): n=3 resolved (all WON), 97 OPEN.
                               # Pre-dedup claimed n=15 was inflated. PF undefined (no losses). Still in
                               # EQUITY_BLOCKED_SYMBOLS. 97 OPEN picks will provide much more data by Jul.
                               # At 2026-07-01: if n>=10/WR>=50%/PF>=1.3 → SHADOW; n>=20 → PROBATION.
                               # See audit_trail/symbol_reviews/XOM_review_20260519.json.
}

# ── COT_DEDUP_SYSTEMS / COT_DEDUP_WINDOW_HOURS (PR-#994, 2026-05-15) ──
# COT picks repeat the same symbol every CFTC weekly release cycle, inflating n
# and headline metrics without adding new directional information.
# Observed artifact: multi_asset_cot CT=F (cotton) accounted for 94.3% of all
# COMMODITY picks (toxic_concentration=true). After 1-pick-per-cycle dedup:
# WR dropped from 79.2%→40%, PF from 4.65→0.17, PnL=-2.
# Guard: if a pick for the same symbol from the same COT source is already active
# and was admitted fewer than 72 hours ago, reject the duplicate.
# 72h ≈ one CFTC report cycle (weekly releases, 3-day publication lag).
# Env kill-switch: COT_DEDUP_GATE_ENABLED=0 (default 1 = ON). Fail-open.
COT_DEDUP_SYSTEMS = frozenset({
    "multi_asset_cot",
    "cot_positioning",
    "cftc_cot_commercial_signal",
    # 2026-05-16 swarm deep-dive: multi_asset_copytrader emits cftc_cot_commercial_signal
    # picks on blacklisted grains (ZW=F, ZS=F active NOW) without dedup protection.
    # Adding here enforces 72h dedup window on its COMMODITY COT signals.
    "multi_asset_copytrader",
})
COT_DEDUP_WINDOW_HOURS = 72

# ── BLOCKED_STRATEGIES: Per-strategy blocks that are asset-class aware ──
# Unlike BLOCKED_SOURCE_SYSTEMS (which blocks an entire source), these block
# specific strategy names that have been proven losers via investigation.
# Format: set of (strategy_name_fragment, asset_class_or_None)
# If asset_class is None, blocked across all asset classes.
# Per TESTING_PROTOCOL ┬º7: investigation doc required before adding entries.
BLOCKED_STRATEGIES = {
    # Equity losers from stocks_competition investigation (2026-04-14):
    # docs/strategy_audits/stocks_competition_2026-04-14.md
    ("Value + Quality", "EQUITY"),      # 6.2% WR, PF 0.14, n=48 — worst equity strategy
    ("Consecutive Beats", "EQUITY"),    # 25.6% WR, PF 0.54, n=39
    ("Earnings Drift", "EQUITY"),       # 15.8% WR, PF 0.30, n=19 (inverse confirmed PF 2.07)
    ("Dividend Aristocrats", "EQUITY"), # 0% WR, n=8
    # Crypto losers confirmed by 3-day audit + Claude convergence:
    ("enhanced_ml_A_xgboost", None),    # 28% WR, PF 0.42, 189 picks, 0% winning days
    # ETF: all strategies losing — block at asset class level instead
    ("extreme_oversold_bounce", "ETF"), # 0% WR, n=5
    ("vix_reversal", "ETF"),            # 33% WR, PF 0.02, n=6
    # 2026-05-13: forex_rsi2_mean_reversion re-blocked post-resolver-v2.
    # n=84 trailing-14d, WR 7.1%, PF 0.09, avg PnL -0.42%. See PERMANENTLY_KILLED_STRATEGIES.
    ("forex_rsi2_mean_reversion", "FOREX"),
    # 2026-05-24 Institutional Readiness P0 — FOREX killers (0% WR, consistent losses).
    ("fx_smart_carry_trade_momentum", "FOREX"),       # n=15, 0% WR, -0.08% sum
    ("fx_smart_forex_rsi2_mean_reversion", "FOREX"),  # n=5, 0% WR, -0.03% sum
    # 2026-04-14 edge-discovery sweep (see updates/2026-04-14-edge-discovery-and-plan.md)
    # Strategies below were scanned from the ~3,500-pick closed ledger (n >= 30).
    # Most: WR < 35% and/or PF < 0.65. Exception: Short-Term Reversal has PF 1.07 but
    # WR 34.2% (blocked on WR / weak edge, not PF).
    # ig_contrarian_sentiment global block REMOVED 2026-05-18 (session CS).
    # Full ledger n=254: LONG WR=16.8% PF=0.252 (n=197, blocked via BLOCKED_DIRECTION_TRIPLES)
    # vs SHORT WR=61.4% PF=2.238 (n=57, T1-grade). Removing global block lets SHORT flow.
    # Evidence: docs/MUTATION_EVIDENCE_direction_flip_2026_05_18.md
    ("ML Ranker", None),                # 31.1% WR, PF 0.58, n=45 — inverted ML signal
    ("Short-Term Reversal", None),      # 34.2% WR, PF 1.07, n=38 -- WR < 35% gate
    ("st_bb_squeeze_expansion", None),  # 38.7% WR, PF 0.83, n=31 — net negative
    ("vix_reversal", None),             # 26.7% WR, PF 0.13 on n=30 (ALL classes; ETF-specific above)
    # 2026-05-16: alpha_engine hs_lb_None catastrophic killer.
    # analyze_validated_data.py: [alpha_engine] hs_lb_None n=74, WR=4.1%, PF=0.21, AvgPnL=-0.52%.
    # hs_lb_None = "highscore_leaderboard_None" replay without any leaderboard filter.
    ("hs_lb_None", None),               # n=74, WR=4.1%, PF=0.21 across all classes
    # 2026-04-18 FUTURES toxic strategies dragging the futures card to WR=5.9%.
    # Verified locally against current dashboard_data.json (26 futures rows).
    # `futures_momentum` was the ONE winner (4W/3L/1F = +4.94% on n=8) but is
    # now KILLED (0% WR on 56 closed, PF 0.00 — added 2026-05-06).
    # See: updates/2026-04-18-non-crypto-synthesis-and-action-plan.md
    ("connors_rsi2", "FUTURES"),               # 0/2/3 = 0% WR n=5 (futures variant)
    ("hyperopt_connors_rsi2", "FUTURES"),      # 0/1/0 = 0% WR n=1 (variant)
    ("mean_reversion_bollinger", "FUTURES"),   # 0/2/0 = 0% WR n=2
    ("extreme_oversold_bounce", "FUTURES"),    # 0/1/1 = 0% WR n=2 (already killed elsewhere)
    ("vix_reversal", "FUTURES"),               # 0/2/2 = 0% WR n=4 (already killed)
    ("futures_mean_reversion", "FUTURES"),     # 0/1/0 (already killed; -0.88% bleed)
    ("ema_stack_momentum", "FUTURES"),         # 1/1/0 marginal but listed as killed by Antigravity
    # liquidity_sweep_reversal n=1 only F=1 — keep watching, not enough data to kill
    # 2026-04-17 deepscan-4 loser anatomy (subagent investigation):
    # Owns the 4 worst absolute losses in the 3,500-pick book (-46.8% FF, -23.8% MMT,
    # -20.8% MMT, -12.3% VANRY). All entries conf=0.90 paired with R:R 0.05-0.46 =
    # structurally negative-EV math. 53 picks, 43.4% WR, PF 0.52, total -88.3% PnL.
    # Removing this single strategy lifts crypto book WR by ~2pp and saves ~88 PnL pts.
    ("claude_gainer_1h", None),                # 53 picks, 43.4% WR, PF 0.52 (deepscan-4)
    # 2026-04-17 11-strategy WR-drop subagent investigation:
    # See updates/2026-04-17-eleven-strategies-decay-investigation.md
    # volume_spike_breakout: 10.8% WR PF 0.136 n=37 full-history (per
    # strategy_performance.json); 0% WR last 30d on n=4. Zero active. Already
    # blocked on FOREX above; this extends to all asset classes.
    ("volume_spike_breakout", None),           # 10.8% WR PF 0.136 (eleven-strategies)
    # crypto_bayesian_regime_transition_momentum_v1: 32% WR n=47 BTCUSDT only.
    # Both LONG and SHORT broken. Binomial-significant. Zero active. Estimated
    # +30 PnL pts saved over next 30 days.
    ("crypto_bayesian_regime_transition_momentum_v1", "CRYPTO"),
    # 2026-04-21 HF-grade audit: per-system-per-asset-class blocks
    # kimi_riseoftheclaw on CRYPTO: 8.3% WR (1W/11L), -59.8% PnL — works on EQUITY (54.6% WR) but toxic on crypto
    ("kimi_signal_tracking", "CRYPTO"),  # 0% WR on crypto (0W/3L), -10.9% PnL
    # goldmine_stocks on EQUITY: 0% WR (0W/5L), -22.3% PnL — dead strategy
    ("goldmine_stocks", "EQUITY"),       # 0% WR n=5, -22.3% PnL — zero wins ever
    # fast_stocks_competition on EQUITY: 0% WR (0W/6L), -22.0% PnL
    ("fast_stocks_competition", "EQUITY"), # 0% WR n=6 — zero wins ever
    # 2026-05-08 swarm #4 drag-cohort kill: alpha_engine_fast on CRYPTO.
    # PF 0.62 system-wide; net drag on `asset_class_health.CRYPTO` aggregate.
    # Asset-scoped block — alpha_engine (non-fast) remains active. Polymarket
    # vol-spike gate v2 (alpha_engine/feed_hygiene.py) is the additional soft
    # filter applied if this hard block is rolled back.
    # Rollback condition: if CRYPTO active n drops >50% within 48h, comment
    # this row + raise an issue (see reports/swarm_decision_2026-05-08.md).
    ("alpha_engine_fast", "CRYPTO"),
    # 2026-05-16: opposite_day on CRYPTO — 158 trades across 14 symbols,
    # avg WR 9.7%, avg PF 0.114 (bt_backtest_runs live-verified 2026-05-16).
    # BTCUSDT 3.6% WR, ETHUSDT 4.6% WR, XRPUSDT 5.3% WR — structurally broken
    # across all major pairs. The strategy's contamination caused BNBUSDT and
    # AVAXUSDT to show PF 0.01 in bt_backtest_runs (100% of their rows are this
    # strategy). LINKUSDT shows PF 1.74 but n=3 — below statistical floor.
    # Source: reports/edge_improvement_analysis_20260516.md §1.
    ("opposite_day", "CRYPTO"),
    # 2026-05-16: ema_crossover in CRYPTO incubator — 219 incubator trades across
    # 4 symbols (ETH-USD n=54 PF 0.137, XRP-USD n=58 PF 0.199), avg PF 0.48,
    # avg WR 27.2% (at_incubator_backtest_results live-verified 2026-05-16).
    # RSI-based entries consistently outperform EMA crossovers in CRYPTO mean-
    # reversion context. Blocking CRYPTO variant; trend-following contexts in other
    # asset classes are unaffected.
    # Source: reports/edge_improvement_analysis_20260516.md §1.
    ("ema_crossover", "CRYPTO"),
    # 2026-05-18: seasonal_factor_rotation CRYPTO — three-axis mutation exhausted.
    # auto_tuner.py: 0/11=0% WR, -1.20% avg_pnl, 100% SL_HIT (fundamentally broken).
    # short_trade_validator.py: 21% WR on 14 shorts — KILL verdict.
    # pf_registry policy-clean-net: n=21, PF=0.63 CRYPTO. Raw: n=21, PF=0.69.
    # Axes: Symbol (WLD/BONK/NEAR/BNB/ATOM/FIL — no winning segment), Direction
    # (both LONG 0% and SHORT 21% below floor), Timeframe (trending+ranging+transitional
    # all failing). No viable mutation path. Source: nextgen_strategies.py generates;
    # auto_tuner 2026-03-xx first flagged; pf_registry 2026-05-18 confirmed negative.
    ("seasonal_factor_rotation", "CRYPTO"),
    # 2026-05-18: quan_engine_position CRYPTO — WR=0%, n=26, all TAOUSDT.
    # Source: quan_engine (same source as quan_engine_scalp, already blocked).
    # All 26 closed picks on TAOUSDT are losses; no winning segment possible
    # (single symbol, source system already in BLOCKED_SOURCE_SYSTEMS via scalp).
    # Scoped to CRYPTO only. Session CZ autopsy from closed_picks.json.
    ("quan_engine_position", "CRYPTO"),
    # 2026-05-18: ml_enhanced_INJUSDT_15m_D_ensemble_stack CRYPTO — SHORT WR=4%, n=26.
    # All 26 picks are SHORT direction; no LONG picks. Contrast with 1d_B_lightgbm
    # variant which has WR=96% LONG n=28 — this is a 15m timeframe failure, not an
    # INJUSDT failure. M-028 (15m quarantine gate) targets this class.
    # Blocking specifically to prevent the 4% SHORT drag while 1d variant earns.
    # Session CZ autopsy from closed_picks.json.
    ("ml_enhanced_INJUSDT_15m_D_ensemble_stack", "CRYPTO"),
    # 2026-05-18: ml_enhanced_TRXUSDT_1d_B_lightgbm CRYPTO — LONG WR=12%, n=26.
    # All 26 picks LONG direction, no SHORT. No rescue via direction flip or symbol
    # pivot (strategy name is TRX-specific). B_lightgbm variant for TRX is broken;
    # other TRX variants (D_ensemble_stack 1h/4h/1d) have n=1 — too small to assess.
    # Session CZ autopsy from closed_picks.json.
    ("ml_enhanced_TRXUSDT_1d_B_lightgbm", "CRYPTO"),
    # 2026-05-18: ml_enhanced_APEUSDT_1d_D_ensemble_stack CRYPTO — SHORT WR=33%, n=30.
    # All 30 picks SHORT direction, no LONG. WR=33% < 50% floor; no direction rescue.
    # Three-axis mutation exhausted: only one symbol (APE), one direction (SHORT),
    # one timeframe (1d). Session CZ autopsy from closed_picks.json.
    ("ml_enhanced_APEUSDT_1d_D_ensemble_stack", "CRYPTO"),
    # 2026-05-18: ml_enhanced_JTOUSDT_1d_B_lightgbm CRYPTO — LONG WR=37%, n=30.
    # All 30 picks LONG direction, no SHORT. WR=37% < 50% floor; no direction rescue.
    # B_lightgbm variant for JTO failing; D_ensemble variants have n<5 — insufficient.
    # Session CZ autopsy from closed_picks.json.
    ("ml_enhanced_JTOUSDT_1d_B_lightgbm", "CRYPTO"),
    # 2026-05-18: ml_enhanced_AVAXUSDT_1d_B_lightgbm CRYPTO — SHORT WR=44%, n=25.
    # All 25 picks SHORT direction, no LONG. WR=44% < 50% floor; no direction rescue.
    # B_lightgbm variant for AVAX failing on 1d SHORT (15m_D variant also underperforming).
    # Session DA autopsy from closed_picks.json.
    ("ml_enhanced_AVAXUSDT_1d_B_lightgbm", "CRYPTO"),
    # 2026-05-18: ml_enhanced_HBARUSDT_1d_D_ensemble_stack CRYPTO — LONG WR=43%, n=28.
    # All 28 picks LONG direction, no SHORT. WR=43% < 50% floor; no direction rescue.
    # D_ensemble_stack variant for HBAR failing on 1d LONG. Session DA autopsy.
    ("ml_enhanced_HBARUSDT_1d_D_ensemble_stack", "CRYPTO"),
    # 2026-05-18: quan_engine_swing CRYPTO — LONG WR=26%, n=104, source=quan_engine.
    # quan_engine_scalp already in BLOCKED_SOURCE_SYSTEMS; swing sub-strategy is
    # a separate pick type from the same source. LONG direction WR=26% (n=104) is
    # structurally broken. SHORT has WR=60% but n=5 — statistically insufficient to
    # rescue. Session DA autopsy from closed_picks.json.
    ("quan_engine_swing", "CRYPTO"),
    # 2026-05-18: rsi_bounce CRYPTO — LONG WR=28%, n=25, source=rapid_fire.
    # All 25 picks LONG direction, no SHORT. WR=28% < 50% floor; no direction rescue.
    # rapid_fire source is under data quality review (raw vs dashboard discrepancy);
    # rsi_bounce sub-strategy is independently failing within that source.
    # Session DA autopsy from closed_picks.json.
    ("rsi_bounce", "CRYPTO"),
    # 2026-05-18: macd_rsi_confluence CRYPTO — LONG WR=36%, n=66, source=rapid_fire.
    # All 66 picks LONG direction, no SHORT. WR=36% < 50% floor; no direction rescue.
    # Largest-n rapid_fire sub-strategy; consistently below floor. Session DA autopsy.
    ("macd_rsi_confluence", "CRYPTO"),
}


def _blocked_name_matches(haystack_upper: str, needle_upper: str) -> bool:
    """True if needle appears as a whole phrase (token boundaries), not as a substring of a larger token.

    Avoids false positives like matching ``ML Ranker`` inside ``XML Ranker``.
    """
    if needle_upper not in haystack_upper:
        return False
    if needle_upper == haystack_upper:
        return True
    esc = re.escape(needle_upper)
    return (
        re.search(rf"(^|[^A-Z0-9]){esc}((?:[^A-Z0-9]|$))", haystack_upper) is not None
    )


def is_strategy_blocked(strategy: str, asset_class: str) -> bool:
    """Check if a strategy is blocked for a given asset class."""
    if not strategy:
        return False
    strat_upper = strategy.upper()
    ac_upper = (asset_class or "").upper()
    for blocked_strat, blocked_ac in BLOCKED_STRATEGIES:
        if _blocked_name_matches(strat_upper, blocked_strat.upper()):
            if blocked_ac is None or blocked_ac.upper() == ac_upper:
                return True
    return False


# Rapid_fire score floor (raised from 10 to match quality floor)
RAPID_FIRE_MIN_SCORE = 50

# Entry price bounds (prevent broken entry-price outliers)
MAX_ENTRY_PRICE = 1_000_000.0

# Age-based staleness bounds: only reject if PnL is also low (winners can run)
# Sync with template.html's renderPicks filtering
# Hard cap for /audit active visibility: stale + flat PnL rows hidden (not booster age limits).
# 2026-04-05: 48h was starving the book (~110/149 actives failed passes_active_gate); 72h keeps
# Layer-0 hygiene while restoring breadth. Promotion / Smart Picks still use tighter gates.
CRYPTO_HARD_MAX_AGE_HOURS = 72
NON_CRYPTO_HARD_MAX_AGE_HOURS_VISIBLE = 336  # 14 days
STALENESS_PNL_LIMIT = 1.0

# Non-crypto Active display: require a minimum *raw* dashboard score (before penalties).
# Elite_score must not override this floor (see tests + _extract_final_score contract).
ACTIVE_DISPLAY_NON_CRYPTO_MIN_RAW_SCORE = 55
# TESTING_PROTOCOL ┬º2.5 uses score>=40 for toxic-pool stats and >=60 for promotion — this is
# **audit default visibility only** for CRYPTO (rank-sort still applies). Floor 40 hid ~74%
# of post-boost actives while non-crypto kept stricter NC raw>=55 + trust rules.
ACTIVE_DISPLAY_CRYPTO_MIN_RAW_SCORE = 30

# Low confidence strategies (0.4x multiplier)
LOW_CONFIDENCE_STRATEGIES = {
    "futures_bb_mean_reversion",
    "futures_ema_stack_momentum",
    "claude_gainer_ml",
    "claude_gainer_ml_perf",
}

# Inverse strategies with proven edge (78%+ WR)
PROVEN_INVERSE_STRATEGIES = {
    "st_multi_day_momentum",
    "claude_gainer_1h",
    "luxalgo_confluence",
    "crypto_rsi_whaleconfirmed_v1",
    "atr_regime_rsi",
    "winner_pattern_precursor_inverse",
    # 2026-04-01: Degraded strategy inverses (0% WR originals)
    "inverse_quan_engine_scalp",
    "inverse_binance_smart_money",
    "inverse_cci_reversal_scout",
    "inverse_macd_momentum",
    "inverse_gainer_compression_relaxed",
    "inverse_mean_reversion_bb",
}

# SHORT strategy exemptions - these have proven profitable SHORT performance
# Based on analysis: 13 strategies with WR >= 50% and positive avg PnL
# See: analyze_short_strategies.py
PROFITABLE_SHORT_STRATEGIES = {
    "tsmom_strategy",  # 2026-04-05: KITE SHORT won on ALL 5 TV books (+2.24 to +8.6%).
    "tsmom_volscaled",  # Leveraged-inverse-alt SHORTs during weak-alt regime. Live-validated.
    "funding_momentum",  # 60.4% WR, +0.12% avg PnL, 106 trades
    # REMOVED: rolling 7d WR collapsed vs baseline on audit — no SHORT exemption
    "crypto_kalman_trend_residual_reversion_v1",  # 80% WR, +2.20% avg PnL, 5 trades
    "crypto_keltner_compression_expansion_v1",  # 75% WR, +0.66% avg PnL, 8 trades
    "vwap_deviation_reversion_xrp_v1",  # 66.7% WR, +0.73% avg PnL, 6 trades
    "crypto_soc_orderflow_absorption_a01_v1",  # 60% WR, +0.36% avg PnL, 10 trades
    "crypto_soc_delta_divergence_a01_v1",  # 66.7% WR, +0.52% avg PnL, 6 trades
    "crypto_soc_delta_divergence_a04_v1",  # 57.1% WR, +0.36% avg PnL, 7 trades
    "crypto_soc_proxy_decoupling_a04_v1",  # 60% WR, +0.50% avg PnL, 5 trades
    "crypto_soc_delta_divergence_a07_v1",  # 60% WR, +0.37% avg PnL, 5 trades
    "crypto_soc_orderflow_absorption_a10_v1",  # 57.1% WR, +0.21% avg PnL, 7 trades
    "crypto_soc_delta_divergence_a10_v1",  # 60% WR, +0.26% avg PnL, 5 trades
    "crypto_soc_orderflow_absorption_a05_v1",  # 60% WR, +0.05% avg PnL, 5 trades
}

# Rolling 7d vs prior window: audit performance_alerts REDUCE strategies — extra sort penalty.
# Keys are canonical strategy names; lookup uses .lower(). See also performance_alerts suppression.
ROLLING_7D_DEGRADATION_STRATEGY_PENALTIES = {
    "quan_engine_scalp": -28,
    "crypto_bayesian_regime_transition_momentum_v1": -28,
    "ml_crypto_predictor": -28,
    "crypto_adx_pullback_trendresume_v1": -28,
    "enhanced_ml_a_xgboost": -32,
    "extreme fear contrarian buy": -28,
    "quan_engine_swing": -25,  # 0% rolling 7d WR vs 38% baseline (n=12 recent, n=78 prior) - 2026-04-14 audit
}
_ROLLING_7D_DEGRADE_LOWER = {
    k.lower(): v for k, v in ROLLING_7D_DEGRADATION_STRATEGY_PENALTIES.items()
}

# ── M-015: Dynamic decay-alert REDUCE soft-demote ────────────────────────────
# Reads performance_alerts REDUCE rows from dashboard_data.json. Applies a
# score penalty proportional to the WR drop so strategies with active decay
# alerts are soft-demoted without a hard block.
#
# Penalty tiers (WR drop = baseline_wr - rolling_wr):
#   > 50pp → -25   > 30pp → -20   > 15pp → -12   > 5pp → -8
#
# Default ON (DECAY_SOFT_DEMOTE_ENABLED default "1"). Kill-switch: DECAY_SOFT_DEMOTE_ENABLED=0.
# Caches on dashboard_data.json mtime so hot-path file I/O is minimal.
# ─────────────────────────────────────────────────────────────────────────────
_DECAY_SOFT_DEMOTE_CACHE: Dict[str, Any] = {"mtime": 0.0, "penalties": {}}


def _get_decay_soft_demote_penalty(strategy: str) -> int:
    """Return score penalty (negative int) for a strategy with active REDUCE alert.

    Returns 0 when gate is disabled, data is missing, or strategy has no alert.
    Caches on dashboard_data.json mtime.
    """
    if os.environ.get("DECAY_SOFT_DEMOTE_ENABLED", "1") not in ("1", "true", "TRUE"):
        return 0
    try:
        mtime = os.path.getmtime(_DASHBOARD_DATA_PATH_QG)
        if mtime != _DECAY_SOFT_DEMOTE_CACHE["mtime"]:
            import json as _json_dsm
            with open(_DASHBOARD_DATA_PATH_QG, "r", encoding="utf-8") as _f:
                dd = _json_dsm.load(_f)
            alerts = dd.get("performance_alerts") or []
            penalties: Dict[str, int] = {}
            for alert in alerts:
                if alert.get("action") != "REDUCE":
                    continue
                details = alert.get("details") or {}
                strat = str(details.get("strategy") or "").lower()
                if not strat:
                    continue
                rolling = details.get("rolling_wr")
                baseline = details.get("baseline_wr")
                if not isinstance(rolling, (int, float)) or not isinstance(baseline, (int, float)):
                    continue
                drop = baseline - rolling
                if drop > 50:
                    penalty = -25
                elif drop > 30:
                    penalty = -20
                elif drop > 15:
                    penalty = -12
                else:
                    penalty = -8
                # Take the larger penalty if strategy appears in multiple alerts
                if strat not in penalties or penalty < penalties[strat]:
                    penalties[strat] = penalty
            _DECAY_SOFT_DEMOTE_CACHE.update(mtime=mtime, penalties=penalties)
        return _DECAY_SOFT_DEMOTE_CACHE["penalties"].get(strategy.lower(), 0)
    except Exception:
        return 0


# Per-symbol strategy blocks: specific (strategy, symbol) pairs with proven 0% WR
# Data: quan_engine_scalp on MATICUSDT = 0 wins / 239 losses = -35.85% PnL
BLOCKED_STRATEGY_SYMBOL_PAIRS = {
    ("quan_engine_scalp", "MATICUSDT"),  # 0/239 WR, -35.85% PnL
    ("quan_engine_scalp", "ADAUSDT"),  # 0/7 WR, -4.19% PnL
    ("quan_engine_scalp", "ICPUSDT"),  # 4/37 WR (10.8%), -16.40% PnL
    ("quan_engine_scalp", "SOLUSDT"),  # 3/20 WR (15%), -8.02% PnL
    # 2026-04-05 claude-bus-setup (bus task 3): enhanced_ml_A_xgboost per-symbol
    # audit on 104 closed picks. Strategy overall 32.7%WR PF=0.73. Winners kept
    # (SEI 100%, CHZ 86%, JTO 57%, ETC 100% — mutate-before-kill policy).
    # These specific symbol-pairs have proven 0-33% WR + negative PnL: hard-block.
    (
        "enhanced_ml_A_xgboost",
        "TRXUSDT",
    ),  # 0/38 WR, -76% PnL (worst) — already -20 penalty, now hard-block
    ("enhanced_ml_A_xgboost", "FILUSDT"),  # 2/9 WR (22%), -8% PnL
    ("enhanced_ml_A_xgboost", "TIAUSDT"),  # 0/3 WR, -6% PnL
    ("enhanced_ml_A_xgboost", "FETUSDT"),  # 0/2 WR, -4% PnL
    ("enhanced_ml_A_xgboost", "SOLUSDT"),  # 0/2 WR, -4% PnL
    ("enhanced_ml_A_xgboost", "WLDUSDT"),  # 1/3 WR (33%), -1% PnL
    # 2026-04-05 claude-bus-setup: REHAB BLOCKS (un-killed strategies, bad symbol pairs)
    # MeanReversionBB re-activated (77.8% WR overall, PF=4.17). Single blocker:
    ("MeanReversionBB", "LINK-USD"),  # 1/3 WR (33%), -2.3% PnL — only loser
    # claude_ml_moderate_mut re-activated (52% WR overall, 2 qualifying symbols).
    # Losers:
    ("claude_ml_moderate_mut", "IMXUSDT"),  # 1/7 WR (12%), -10.1% PnL — worst
    ("claude_ml_moderate_mut", "TIAUSDT"),  # 0/3 WR, -4.2% PnL
    # 2026-05-02 mutation analysis (issue #691, tools/mutation_analysis.py):
    # quan_engine bare strategy has 51pp WR spread by symbol. HYPEUSDT is the
    # dominant drag: n=553, WR 41.6%, avg -0.22% per trade = ~-121% sum PnL.
    # Symbol-allowlist mutation per CLAUDE.md MUTATION_THREE_AXIS_PROTOCOL —
    # block only the worst symbol; XRPUSDT (51% WR) / TRXUSDT (49% WR) /
    # BNBUSDT (46% WR) variants of the same strategy retain edge.
    # Cross-AI consensus: Claude per-asset audit + Kimi #691 + Grok-4 review.
    # Expected lift: CRYPTO 30d PF 1.33 -> ~1.40-1.45 (Grok estimate +0.15-0.20).
    ("quan_engine", "HYPEUSDT"),
    # 2026-05-19 FINDING-19: multi_asset_copytrader × metals cluster — 7d regime collapse.
    # 7d: n=22, PF=0.177, WR=9.1%, sum=-62.2%. 30d healthy (PF=1.633, WR=53.6%, CT=F anchor).
    # 3/3 AI consensus (deepseek+kilo+claude): targeted symbol block, not class-level kill.
    # Review: 2026-06-09. Unblock if metals regime softens AND 14d WR returns to ≥35%.
    # Report: reports/finding19_3ai_consensus_2026_05_19.md
    ("multi_asset_copytrader", "PL=F"),  # Platinum: 0% WR 7d
    ("multi_asset_copytrader", "GC=F"),  # Gold: 0% WR 7d, near ATH $4,511
    ("multi_asset_copytrader", "HG=F"),  # Copper: 0% WR 7d
}

# Symbols with known data quality issues (token redenomination, bad price feeds)
# MERGED into BLOCKED_SYMBOLS above (line ~251) — do NOT redefine here.
# "KATUSDT" and "TRXUSDT" are now in the main BLOCKED_SYMBOLS set.

# PnL sanity bounds — if computed PnL is outside these bounds and entry/live math
# disagrees, the pick has a data quality issue and should be flagged.
PNL_SANITY_MAX = 200.0  # No single pick should show >200% PnL
PNL_SANITY_MIN = -50.0  # No active pick should be beyond -50% without SL firing

# Asset-aware blocks for systems/strategies that are dragging down low-WR
# non-crypto books. Keep this narrow so verified PM/pro-trader sources still flow.
BLOCKED_ASSET_SOURCE_PAIRS = {
    ("FOREX", "signal_validation"),
    # EAGLE2 Phase 0 (2026-06-02): CRYPTO concentration drag + false consensus.
    ("CRYPTO", "incubator_gainer"),
    ("CRYPTO", "regime_terminal"),
    ("FOREX", "regime_terminal"),
    # 2026-05-28 Tier-0 fix: forex_rsi2_mean_reversion is in BLOCKED_SOURCE_SYSTEMS (WR 7.1% / PF 0.09
    # trailing-14d) but leaks into opened FOREX picks via these aggregator/copy emitters (90d sample:
    # multi_asset_copytrader=104, forex_copy_trader=13). Block at the (class,source) pair level so the
    # leak is closed even after the BLOCKED_ASSET_CLASSES freeze is eventually lifted.
    # Ref: reports/ASSET_CLASS_EDGE_FIX_PLAN_2026-05-27.md action #6 (FOREX agent audit).
    ("FOREX", "multi_asset_copytrader"),
    ("FOREX", "forex_copy_trader"),
    # ("EQUITY", "stocks_competition"),  # UNBLOCKED 2026-04-04: stocks WR 48.3%, block was overkill
}

BLOCKED_ASSET_STRATEGY_PAIRS = {
    ("FOREX", "MomentumEMA"),
    ("FOREX", "volume_spike_breakout"),
    # 2026-05-11 SUPREME EDGE re-block: TEMP UNBLOCK from 2026-05-08 was conditioned
    # on phantom_expired < 10% which has NOT been achieved (still 100% per DB Health
    # red-tier panel even post-Wave-1 unfreeze; outcome_resolver lag). Re-block
    # restores test_fx_kill_switch.py + test_kill_2026_05_02_live_data.py expectations
    # and aligns with master plan FOREX BLOCKED state machine + elite-score 70 floor.
    ("FOREX", "myfxbook_retail_contrarian"),
    ("EQUITY", "ML Ranker"),
    # 2026-04: goldmine consensus on CRYPTO = 18-19% WR, -29 to -87% PnL.
    # Equity application retained (commented out of kill list 2026-04-05).
    ("CRYPTO", "goldmine_1x_consensus"),
    ("CRYPTO", "goldmine_2x_consensus"),
    ("CRYPTO", "goldmine_3x_consensus"),
    # 2026-04-18 Codex equity attribution — re-verified locally against
    # 693-row equity closed ledger. Both goldmine variants already blocked on
    # CRYPTO; equity equivalents are similarly destructive:
    #   goldmine_2x_consensus  EQUITY  n=20  WR=20.0%  PF=0.174  total=-110.13%
    #   goldmine_1x_consensus  EQUITY  n=23  WR=26.1%  PF=0.597  total= -26.74%
    # See: updates/2026-04-18-non-crypto-synthesis-and-action-plan.md (P4.2)
    ("EQUITY", "goldmine_1x_consensus"),
    ("EQUITY", "goldmine_2x_consensus"),
    # 2026-04-18 top-loser audit additions — found in worst-30 review against
    # current dashboard ledger. The 3x/4x variants extend the same goldmine
    # consensus pattern that's already blocked on 1x/2x; per-trade losses on
    # AMD show the same characteristic SL hits.
    #   AMD goldmine_3x_consensus -17.51% / goldmine_2x_consensus -13.22% / -10.74%
    #   CRM goldmine_4x_consensus -9.47% / goldmine_3x_consensus -9.44%
    ("EQUITY", "goldmine_3x_consensus"),
    ("EQUITY", "goldmine_4x_consensus"),
    # ml_enhanced_APEUSDT_1d_D_ensemble_stack: 3 closed picks in current
    # ledger, all SHORT, all hit SL at 0.1039 (broken or stale SL price),
    # losing -22.60%, -21.88%, -19.22% = -63.69% total. Symbol-specific
    # block until the strategy is re-tuned.
    ("CRYPTO", "ml_enhanced_APEUSDT_1d_D_ensemble_stack"),
    # 2026-04-22: RCA — quan_engine_scalp = largest closed volume, ~23% WR, PF 0.27;
    # pair blocks above still allow other symbols. Full class block stops new emissions.
    ("CRYPTO", "quan_engine_scalp"),
    # penny_deep_oversold (multi_asset_institutional source): IONQ -14.63%,
    # RIOT -11.80% in worst-30 review. Penny stock mean reversion is a
    # documented loser pattern (no edge — see updates/non_crypto policy).
    ("EQUITY", "penny_deep_oversold"),
    # ── 2026-05-02 live-data kills (issues #686, #688, #689) ──
    # forex_carry_momentum: PR #687 fixed the JPY-cross BUY rule bypass
    # (was -23% sum on 49 JPY-cross LONGs in 7d), but the strategy's non-JPY
    # component is also dead: n=8 NZDUSD=X picks, 0% WR, -4% sum (30d).
    # Strategy has zero edge anywhere. Cross-AI consensus (Kimi #688 + Claude
    # subagents + Grok-4 review of #687): kill outright. Gate-level block
    # still allows historical attribution; mutations of the strategy can be
    # researched separately per docs/MUTATION_THREE_AXIS_PROTOCOL.md.
    # 2026-05-11 SUPREME EDGE re-block: same logic as myfxbook_retail_contrarian above.
    # phantom_expired condition not met. Restores CI Tests green.
    ("FOREX", "forex_carry_momentum"),
    # goldmine_6x_consensus EQUITY: extends the same goldmine consensus
    # destruction pattern blocked on 1x/2x/3x/4x above. Live data 2026-05-02:
    # n=16 closed picks over 30d, 0% WR, -55.41% sum PnL. The previous
    # comment on goldmine_2x/3x/4x cited the same per-trade SL pattern; 6x
    # is the highest-leverage variant of the same broken signal source.
    # Cross-AI consensus (Kimi #689 + Claude subagent verification).
    ("EQUITY", "goldmine_6x_consensus"),
    # goldmine_7x_consensus EQUITY: same goldmine consensus pattern; 0% WR n=1 (XOM -5.59%)
    # in current dashboard. Source system already in BLOCKED_SOURCE_SYSTEMS — this is
    # defense-in-depth in case the source block is ever conditionally rolled back.
    # Confirmed by mutation analysis 2026-05-16 (reports/goldmine_stocks_mutation_analysis_2026-05-16.md).
    ("EQUITY", "goldmine_7x_consensus"),
    # ── 2026-05-11 SUPREME EDGE P0 #3: baby_strats:crypto_soc_* overfit quarantine ──
    # fwd_vs_bt_divergence flagged ~12 strategies in this family; Antigravity audit
    # (Gemini WIP, 2026-05-11) named 3 worst by forward-decay severity:
    #   crypto_soc_proxy_decoupling_a03_v1     decay -32.2% (severity 5.73)
    #   crypto_soc_delta_divergence_a07_v1     decay -21.6% (severity 4.93)
    #   crypto_soc_orderflow_absorption_a07_v1 decay -14.8% (severity 4.76)
    # Family signature: 66% backtest WR vs 32% live WR (Kimi audit). Surgical
    # per-strategy quarantine per docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md.
    # Remaining 23 baby_strats:crypto_soc_* variants queued for follow-up PR;
    # MIN_ELITE_SCORE_BY_CLASS["CRYPTO"]=70 floor cuts most low-quality emissions
    # while explicit enumeration is in progress.
    # Refs: reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md,
    # updates/2026-05-11-money-maker-master-plan.html
    ("CRYPTO", "crypto_soc_proxy_decoupling_a03_v1"),
    ("CRYPTO", "crypto_soc_delta_divergence_a07_v1"),
    ("CRYPTO", "crypto_soc_orderflow_absorption_a07_v1"),
    # 2026-05-12 PR-C: base-name aliases for the same 3 baby_strats:crypto_soc_*
    # draggers above. The _a0X_v1 suffixed variants block currently-emitted picks;
    # these base-name pairs cover any future emitter that drops the suffix and
    # are also the canonical names cited in
    # reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md
    # (decay -32.2% / -21.6% / -14.8% respectively).
    ("CRYPTO", "crypto_soc_proxy_decoupling"),
    ("CRYPTO", "crypto_soc_delta_divergence"),
    ("CRYPTO", "crypto_soc_orderflow_absorption"),
    # ── 2026-05-15 baby_strats overfit quarantine (9 remaining, user-approved) ──
    # fwd_vs_bt_divergence flags + money-maker-ready audit (20260515T211949Z):
    # backtest WR 49-66% vs forward WR 33-41% across all 9. Severity scores 4.15-4.87.
    # Base-name blocks above catch future emissions without the _aXX_v1 suffix;
    # these explicit variants block currently-live suffixed picks.
    # Refs: reports/money_maker_ready_20260515T211949Z.md §5,
    #       reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md
    ("CRYPTO", "crypto_soc_orderflow_absorption_a04_v1"),  # severity 4.87
    ("CRYPTO", "crypto_soc_orderflow_absorption_a03_v1"),  # severity 4.86
    ("CRYPTO", "crypto_adx_pullback_trendresume_v1"),       # severity 4.84, WR 14.3%
    ("CRYPTO", "crypto_soc_delta_divergence_a02_v1"),       # severity 4.73
    ("CRYPTO", "crypto_soc_orderflow_absorption_a08_v1"),   # severity 4.71
    ("CRYPTO", "crypto_soc_proxy_decoupling_a07_v1"),       # severity 4.64
    ("CRYPTO", "crypto_soc_orderflow_absorption_a02_v1"),   # severity 4.37
    ("CRYPTO", "crypto_choppiness_regime_switch_v1"),        # severity 4.35
    ("CRYPTO", "crypto_soc_orderflow_absorption_a09_v1"),   # severity 4.15
    # ── 2026-05-19 T2-02 defense-in-depth: quan_engine already in BLOCKED_SOURCE_SYSTEMS ──
    # policy_clean_net: n=3037, WR=36.4%, PF=0.41 — confirmed losing. Pair is redundant safety net.
    # cta_replicator/COMMODITY, multi_asset_copytrader/FOREX+EQUITY REMOVED: insufficient
    # policy-clean picks (n=1, n=25, n=2) — below 30-pick floor required for a block verdict.
    # 2-engine swarm consensus (DeepSeek+Cerebras) 2026-05-19. Re-evaluate when n≥30.
    ("CRYPTO", "quan_engine"),
    # ── 2026-05-12 SUPREME EDGE — decay-alert P0 hard-blocks ──
    # Per /audit Decay Alerts panel rolling-7d WR drop > 20pp + master plan triage:
    #   futures_momentum: 7d WR 4% vs baseline 42% (-38pp). FUTURES class already
    #     BLOCKED per Codex state machine; this strategy was the largest single
    #     contributor. Add to BLOCKED_ASSET_STRATEGY_PAIRS at FUTURES.
    #   MeanReversionBB: 7d WR 25% vs baseline 60% (-35pp). Class-agnostic
    #     mean-reversion BB strategy; drift_alert TRUE in master plan suggests
    #     regime-broken. Block across CRYPTO + EQUITY (the 2 classes it emits to).
    # Mutation-before-kill protocol satisfied: alerts are dashboard-auto-flagged
    # from rolling 7d window vs cumulative baseline — already statistical, not
    # gut-call.
    # 2026-05-19 ESCALATION (autonomous, per MONITORED_FUTURES_STRATEGIES criteria):
    # H-005 FAILED_ARCHIVED — inversion does NOT rescue it (WR=2% n=202, both directions broken).
    # Escalation criterion met: WR=2% < 10% escalation_wr_floor + H-005 confirms no rescue path.
    ("FUTURES", "futures_momentum"),  # re-blocked 2026-05-19 — H-005 escalation
    ("CRYPTO", "MeanReversionBB"),
    ("EQUITY", "MeanReversionBB"),
    # ── 2026-05-12 MEMECOIN class-wide quarantine (Kimi F13/F14 + 5-agent synthesis) ──
    # Kimi edge audit 2026-05-11 (`reports/kimi_edge_audit_2026-05-11/metrics_by_asset_class.csv`):
    #   MEMECOIN class: n=1869, WR 15.7%, avg_return -3.58%, Sharpe -2.79, PF 0.50.
    # Production raw_picks_clean confirms PF 0.58 / WR 31.6% at n=123,648 emission
    # volume — no edge anywhere in the class. F13 separately flagged `meme_signals`
    # as a synthetic PEPE/PEPE2 training fixture leaking into live picks
    # (`tools/ghost_sweep_2026_05_08.py:36`, `tools/recon_uncharted_tables.py:141`).
    # Both Agent B and Agent D from the 2026-05-12 5-subagent swarm flagged MEMECOIN
    # as MISSING from the master plan blocked list. Block enumerates every distinct
    # `strategy` value observed emitting MEMECOIN picks in the Kimi raw audit CSV
    # (the gate at line 2814 / 4745 does exact-tuple match, no wildcard support).
    # Mutate-before-kill exempt: class-level PF 0.50 over 1869 trades + synthetic
    # fixture root cause = structurally broken, not regime drift.
    # Refs: reports/kimi_edge_audit_2026-05-11/, updates/2026-05-12-5-agent-synthesis.md
    ("MEMECOIN", "meme_signals"),
    ("MEMECOIN", "incubator_gainer"),
    ("MEMECOIN", "quan_engine"),
    ("MEMECOIN", "meta_strategy"),
    # ── 2026-05-12 meta_strategy CRYPTO blanket block ──
    # Per Investigator a207fe2023ae4fdf4 (2026-05-12), meta_strategy's
    # permutation_engine._simulate_portfolio() (meta_strategy/permutation_engine.py:147-168)
    # generates synthetic test trades at constant pnl_pct. Live picks JSON
    # (meta_strategy/data/active_picks.json) does not exist; meta_strategy
    # is listed in dashboard_generator.py:4171 _GHOST_SYSTEMS as "FILE MISSING".
    # 1.6M backtest rows in bt_backtest_trades across ~140 symbol/dir pairs
    # are all template artifacts, not live outcomes. Safe to blanket-block at
    # the (CRYPTO, meta_strategy) level since the strategy has never emitted
    # live picks to the production pipeline.
    # Refs: reports/db_evidence_graded_final_2026-05-08.md F2,
    #       reports/session_summary_2026-05-12.md
    ("CRYPTO", "meta_strategy"),
    ("MEMECOIN", "goldmine_meme"),
    ("MEMECOIN", "sandbox_opposite"),
    ("MEMECOIN", "opposite_day"),
    ("MEMECOIN", "ema_stack"),
    ("MEMECOIN", "macd_rsi_confluence"),
    ("MEMECOIN", "predictions"),
    ("MEMECOIN", "FearGreedReversal"),
    ("MEMECOIN", "AltseasonRotation"),
    ("MEMECOIN", "hurst_mean_reversion"),
    ("MEMECOIN", "fractal_sr_bounce"),
    ("MEMECOIN", "volume_spike_breakout"),
    ("MEMECOIN", "winner_pattern_precursor"),
    ("MEMECOIN", "inverse_winner_pattern_precursor"),
    ("MEMECOIN", "st_obv_support_divergence"),
    ("MEMECOIN", "coinglass_funding_confluence"),
    ("MEMECOIN", "coinglass_leverage_squeeze"),
    ("MEMECOIN", "kimi_tracker"),
    ("MEMECOIN", "Kimi LGBM Feature Proxy"),
    ("MEMECOIN", "Correlation - KAMA Adaptive"),
    ("MEMECOIN", "SCALP"),
    ("MEMECOIN", "justin_rsi_divergence_v2"),
    ("MEMECOIN", "justin_ema9_pullback_v2"),
    ("MEMECOIN", "justin_breakout_volume_v2"),
    ("MEMECOIN", "justin_trend_follow_v2"),
    ("MEMECOIN", "ml_enhanced_DOGEUSDT_15m_D_ensemble_stack"),

    # === 2026-05-12 Dragger Quarantine (money-maker-ready audit) ===
    # kimi_signal_tracking: 673 closed, PF 0.28, -930% PnL, 995% MDD
    #   Classes: CRYPTO, EQUITY, FOREX. Deep negative edge across all three.
    #   Rollback: needs full rehab (3-axis autopsy + DNA mutation) before unblock.
    ("CRYPTO", "kimi_signal_tracking"),
    ("EQUITY", "kimi_signal_tracking"),
    ("FOREX", "kimi_signal_tracking"),

    # alpha_engine_fast: 362 closed, PF 0.62, -128% PnL, 155% MDD
    #   All 7 classes. alpha_engine (non-fast, PF 1.61) remains active and profitable.
    #   Rollback: if any class active picks drop >30% within 48h, re-evaluate.
    ("BOND", "alpha_engine_fast"),
    ("COMMODITY", "alpha_engine_fast"),
    ("CRYPTO", "alpha_engine_fast"),
    ("EQUITY", "alpha_engine_fast"),
    ("ETF", "alpha_engine_fast"),
    ("FOREX", "alpha_engine_fast"),
    ("UNKNOWN", "alpha_engine_fast"),

    # multi_asset: 222 closed, PF 0.31, -160% PnL, 167% MDD
    #   COMMODITY + FOREX. NOT multi_asset_cot (PF 20.54) or multi_asset_copytrader (PF 4.09).
    #   Rollback: run 3-axis autopsy; if profitable on one side/symbol, split block.
    ("COMMODITY", "multi_asset"),
    ("FOREX", "multi_asset"),

    # === 2026-05-13 AA-6 (multi_asset_copytrader per-class audit) ===
    # cavecrew-investigator a4a7d4aa692a6c056 decomposed 943 closed picks:
    #   COMMODITY: n=96, WR=93.8%  -> KEEP (real edge)
    #   EQUITY:    n=28, WR=42.9%  -> thin, monitor
    #   FOREX:     n=662, WR=14.8% -> 44% volume drag (AA-7 mutation gate)
    #   FUTURES:   n=157, WR=2.5%  -> critical drain, surgical block here
    # FUTURES class is silent-dead per memory project_futures_kill_without_replacement;
    # this surgical add does not require mutate-before-kill (FOREX/COMMODITY carve-out).
    # FOREX-side block deferred to AA-7 after mutation-axes analysis.
    # 2026-05-18 OPERATOR DECISION: FUTURES/multi_asset_copytrader moved to
    # MONITORED_FUTURES_STRATEGIES for stats accumulation. Picks tagged _monitor_mode=True.
    # 2026-05-19 ESCALATION (autonomous, per MONITORED_FUTURES_STRATEGIES criteria):
    # WR=2.5% n=157 well below escalation_wr_floor=0.10 (same pattern as futures_momentum).
    # No profitable per-symbol subset found in FUTURES class (copper/platinum monitor-only).
    # Escalation criterion met: monitoring confirms no rescue path.
    ("FUTURES", "multi_asset_copytrader"),  # re-blocked 2026-05-19 — WR=2.5% escalation

    # ── 2026-05-14 Money-Maker-Ready P0: dragger quarantine ──
    # mercury2_fast (CRYPTO): n=32, -140% PnL, PF 0.07
    # ml_bg_system_a (CRYPTO): n=19, -50% PnL, PF 0.14
    # ml_bg_system_b (CRYPTO): n=19, -55% PnL, PF 0.02
    # NOTE: (COMMODITY, multi_asset) and (FOREX, multi_asset) already
    # blocked above at lines ~1851-1852 — not duplicated here.
    ("CRYPTO", "mercury2_fast"),
    ("CRYPTO", "ml_bg_system_a"),
    ("CRYPTO", "ml_bg_system_b"),

    # END Dragger Quarantine

    # ── 2026-05-16 EQUITY dragger quarantine (swarm deep-dive 2026-05-16) ──
    # regime_terminal EQUITY: n=72, WR=34.7%, PF=1.06. strategy "unknown" dominates.
    # Below 45% WR charter floor. Mutation: no profitable direction/symbol subset found (n=72 satisfies threshold).
    ("EQUITY", "regime_terminal"),
    # EAGLE2 Phase 0 (2026-06-02): extend regime_terminal block to CRYPTO/FOREX emitters.
    ("CRYPTO", "regime_terminal"),
    ("FOREX", "regime_terminal"),
    # skyrocket-breakout-scalper EQUITY: n=14, WR=28.6%, PnL=-7.0% — kimi EQUITY loser.
    ("EQUITY", "skyrocket-breakout-scalper"),

    # ── 2026-05-16 stocks_rsi2_pullback EQUITY: RSI(2) dead on live stocks ──
    # Closed-ledger: n=37, WR=38%, PF=0.97 (sub-45% charter floor, PF<1.0).
    # Same RSI(2) Connors/Alvarez pattern as forex_rsi2_mean_reversion (already
    # blocked in BLOCKED_STRATEGIES). All 37 picks are LONG; still actively
    # emitting as of 2026-05-16. n=37 exceeds kill threshold (n>=30).
    # PENDING_UNBLOCK_REVIEW 2026-05-19: WR=50.7%/n=73 above 45% floor; circuit_breaker 55.1%/n=89.
    # 2/2 swarm engines (deepseek + kilo) voted PENDING_UNBLOCK_REVIEW (xai key unavailable).
    # Risk: post-block resolved n≈3 — pre-block performance may contaminate 30d window.
    # Auto-reblock trigger: if WR<40% on next 30 resolved picks, reinstate block immediately.
    # Mandatory re-review: 2026-06-15 (or when post-block n_resolved>=30, whichever is later).
    # ("EQUITY", "stocks_rsi2_pullback"),  # REMOVED 2026-05-19: WR=50.7% (n=73) now exceeds 45% floor

    # ── 2026-05-16 CRYPTO WR lift: sub-floor strategy quarantine ──
    # Dashboard audit 2026-05-16T02:47Z: CRYPTO WR=46.5%, PF=1.31, n=7885.
    # Blocks below target WR<45%, n>=30, PF<1.0 — mutation-protocol gate (n>=30) satisfied.
    # Strategy-level blocks; no source-specific carve-outs needed (all sources drag).
    # Expected impact: ~1,281 bad trades removed, estimated WR lift to ~48.5%.

    # bollinger_squeeze: n=107, WR=26.2%, PF=0.21 — severe drag, 79 losses vs 28 wins
    ("CRYPTO", "bollinger_squeeze"),  # n=107, WR=26.2%, PF=0.21 — sub-floor CRYPTO drag

    # gainer_compression_relaxed_mut: n=48, WR=18.8%, PF=0.51 — extreme drag
    ("CRYPTO", "gainer_compression_relaxed_mut"),  # n=48, WR=18.8%, PF=0.51 — sub-floor CRYPTO drag

    # rapid_momentum_filter_mut: n=34, WR=29.4%, PF=0.67 — dna_rapid_fire_mutations source
    ("CRYPTO", "rapid_momentum_filter_mut"),  # n=34, WR=29.4%, PF=0.67 — sub-floor CRYPTO drag

    # multi_period_rsi_confluence_doge: n=46, WR=33.3%, PF=0.0 — zero PF, dead strategy
    ("CRYPTO", "multi_period_rsi_confluence_doge"),  # n=46, WR=33.3%, PF=0.0 — sub-floor CRYPTO drag

    # crypto_shortterm_nr_er_cci_ignition_v1: n=128, WR=34.4%, PF=0.0 — 128 trades, zero PF
    ("CRYPTO", "crypto_shortterm_nr_er_cci_ignition_v1"),  # n=128, WR=34.4%, PF=0.0 — sub-floor CRYPTO drag

    # crypto_shortterm_nr_er_adx_ignition_v1: n=132, WR=34.8%, PF=0.91 — 132 trades, no edge
    ("CRYPTO", "crypto_shortterm_nr_er_adx_ignition_v1"),  # n=132, WR=34.8%, PF=0.91 — sub-floor CRYPTO drag

    # crypto_shortterm_nr_er_bbands_ignition_v1: n=94, WR=41.5%, PF=None — PF unresolved, sub-floor
    ("CRYPTO", "crypto_shortterm_nr_er_bbands_ignition_v1"),  # n=94, WR=41.5%, PF=None — sub-floor CRYPTO drag

    # crypto_soc_delta_divergence_a05_v1: n=61, WR=37.7%, PF=0.0 — soc family, zero PF
    ("CRYPTO", "crypto_soc_delta_divergence_a05_v1"),  # n=61, WR=37.7%, PF=0.0 — sub-floor CRYPTO drag

    # crypto_soc_delta_divergence_a09_v1: n=84, WR=38.1%, PF=0.0 — soc family, zero PF
    ("CRYPTO", "crypto_soc_delta_divergence_a09_v1"),  # n=84, WR=38.1%, PF=0.0 — sub-floor CRYPTO drag

    # crypto_soc_delta_divergence_a06_v1: n=129, WR=39.5%, PF=0.11 — soc family, near-zero PF
    ("CRYPTO", "crypto_soc_delta_divergence_a06_v1"),  # n=129, WR=39.5%, PF=0.11 — sub-floor CRYPTO drag

    # crypto_soc_orderflow_absorption_a05_v1: n=125, WR=40.0%, PF=None — PF unresolved, sub-floor
    ("CRYPTO", "crypto_soc_orderflow_absorption_a05_v1"),  # n=125, WR=40.0%, PF=None — sub-floor CRYPTO drag

    # crypto_soc_orderflow_absorption_a06_v1: n=199, WR=41.2%, PF=0.37 — largest volume drag
    ("CRYPTO", "crypto_soc_orderflow_absorption_a06_v1"),  # n=199, WR=41.2%, PF=0.37 — sub-floor CRYPTO drag

    # crypto-fear-reversal-scout: n=32, WR=40.6%, PF=0.85 — kimi_riseoftheclaw source
    ("CRYPTO", "crypto-fear-reversal-scout"),  # n=32, WR=40.6%, PF=0.85 — sub-floor CRYPTO drag

    # multi_period_rsi_confluence_sol: n=62, WR=41.9%, PF=0.88 — baby_strats_forward source
    ("CRYPTO", "multi_period_rsi_confluence_sol"),  # n=62, WR=41.9%, PF=0.88 — sub-floor CRYPTO drag

    # ── M-105 (surgical): ml_enhanced _D_ensemble_stack 15m draggers quarantine (2026-05-18) ──
    # The _D_ensemble_stack 15m sub-family is the structural drag within ml_enhanced.
    # _B_lightgbm sub-family is ELITE (WR=81.6%, PF=9.70, n=190) — NOT touched.
    # _A_xgboost is CLEAN (WR=75.0%, PF=3.77, n=24) — NOT touched.
    # Do NOT use startswith('ml_enhanced') blanket block — would kill elite lightgbm variants.
    # Expected impact: CRYPTO filter n: ~469→~357, WR: 66.7%→73.4%, PF: 2.56→2.99 (T1 territory).
    # Source: closed_picks.json autopsy 2026-05-18 swarm analysis.
    # Re-evaluate each variant individually at n=30+ — DOGEUSDT may recover with regime shift.
    ("CRYPTO", "ml_enhanced_INJUSDT_15m_D_ensemble_stack"),    # n=26 WR=4%  PF=0.070 all-SHORT loser
    ("CRYPTO", "ml_enhanced_DOGEUSDT_15m_D_ensemble_stack"),   # n=23 WR=61% PF=0.776 losses catastrophic
    ("CRYPTO", "ml_enhanced_AVAXUSDT_15m_D_ensemble_stack"),   # n=23 WR=52% PF=0.502 net negative
    ("CRYPTO", "ml_enhanced_TONUSDT_4h_D_ensemble_stack"),     # n=19 WR=58% PF=0.979 kills edge
    ("CRYPTO", "ml_enhanced_ALGOUSDT_15m_B_lightgbm"),         # n=21 WR=62% PF=0.431 anomalous B loser

    # ── M-109: ml_enhanced extended quarantine (2026-05-18) ──
    # Extends M-105 to 16 additional ml_enhanced variants confirmed n>=10, PF<1.2.
    # Source: strategy_performance.json autopsy 2026-05-18. 10 active picks blocked.
    # PROTECTED (not touched): _B_lightgbm elite variants (PF>=2.0, n>=20).
    # Re-evaluate at n>=30 if WR improves above 50% and PF above 1.3.
    ("CRYPTO", "ml_enhanced_TRXUSDT"),                      # n=12  WR=0%  PF=0.000 zero wins
    ("CRYPTO", "ml_enhanced_TRXUSDT_1d_B_lightgbm"),        # n=26  WR=12% PF=0.003 near-zero PF
    ("CRYPTO", "ml_enhanced_HBARUSDT_1d_D_ensemble_stack"), # n=28  WR=43% PF=0.288 losses dominate
    ("CRYPTO", "ml_enhanced_JTOUSDT_1d_B_lightgbm"),        # n=30  WR=37% PF=0.297 sub-floor
    ("CRYPTO", "ml_enhanced_FILUSDT"),                      # n=12  WR=17% PF=0.300 low WR/PF
    ("CRYPTO", "ml_enhanced_ARBUSDT"),                      # n=12  WR=17% PF=0.316 low WR/PF
    ("CRYPTO", "ml_enhanced_AVAXUSDT_1d_B_lightgbm"),       # n=25  WR=44% PF=0.337 sub-floor
    ("CRYPTO", "ml_enhanced_OPUSDT_4h_D_ensemble_stack"),   # n=12  WR=25% PF=0.416 sub-floor
    ("CRYPTO", "ml_enhanced_AVAXUSDT"),                     # n=11  WR=36% PF=0.622 sub-floor
    ("CRYPTO", "ml_enhanced_SUIUSDT"),                      # n=11  WR=36% PF=0.624 sub-floor
    ("CRYPTO", "ml_enhanced_POLUSDT_1d_B_lightgbm"),        # n=27  WR=48% PF=0.668 sub-floor
    ("CRYPTO", "ml_enhanced_APEUSDT"),                      # n=16  WR=38% PF=0.900 sub-floor
    ("CRYPTO", "ml_enhanced_LINKUSDT"),                     # n=11  WR=36% PF=0.939 sub-floor
    ("CRYPTO", "ml_enhanced_ADAUSDT"),                      # n=10  WR=40% PF=1.000 break-even
    ("CRYPTO", "ml_enhanced_ADAUSDT_15m_B_lightgbm"),       # n=28  WR=61% PF=1.076 sub-1.2
    ("CRYPTO", "ml_enhanced_APTUSDT"),                      # n=10  WR=40% PF=1.112 sub-1.2
    # ── 2026-05-18: super_signals CRYPTO — 3-agent swarm consensus BLOCK ──
    # docs/STRATEGY_INVESTIGATION_super_signals_CRYPTO_2026-05-18.md (complete):
    #   WR=33% PF=0.65 n=139 MDD=105% — both kill criteria met (PF<1, n>=100).
    # super_signals EQUITY (WR=55.7% PF=1.27) retains edge — per-class block only.
    # Unblock when: regime gate implemented + CRYPTO subset PF≥1.5 in n≥50 regime bucket.
    ("CRYPTO", "super_signals"),                            # n=139 WR=33% PF=0.65 MDD=105%
    # ── 2026-05-18: aggregated_picks CRYPTO — kill criteria met ──
    # docs/STRATEGY_INVESTIGATION_aggregated_picks_CRYPTO_2026-05-18.md (complete):
    #   WR=35% PF=0.93 n=106 MDD=39% — both kill criteria met (PF<1, n>=100).
    # All aggregated_picks CRYPTO are LONG only — no SHORT subset to protect.
    # aggregated_picks overall n=389 PF=6.90 (other classes healthy) — per-class block only.
    # Unblock when: aggregator confidence filter tightened + CRYPTO PF≥1.5 on n≥50 re-test.
    ("CRYPTO", "aggregated_picks"),                         # n=106 WR=35% PF=0.93 MDD=39%
    # ── 2026-05-18 Session CU: rapid_fire CRYPTO — 3-engine swarm BLOCK ──
    # docs/STRATEGY_INVESTIGATION_rapid_fire_CRYPTO_2026-05-18.md updated (addendum):
    # Session CK said MONITOR (WR=40% PF=1.10 dashboard view). pf_registry policy-clean
    # (post-dedup, authoritative) shows WR=33% PF=0.368 Kelly=-0.563 — reversed to KILL.
    # Swarm consensus: deepseek+kilo unanimous BLOCK. User approved: "proceed to your discretion".
    ("CRYPTO", "rapid_fire"),                               # n=91 WR=33% PF=0.37 Kelly=-0.56
    # ── 2026-05-18 Session CU: copy_trader_intel CRYPTO — zero-win kill ──
    # docs/STRATEGY_INVESTIGATION_copy_trader_intel_CRYPTO_2026-05-18.md:
    # n=32 WR=0.0% PF=0.000 — zero wins across 32 resolved picks. Unambiguous kill.
    # Swarm consensus: deepseek unanimous BLOCK. User approved: "proceed to your discretion".
    ("CRYPTO", "copy_trader_intel"),                        # n=32 WR=0% PF=0 zero wins
    # ── 2026-05-19 Session CV: copy_trader_clones CRYPTO — negative Kelly kill ──
    # docs/STRATEGY_INVESTIGATION_copy_trader_clones_CRYPTO_2026-05-19.md:
    # n=34 WR=44% PF=0.78 Kelly=-0.123 RR=0.990 (symmetric). Negative expectancy at n>=30.
    ("CRYPTO", "copy_trader_clones"),                       # n=34 WR=44% PF=0.78 Kelly=-0.12
    # __ 2026-05-19 Session: ensemble CRYPTO __ largest single drag in canonical __
    # docs/STRATEGY_INVESTIGATION_ensemble_CRYPTO_2026-05-19.md (complete):
    #   pf_registry.json by_asset_class_strategy_policy_clean_net (post-dedup, net):
    #   n=79 wins=4 losses=75 WR=5.06% PF=0.013 pnl_pct=-56.346.
    #   25 distinct symbols, 24/25 WR=0% (only SOLUSDT n=1 won) - NOT a symbol ghost.
    #   136 LONG / 0 SHORT raw - direction-mono; sign-flip = post-selection bias.
    #   Live emitting today (entry dates 2026-05-14..17). Halt highest-leverage drag.
    #   Removing ensemble flips canonical CRYPTO PF 0.64->1.21 (arithmetic, NOT new edge).
    # Reproducer: tools/build_pf_registry.py + check by_asset_class_strategy_policy_clean_net.
    # Unblock: pre-register as H-039+ (M-107) AND clear unmodified edge_stability_harness.
    ("CRYPTO", "ensemble"),                                 # n=79 WR=5% PF=0.013 pnl=-56pp largest single drag
    # __ 2026-05-20 Session: opencode per-class table verdict __
    #   FOREX is 0.01 PF from Tier-2; block 2 toxic emitters (alpha_engine + multi_asset_scanner)
    #   to remove drag. cta_replicator FOREX (n=97 PF 2.38 WR 64.9%) carries the class once these
    #   2 are blocked. NOT a whitelist promotion — drag removal only. Real T2 still gated on
    #   harness clearance per F-1 plan + Kimi-P0 resolver coverage fix (commit f1370a3).
    ("FOREX", "alpha_engine"),                              # n=15 WR=40% PF=0.84 sub-T2 drag
    ("FOREX", "multi_asset_scanner"),                       # n=11 WR=9% PF=0.21 -2.3bps drag
    # __ CRYPTO luxalgo_filters: opencode table flagged 17.5% vol drag at PF 1.12 __
    # Concentration cap rather than full block deferred until forward 200-close verification
    # of recent block batch lands. Adding here as full block — narrowest reading of opencode's
    # "hot-list only during UTC 14-22" recommendation = block lazlxalgo-class strategy outright.
    ("CRYPTO", "luxalgo_filters"),                          # n>=20 PF~1.12 17.5% vol drag concentration risk
}


# Direction-aware blocks — kills (asset_class, strategy, direction) triples.
# Used by historical-blocked filter to exclude rows from aggregations and by
# active-pick gating to reject new emissions. Adds the missing third axis on
# top of BLOCKED_ASSET_STRATEGY_PAIRS for cases where a strategy has edge in
# one direction only.
#
# 2026-04-17 deep-dive (subagent A) on ml_crypto_predictor SHORTs:
#   - Total: 297 SHORTs, 38.4% WR, PF 0.62, -568.3% PnL
#   - APEUSDT alone: 28 SHORTs, 0% WR, -459.5% PnL (all hit identical SL
#     at 0.1039 — broken/stale SL logic, NOT real losses)
#   - 2026-04-16 single-day catastrophe: 69 SHORTs, 0% WR, -558.5% PnL,
#     all closed at 22:52:26Z (synchronized — exchange/liquidation issue)
#   - LONG variants remain healthy: 89 picks, 86.5% WR, +270.4% PnL
#     (do NOT extend block to LONG)
#   - FETUSDT bonus claim ("100% WR" at line 2748) outdated:
#     current data shows 53.4% WR, +4.3% PnL (still slightly profitable)
# ── BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES (2026-05-12) ──
# Per-symbol surgical quarantine for ghost-row cohorts in bt_backtest_trades —
# (class, strategy, symbol) tuples where the cohort shows constant pnl_pct +
# <5 distinct entry prices over >1000 rows. These are template/synthetic
# emissions, not real trades; including them pollutes dashboard aggregates.
#
# Evidence: reports/db_evidence_graded_final_2026-05-08.md F2 + Investigator C
# sweep 2026-05-12 against db_health.json::ghost_rows (total 655k rows / 18
# cohorts). 5 confirmed patterns documented; 4 here are symbol-specific. The
# 5th (meta_strategy 1.6M rows across 140 symbol/dir pairs) is deferred until
# cohort detail re-populates and the full pair list is enumerated.
#
# Used by:
#   - quality_gates.py::passes_active_gate (rejects new emissions)
#   - dashboard_generator.py::_is_historical_blocked_pick (excludes from
#     historical aggregates so the ghost rows stop polluting WR/PF/MDD)
BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES = {
    # quan_engine MATIC LONG — 215,248 rows, constant pnl_pct = -15.0000%,
    # STDDEV=0, single entry price. Memory `project_quan_engine_matic_positive_artifact`
    # confirms 755/1001 quan_engine picks are MATICUSDT LONG at a fixed 2.5% TP.
    # quan_engine_scalp already blocked CRYPTO-wide at line 1572; this is the
    # base quan_engine variant, blocked only on the MATIC artifact.
    ("CRYPTO", "quan_engine", "MATICUSDT"),
    # KIMI_signal_tracker ETH/BTC LONG — ~597 rows × 4 pnl buckets each on
    # ETHUSDT, similar on BTCUSDT. Multi-TP template signature.
    ("CRYPTO", "KIMI_signal_tracker", "ETHUSDT"),
    ("CRYPTO", "KIMI_signal_tracker", "BTCUSDT"),
    # irb_hoffman ADAUSDT SHORT — exact 50/50 split between -1.78% and +30.30%
    # pnl buckets, 2 distinct entry prices. Backtest emitter artifact.
    ("CRYPTO", "irb_hoffman", "ADAUSDT"),
    # funding_rate_carry ROBOUSDT LONG — 566 rows constant -99.26% pnl. ROBO
    # was delisted; the strategy auto-force-closed every entry against a stale
    # exit price. Symbol-block until delisting handling lands.
    ("CRYPTO", "funding_rate_carry", "ROBOUSDT"),
    # ── FX1 JPY-cross block (AA-7 mutation analysis 2026-05-13) ──
    # Per-symbol decomposition of multi_asset_copytrader × FOREX (n=662 terminal):
    # all 5 JPY-cross pairs catastrophic (combined n=484, WR ~4%, PF <0.15).
    # Non-JPY majors (EURGBP/GBPUSD/AUDUSD/USDCHF) preserved at 61-100% WR.
    # Root cause: BoJ tightening 2024-2025 inverted prior LONG-USD-vs-JPY carry
    # bias without strategy update. 4-engine swarm consensus 2026-05-13.
    # See reports/aa7_forex_per_symbol_mutation_20260513.md + reports/
    # swarm_revalid_20260513/synthesis_forex.md.
    ("FOREX", "multi_asset_copytrader", "EURJPY=X"),  # n=154 WR 1.9% PF 0.02
    ("FOREX", "multi_asset_copytrader", "USDJPY=X"),  # n=132 WR 3.0% PF 0.04
    ("FOREX", "multi_asset_copytrader", "GBPJPY=X"),  # n=84  WR 7.1% PF 0.10
    ("FOREX", "multi_asset_copytrader", "AUDJPY=X"),  # n=77  WR 3.9% PF 0.06
    ("FOREX", "multi_asset_copytrader", "CADJPY=X"),  # n=37  WR 10.8% PF 0.14
}


BLOCKED_DIRECTION_TRIPLES = {
    # 2026-05-06 FOREX mutation decisions: block LONG direction for strategies
    # that have proven edge SHORT only (anti-edge long confirmed on live data).
    # ── 2026-05-16 FOREX LONG-direction blocks (14d temp-unblock expired 2026-05-22) ──
    # ig_contrarian_sentiment LONG: 15.7% WR, PF 0.35 (n=46); SHORT keeps 57.1% WR, PF 1.54
    # myfxbook_retail_contrarian LONG: 10.6% WR, PF 0.34; SHORT keeps 46.2% WR
    # Evidence: reports/money_maker_ready_20260516T000106Z.md §9
    ("FOREX", "ig_contrarian_sentiment", "LONG"),
    ("FOREX", "myfxbook_retail_contrarian", "LONG"),
    ("FOREX", "quan_engine_swing", "LONG"),
    ("CRYPTO", "ml_crypto_predictor", "SHORT"),
    # 2026-04-17 11-strategy WR-drop subagent (MUTATE recommendations).
    # See updates/2026-04-17-eleven-strategies-decay-investigation.md
    # quan_engine_swing LONG: 0% WR last 7d; sister to quan_engine_scalp which
    # has same LONG-bias bleed (-83% PnL — see deepscan-1 + mutation MD).
    # SHORT variant of quan_engine_swing remains profitable; keep direction-only.
    ("CRYPTO", "quan_engine_swing", "LONG"),
    # crypto_keltner_compression_expansion_v1 LONG = 17% WR -2.7% avg;
    # SHORT = 55% WR +0.7%. Asymmetric edge — block LONG only.
    ("CRYPTO", "crypto_keltner_compression_expansion_v1", "LONG"),
    # keltner_compression_expansion_eth_v1 LONG = 27% WR -3.6%; SHORT 1/1 OK.
    # Same Keltner family pattern as above.
    ("CRYPTO", "keltner_compression_expansion_eth_v1", "LONG"),
    # 2026-05-15 FOREX LONG-side autopsy (reports/forex_mutation_autopsy_20260515.md):
    # FOREX LONG n=119 WR 29.4% PF 0.80 is the class drag; SHORT PF 8.11.
    # Block the named LONG losers only — forex-rsi-ema-scout LONG (PF 1.68)
    # and the entire SHORT side stay untouched so the class is not starved.
    ("FOREX", "fx_smart_carry_trade_momentum", "LONG"),  # n=24 WR 20.8% PF 0.47
    ("FOREX", "dxy-reversal-scout", "LONG"),             # n=10 WR 20.0% PF 0.44
    ("FOREX", "MeanReversionBB", "LONG"),                # LONG PF 0.22; SHORT stays
    # 2026-05-16 cta_cross_asset_tsmom direction autopsy (closed_picks.json):
    # LONG = NZDUSD=X n=60, WR=42%, PF=1.07 (sub-45% charter floor)
    # SHORT = USDJPY=X n=109, WR=71%, PF=3.61 (T1 edge — keep)
    # Direction gap: 29pp WR difference with n=60 LONG confirms mutation block.
    ("FOREX", "cta_cross_asset_tsmom", "LONG"),
    # 2026-05-17 COMMODITY cta_cross_asset_tsmom direction autopsy:
    # LONG n=24 (valid resolved), WR=0%, PF=0.00 (complete wipeout)
    # SHORT n=47 (valid resolved), WR=19%, PF=0.39; binomial p=0.000012 vs H0=WR≥50%
    # Both directions are losers — COT strategies (WR 75-80%, PF 4.5-5.0) carry COMMODITY edge.
    # n<100 but binomial test is conclusive; re-evaluate if n reaches 100+ post-purge (2026-05-24).
    ("COMMODITY", "cta_cross_asset_tsmom", "LONG"),
    ("COMMODITY", "cta_cross_asset_tsmom", "SHORT"),
    # 2026-05-17 multi_asset_copytrader FOREX direction autopsy (M-063):
    # LONG n=603, WR=10.9%, PF=0.140 — JPY-cross concentration is the killer
    # (EURJPY=X WR=1.9%/n=154, USDJPY=X WR=3.0%/n=133, GBPJPY=X WR=10.3%/n=87, AUDJPY=X WR=3.6%/n=84).
    # SHORT n=93, WR=52.7%, PF=1.351 — sub-T2 PF but not a loser; watch for improvement.
    # Non-JPY pairs show real edge (EURGBP=X WR=70.8%/PF=3.437, GBPUSD=X WR=66.7%/PF=2.449).
    # Kill the LONG direction to stop the JPY-cross bleed while SHORT accumulates data.
    ("FOREX", "multi_asset_copytrader", "LONG"),
    # 2026-05-17 combined_confidence_strategy LONG autopsy (closed_picks.json):
    # LONG (BUY) n=10, WR=10%, binomial p≈0.011 vs H0=WR≥50% — pre-SPA kill.
    # SHORT (SELL) n=9, WR=56% — marginal edge, keep. Re-evaluate at n=20+.
    ("CRYPTO", "combined_confidence_strategy", "LONG"),
    ("EQUITY", "combined_confidence_strategy", "LONG"),
    ("COMMODITY", "combined_confidence_strategy", "LONG"),
    # 2026-05-17 cta_commodity_momentum_term direction autopsy (pending_spa_scan):
    # n=11, WR=0%, PF=0.00, avg=-3.55% — both directions losing. Pre-SPA kill.
    # Re-evaluate after n=20+ (est. 9 more picks). Binomial p<0.001 for WR=0 at n=11.
    ("COMMODITY", "cta_commodity_momentum_term", "LONG"),
    ("COMMODITY", "cta_commodity_momentum_term", "SHORT"),
    # cta_replicator COMMODITY autopsy 2026-05-17: WR=0-19% PF=0.22 n=83
    # (Oil CL=F n=47 WR=19.1%, Gas NG=F n=24 WR=0.0%, Corn ZC=F n=8 WR=0.0%)
    # Both directions sub-floor (<45% charter). CT=F Cotton edge (WR=84-87%)
    # is from cot_positioning / cftc_cot_commercial_signal — unaffected by this block.
    # Defense-in-depth companion to BLOCKED_SOURCE_SYMBOL_PAIRS (CL=F/NG=F/ZC=F).
    # Re-evaluate if non-CT=F picks accumulate n≥30 with WR≥50% in one direction.
    ("COMMODITY", "cta_replicator", "LONG"),
    ("COMMODITY", "cta_replicator", "SHORT"),
    # 2026-05-17 P1-1: ml_enhanced_*USDT_15m_D direction autopsy (closed_picks.json):
    # Both strategies emit SELL only. BTCUSDT n=12 WR=17% avg=-0.07%; ADAUSDT n=12 WR=17% avg=-0.09%.
    # n≥5 and WR<50% — block SHORT. No BUY direction to evaluate; re-assess when BUY n≥5.
    ("CRYPTO", "ml_enhanced_BTCUSDT_15m_D_ensemble_stack", "SHORT"),
    ("CRYPTO", "ml_enhanced_ADAUSDT_15m_D_ensemble_stack", "SHORT"),
    ("CRYPTO", "ml_enhanced_INJUSDT_15m_D_ensemble_stack", "SHORT"),  # n=26 WR=3.8% gap in direction blocks
    # 2026-05-17 FUTURES classification audit (reports/futures_classification_audit_2026_05_17.md):
    # multi_asset_copytrader on commodity futures =F symbols — 203 picks, WR=3%, PF=0.06.
    # BUY n=147 WR=2.0%; SELL n=56 WR=5.4% — both directions catastrophic.
    # Same symbols (CT=F, SI=F, HG=F) show WR=85.7% under COT strategies (COMMODITY class).
    # 2026-05-18 OPERATOR DECISION: moved to MONITORED_FUTURES_STRATEGIES (stats mode).
    # ("FUTURES", "multi_asset_copytrader", "LONG"),   # unblocked 2026-05-18 — monitor
    # ("FUTURES", "multi_asset_copytrader", "SHORT"),  # unblocked 2026-05-18 — monitor
}

# ── MONITORED_FUTURES_STRATEGIES (2026-05-18) ──
# Operator decision 2026-05-18: futures strategies moved from hard-block to
# shadow/stats accumulation mode. Picks from these strategies are allowed to
# pass gates but are tagged with _monitor_mode=True and NOT sized for real
# capital. Goal: accumulate n-count so per-regime optimization can determine
# if any subset (symbol, direction, regime) shows viable edge.
#
# Criteria to graduate from MONITOR → LIVE:
#   - n >= 50 in the monitoring window
#   - WR >= 50% AND PF >= 1.5 on the monitored subset
#   - At least 3 contiguous weeks of positive expected value
#
# Criteria to escalate back to BLOCKED:
#   - Monitoring period completes with WR < 30% or PF < 0.8
#   - Any single-week realized PF < 0.5 (emergency re-block)
MONITORED_FUTURES_STRATEGIES: dict[str, dict] = {
    "futures_momentum": {
        "blocked_since": "2026-05-06",
        "unblocked_for_monitor": "2026-05-18",
        "stats_at_unblock": {"n": 201, "wr": 0.020, "pf": None},
        "reason": "WR=2% on n=201. Monitor to collect regime-stratified stats for optimization.",
        # 2026-05-19: ESCALATED back to BLOCKED. H-005 FAILED_ARCHIVED (inversion does NOT rescue it).
        # WR=2% n=202 — well below escalation_wr_floor=0.10. Added back to BLOCKED_ASSET_STRATEGY_PAIRS.
        "escalated_to_blocked": "2026-05-19",
        "escalation_reason": "H-005 FAILED_ARCHIVED: inversion WR also ~2%. No rescue path. Swarm unanimous.",
        "review_date": "2026-07-18",
        "sizing": "zero",
        "escalation_wr_floor": 0.10,
        "min_picks_per_week": 5,
    },
    "multi_asset_copytrader": {
        "blocked_since": "2026-05-13",
        "unblocked_for_monitor": "2026-05-18",
        "stats_at_unblock": {"n": 157, "wr": 0.025, "pf": 0.06},
        "reason": "FUTURES WR=2.5% on n=157. Monitor per-symbol breakdown for optimization.",
        # 2026-05-19: ESCALATED back to BLOCKED. WR=2.5% < 10% escalation_wr_floor.
        # No profitable per-symbol subset in FUTURES (copper/platinum monitor-only, no clean edge).
        # Added back to BLOCKED_ASSET_STRATEGY_PAIRS.
        "escalated_to_blocked": "2026-05-19",
        "escalation_reason": "WR=2.5% < 10% floor. No FUTURES sub-segment with positive edge found.",
        # Extended 2026-06-18→2026-07-18 per swarm review (60 days needed for n≥50)
        "review_date": "2026-07-18",
        "sizing": "zero",
        "escalation_wr_floor": 0.10,
        "min_picks_per_week": 5,
    },
}
_MONITORED_FUTURES_STRATS_LOWER = {s.lower() for s in MONITORED_FUTURES_STRATEGIES}


def is_futures_monitored(pick: dict) -> bool:
    """Return True if pick is a FUTURES strategy in monitor-only mode (no real sizing)."""
    return (
        str(pick.get("asset_class", "")).upper() == "FUTURES"
        and str(pick.get("strategy", "")).lower() in _MONITORED_FUTURES_STRATS_LOWER
    )


def tag_futures_monitor(pick: dict) -> dict:
    """Add _monitor_mode=True tag to FUTURES monitored picks. Modifies in-place."""
    if is_futures_monitored(pick):
        pick["_monitor_mode"] = True
        pick["_monitor_tag"] = "FUTURES_STATS_ONLY"
        pick["_sizing_override"] = "zero"
    return pick



# ── BABY_STRATEGY_MONITOR (2026-05-28) ──
# Shadow/monitor mode for 6 new baby strategies wired into production.
# Picks from these strategies are tagged _monitor_mode=True so they accumulate
# stats in MySQL but do NOT surface on the live dashboard or trigger trading signals.
#
# Criteria for promotion from SHADOW → LIVE (per strategy):
#   - n >= 20 resolved picks
#   - WR >= 50%
#   - PF >= 1.2
#   - Manual operator review via review_baby_monitor.py results
#
# etf_dual_momentum_rotation:     DIA WR 58.8%, PF 2.64 (backtest) — strongest ETF edge
# futures_session_breakout_cot:   ES=F WR 61.5%, PF 1.39 (backtest) — strong futures edge
# copper_platinum_cot_momentum:   COMMODITY spread, COT-aligned — edge TBD
# bond_yield_curve_momentum:      BOND curve steepener/flattener — edge TBD
# equity_sector_rotation_momentum:EQUITY sector momentum rotation — edge TBD
# crypto_atr_ratio_expansion_long:CRYPTO ATR expansion long — edge TBD
BABY_STRATEGY_MONITOR: dict[str, dict] = {
    "etf_dual_momentum_rotation": {
        "asset_class": "ETF",
        "backtest_wr_pct": 58.8,
        "backtest_pf": 2.64,
        "shadow_since": "2026-05-28",
        "promotion_criteria": "n>=20, WR>=50%, PF>=1.2",
        "notes": "DIA dual momentum rotation — strongest ETF edge in backtest",
    },
    "futures_session_breakout_cot": {
        "asset_class": "FUTURES",
        "backtest_wr_pct": 61.5,
        "backtest_pf": 1.39,
        "shadow_since": "2026-05-28",
        "promotion_criteria": "n>=20, WR>=50%, PF>=1.2",
        "notes": "ES=F session breakout with COT alignment — strong futures edge",
    },
    "copper_platinum_cot_momentum": {
        "asset_class": "COMMODITY",
        "backtest_wr_pct": None,
        "backtest_pf": None,
        "shadow_since": "2026-05-28",
        "promotion_criteria": "n>=20, WR>=50%, PF>=1.2",
        "notes": "Copper/platinum spread with COT momentum — edge TBD",
    },
    "bond_yield_curve_momentum": {
        "asset_class": "BOND",
        "backtest_wr_pct": None,
        "backtest_pf": None,
        "shadow_since": "2026-05-28",
        "promotion_criteria": "n>=20, WR>=50%, PF>=1.2",
        "notes": "Yield curve steepener/flattener momentum — edge TBD",
    },
    "equity_sector_rotation_momentum": {
        "asset_class": "EQUITY",
        "backtest_wr_pct": None,
        "backtest_pf": None,
        "shadow_since": "2026-05-28",
        "promotion_criteria": "n>=20, WR>=50%, PF>=1.2",
        "notes": "Sector rotation momentum — edge TBD",
    },
    "crypto_atr_ratio_expansion_long": {
        "asset_class": "CRYPTO",
        "backtest_wr_pct": None,
        "backtest_pf": None,
        "shadow_since": "2026-05-28",
        "promotion_criteria": "n>=20, WR>=50%, PF>=1.2",
        "notes": "ATR ratio expansion long entries — edge TBD",
    },
}

_BABY_MONITORED_STRATS_LOWER = {s.lower() for s in BABY_STRATEGY_MONITOR}


def is_baby_monitored(pick: dict) -> bool:
    """Return True if this pick is from a shadow-mode baby strategy."""
    return (
        pick.get("origin") in ("baby_strategies", "antigravity_strategies")
        and str(pick.get("strategy", "")).lower() in _BABY_MONITORED_STRATS_LOWER
    )


def tag_baby_monitor(pick: dict) -> dict:
    """Add _monitor_mode=True tag to baby strategy shadow picks. Modifies in-place."""
    if is_baby_monitored(pick):
        strat = str(pick.get("strategy", "")).lower()
        meta = None
        for key, val in BABY_STRATEGY_MONITOR.items():
            if key.lower() == strat:
                meta = val
                break
        pick["_monitor_mode"] = True
        pick["_monitor_tag"] = "BABY_SHADOW"
        pick["_sizing_override"] = "zero"
        if meta:
            pick["_baby_backtest_wr"] = meta.get("backtest_wr_pct")
            pick["_baby_backtest_pf"] = meta.get("backtest_pf")
    return pick

# Single-axis kill list extension — 2026-04-17 forex bleed forensics.
# These strategies have a -20 score penalty (`STRATEGY_NEGATIVE_BIAS_SCORES`)
# but were NOT in PERMANENTLY_KILLED so historical aggregations still
# included them. Adding here so _is_historical_blocked_pick excludes them
# AND so they're hard-killed for new picks (not just demoted).
EXTRA_KILLED_FOREX_STRATEGIES = {
    "community_london_breakout_v2_forex",  # 0.0% WR on n=16, -7.9% PnL
                                           # London ORB academic edge is 40-60% WR;
                                           # this implementation has zero edge
    # 2026-05-24 Institutional Readiness P0 — FOREX killers.
    # Historical closed_picks.json shows consistent negative edge.
    "fx_smart_carry_trade_momentum",       # n=15, 0% WR, -0.08% sum PnL
    "fx_smart_forex_rsi2_mean_reversion",  # n=5, 0% WR, -0.03% sum PnL
}
PERMANENTLY_KILLED_STRATEGIES |= EXTRA_KILLED_FOREX_STRATEGIES
# Refresh case-insensitive lookup
_KILLED_STRATEGIES_LOWER = {s.lower() for s in PERMANENTLY_KILLED_STRATEGIES}


def _forward_lane_wr_ratio(pick: Dict[str, Any]) -> float:
    """Best win-rate among forward/out-of-sample fields only (0-1). Ignores history_wr."""
    return max(
        _ratio(pick.get("strat_fwd_wr")),
        _ratio(pick.get("strategy_fwd_wr")),
        _ratio(pick.get("forward_wr")),
    )


def _forward_lane_trades(pick: Dict[str, Any]) -> int:
    """Largest forward/out-of-sample trade count. Ignores history_trades."""
    return max(
        _int(pick.get("strat_fwd_trades")),
        _int(pick.get("strategy_fwd_trades")),
        _int(pick.get("forward_trades")),
    )


def _non_crypto_active_raw_score_bypass(pick: Dict[str, Any]) -> bool:
    """Strong audited history can justify surfacing a low raw dashboard score.

    Requires both (1) concentrated backtest history and (2) a minimum forward
    lane with non-random WR so picks cannot bypass the floor on BT alone.
    """
    n = _int(pick.get("history_trades", 0))
    if n < 30:
        return False
    hist_ok = _ratio(pick.get("history_wr_bayes", 0)) >= 0.88 or (
        _ratio(pick.get("history_wr", 0)) >= 0.88 and n >= 40
    )
    if not hist_ok:
        return False
    fwd_n = _forward_lane_trades(pick)
    fwd_wr = _forward_lane_wr_ratio(pick)
    if fwd_n < NC_RAW_SCORE_BYPASS_MIN_FORWARD_TRADES:
        return False
    if fwd_wr < NC_RAW_SCORE_BYPASS_MIN_FORWARD_WR:
        return False
    return True


# ── B18: Shadow-mode auto-promotion constants (default-OFF) ──
# Strategies with zero closed history but active emission are trapped in the
# chicken-and-egg problem: the HC gate requires forward-WR to promote, but
# forward-WR requires closed picks, which requires passing the gate.
# Shadow promotion breaks the trap by allowing ONE pick per qualifying strategy
# through as a labeled "shadow active" pick (visible on /audit, sized 10% of normal).
# Operator flips SHADOW_MODE_AUTO_PROMOTE_ENABLED=1 to activate.
_SHADOW_EMIT_WINDOW_DAYS = 14  # look-back window for raw-emit count
_SHADOW_MIN_RAW_EMITS = 10     # minimum raw emits in window to qualify
_SHADOW_MAX_CONCURRENT = 5     # global cap on simultaneous shadow picks
_SHADOW_SIZE_MULTIPLIER = 0.1  # informational sizing hint (10% of normal)


def should_shadow_promote(
    strategy: str,
    raw_emit_count: int,
    closed_count: int,
) -> bool:
    """Return True when a zero-history strategy qualifies for shadow promotion.

    Requires SHADOW_MODE_AUTO_PROMOTE_ENABLED=1 (default=0 → no behavior change).
    A strategy qualifies when it has no closed-pick history yet is actively
    emitting picks (≥10 in the current raw-active pool, used as a proxy for
    the 14-day window since the raw pool is refreshed each cycle).
    """
    if os.environ.get("SHADOW_MODE_AUTO_PROMOTE_ENABLED", "0") != "1":
        return False
    if not strategy:
        return False
    if closed_count > 0:
        return False  # strategy already has history; gate applies normally
    if raw_emit_count < _SHADOW_MIN_RAW_EMITS:
        return False
    return True


# UEPS bypass is ONLY allowed for data-quality blocks (delisted / redenomination),
# NOT for pattern-mined drain symbols. See updates/2026-05-16-blocked-symbol-leak-fix.md.
_DATA_QUALITY_BLOCKS = frozenset({"MATICUSDT", "UUSDT", "XMR", "XMRUSDT", "KATUSDT"})


def _ueps_long_horizon_bypass_active(pick: Dict[str, Any]) -> bool:
    """Per reports/UEPS_GATE_FIX_PLAN_2026_05_01.md (3-AI unanimous Option B).

    Long-horizon (3y+) UEPS value picks are currently rejected by three
    short-term-calibrated filters that don't apply to the value horizon:
    raw-score-55 floor, BLOCKED_SYMBOLS data-feed blacklist, elite_grade D
    short-term momentum grade. When this flag is ON, those three filters
    are skipped *only* for source_system=ueps + trade_timeframe=POSITION.

    NOTE: the BLOCKED_SYMBOLS bypass is further restricted in
    passes_active_gate() to only _DATA_QUALITY_BLOCKS (MATICUSDT, UUSDT,
    XMR, XMRUSDT, KATUSDT). Pattern-mined drain symbols are NOT bypassed.
    This function itself remains unrestricted for score-floor / grade-D
    bypasses which apply to all UEPS POSITION picks.

    All real-safety gates (trust_score, status, wf_verdict, forward_wr
    floor, EXEMPT_FROM_SAFETY_GATES, jpy_cross_buy_kill, healthcare_long_
    momentum_blacklist, entry_price sanity) continue to apply.

    Default-OFF (Wire-Up Rule + 14-day shadow rule). Operator flips ON
    after monitoring `picks.active` count for non-UEPS leak.
    """
    if os.environ.get("UEPS_LONG_HORIZON_GATE_BYPASS_ENABLED", "0") != "1":
        return False
    if str(pick.get("source_system", "") or "").lower() != "ueps":
        return False
    if str(pick.get("trade_timeframe", "") or "").upper() != "POSITION":
        return False
    return True


def _float(value: Any) -> float:
    """Safely convert to float."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _ratio(value: Any) -> float:
    """Normalize win-rate style fields to a 0-1 ratio."""
    val = _float(value)
    if val > 1:
        return val / 100.0
    return val


def _normalize_confidence(value: Any) -> float:
    """Normalize confidence to a 0-1 ratio, defending against 0-10 and 0-100 scale leakage.

    SUPREME EDGE 2026-05-11 P0 #9 BONUS finding: prod DB has mixed-scale
    confidence values — 984 rows in trading_picks + 1,038 in at_local_picks
    (~2k total) carry values up to 9.9999 (0-10 scale) alongside the canonical
    0-1 scale rows from named-strategy writers. Un-named-strategy writers leak.

    2026-05-19 extension: cot_signals/kimi_inverse/rocket_picks emit confidence
    as percent integers (50-100 scale). Values >10 are treated as 0-100 percent.

    Scale detection:
      val > 10  → 0-100 percent format → divide by 100
      val > 1   → 0-10 scale leakage  → divide by 10
      else      → already 0-1         → no-op
    """
    val = _float(value)
    if val < 0:
        return 0.0
    if val > 10.0:
        # 0-100 percent-format leakage (e.g. kimi_inverse confidence=75)
        val = val / 100.0
    elif val > 1.0:
        # 0-10 scale leakage — divide and clamp
        val = val / 10.0
    return min(val, 1.0)


def _int(value: Any) -> int:
    """Safely convert to int."""
    return int(round(_float(value)))


def _as_list(value: Any) -> list[str]:
    """Normalize CSV/list-like fields into a list of strings."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


# ── Exit-reason normalization (issue #186) ────────────────────────────────
# Some closed picks carry binary outcome labels (WON/LOST/WIN/LOSS) instead of
# canonical exit reasons (TP_HIT/SL_HIT/TIME_EXIT). The labels leak from
# copy-trader scrapers via dashboard_generator.py:5139's outcome fallback chain.
# Forensic analysis (issue #186 + the late 2026-04-14 audit): 92% of forex
# LOST picks have |pnl_pct| < 0.5% but forex SL median is 0.5%, and 60% exit
# within 0.1% of entry price — meaning these are unresolved mark-to-market
# force-closes, NOT stop-loss events. Treating them as SL_HIT corrupts
# stop-discipline metrics.
#
# This helper canonicalizes exit_reason into one of:
#   TP_HIT, SL_HIT, TIME_EXIT, EXPIRED, FORCE_CLOSED, UNKNOWN
#
# Wired into ``audit_trail/dashboard_generator.py`` for deduped ``resolved_closed``
# (see ``_apply_issue186_exit_normalization``). Set ``AUDIT_SKIP_EXIT_NORMALIZATION=1``
# to disable. Raw scrape label is preserved on each pick as ``exit_reason_raw``.
# Upstream scrapers should still prefer correct exit_reason at ingest time.

# Canonical exit reason families
_TP_FAMILY = {"TP_HIT", "TP", "WON", "WIN", "TAKE_PROFIT"}
_SL_FAMILY = {"SL_HIT", "SL", "LOST", "LOSS", "STOP_LOSS"}
_TIME_FAMILY = {"TIME_EXIT", "TIME_EXPIRY", "TIME", "MAX_HOLD_EXCEEDED"}
_EXPIRED_FAMILY = {"EXPIRED", "EXPIRED_RESOLVED"}


def _canonical_exit_reason(raw: str) -> str:
    """Map a raw exit_reason string to one of the canonical families.

    Legacy 'TP'/'SL'/'WON'/'LOST' (which include the unsafe binary outcome
    labels from copy-trader scrapers) are mapped to 'TP_HIT'/'SL_HIT' as a
    last resort if no price-distance refinement is available. Use
    `normalize_exit_reason(pick)` instead when you have access to the full
    pick dict — that function refines binary labels using exit_price vs
    take_profit / stop_loss distance.
    """
    if not raw:
        return "UNKNOWN"
    upper = raw.upper().strip()
    # Direct family match
    if upper in _TP_FAMILY:
        return "TP_HIT"
    if upper in _SL_FAMILY:
        return "SL_HIT"
    if upper in _TIME_FAMILY:
        return "TIME_EXIT"
    if upper in _EXPIRED_FAMILY:
        return "EXPIRED"
    # Substring matches for parameterized labels like "TAKE_PROFIT 4.2% (ATR ...)"
    if "TAKE_PROFIT" in upper or "TP_HIT" in upper or "TP HIT" in upper:
        return "TP_HIT"
    if "STOP_LOSS" in upper or "SL_HIT" in upper or "SL HIT" in upper:
        return "SL_HIT"
    if "TIME" in upper or "MAX_HOLD" in upper or "MAX HOLD" in upper:
        return "TIME_EXIT"
    if "EXPIRED" in upper:
        return "EXPIRED"
    if "ATR" in upper or "TRAILING" in upper or "hit at $" in upper.lower():
        # ATR/trailing stops — usually SL-style but could be TP. Mark as TP_HIT
        # only if the original contained 'tp' or 'profit'; otherwise treat as
        # SL_HIT-equivalent for discipline purposes.
        return "TP_HIT" if ("TP" in upper or "PROFIT" in upper) else "SL_HIT"
    return "UNKNOWN"


def normalize_exit_reason(pick: Dict[str, Any]) -> str:
    """Canonicalize a closed pick's exit_reason using both the raw label and
    price-distance refinement.

    Returns one of: TP_HIT, SL_HIT, TIME_EXIT, EXPIRED, FORCE_CLOSED, UNKNOWN.

    Refinement logic for binary outcome labels (WON/LOST/WIN/LOSS):
      - If exit_price is within 0.5% of take_profit ÔåÆ TP_HIT
      - If exit_price is within 0.5% of stop_loss ÔåÆ SL_HIT
      - Otherwise ÔåÆ FORCE_CLOSED (e.g., copy-trader leader exit, scanner pruning,
        mark-to-market reconciliation — these are NOT stop-loss events even
        though they typically have small negative pnl)

    For canonical labels (TP_HIT/SL_HIT/TIME_EXIT/EXPIRED), passes through
    without refinement.

    Per issue #186: 92% of forex LOST picks have |pnl| < 0.5% (well below the
    forex SL median), 60% exit within 0.1% of entry price. Treating them as
    SL_HIT corrupts stop-discipline metrics. FORCE_CLOSED is the honest label.
    """
    raw = (pick.get("exit_reason") or pick.get("close_reason") or "").upper().strip()
    if not raw:
        # No exit_reason at all — see if it's a stale active or actually closed
        if pick.get("pnl_pct") is None:
            return "UNKNOWN"
        # Has pnl but no exit_reason — try outcome field as last resort
        outcome = (pick.get("outcome") or pick.get("status") or "").upper().strip()
        if outcome in {"WON", "LOST", "WIN", "LOSS"}:
            raw = outcome
        else:
            return "UNKNOWN"

    canonical = _canonical_exit_reason(raw)

    # If the raw label was already a clean TP_HIT/SL_HIT/TIME_EXIT/EXPIRED with
    # a distinctive prefix (not from the binary WON/LOST family), trust it.
    if raw in {"TP_HIT", "SL_HIT", "TIME_EXIT", "EXPIRED"}:
        return canonical

    # Otherwise, this might be from the binary WON/LOST family — refine using
    # price-distance to TP/SL.
    if raw in {"WON", "LOST", "WIN", "LOSS"}:
        try:
            entry = float(pick.get("entry_price") or 0)
            exit_price = float(pick.get("exit_price") or 0)
            tp = float(pick.get("take_profit") or 0)
            sl = float(pick.get("stop_loss") or 0)
        except (TypeError, ValueError):
            return canonical  # fall back to family map

        if entry > 0 and exit_price > 0:
            # Distance to TP and SL as percent of TP/SL respectively
            tp_dist = abs(exit_price - tp) / tp if tp > 0 else 1.0
            sl_dist = abs(exit_price - sl) / sl if sl > 0 else 1.0
            EPS = 0.005  # within 0.5% counts as a hit
            if tp_dist < EPS and tp_dist < sl_dist:
                return "TP_HIT"
            if sl_dist < EPS and sl_dist < tp_dist:
                return "SL_HIT"
            # Neither TP nor SL was hit. Distinguish two sub-cases:
            #   (a) TP/SL were not set (both <= 0) — trust the raw WON/LOST
            #       label (per PR #606 — FOREX/COMMODITY picks where the
            #       resolver couldn't compute price-distance because TP/SL
            #       were missing).
            #   (b) TP/SL were set but exit_price is far from both — this is
            #       a force-close (copy-trader leader exit, scanner pruning,
            #       mark-to-market reconciliation). Per docstring + the
            #       _far_from_sl_becomes_force_closed / _far_from_tp_becomes_
            #       force_closed regression tests.
            #
            # PR #606 collapsed both cases to "return raw"; this regressed
            # case (b) and broke the FORCE_CLOSED tests. Fixed 2026-05-02.
            if tp <= 0 and sl <= 0:
                return raw if raw not in ("", "UNKNOWN") else "FORCE_CLOSED"
            return "FORCE_CLOSED"

    return canonical


def _effective_forward_wr_ratio(pick: Dict[str, Any]) -> float:
    """Return the strongest available forward win rate as a 0-1 ratio."""
    return max(
        _ratio(pick.get("strat_fwd_wr")),
        _ratio(pick.get("strategy_fwd_wr")),
        _ratio(pick.get("forward_wr")),
        _ratio(pick.get("history_wr")),
        _ratio(pick.get("history_wr_bayes")),
    )


def _effective_forward_trades(pick: Dict[str, Any]) -> int:
    """Return the strongest available forward trade sample size."""
    return max(
        _int(pick.get("strat_fwd_trades")),
        _int(pick.get("strategy_fwd_trades")),
        _int(pick.get("forward_trades")),
        _int(pick.get("history_trades")),
    )


def _is_futures_contract_pick(pick: Dict[str, Any]) -> bool:
    """Return True for futures contracts, including commodity/index futures aliases."""
    asset_class = str(pick.get("asset_class", "") or "").upper()
    symbol = str(pick.get("symbol", "") or "").upper().strip()
    category = str(pick.get("category", "") or "").lower().strip()
    # Copper/platinum reclassified as COMMODITY — do not apply futures probation.
    # They receive COMMODITY non-crypto probation instead (−16 vs −20).
    if symbol in {"HG=F", "PL=F"} and asset_class == "COMMODITY":
        return False
    return symbol.endswith("=F") or asset_class == "FUTURES" or category == "futures"


def _is_consensus_pick(pick: Dict[str, Any]) -> bool:
    """Return True for consensus/super-signal style picks."""
    source = str(pick.get("source_system", "") or "").lower()
    strategy = str(pick.get("strategy", "") or "").lower()
    return (
        "consensus" in strategy
        or strategy.startswith("super signal")
        or source == "super_signals"
    )


def _trade_bias(pick: Dict[str, Any]) -> str:
    """Return BUY/SELL based on the pick direction."""
    direction = str(pick.get("direction", pick.get("signal_type", "")) or "").upper()
    if direction in ("LONG", "BUY"):
        return "BUY"
    if direction in ("SHORT", "SELL"):
        return "SELL"
    return ""


def _technical_alignment_bucket(pick: Dict[str, Any]) -> str:
    """
    Return a direction-aware technical-alignment bucket.

    Values:
      full_support, strong_support, weak_support, no_support,
      strong_opposition, weak_opposition, unknown
    """
    expected_bias = _trade_bias(pick)
    if not expected_bias:
        return "unknown"

    tech_align = str(pick.get("technical_alignment_str", "") or "").upper().strip()
    match = _TECH_ALIGN_RE.search(tech_align)
    if match:
        aligned = _int(match.group("aligned"))
        reported_total = max(_int(match.group("total")), aligned)
        reported_bias = match.group("bias").upper()
        if reported_bias != expected_bias:
            if aligned >= 2:
                return "strong_opposition"
            if aligned == 1:
                return "weak_opposition"
            return "unknown"
        if aligned >= 3:
            return "full_support"
        if aligned >= 2:
            return "strong_support"
        if aligned == 1:
            return "weak_support"
        if reported_total > 0:
            return "no_support"
        return "unknown"

    buy_tfs = _int(pick.get("technical_buy_tfs", 0))
    sell_tfs = _int(pick.get("technical_sell_tfs", 0))
    supporting = buy_tfs if expected_bias == "BUY" else sell_tfs
    opposing = sell_tfs if expected_bias == "BUY" else buy_tfs
    total = max(supporting + opposing, supporting, opposing)

    if opposing >= 2:
        return "strong_opposition"
    if opposing == 1 and total >= 2 and supporting == 0:
        return "weak_opposition"
    if supporting >= 3:
        return "full_support"
    if supporting >= 2:
        return "strong_support"
    if supporting == 1:
        return "weak_support"
    if total > 0:
        return "no_support"
    return "unknown"


def _wf_verdict(pick: Dict[str, Any]) -> str:
    """Return normalized walk-forward verdict."""
    return str(pick.get("wf_verdict", "") or "").upper().strip()


def _has_direction_conflict(pick: Dict[str, Any]) -> bool:
    """Return True when the symbol has live opposite-direction picks."""
    return bool(pick.get("_direction_conflict") or pick.get("has_conflict"))


def _audit_pick_sanity_gate_enabled() -> bool:
    """Strict data-quality gate for active picks (off by default).

    Set ``AUDIT_PICK_SANITY_GATE=1`` (or ``true``/``yes``/``on``) to reject rows
    that fail ``audit_trail.pick_sanity`` (R:R bounds, score ranges, geometry
    when TP/SL present). Prediction-market rows use the same exemptions as
    trade-geometry checks.
    """
    v = str(os.environ.get("AUDIT_PICK_SANITY_GATE", "") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _pick_sanity_gate_exempt(pick: Dict[str, Any]) -> bool:
    """Sources where pick_sanity is skipped (non-standard economics)."""
    source = str(pick.get("source_system", "") or "").lower()
    strategy = str(pick.get("strategy", "") or "").lower()
    if source in {
        "prediction_market_consensus",
        "pm_kalshi_signals",
        "pm_whale_signals",
        "polymarket_signals",
    } or strategy.startswith("copy_pm_"):
        return True
    return False


def _has_valid_trade_geometry(pick: Dict[str, Any]) -> bool:
    """Return True when entry/TP/SL form a valid directional trade.
    
    FIXED 2026-04-10: Now applies validation to ALL asset classes (CRYPTO, FOREX,
    EQUITY, COMMODITY, FUTURES) - previously non-CRYPTO assets skipped validation.
    """
    # Use unified trade_geometry module if available (applies to ALL asset classes)
    if _TRADE_GEOMETRY_AVAILABLE:
        return has_valid_trade_geometry(pick)
    
    # Fallback to inline validation (CRYPTO only) if module not available
    if _pick_sanity_gate_exempt(pick):
        return True

    entry = _float(pick.get("entry_price", 0))
    tp = _float(pick.get("take_profit", 0))
    sl = _float(pick.get("stop_loss", 0))
    # Only reject if entry price is missing — TP/SL may not be populated yet
    if entry <= 0:
        return False
    # If TP and SL are both present, check directional consistency
    if tp > 0 and sl > 0:
        direction = str(
            pick.get("direction", pick.get("signal_type", "LONG")) or ""
        ).upper()
        if direction in ("LONG", "BUY"):
            return tp > entry > sl
        if direction in ("SHORT", "SELL"):
            return tp < entry < sl
        return False
    # If TP/SL missing, allow through — many valid picks lack TP/SL at emission time
    return True


def _trade_rr(pick: Dict[str, Any]) -> float:
    """Return normalized risk/reward for the pick."""
    rr = _float(pick.get("rr_ratio", 0))
    if rr > 0:
        return rr

    entry = _float(pick.get("entry_price", 0))
    tp = _float(pick.get("take_profit", 0))
    sl = _float(pick.get("stop_loss", 0))
    if entry <= 0 or tp <= 0 or sl <= 0 or entry == sl:
        return 0.0

    direction = str(
        pick.get("direction", pick.get("signal_type", "LONG")) or ""
    ).upper()
    if direction in ("LONG", "BUY"):
        return (tp - entry) / (entry - sl) if tp > entry > sl else 0.0
    if direction in ("SHORT", "SELL"):
        return (entry - tp) / (sl - entry) if tp < entry < sl else 0.0
    return 0.0


def _equity_forward_proven_mitigates_conf_deadzone(pick: Dict[str, Any]) -> bool:
    """EQUITY rows with validated forward history: conf 0.60–0.69 is a weak proxy.

    Otherwise `conf_danger_zone` and `long_deadzone_combo` stack (-22) on picks that
    already show strong strategy-level forward WR (e.g. multi_asset_copytrader META).
    Requires large-n, above-floor WR — same spirit as HC Gate 5.
    """
    if str(pick.get("asset_class", "") or "").upper() != "EQUITY":
        return False
    if not pick.get("forward_validated"):
        return False
    n = _effective_forward_trades(pick)
    wr = _effective_forward_wr_ratio(pick)
    return n >= 50 and wr >= 0.45


def _extract_final_score(pick: Dict[str, Any]) -> tuple[float, bool]:
    """Return (score_value, has_explicit_score_field).

    has_explicit_score_field=False means the pick has no meaningful score yet
    and _apply_score_penalties will apply the baseline of 50.
    Treat score=0 as 'unscored' — upstream scanners emit 0 as a sentinel for
    'not yet scored', not as a legitimate quality signal of zero.
    """
    # Prefer the final post-penalty score, then fall back through scoring fields
    for key in ("score", "elite_score", "smart_score", "ml_score"):
        raw = pick.get(key)
        if raw not in (None, ""):
            val = _float(raw)
            if val > 0:  # treat 0 as unscored (scanners emit 0 as sentinel)
                return val, True
    # Confidence (0-1 scale) ÔåÆ map to 0-100 scale
    conf = pick.get("confidence")
    if conf not in (None, ""):
        val = _float(conf)
        if 0 < val <= 1:
            return val * 100, True
        elif val > 1:
            return val, True
    return 0.0, False


def _calculate_age_hours(timestamp_str: Optional[str]) -> float:
    """Calculate age in hours from timestamp string."""
    if not timestamp_str:
        return 0.0

    try:
        # Try ISO format
        if "T" in timestamp_str:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            # Try common formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    dt = dt.replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue
            else:
                return 0.0

        now = datetime.now(timezone.utc)
        age = now - dt
        return age.total_seconds() / 3600
    except Exception as e:
        logger.warning(f"Failed to parse timestamp {timestamp_str}: {e}")
        return 0.0


def _get_strategy_tier(strategy: str) -> str:
    """Get tier for a strategy."""
    if strategy in PROVEN_INVERSE_STRATEGIES:
        return "TOP_TIER"
    if strategy in LOW_CONFIDENCE_STRATEGIES:
        return "UNDERPERFORMING"
    if strategy.lower() in _KILLED_STRATEGIES_LOWER:
        return "TOXIC"
    return "WATCH"  # Default


def _is_15m_model(strategy: str) -> bool:
    """Check if strategy uses anti-predictive 15m timeframe."""
    return "_15m_" in strategy or strategy.endswith("_15m")


def _concentration_risk(pick: Dict[str, Any]) -> str:
    """Return the normalized concentration-risk label."""
    return str(
        pick.get("strategy_concentration_risk")
        or pick.get("strat_concentration_level")
        or pick.get("strat_concentration_risk")
        or ""
    ).upper()


def _concentration_penalty(pick: Dict[str, Any]) -> float:
    """Return an extra penalty for concentrated strategy track records."""
    penalty = max(
        _float(pick.get("strat_concentration_penalty")),
        _float(pick.get("strategy_concentration_penalty")),
    )
    risk = _concentration_risk(pick)
    if risk == "HIGH":
        penalty = max(penalty, SMART_CONCENTRATION_HIGH_PENALTY)
    elif risk == "MODERATE":
        penalty = max(penalty, SMART_CONCENTRATION_MODERATE_PENALTY)

    top_symbol_pnl = max(
        _float(pick.get("strat_top_symbol_pnl_pct")),
        _float(pick.get("strategy_top_symbol_pnl_pct")),
    )
    if top_symbol_pnl >= 150:
        penalty = max(penalty, SMART_CONCENTRATION_HIGH_PENALTY)
    elif top_symbol_pnl >= 100:
        penalty = max(penalty, SMART_CONCENTRATION_MODERATE_PENALTY)

    return penalty


def _trust_tier(pick: Dict[str, Any]) -> str:
    """Return normalized trust tier."""
    return str(pick.get("trust_tier", "") or "").upper()


def _has_source_provenance(pick: Dict[str, Any]) -> bool:
    """Return True when a pick has an explicit, non-placeholder source."""
    source = (
        str(pick.get("source_system", pick.get("source", "")) or "").strip().lower()
    )
    return bool(source and source not in {"unknown", "none", "null", "nan"})


def _has_strong_audited_pm_history(pick: Dict[str, Any]) -> bool:
    """
    Allow audited PM consensus rows to survive a strict score floor if the
    attached history is both strong and multi-source.
    """
    source = str(pick.get("source_system", "") or "").lower()
    strategy = str(pick.get("strategy", "") or "").lower()
    if (
        source != "prediction_market_consensus"
        and strategy != "prediction_market_consensus"
    ):
        return False

    history_wr = max(
        _ratio(pick.get("history_wr_bayes")),
        _ratio(pick.get("profile_crypto_wr_bayes")),
        _ratio(pick.get("history_wr")),
        _ratio(pick.get("profile_crypto_wr")),
    )
    history_trades = max(
        _int(pick.get("history_trades")),
        _int(pick.get("profile_crypto_trades")),
    )
    pm_source_systems = _as_list(pick.get("pm_source_systems"))
    source_count = max(
        _int(pick.get("source_count")),
        _int(pick.get("agreement_count")),
        len(pm_source_systems),
    )

    return (
        history_wr >= AUDITED_PM_MIN_HISTORY_WR
        and history_trades >= AUDITED_PM_MIN_HISTORY_TRADES
        and source_count >= AUDITED_PM_MIN_SOURCE_COUNT
    )


def _active_floor_score(pick: Dict[str, Any]) -> float:
    """Return score used for the active-feed quality floor."""
    score, _ = _extract_final_score(pick)
    if _has_strong_audited_pm_history(pick):
        score += AUDITED_PM_SCORE_BONUS
    return score


def _smart_floor_score(pick: Dict[str, Any]) -> float:
    """Return score used for the Smart Picks quality floor."""
    return _active_floor_score(pick) - _concentration_penalty(pick)


def is_profitable_short_strategy(pick: Dict[str, Any]) -> bool:
    """
    Check if a SHORT pick is from a proven profitable short strategy.
    These strategies are exempt from blanket SHORT penalties.
    """
    direction = pick.get("direction", "LONG").upper()
    if direction != "SHORT":
        return False

    strategy = pick.get("strategy", "")
    return strategy in PROFITABLE_SHORT_STRATEGIES


def _evaluate_forex_carry_ema_filter(pick: dict) -> tuple[int, list[str]]:
    """Return (score_delta, penalty_labels) for FOREX carry+EMA alignment check.

    Returns (0, []) for non-FOREX picks or if the kill-switch is set.
    Only penalizes — never boosts. Penalty logic:
      - Both carry AND EMA misaligned → -20 (forex_carry_ema_both_fail)
      - Carry only misaligned        → -10 (forex_carry_against)
      - EMA only misaligned          → -10 (forex_ema_misaligned)
    Fail-open: missing data fields → skip that check (no penalty).
    """
    if os.environ.get("FOREX_CARRY_EMA_FILTER_DISABLED", "0").strip() == "1":
        return 0, []
    ac = str(pick.get("asset_class", "") or "").strip().upper()
    if ac != "FOREX":
        return 0, []

    direction = str(pick.get("direction") or pick.get("signal_type") or "").strip().upper()
    is_long = direction in ("LONG", "BUY")
    is_short = direction in ("SHORT", "SELL")
    if not (is_long or is_short):
        return 0, []

    symbol = str(pick.get("symbol") or pick.get("ticker") or "").strip()

    # ── carry check ──────────────────────────────────────────────────────
    carry_fail = False
    try:
        from alpha_engine import config as _ae_cfg
        fx_symbols = getattr(_ae_cfg, "FOREX_SYMBOLS", {})
        sym_cfg = fx_symbols.get(symbol) or fx_symbols.get(symbol.replace("=X", ""))
        if sym_cfg:
            carry_diff = sym_cfg.get("carry_yield_diff")
            if carry_diff is not None:
                carry_diff = float(carry_diff)
                if is_long and carry_diff < 0:
                    carry_fail = True  # longing the low-yielder
                elif is_short and carry_diff > 0:
                    carry_fail = True  # shorting the high-yielder
    except Exception:
        pass  # fail-open: missing config → skip carry check

    # ── EMA trend check ──────────────────────────────────────────────────
    ema_fail = False
    try:
        extra = pick.get("extra") or {}
        ema20 = (
            pick.get("ema_20") or pick.get("ema20")
            or extra.get("ema_20") or extra.get("ema20")
        )
        price = (
            pick.get("entry_price") or pick.get("price") or pick.get("close")
        )
        if ema20 is not None and price:
            ema20 = float(ema20)
            price = float(price)
            if price > 0 and ema20 > 0:
                if is_long and price < ema20:
                    ema_fail = True  # longing below EMA20 (downtrend)
                elif is_short and price > ema20:
                    ema_fail = True  # shorting above EMA20 (uptrend)
    except Exception:
        pass  # fail-open

    if carry_fail and ema_fail:
        return -20, ["forex_carry_ema_both_fail:-20"]
    if carry_fail:
        return -10, ["forex_carry_against:-10"]
    if ema_fail:
        return -10, ["forex_ema_misaligned:-10"]
    return 0, []


def _apply_score_penalties(pick: Dict[str, Any]) -> None:
    """
    Apply score penalties/bonuses to a pick based on quality signals.

    Philosophy: ALL picks reach the dashboard. Quality signals adjust the
    score so weaker picks sort lower rather than being hidden entirely.
    Penalties are stored in pick["_penalties"] for transparency.
    """
    # Idempotency guard: passes_active_gate and passes_smart_gate both call this
    # function. The second call would re-apply all penalties to the already-penalized
    # score, causing picks to be double-penalized into the floor (e.g. 50->36->7).
    if pick.get("_penalties") is not None:
        return  # Already scored — skip second application

    penalties = []
    score, has_score = _extract_final_score(pick)
    if not has_score:
        score = 50.0  # Default baseline for unscored picks

    strategy = pick.get("strategy", "")

    # Rehab child strategies (parent_* + rsi2/confluence/mtf/regime/...) — mutate-before-kill path
    if _is_rehab_variant_strategy(strategy):
        score += 8
        penalties.append("rehab_variant_confluence:+8")

    # BLOCKED SYMBOLS — phantom/delisted symbols that generate 0% WR trades
    _symbol = str(pick.get("symbol", "") or "").upper()
    if _symbol in BLOCKED_SYMBOLS:
        score -= 50
        penalties.append(f"blocked_symbol({_symbol}):-50")

    # BLOCKED ASSET CLASSES — temporarily disable entire classes with systemic issues
    _asset_class = str(pick.get("asset_class", "CRYPTO") or "CRYPTO").upper()
    if _asset_class in BLOCKED_ASSET_CLASSES:
        score -= 60
        # Breadcrumb label must match the actual delta (2026-04-19 code review, Finding 1).
        penalties.append(f"blocked_asset_class({_asset_class}):-60")

    # Futures probation: pipeline support exists, but the live cohort is still thin,
    # mostly forward-test-only, and recent realized outcomes are poor. Keep these rows
    # visible but force them below premium ranks until they earn real sample support.
    if _is_futures_contract_pick(pick):
        _forward_test_only = bool(pick.get("forward_test_only"))
        _forward_validated = bool(pick.get("forward_validated"))
        _edge_trades = _effective_forward_trades(pick)
        _edge_wr = _effective_forward_wr_ratio(pick)
        if _forward_test_only and not _forward_validated:
            if _edge_trades <= 0:
                score -= 20
                penalties.append("futures_forward_test_only_no_sample:-20")
            elif _edge_trades < 5 or _edge_wr < 0.45:
                score -= 12
                penalties.append(
                    f"futures_forward_test_only_thin_sample(wr={_edge_wr:.0%},n={_edge_trades}):-12"
                )

    # Non-crypto probation: keep weak-evidence classes visible but de-prioritized.
    # This mirrors the futures probation stance from edge-review docs:
    # - FOREX often shows weak score discrimination unless validated sample exists.
    # - COMMODITY / ETF / BOND are usually thin-sample lanes.
    _forward_test_only = bool(pick.get("forward_test_only"))
    _forward_validated = bool(pick.get("forward_validated"))
    _edge_trades = _effective_forward_trades(pick)
    _edge_wr = _effective_forward_wr_ratio(pick)
    if _asset_class in {"FOREX", "COMMODITY", "ETF", "BOND"} and _forward_test_only and not _forward_validated:
        if _edge_trades <= 0:
            score -= 16
            penalties.append(f"{_asset_class.lower()}_forward_test_only_no_sample:-16")
        elif _edge_trades < 5 or _edge_wr < 0.50:
            score -= 10
            penalties.append(
                f"{_asset_class.lower()}_forward_test_only_thin_sample(wr={_edge_wr:.0%},n={_edge_trades}):-10"
            )

    # Forex-specific confidence calibration guard:
    # high confidence with weak sample should not rank as premium by default.
    if _asset_class == "FOREX":
        _fx_conf = _normalize_confidence(pick.get("confidence", 0))
        if _fx_conf >= 0.75 and (_edge_trades < 10 or _edge_wr < 0.52):
            score -= 8
            penalties.append(
                f"forex_confidence_uncalibrated(conf={_fx_conf:.2f},wr={_edge_wr:.0%},n={_edge_trades}):-8"
            )

    # EQUITY confidence inversion penalty (2026-05-16 validation finding).
    # LOW-confidence EQUITY picks outperform HIGH-confidence by 32pp WR
    # (LOW=70.2% WR / PF 4.31 vs HIGH=38.1% WR / PF 1.04). The model is
    # systematically overconfident on losers. Penalize high-confidence EQUITY
    # picks to correct the inversion and lift aggregate WR toward Tier 1.
    # Rollback: EQUITY_CONFIDENCE_INVERSION_PENALTY_DISABLED=1
    if _asset_class == "EQUITY" and os.environ.get("EQUITY_CONFIDENCE_INVERSION_PENALTY_DISABLED", "0") != "1":
        _eq_conf = _normalize_confidence(pick.get("confidence", 0))
        if _eq_conf > 0.70:
            score -= 15
            penalties.append(
                f"equity_overconfidence_penalty(conf={_eq_conf:.2f}):-15"
            )

    # CONFIDENCE TRAP — DATA 2026-04-03 (1952 closed picks):
    #   conf >= 0.65 AND elite_score < 40 = 581 trades at 9% WR
    #   These are high-confidence picks from low-quality strategies — deadly combo
    #   RECALIBRATED 2026-04-05: Reduced from -25 to -18 for 0.90-0.95 bucket
    _elite = _float(pick.get("elite_score", 0))
    _conf_raw = _normalize_confidence(pick.get("confidence", 0))
    if _conf_raw >= 0.65 and 0 < _elite < 40:
        # Tiered penalty based on confidence level
        if _conf_raw >= 0.90:
            score -= 18  # Reduced from -25: worst bucket is 0.90-0.95 (36% WR)
            penalties.append(
                f"confidence_trap(conf={_conf_raw:.2f},elite={_elite:.0f}):-18"
            )
        else:
            score -= 15
            penalties.append(
                f"confidence_trap(conf={_conf_raw:.2f},elite={_elite:.0f}):-15"
            )

    # Killed strategies get heavy penalty but still show (so user sees them flagged)
    if strategy.lower() in _KILLED_STRATEGIES_LOWER:
        score -= 40
        penalties.append("killed_strategy:-40")

    # 2026-04-05: TOXIC COMBO blocks from antigrav-independent-review findings.
    # These strategy+direction combos have confirmed 0-17% WR with negative avg PnL:
    # - tsmom_volscaled+SHORT: 0% WR, -1.43% avg
    # - rocket_scanner+SHORT: 0% WR, -0.77% avg
    # - enhanced_ml_A_xgboost+LONG: 17% WR, -0.48% avg
    _strat_low = strategy.lower()
    _dir_up = (pick.get("direction") or pick.get("signal_type") or "").upper()
    _toxic = False
    if "tsmom_volscaled" in _strat_low and _dir_up in ("SHORT", "SELL"):
        _toxic = True
    elif "rocket_scanner" in _strat_low and _dir_up in ("SHORT", "SELL"):
        _toxic = True
    elif "enhanced_ml_a_xgboost" in _strat_low and _dir_up in ("LONG", "BUY"):
        _toxic = True
    if _toxic:
        score -= 10
        penalties.append(f"toxic_combo({_strat_low[:20]}/{_dir_up}):-10")

    # 2026-04-05: MASTERED PAIR boosts - strategy+symbol combos with verified edge.
    # 2026-05-28: Removed claude_gainer_st entries (778/790 PROVEN picks, 26.5% WR, -355% PnL).
    #             Source is in PERMANENTLY_KILLED_STRATEGIES; "mastered" claim was from only 3 closed rows.
    _sym_up = str(pick.get("symbol", "") or "").upper()
    _mastered_pairs = {
        ("quan_engine", "ETCUSDT"),
        ("kimi_riseoftheclaw", "AVAXUSDT"),
    }
    for _ms, _msym in _mastered_pairs:
        if _ms in _strat_low and _sym_up.startswith(_msym):
            score += 10
            penalties.append(f"mastered_pair({_ms[:12]}+{_msym[:8]}):+10")
            break

    # 2026-04-05: SHARP TOOLS EDGE MAP - st_fear_greed_contrarian CROWN JEWEL.
    # Validated on 525 closed picks, overall 61.9% WR. Per-symbol LONG verified:
    # LTC 96% (n=25), BNB 93% (n=28), TRX 85% (n=13), XRP 82% (n=34), DOT 77% (n=35), LINK 75% (n=12).
    # Boost is LARGER than mastered_pair because WR>75% on all 6 pairs.
    _sharp_fear_greed = {
        "LTCUSDT",
        "BNBUSDT",
        "TRXUSDT",
        "XRPUSDT",
        "DOTUSDT",
        "LINKUSDT",
    }
    if (
        "fear_greed" in _strat_low
        and _dir_up in ("LONG", "BUY")
        and any(_sym_up.startswith(s) for s in _sharp_fear_greed)
    ):
        score += 12
        penalties.append(f"sharp_fear_greed+{_sym_up[:8]}:+12")

    # 2026-04-05: QUALITY FILTER BOOSTS (user-verified asset-class edges).
    # CRYPTO filter: trust>=3.5 AND strat_fwd_wr>=50% -> 60.3% WR (+16.8pp, n=2881)
    # EQUITY filter: strat_fwd_wr>=60% AND strat_fwd_pf>=1.5 -> 65% WR (+31.3pp, n=531)
    _ac_quality = str(pick.get("asset_class", "") or "").upper()
    _trust_val = _float(pick.get("trust_score") or 0)
    _sfwd_wr = _float(pick.get("strat_fwd_wr") or 0)
    if _sfwd_wr > 1.5:
        _sfwd_wr = _sfwd_wr / 100.0
    _sfwd_pf = _float(pick.get("strat_fwd_pf") or 0)
    if _ac_quality == "CRYPTO" and _trust_val >= 3.5 and _sfwd_wr >= 0.50:
        score += 7
        penalties.append(f"crypto_quality_filter(tr>=3.5,wr>=50):+7")
    elif _ac_quality == "EQUITY" and _sfwd_wr >= 0.60 and _sfwd_pf >= 1.5:
        score += 10
        penalties.append(f"equity_quality_filter(wr>=60,pf>=1.5):+10")
    elif _ac_quality == "COMMODITY":
        # 2026-05-14 Grok audit: COT commercial positioning is the COMMODITY edge.
        # COT z-score > +1.0 + direction alignment → +2.8pp WR lift, PF > 4.5.
        # NOTE (2026-05-18): cot_net_z now populated by alpha_engine/cot_positioning.py
        # compute_net_positioning() since the COT feature enrichment fix (M-097 session).
        _cot_z = _float(pick.get("cot_net_z") or 0)
        _cot_direction = str(pick.get("cot_commercial_direction", "") or "").upper()
        if _cot_z > 1.0 and _cot_direction == _dir_up:
            score += 10
            penalties.append(f"commodity_cot_aligned(z={_cot_z:.1f},dir={_cot_direction}):+10")
        elif _cot_z > 0.5:
            score += 5
            penalties.append(f"commodity_cot_moderate(z={_cot_z:.1f}):+5")
        elif _cot_z < -1.0 and _cot_direction and _cot_direction != _dir_up:
            score -= 8
            penalties.append(f"commodity_cot_inverse(z={_cot_z:.1f}):-8")

    # 2026-04-05: Asset-class-specific rr_ratio gating (from factor deep-dive).
    # CRYPTO: rr_ratio>=2.0 -> 68.4% WR n=177 vs 43% baseline (massive edge cliff).
    # EQUITY: rr_ratio INVERTS - tight 1.6-1.9 is optimal, >2.0 drops WR to 24%.
    _rr = _float(pick.get("rr_ratio") or 0)
    if _ac_quality == "CRYPTO" and _rr >= 2.0:
        score += 8
        penalties.append(f"crypto_rr_sweetspot(rr={_rr:.1f}):+8")
    elif _ac_quality == "EQUITY" and 1.6 <= _rr <= 1.9:
        score += 6
        penalties.append(f"equity_rr_sweetspot(rr={_rr:.1f}):+6")
    elif _ac_quality == "EQUITY" and _rr > 2.0:
        score -= 5
        penalties.append(f"equity_rr_inverted(rr={_rr:.1f}):-5")

    # 2026-05-14 Grok audit: FOREX SHORT bias — SHORT direction across all FOREX
    # strategies has 46-60% WR vs LONG at 10-35%. Surgically favor SHORT, penalize
    # LONG unless the strategy has proven WR >= 50% on LONG direction.
    if _ac_quality == "FOREX":
        if _dir_up in ("SHORT", "SELL"):
            score += 10
            penalties.append("forex_short_bias:+10")
        elif _dir_up in ("LONG", "BUY"):
            _fwd_wr_long = _float(pick.get("strat_fwd_wr") or 0)
            if _fwd_wr_long > 1.5:
                _fwd_wr_long = _fwd_wr_long / 100.0
            if _fwd_wr_long >= 0.50:
                score += 3
                penalties.append(f"forex_long_proven(wr={_fwd_wr_long:.0%}):+3")
            else:
                score -= 15
                penalties.append("forex_long_unproven:-15")

    # 2026-05-16: FOREX carry+EMA alignment filter. Penalizes picks that trade
    # against the interest-rate differential AND/OR the EMA20 trend. Data-driven
    # draft per updates/2026-05-16-FOREX-carry-ema-filter-draft.md.
    _forex_carry_delta, _forex_carry_labels = _evaluate_forex_carry_ema_filter(pick)
    if _forex_carry_delta != 0:
        score += _forex_carry_delta
        penalties.extend(_forex_carry_labels)

    # 2026-04-05: EQUITY tp_dist_pct>8% HARD BLOCK - 18% WR, -3.4% avg PnL n=89.
    # Greedy TPs are disaster on equities (factor deep-dive P3).
    _tp_dist = _float(pick.get("tp_dist_pct") or 0)
    if _tp_dist > 1.5:  # could be stored as 8.0 or 0.08
        _tp_dist = _tp_dist / 100.0
    if _ac_quality == "EQUITY" and _tp_dist > 0.08:
        score -= 20
        penalties.append(f"equity_greedy_tp(tp_dist={_tp_dist * 100:.1f}pct):-20")

    # 2026-04-05: CRYPTO wf_p_value<0.01 - strongest statistical filter.
    # 63.2% WR n=552 vs 36% at p>0.224 (from factor deep-dive P4).
    _wf_p = _float(pick.get("wf_p_value") or 0)
    if _ac_quality == "CRYPTO" and 0 < _wf_p < 0.01:
        score += 8
        penalties.append(f"crypto_wf_significant(p={_wf_p:.4f}):+8")

    # 2026-05-14 Grok audit: CRYPTO Tuesday institutional flow edge.
    # Tuesday has +18% WR lift vs other weekdays due to institutional rebalancing
    # flows after weekend. Boost Tuesday picks, cap known volume-drag sources.
    _entry_ts = str(pick.get("entry_time", pick.get("generated_at", "")) or "")
    _is_tuesday = False
    if _entry_ts:
        try:
            _dt = datetime.fromisoformat(_entry_ts.replace("Z", "+00:00"))
            _is_tuesday = _dt.weekday() == 1
        except Exception:
            pass
    if _ac_quality == "CRYPTO" and _is_tuesday:
        score += 8
        penalties.append("crypto_tuesday_flow:+8")
    # Cap quan_engine picks to prevent volume-drag dominance
    _src_sys = str(pick.get("source_system", "") or "").lower()
    if "quan_engine" in _src_sys and _ac_quality == "CRYPTO":
        score -= 5
        penalties.append("quan_engine_volume_cap:-5")

    # 15m anti-predictive models
    if _is_15m_model(strategy) and not is_profitable_short_strategy(pick):
        score -= 30
        penalties.append("15m_model:-30")

    # Missing entry price / TP/SL — less actionable
    entry = _float(pick.get("entry_price", 0))
    tp = _float(pick.get("take_profit", 0))
    sl = _float(pick.get("stop_loss", 0))
    if entry <= 0:
        score -= 10
        penalties.append("no_entry:-10")
    if tp <= 0 or sl <= 0:
        score -= 10
        penalties.append("no_tp_sl:-10")
    if not _has_valid_trade_geometry(pick):
        score -= 35
        penalties.append("invalid_trade_geometry:-35")

    # R:R scoring — DATA CORRECTED 2026-04-01:
    # Closed-pick analysis (1868 picks) shows R:R is INVERTED:
    #   R:R < 1.0 = 66.7% WR, R:R 1.0-1.5 = 70.8% WR (BEST),
    #   R:R 1.5-2.0 = 45.6%, R:R 2.0-3.0 = 42.4%
    # Tight TP/SL wins more often. Wider R:R means TP is too far.
    rr = _trade_rr(pick)
    if 0 < rr <= 1.5:
        # Tight R:R is the proven winner zone
        score += 10
        penalties.append(f"tight_rr_winner({rr:.1f}):+10")
    elif 1.5 < rr <= 2.0:
        # Neutral zone
        score += 0
        penalties.append(f"mid_rr({rr:.1f}):+0")
    elif 2.0 < rr <= 3.0:
        # Wide R:R underperforms — slight penalty
        score -= 5
        penalties.append(f"wide_rr({rr:.1f}):-5")
    elif rr > 3.0:
        # Very wide R:R — TP too ambitious
        score -= 10
        penalties.append(f"overwide_rr({rr:.1f}):-10")

    # Confidence — RECALIBRATED 2026-04-05 on 3500 closed picks (bus task 2):
    #   <0.60 = 42.7% WR (n=911), 0.60-0.64 = 37.9% WR (DANGER, n=663),
    #   0.65-0.69 = 45.8% WR (n=411), 0.70-0.74 = 49.5% WR (n=276),
    #   0.75-0.79 = 58.8% WR (SWEET SPOT, n=974, +337% totalPnL),
    #   0.80-0.84 = 61.1% WR (PEAK, n=54, +1.70% avgPnL),
    #   0.85-0.89 = 50.0% WR (n=36), 0.90-0.94 = 36.1% WR (DANGER, -2.60% avgPnL),
    #   0.95-1.00 = 43.6% WR (n=78, -1.25% avgPnL).
    # Previous 2026-04-03 claim (87.4% sweet spot, 22.2% overconf) was from n=1000
    # older sample — revised down but pattern holds: 0.75-0.84 is best, 0.90+ worst.
    conf = _normalize_confidence(pick.get("confidence", 0))
    if conf >= 0.95:
        # 43.6% WR but -1.25% avgPnL = still losing money
        score -= 12
        penalties.append(f"conf_extreme_overconfident({conf:.2f}):-12")
    elif 0.90 <= conf < 0.95:
        # 36.1% WR, -2.60% avgPnL = WORST avg PnL bucket
        score -= 18
        penalties.append(f"conf_overconfident({conf:.2f}):-18")
    elif 0.85 <= conf < 0.90:
        # 50% WR neutral
        score += 2
        penalties.append(f"conf_high_neutral({conf:.2f}):+2")
    elif 0.80 <= conf < 0.85:
        # 61.1% WR, +1.70% avgPnL = PEAK (small n=54, moderate bonus)
        score += 10
        penalties.append(f"conf_peak({conf:.2f}):+10")
    elif 0.75 <= conf < 0.80:
        # 58.8% WR, +0.35% avgPnL = SWEET SPOT (large n=974)
        score += 12
        penalties.append(f"conf_sweet_spot({conf:.2f}):+12")
    elif 0.70 <= conf < 0.75:
        # 49.5% WR = break-even
        score += 3
        penalties.append(f"conf_good({conf:.2f}):+3")
    elif 0.65 <= conf < 0.70:
        # 45.8% WR
        score -= 3
        penalties.append(f"conf_below_avg({conf:.2f}):-3")
    elif 0.60 <= conf < 0.65:
        # 37.9% WR, ~flat avgPnL = DANGER ZONE — unless EQUITY + proven forward book
        if _equity_forward_proven_mitigates_conf_deadzone(pick):
            score -= 3
            penalties.append(
                f"conf_below_avg_equity_forward_proven({conf:.2f}):-3"
            )
        else:
            score -= 10
            penalties.append(f"conf_danger_zone({conf:.2f}):-10")
    elif conf < 0.60:
        # 42.7% WR, ~flat avgPnL
        score -= 3
        penalties.append(f"conf_low({conf:.2f}):-3")

    edge_wr = _effective_forward_wr_ratio(pick)
    edge_trades = _effective_forward_trades(pick)
    if conf > SMART_PICKS_MAX_CONFIDENCE:
        if edge_trades == 0 and not _is_verified_pm_or_copy_pick(pick):
            score -= 30
            penalties.append(f"overconfident_no_history({conf:.2f}):-30")
        elif edge_trades >= 10 and edge_wr >= 0.60:
            penalties.append(f"overconfident_but_proven({conf:.2f}):+0")
        else:
            score -= 12
            penalties.append(f"overconfident_unproven({conf:.2f}):-12")

    # Technical alignment must be evaluated against trade direction.
    # DATA UPDATE 2026-04-03: Dashboard analysis shows tech_alignment penalty
    # averages -17.3 pts but picks receiving it still win 59.8% of the time.
    # Penalties were too harsh — reduced to avoid over-penalizing winning picks.
    tech_bucket = _technical_alignment_bucket(pick)
    if tech_bucket == "full_support":
        score += 10
        penalties.append("tech_full_support:+10")
    elif tech_bucket == "strong_support":
        score += 6
        penalties.append("tech_strong_support:+6")
    elif tech_bucket == "weak_support":
        score -= 3
        penalties.append("tech_weak_support:-3")
    elif tech_bucket == "no_support":
        score -= 8
        penalties.append("tech_no_support:-8")
    elif tech_bucket == "weak_opposition":
        score -= 8
        penalties.append("tech_weak_opposition:-8")
    elif tech_bucket == "strong_opposition":
        score -= 12
        penalties.append("tech_strong_opposition:-12")

    wf_verdict = _wf_verdict(pick)
    # 2026-04-05: Rebalanced from 3500-pick forensic. wf_verdict is STRONGEST
    # discrete signal (Spearman -0.132 on p_value, r=+0.173 on forward_wr).
    # Data: ELITE=94% WR (n=16), STRONG=77% WR (n=64), VIABLE=56% WR (n=1132),
    # FAILING=39% WR (n=1736). Previous lumped ELITE+STRONG at +8 underweighted ELITE.
    if wf_verdict == "ELITE":
        score += 18  # 94% WR - preserve the 48pp edge over baseline
        penalties.append("wf_elite:+18")
    elif wf_verdict == "STRONG":
        score += 12  # 77% WR - 31pp edge
        penalties.append("wf_strong:+12")
    elif wf_verdict == "VIABLE":
        score += 4  # 56% WR - 10pp edge
        penalties.append("wf_viable:+4")
    elif wf_verdict in {"DECAYING", "WEAK", "WARNING"}:
        score -= 10
        penalties.append(f"wf_{wf_verdict.lower()}:-10")
    elif wf_verdict in {"FAILING", "REJECTED", "BROKEN"}:
        score -= 20
        penalties.append(f"wf_{wf_verdict.lower()}:-20")

    if _has_direction_conflict(pick):
        score -= 8
        penalties.append("direction_conflict:-8")

    # Only trust the kill flag when other live evidence also looks bad.
    if pick.get("_killed_strategy") and wf_verdict in {"FAILING", "REJECTED", "BROKEN"}:
        score -= 10
        penalties.append("corroborated_killed_strategy:-10")

    # Health at entry: panic = 24% WR (889 trades), caution = 60% WR
    # v101: -8 was too soft — panic picks lose 76% of the time
    health = str(pick.get("health_at_entry", "") or "").lower()
    if health == "panic":
        score -= 30
        penalties.append("health_panic:-30")
    elif health == "caution":
        score += 5
        penalties.append("health_caution:+5")

    # Volume ratio: 1.5-2.0x is the only profitable bucket; spikes >2x are bad
    vol_ratio = _float(pick.get("volume_ratio", 0))
    if 1.5 <= vol_ratio <= 2.0:
        score += 5
        penalties.append(f"vol_sweetspot({vol_ratio:.1f}):+5")
    elif vol_ratio > 3.0:
        score -= 5
        penalties.append(f"vol_spike({vol_ratio:.1f}):-5")

    # Age penalty — DATA CORRECTED 2026-04-01:
    # Portfolio A lesson: stale picks LOSE. ADAUSDT SHORT from 12h+ old data hit SL.
    # Fresh picks (<6h) are dramatically better than stale ones.
    # Aggressive age penalty for crypto — prices move fast.
    created = (
        pick.get("created_at") or pick.get("timestamp") or pick.get("generated_at")
    )
    if created:
        age_hours = _calculate_age_hours(created)
        asset_class = str(pick.get("asset_class", "CRYPTO")).upper()
        if asset_class in {"FOREX", "EQUITY", "COMMODITY", "FUTURES"}:
            max_age = NON_CRYPTO_MAX_AGE_HOURS
            if age_hours > max_age:
                score -= 25
                penalties.append(f"stale({age_hours:.0f}h):-25")
            elif age_hours > max_age * 0.75:
                score -= 10
                penalties.append(f"aging({age_hours:.0f}h):-10")
        else:
            # Crypto: much more aggressive age penalty
            if age_hours > 48:
                score -= 35
                penalties.append(f"crypto_very_stale({age_hours:.0f}h):-35")
            elif age_hours > 24:
                score -= 25
                penalties.append(f"crypto_stale({age_hours:.0f}h):-25")
            elif age_hours > 12:
                score -= 15
                penalties.append(f"crypto_aging({age_hours:.0f}h):-15")
            elif age_hours > 6:
                score -= 8
                penalties.append(f"crypto_warming({age_hours:.0f}h):-8")
            elif age_hours < 2:
                score += 5
                penalties.append(f"crypto_fresh({age_hours:.0f}h):+5")

    # ASSET CLASS TRUST BONUS — DATA 2026-04-04 (attribution_tracker on 1200 closed picks):
    # EQUITY 67.2% WR, FOREX 55.7%, CRYPTO 49.8% — route picks toward proven classes.
    # Corrects under-allocation: 43 active CRYPTO vs 2 EQUITY despite EQUITY PF 2.17.
    _ac_bonus = ASSET_CLASS_BONUSES.get(_asset_class, 0)
    if _ac_bonus != 0:
        score += _ac_bonus
        penalties.append(f"asset_class({_asset_class}):{_ac_bonus:+d}")

    # VIX+YC REGIME BONUS (2026-05-16) — EQUITY score lift when macro regime is favorable.
    # Backtest: VIX<22 AND YC>0 → WR=75.95%, PF=4.98, Sharpe=2.08, MDD=16.8% (n=79, 11y).
    # vs baseline WR=64.75%, PF=2.82. +11pp WR and 1.76× PF improvement.
    # Score bonus (+12) when EQUITY pick enters favorable regime window.
    # Fail-open: if VIX/YC fetch fails, no bonus (no penalty).
    # Env: VIX_YC_SCORE_BONUS_ENABLED=1 (default ON); bonus size in VIX_YC_SCORE_BONUS_SIZE.
    if _asset_class == "EQUITY" and os.environ.get("VIX_YC_SCORE_BONUS_ENABLED", "1") == "1":
        try:
            from audit_trail.vix_regime_gate import get_cached_vix, get_cached_yc
            _vix_now = get_cached_vix()
            _yc_now = get_cached_yc()
            _vix_thr = float(os.environ.get("VIX_REGIME_GATE_THRESHOLD", "22.0"))
            _yc_thr = float(os.environ.get("YC_REGIME_GATE_MIN_SPREAD", "0.0"))
            if (
                _vix_now is not None and _yc_now is not None
                and _vix_now < _vix_thr and _yc_now > _yc_thr
            ):
                _vix_yc_bonus = int(os.environ.get("VIX_YC_SCORE_BONUS_SIZE", "15"))
                score += _vix_yc_bonus
                penalties.append(
                    f"vix_yc_regime_favorable(vix={_vix_now:.1f},yc={_yc_now:.2f}):+{_vix_yc_bonus}"
                )
        except Exception:
            pass  # fail-open: no bonus if regime data unavailable

    # ── ETF Sector Rotation — Approach B: macro-regime veto (2026-05-16) ──
    # Soft -10 score penalty for defensive sector ETFs (XLU/XLP/XLV) when
    # VIX > 30 (risk-off regime). Literature: defensive sectors underperform
    # in high-vol environments (Invesco 2023, SPDR sector analysis 2000-2024).
    # Shadow mode: ETF_MACRO_VETO=1 to enable (default OFF).
    # Only adjusts score — never hard-blocks (n=105, below the 150-pick floor
    # required for hard admission gates per charter).
    if (
        _asset_class == "ETF"
        and os.environ.get("ETF_MACRO_VETO", "0") == "1"
        and str(pick.get("symbol", "") or "").upper().strip() in DEFENSIVE_SECTOR_ETFS
    ):
        try:
            from audit_trail.vix_regime_gate import get_cached_vix as _get_vix_macro
            _etf_vix = _get_vix_macro()
            _etf_vix_thresh = float(os.environ.get("ETF_MACRO_VETO_VIX_THRESHOLD", "30.0"))
            if _etf_vix is not None and _etf_vix > _etf_vix_thresh:
                _etf_macro_penalty = int(os.environ.get("ETF_MACRO_VETO_PENALTY", "10"))
                score -= _etf_macro_penalty
                penalties.append(
                    f"etf_macro_veto_risk_off(vix={_etf_vix:.1f},sym={str(pick.get('symbol','') or '').upper()}):-{_etf_macro_penalty}"
                )
        except Exception:
            pass  # fail-open: missing VIX data → no penalty

    # ── ETF Sector Rotation — Approach A: RS overlay (2026-05-16) ──
    # Soft -5 score penalty when the ETF's 20-day return vs SPY is negative
    # (underperforming the broad market). RS score < 0 signals loss of
    # relative momentum — the primary edge driver for ETF sector rotation.
    # Shadow mode: ETF_RS_GATE=1 to enable (default OFF).
    # Only adjusts score — never hard-blocks (n=105, below 150-pick floor).
    if (
        _asset_class == "ETF"
        and os.environ.get("ETF_RS_GATE", "0") == "1"
    ):
        try:
            from tools.research.etf_rs import compute_etf_rs_score as _etf_rs
            _etf_sym = str(pick.get("symbol", "") or "").upper().strip()
            _rs_score = _etf_rs(_etf_sym)
            if _rs_score is not None and _rs_score < 0:
                _etf_rs_penalty = int(os.environ.get("ETF_RS_PENALTY", "5"))
                score -= _etf_rs_penalty
                penalties.append(
                    f"etf_rs_underperform(sym={_etf_sym},rs={_rs_score:.4f}):-{_etf_rs_penalty}"
                )
        except Exception:
            pass  # fail-open: yfinance unavailable → no penalty

    # Copy-trader staleness penalty (2026-04-04 antigrav-dash-integrity P1 request):
    # copy_trader_intel/highscore/clones ingestion dead 7 days (last_signal=2026-03-28).
    # Penalize picks where last_signal_at exceeds 72h threshold.
    _last_signal = pick.get("last_signal_at") or pick.get("last_signal")
    _source_sys = str(pick.get("source_system", pick.get("source", "")) or "").lower()
    if _last_signal and ("copy_trader" in _source_sys or "copytrader" in _source_sys):
        _signal_age_hrs = _calculate_age_hours(_last_signal)
        if _signal_age_hrs > 168:  # 7 days
            score -= 35
            penalties.append(f"copytrader_dead_signal({_signal_age_hrs:.0f}h):-35")
        elif _signal_age_hrs > 72:  # 3 days
            score -= 20
            penalties.append(f"copytrader_stale_signal({_signal_age_hrs:.0f}h):-20")

    # Trust penalties
    trust_label = str(pick.get("trust_label", "") or "").upper()
    if trust_label == "AVOID":
        score -= 20
        penalties.append("trust_AVOID:-20")
    elif trust_label == "LOW":
        score -= 10
        penalties.append("trust_LOW:-10")

    trust_tier = _trust_tier(pick)
    if trust_tier == "BANNED":
        score -= 25
        penalties.append("tier_BANNED:-25")
    elif trust_tier == "AVOID":
        score -= 15
        penalties.append("tier_AVOID:-15")

    # Blocked asset/strategy pairs get penalty
    asset_class = str(pick.get("asset_class", "CRYPTO")).upper()
    source = pick.get("source_system", pick.get("source", ""))
    if (asset_class, str(source)) in BLOCKED_ASSET_SOURCE_PAIRS:
        score -= 20
        penalties.append("blocked_source:-20")
    if (asset_class, str(strategy)) in BLOCKED_ASSET_STRATEGY_PAIRS:
        score -= 20
        penalties.append("blocked_strategy:-20")

    # Concentration penalty
    # 2026-04-05: Exempt per-symbol ensemble stacks from the generic
    # concentration penalty. Strategies like ml_enhanced_APEUSDT_1d_B_ensemble_stack
    # are DESIGNED to be single-symbol by architecture — penalizing them
    # for concentration is triple-counting (they already carry their own
    # strategy_concentration_multiplier=0.25 in source score breakdown).
    _strat_lower = str(strategy or "").lower()
    _is_per_symbol_stack = "_ensemble_stack" in _strat_lower and (
        "ml_enhanced_" in _strat_lower or "per_symbol_" in _strat_lower
    )
    conc_penalty = 0 if _is_per_symbol_stack else _concentration_penalty(pick)
    if conc_penalty > 0:
        score -= conc_penalty
        penalties.append(f"concentration:-{conc_penalty:.0f}")
    elif _is_per_symbol_stack:
        penalties.append("per_symbol_stack_exempt(+0)")

    # ── FORWARD-TEST VIABILITY BONUS (2026-04-10 audit) ──
    # Only 5/23 strategies viable in forward testing - boost the proven ones
    strategy_lower = str(strategy).lower()
    for viable_strat, viable_bonus in _VIABLE_STRATEGIES_FORWARD.items():
        if viable_strat in strategy_lower:
            score += viable_bonus
            penalties.append(f"forward_viable({viable_strat}):+{viable_bonus}")
            break
    
    # Demote non-viable strategies
    for demoted_strat in _DEMOTED_STRATEGIES_FORWARD:
        if demoted_strat in strategy_lower:
            score -= 25
            penalties.append(f"forward_demoted({demoted_strat}):-25")
            break

    # ── DATA-DRIVEN SCORING (from closed-pick correlation analysis) ──

    # 1. SOURCE SYSTEM PERFORMANCE (strongest predictor: source determines WR)
    source = str(pick.get("source_system", pick.get("source", "")) or "").lower()
    source_bonus = _SOURCE_SYSTEM_SCORES.get(source, 0)
    if source_bonus > 0:
        score += source_bonus
        penalties.append(f"proven_source({source}):+{source_bonus}")
    elif source_bonus < 0:
        score += source_bonus
        penalties.append(f"weak_source({source}):{source_bonus}")

    # 1b. PER-ASSET-CLASS SOURCE OVERRIDE — surgical correction for sources with
    #     class-specific track records that diverge from their global score.
    _ac_key = (asset_class.upper() if asset_class else "", source)
    _ac_delta = _SOURCE_ASSET_CLASS_OVERRIDES.get(_ac_key, 0)
    if _ac_delta != 0:
        score += _ac_delta
        if _ac_delta > 0:
            penalties.append(f"class_source_boost({asset_class},{source}):+{_ac_delta}")
        else:
            penalties.append(f"class_source_penalty({asset_class},{source}):{_ac_delta}")

    # 2. STRATEGY PERFORMANCE (second strongest predictor)
    strategy_l = str(strategy or "").lower()
    strat_bonus = _STRATEGY_SCORES.get(strategy_l, 0)
    if not strat_bonus:
        # Partial match for strategy families
        for pattern, bonus in _STRATEGY_FAMILY_SCORES.items():
            if pattern in strategy_l:
                strat_bonus = bonus
                break
    if strat_bonus > 0:
        score += strat_bonus
        penalties.append(f"proven_strat:+{strat_bonus}")
    elif strat_bonus < 0:
        score += strat_bonus
        penalties.append(f"weak_strat:{strat_bonus}")

    if strategy_l not in _KILLED_STRATEGIES_LOWER:
        _roll_d = _ROLLING_7D_DEGRADE_LOWER.get(strategy_l)
        if _roll_d:
            score += _roll_d
            penalties.append(f"rolling_7d_degrade({_roll_d:+d})")
        # M-015: dynamic decay-alert REDUCE soft-demote (stacks with static penalty)
        _decay_penalty = _get_decay_soft_demote_penalty(strategy_l)
        if _decay_penalty:
            score += _decay_penalty
            penalties.append(f"decay_alert_reduce({_decay_penalty:+d})")

    # 3. TRUST SCORE — DATA CORRECTED 2026-04-03 (1000 closed dashboard picks):
    #   Trust 1-3 = 38.0% WR, Trust 4-5 = 57.6% WR, Trust 6-7 = 76.9% WR
    #   Trust is the strongest single predictor (39pp spread). Low trust = penalty.
    trust_score = _float(pick.get("trust_score", 0))
    if trust_score >= 6:
        trust_bonus = min(15, int(trust_score * 2.0))
        score += trust_bonus
        penalties.append(f"trust_high({trust_score:.0f}):+{trust_bonus}")
    elif trust_score >= 4:
        trust_bonus = min(10, int(trust_score * 1.5))
        score += trust_bonus
        penalties.append(f"trust_mid({trust_score:.0f}):+{trust_bonus}")
    elif trust_score > 0:
        # REDUCED -15 → -10: trust_label "LOW" already applies -10 for the
        # same picks, creating a -35 total stack (trust_LOW + trust_low + long_low_trust_combo)
        # that kills any pick starting under score ~85.  -10 keeps the signal
        # meaningful (-30 max stack) without being devastating.
        score -= 10
        penalties.append(f"trust_low({trust_score:.0f}):-10")

    # LONG + CONFIDENCE COMBO PENALTIES — DATA 2026-04-03 + codebuff analysis:
    #   LONG + conf 0.80-0.89 = 50% WR (fine, no penalty)
    #   LONG + conf 0.90+ = 19.5% WR (TOXIC — worse than coin flip)
    #   LONG + conf 0.60-0.69 = 31.3% WR on 182 picks (dead zone for LONGs)
    #   LONG + trust 0-3 = 36.2% WR on 506 picks (biggest volume loser)
    direction = str(pick.get("direction", "") or "").upper()
    if direction in ("LONG", "BUY") and conf >= 0.90:
        score -= 15
        penalties.append(f"long_overconf_combo({conf:.2f}):-15")
    elif direction in ("LONG", "BUY") and 0.60 <= conf < 0.70:
        if _equity_forward_proven_mitigates_conf_deadzone(pick):
            penalties.append(
                f"long_deadzone_exempt_equity_forward_proven(conf={conf:.2f}):+0"
            )
        else:
            score -= 12
            penalties.append(f"long_deadzone_combo({conf:.2f}):-12")

    # LONG + LOW TRUST combo — 36.2% WR on 506 picks
    if direction in ("LONG", "BUY") and 0 < trust_score <= 3:
        score -= 10
        penalties.append(f"long_low_trust_combo(trust={trust_score:.0f}):-10")

    # 5. SYMBOL+DIRECTION EDGE — DATA 2026-04-03 (1000 closed picks):
    #    Certain symbols have strong directional bias (e.g., LTCUSDT LONG 92% WR,
    #    XMR LONG 0% WR). Apply bonuses/penalties based on proven track record.
    symbol = str(pick.get("symbol", "") or "").upper()
    sym_dir_key = (symbol, direction)
    sym_dir_bonus = SYMBOL_DIRECTION_BONUSES.get(sym_dir_key, 0)
    if sym_dir_bonus != 0:
        score += sym_dir_bonus
        penalties.append(f"sym_dir({symbol}_{direction}):{sym_dir_bonus:+d}")

    # 6. STRATEGY+SYMBOL COMBO EDGE — DATA 2026-04-03:
    #    Some strategies work brilliantly on specific symbols but fail on others.
    strat_sym_key = (strategy, symbol)
    strat_sym_bonus = STRATEGY_SYMBOL_BONUSES.get(strat_sym_key, 0)
    if strat_sym_bonus != 0:
        score += strat_sym_bonus
        penalties.append(f"strat_sym({strategy[:20]}_{symbol}):{strat_sym_bonus:+d}")

    # 6b. PROVEN SYMBOL BOOSTS (T1-D, 2026-04-15)
    #    Top symbols with WR >= 50% and n >= 20. Nudges picks over gate thresholds.
    #    Cap: score cannot exceed 100 after boost.
    #    Skip when a SYMBOL_DIRECTION_BONUS already applies (direction-specific edge
    #    overrides generic proven boost; avoids double-boosting or partial penalty undo).
    _proven_boost = PROVEN_SYMBOL_BOOSTS.get(symbol, 0)
    if _proven_boost != 0 and sym_dir_bonus == 0:
        score = min(100, score + _proven_boost)
        penalties.append(f"proven_symbol({symbol}):{_proven_boost:+d}")

    # 7. REGIME DRIFT DETECTION — DATA 2026-04-04 (regime analysis):
    #    ml_enhanced_stack: BTC 14% WR vs ALT 51% WR (37pp gap) ÔåÆ block BTC
    #    ml_enhanced_lightgbm: LONG 49% vs SHORT 68% (19pp gap) ÔåÆ prefer SHORT
    #    ml_enhanced_lightgbm LONG: 71% ÔåÆ 42% decline (regime ended)
    strat_lower = str(strategy or "").lower()
    if "ml_enhanced_stack" in strat_lower and symbol == "BTCUSDT":
        score -= 25
        penalties.append("ml_stack_btc_regime_broken:-25")
    if "ml_enhanced_lightgbm" in strat_lower and direction in ("LONG", "BUY"):
        score -= 15
        penalties.append("ml_lightgbm_long_degraded:-15")
    if "ml_enhanced_lightgbm" in strat_lower and direction in ("SHORT", "SELL"):
        score += 10
        penalties.append("ml_lightgbm_short_edge:+10")

    # 7a. CONSENSUS PERCENTAGE — DATA 2026-04-03 (2109 closed picks):
    #   consensus_pct < 0.67 = 12.2% WR (589 picks) — death zone
    #   consensus_pct = 1.0 = 32.2% WR — better but still below average
    #   The specific strategy COMBINATION matters more than raw agreement count.
    _consensus_pct = _float(pick.get("consensus_pct", 0))
    if 0 < _consensus_pct < 0.67:
        score -= 10
        penalties.append(f"consensus_death_zone({_consensus_pct:.2f}):-10")

    # 7b. METHOD A GRADE — DATA 2026-04-03 (2109 closed picks):
    #   INVERTED relationship: Grade F = 76.5% WR, Grade D = 45.1%, Grade B = 14.3%
    #   This is because method_a penalizes contrarian strategies which actually win.
    #   Don't use method_a_grade for scoring since it's anti-predictive in this system.
    #   Instead, use method_a_score >= 80 as a positive signal (42.8% WR vs 20.4%)
    _method_a = _float(pick.get("method_a_score", 0))
    if _method_a >= 80:
        score += 8
        penalties.append(f"method_a_strong({_method_a:.0f}):+8")

    # 7c. TOXIC STRATEGY COMBINATIONS — DATA 2026-04-03 (2109 closed picks):
    #   Specific 3-strategy combos have extreme WR. The composition of strategies_agreed
    #   matters more than the count.
    _strats_agreed = str(pick.get("strategies_agreed", "") or "")
    if "proven_propfirm" in _strats_agreed and "proven_triple_ema" in _strats_agreed:
        # This combo = 1.7% WR on 481 picks — toxic
        score -= 15
        penalties.append("toxic_strat_combo(propfirm+triple_ema):-15")
    elif (
        "corr_hma_trend" in _strats_agreed and "fear_greed_contrarian" in _strats_agreed
    ):
        # This combo = 70.6% WR on 34 picks — golden
        score += 10
        penalties.append("golden_strat_combo(hma+fgc):+10")

    # 4. MULTI-SOURCE CONSENSUS
    # Cross-run analysis shows raw agreement count is noisy by itself. Consensus
    # only deserves meaningful credit when the underlying strategy actually has
    # decent forward edge.
    agreement = _float(pick.get("agreement_count", 0))
    source_systems = pick.get("source_systems", [])
    if isinstance(source_systems, str):
        source_systems = [s.strip() for s in source_systems.split(",") if s.strip()]
    n_sources = max(len(source_systems), int(agreement))
    proven_edge = edge_trades >= 10 and edge_wr >= 0.55
    decent_edge = edge_trades >= 5 and edge_wr >= 0.50
    weak_edge = edge_trades >= 10 and 0 < edge_wr < 0.35
    if n_sources >= 5:
        if weak_edge:
            score -= 10
            penalties.append(
                f"crowded_consensus_weak_edge({n_sources}|{edge_wr:.0%}):-10"
            )
        elif proven_edge:
            score += 6
            penalties.append(f"crowded_consensus_proven({n_sources}):+6")
        else:
            score += 2
            penalties.append(f"crowded_consensus_unproven({n_sources}):+2")
    elif n_sources >= 3:
        if weak_edge:
            score -= 6
            penalties.append(f"multi_consensus_weak_edge({n_sources}|{edge_wr:.0%}):-6")
        elif decent_edge:
            score += 5
            penalties.append(f"multi_consensus_proven({n_sources}):+5")
        else:
            # v101: 2-4 strategy consensus WITHOUT proven edge is the WORST WR bucket (14.6%)
            # Data shows U-shaped curve: 0 strats (46.2% WR) and 5+ strats (44.7%) beat 3-4 strats (14.6%)
            score -= 5
            penalties.append(f"consensus_dead_zone({n_sources}):-5")
    elif n_sources == 2:
        if weak_edge:
            score -= 3
            penalties.append(f"dual_source_weak_edge({edge_wr:.0%}):-3")
        elif decent_edge:
            score += 3
            penalties.append("dual_source_proven:+3")
        else:
            score += 1
            penalties.append("dual_source_unproven:+1")

    # 4b. NULL-ML + SINGLE-SOURCE PENALTY (2026-04-05 claude-bus-setup, P0-A fix)
    # Mirrors smart_picks_engine._compute_ml_composite fallback penalty at the
    # dashboard-aggregation path. Picks arriving from upstream aggregators
    # (alpha_engine, super_signals, ml_crypto_pred) bypass smart_picks_engine and
    # the ml_null penalty never fires. Result: 104/106 picks score=120 with
    # null ml_composite_score (observed on 2026-04-05 01:17Z payload).
    # Fix: apply score cap when BOTH ml_score is None AND single-source.
    # Multi-source picks are exempt — confluence IS their edge signal.
    #
    # 2026-04-14: goldmine_stocks — consensus/avg_score ARE the ML signal; applying
    # null_ml_solo_source when ml_composite_score is not yet merged duplicates a
    # timing bug. Exempt (consensus row is not "missing ML").
    _skip_null_ml_penalty = str(pick.get("source_system") or "").lower() == "goldmine_stocks"
    if not _skip_null_ml_penalty:
        _ml = pick.get("ml_score")
        _ml_comp = pick.get("ml_composite_score")
        if (_ml is None or _float(_ml) <= 0) and (
            _ml_comp is None or _float(_ml_comp) <= 0
        ):
            if n_sources < 2:
                score -= 20
                penalties.append(f"null_ml_solo_source({n_sources}):-20")
            elif n_sources < 3:
                # Dual-source with null ml gets a smaller demotion
                score -= 8
                penalties.append(f"null_ml_dual_source:-8")
            # n_sources >= 3 with null ml: confluence carries, no extra penalty

    # 5. TECHNICAL BIAS ALIGNMENT (58.8% WR aligned vs 43.1% misaligned)
    direction = str(pick.get("direction", pick.get("signal_type", "")) or "").upper()
    tech_verdict = str(pick.get("technical_verdict", "") or "").upper()
    htf_bias = str(pick.get("htf_bias", "") or "").upper()
    bias = htf_bias or tech_verdict
    if bias and direction:
        bullish_bias = bias in ("BULL", "BULLISH", "BUY", "STRONG BUY", "STRONG_BUY")
        bearish_bias = bias in ("BEAR", "BEARISH", "SELL", "STRONG SELL", "STRONG_SELL")
        if (direction in ("LONG", "BUY") and bullish_bias) or (
            direction in ("SHORT", "SELL") and bearish_bias
        ):
            score += 8
            penalties.append("htf_aligned:+8")
        elif (direction in ("LONG", "BUY") and bearish_bias) or (
            direction in ("SHORT", "SELL") and bullish_bias
        ):
            score -= 8
            penalties.append("htf_misaligned:-8")

    # 6. OVERFITTING PENALTY (forward_wr r=-0.49 with PnL — high backtest WR = worse live)
    fwd_wr = edge_wr
    fwd_trades = edge_trades
    if fwd_wr > 0.75 and fwd_trades < 20:
        score -= 10
        penalties.append(f"overfit_risk(wr={fwd_wr:.0%},n={fwd_trades:.0f}):-10")
    elif fwd_wr > 0 and fwd_trades >= 20 and fwd_wr >= 0.50:
        # Genuine track record with enough trades — small bonus
        score += 5
        penalties.append(f"proven_track(wr={fwd_wr:.0%},n={fwd_trades:.0f}):+5")

    # 6a. HF THRESHOLD A — BT vs forward decay (user-approved 2026-04-04)
    # Requires bt_win_rate on pick (dashboard join from strategy leaderboard /
    # survivor BT). Skips when missing — no penalty for unknown BT.
    _bt_win = pick.get("bt_win_rate")
    if decay_hard_gate_triggers(_bt_win, edge_wr, edge_trades):
        pick["_hf_threshold_a"] = True
        score -= 45
        _bt_disp = normalize_wr_percent(_bt_win)
        _fwd_disp = normalize_wr_percent(edge_wr)
        _bt_s = ("%.1f" % _bt_disp) if _bt_disp is not None else "?"
        _fwd_s = ("%.1f" % _fwd_disp) if _fwd_disp is not None else "?"
        penalties.append(
            "hf_decay_gate_A(bt=%s%%,fwd=%s%%,n=%d):-45" % (_bt_s, _fwd_s, edge_trades)
        )

    # 7. DIRECTION BIAS — DATA CORRECTED 2026-04-01:
    # Closed analysis: SHORT 50.3% WR (+0.19% avg) vs LONG 43.6% (+0.06% avg)
    # SHORT+highConf+tightRR = 80.0% WR (best combo). Remove SHORT penalty.
    if direction in ("SHORT", "SELL"):
        # SHORT outperforms LONG by 8pp (56.7% vs 48.7%) across ALL trust/conf buckets
        score += 5
        penalties.append("short_base_bonus:+5")
        # Extra boost if tight R:R + high confidence (golden combo: 80% WR)
        if rr <= 1.5 and rr > 0 and conf >= 0.70:
            score += 8
            penalties.append("short_golden_combo:+8")

    # 8. TRADE MODE — SCALP ELIMINATED (24.8% WR across 855 trades = biggest WR drag)
    # Data: SWING +0.013% avg (only profitable mode), SCALP -0.171%, POSITION 0% WR
    mode = str(pick.get("mode", pick.get("trade_mode", "")) or "").upper()
    if mode == "SCALP":
        score -= 40  # Effectively kills SCALP (was -25, now -40 to guarantee bottom)
        penalties.append("scalp_killed:-40")
    elif mode == "POSITION":
        score -= 30  # 0% WR on 13 trades
        penalties.append("position_killed:-30")
    elif mode == "SWING":
        score += 5
        penalties.append("swing_mode:+5")

    # 9. STRATEGY FORWARD WR (strongest Q1->Q4 spread: 19.1% -> 56.2%)
    # KiloCode analysis: strategy_fwd_wr has the largest WR spread of any metric
    strat_fwd_wr = max(
        _ratio(pick.get("strat_fwd_wr")),
        _ratio(pick.get("strategy_fwd_wr")),
        _ratio(pick.get("forward_wr")),
    )
    strat_fwd_trades = max(
        _float(pick.get("strat_fwd_trades", 0)),
        _float(pick.get("strategy_fwd_trades", 0)),
        _float(pick.get("forward_trades", 0)),
    )
    if strat_fwd_wr >= 0.60 and strat_fwd_trades >= 10:
        score += 12
        penalties.append(
            f"strat_wr_proven({strat_fwd_wr:.0%}/{strat_fwd_trades:.0f}t):+12"
        )
    elif strat_fwd_wr >= 0.50 and strat_fwd_trades >= 5:
        score += 6
        penalties.append(
            f"strat_wr_decent({strat_fwd_wr:.0%}/{strat_fwd_trades:.0f}t):+6"
        )
    elif strat_fwd_wr > 0 and strat_fwd_wr < 0.35 and strat_fwd_trades >= 10:
        score -= 10
        penalties.append(
            f"strat_wr_poor({strat_fwd_wr:.0%}/{strat_fwd_trades:.0f}t):-10"
        )

    # 10. Multi-timeframe support breadth, made direction-aware.
    tech_buy_tfs = _int(pick.get("technical_buy_tfs", 0))
    tech_sell_tfs = _int(pick.get("technical_sell_tfs", 0))
    supporting_tfs = tech_buy_tfs if direction in ("LONG", "BUY") else tech_sell_tfs
    if supporting_tfs >= 3:
        score += 8
        penalties.append(f"multi_tf_support({supporting_tfs}tf):+8")
    elif supporting_tfs == 2:
        score += 4
        penalties.append("multi_tf_support(2tf):+4")
    elif supporting_tfs == 0 and tech_bucket in {"no_support", "strong_opposition"}:
        score -= 6
        penalties.append("multi_tf_support_missing:-6")

    # Legacy bonuses
    if _has_strong_audited_pm_history(pick):
        score += AUDITED_PM_SCORE_BONUS
        penalties.append(f"audited_pm:+{AUDITED_PM_SCORE_BONUS}")

    verified_bonus = _verified_pm_or_copy_bonus(pick)
    if verified_bonus:
        score += verified_bonus
        penalties.append(f"verified_source:+{verified_bonus}")

    if strategy in PROVEN_INVERSE_STRATEGIES:
        score += 10
        penalties.append("proven_inverse:+10")

    # Backtest-validated strategy bonus (970-run case study 2026-04-04)
    _bt_bonus = 0
    for _bt_key, _bt_val in BACKTEST_VALIDATED_STRATEGIES.items():
        if _bt_key in strategy_l:
            _bt_bonus = _bt_val
            break
    if _bt_bonus > 0:
        score += _bt_bonus
        penalties.append(f"backtest_validated({strategy_l[:25]}):+{_bt_bonus}")

    # Symbol-Aware Track Record (SAG) - MANDATORY FOR TRUST (2026-03-29 upgrade)
    sym_track_wr = pick.get("sym_track_wr")
    sym_track_total = _int(pick.get("sym_track_total", 0))
    if sym_track_wr is not None and sym_track_total >= 3:
        if sym_track_wr < 45:
            score -= 35  # Heavy penalty for proven losers on this symbol
            penalties.append(f"bad_sym_track({sym_track_wr}%):-35")
        elif sym_track_wr >= 45 and sym_track_wr < 55:
            score -= 10
            penalties.append(f"mediocre_sym_track({sym_track_wr}%):-10")
        elif sym_track_wr >= 65:
            score += 15
            penalties.append(
                f"proven_sym_track({sym_track_wr}%/n={sym_track_total}):+15"
            )

    # Mercury 2 quality flag penalty
    m2_flags = pick.get("quality_flags", [])
    if isinstance(m2_flags, list) and m2_flags:
        flag_penalty = min(len(m2_flags) * 5, 15)  # -5 per flag, max -15
        score -= flag_penalty
        penalties.append(f"m2_quality_flags:-{flag_penalty}")

    # Meta-labeler filter (Lopez de Prado): P(profitable) score from ML model
    # Picks with meta_label_score < 0.60 are predicted unprofitable by the secondary model
    meta_score = _float(pick.get("meta_label_score", 0))
    if meta_score > 0:
        if meta_score >= 0.75:
            score += 10  # High confidence from meta-labeler
            penalties.append(f"meta_label_high({meta_score:.2f}):+10")
        elif meta_score >= 0.60:
            score += 5
            penalties.append(f"meta_label_ok({meta_score:.2f}):+5")
        elif meta_score < 0.40:
            score -= 15  # Meta-labeler says this pick is likely unprofitable
            penalties.append(f"meta_label_reject({meta_score:.2f}):-15")

    # Track record bonus (98% NULL but +97% WR spread when populated)
    track_record = _float(
        pick.get("track_record", pick.get("sb_strategy_track_record", 0))
    )
    if track_record > 0:
        if track_record >= 80:
            score += 12
            penalties.append(f"track_record_elite({track_record:.0f}):+12")
        elif track_record >= 60:
            score += 8
            penalties.append(f"track_record_good({track_record:.0f}):+8")
        elif track_record < 30:
            score -= 10
            penalties.append(f"track_record_poor({track_record:.0f}):-10")

    # ── QUANT PLAN SCORING ENHANCEMENTS (Mar 31, 2026) ──
    # Based on 1886 closed pick DNA, inverse analysis, and statistical validation.
    # All picks stay visible — better picks get higher scores.

    # Q1. INVERSE STRATEGY DETECTION: strategies with <30% WR on LONGs
    # Data: quan_engine LONG 29% WR (387 trades), ml_crypto_predictor LONG 0% WR (41)
    # If a strategy is a known bad LONG predictor, heavily penalize LONG picks from it
    _INVERSE_LONG_PENALTIES = {
        "ml_crypto_predictor": -20,  # 0% WR on LONGs (41 trades)
        "quan_engine": -15,  # 29% WR on LONGs (387 trades)
        "atr_regime_rsi": -12,  # 23% WR on LONGs (26 trades)
        "ensemble": -10,  # 24% WR on LONGs (45 trades)
        "enhanced_ml_a_xgboost": -10,  # 29% WR on LONGs (24 trades)
        "macd_crossover": -10,  # 25% WR on LONGs (8 trades)
    }
    if direction in ("LONG", "BUY"):
        for inv_strat, inv_penalty in _INVERSE_LONG_PENALTIES.items():
            if inv_strat in strategy_l:
                score += inv_penalty
                penalties.append(f"inverse_long_trap({inv_strat}):{inv_penalty}")
                break

    # Q2. KELLY-INSPIRED CONFIDENCE BONUS: picks with optimal params get boosted
    # Data: confidence 70-80% = 64% WR (only profitable band)
    # Data: R:R 1.2-1.5 = 67% WR (best bracket)
    # Combined: if both in optimal range, big boost
    _conf = _normalize_confidence(pick.get("confidence", 0))
    if _conf > 1:
        _conf = _conf / 100  # normalize
    _rr = _float(pick.get("rr", pick.get("rr_ratio", pick.get("risk_reward", 0))))
    if 0.70 <= _conf <= 0.80 and 1.2 <= _rr <= 1.5:
        score += 15  # Golden combo: optimal confidence + optimal R:R
        penalties.append("kelly_golden_combo:+15")
    elif 0.70 <= _conf <= 0.80:
        score += 8  # Confidence in sweet spot
        penalties.append("conf_sweet_spot:+8")
    elif 1.2 <= _rr <= 1.5:
        score += 5  # R:R in sweet spot
        penalties.append("rr_sweet_spot:+5")

    # Q3. TRADE COUNT RELIABILITY BONUS (more data = more trustworthy)
    # Kelly fraction scales with trade count — reflect this in score
    _fwd_trades = max(
        _float(pick.get("strat_fwd_trades", 0)),
        _float(pick.get("strategy_fwd_trades", 0)),
        _float(pick.get("forward_trades", 0)),
    )
    if _fwd_trades >= 200:
        score += 10  # Half-Kelly territory — high trust
        penalties.append(f"trade_count_elite({_fwd_trades:.0f}):+10")
    elif _fwd_trades >= 100:
        score += 7
        penalties.append(f"trade_count_strong({_fwd_trades:.0f}):+7")
    elif _fwd_trades >= 50:
        score += 4
        penalties.append(f"trade_count_decent({_fwd_trades:.0f}):+4")
    elif _fwd_trades < 10 and _fwd_trades > 0:
        score -= 5  # Too few trades to trust
        penalties.append(f"trade_count_thin({_fwd_trades:.0f}):-5")

    # Q4. 100% WR PROVEN COMBO SUPER-BOOST — DISABLED 2026-05-18
    # All combos stripped: every "100% WR" entry was a small-sample / placeholder-stat
    # artifact, none canonical-verified. Dict empty; loop below is a harmless no-op.
    _100WR_COMBOS = {
        # ALL combos stripped 2026-05-18: unverified 100%-WR boosts, none in canonical
        # pf_registry policy-clean-net; st_fear_greed_contrarian is NOT harness-admissible
        # (one-window fluke per DEEP_DIVE_MONEYREADY_2026-05-18). Dict intentionally empty.
        # ml_enhanced combos REMOVED 2026-05-18 (M-105 / EDGE_VERDICT_2026-05-18):
        # the "100% WR" was a placeholder-stat artifact (near-zero avg_loss),
        # the family is 149 curve-fit per-symbol variants (net PF 0.63), and
        # M-108 magnitude-sanity rejects ml_enhanced FETUSDT (~40% fantasy TP)
        # at emission. Boosting their score contradicts both — do NOT re-add.
        # auditensemble_long/vwap/momentumema etc. also stripped — placeholder-stat
        # artifacts (PF 38-119 = near-zero avg_loss) flagged by BURIED_WINNER_HUNT.
    }
    _sym = str(pick.get("symbol", "") or "").upper()
    for (combo_strat, combo_sym, combo_dir), combo_boost in _100WR_COMBOS.items():
        if combo_strat in strategy_l and (combo_sym is None or combo_sym == _sym) and combo_dir == direction:
            score += combo_boost
            penalties.append(
                f"100pct_wr_combo({combo_strat[:20]}+{combo_sym}+{combo_dir}):+{combo_boost}"
            )
            break

    # Q5. REGIME-AWARE DIRECTION PREMIUM (from 1886 pick analysis)
    # SHORT = 68% WR overall, LONG = 36% in extreme fear
    # Scale the premium by how extreme the fear is (use FGI if available)
    _fgi = _float(pick.get("fear_greed", pick.get("fgi", 0)))
    _is_contrarian_strat = "contrarian" in strategy_l or "fear_greed" in strategy_l
    if _fgi > 0 and _fgi < 25:
        _fear_intensity = (25 - _fgi) / 25  # 1.0 at FGI=0, 0.0 at FGI=25
        if direction in ("SHORT", "SELL") and not _is_contrarian_strat:
            _regime_boost = int(12 * _fear_intensity)
            score += _regime_boost
            penalties.append(f"fear_short_premium(fgi={_fgi:.0f}):+{_regime_boost}")
        elif direction in ("LONG", "BUY") and _is_contrarian_strat:
            # Contrarian LONGs in extreme fear = 88.2% WR (best validated edge)
            _contrarian_boost = int(15 * _fear_intensity)
            score += _contrarian_boost
            penalties.append(
                f"fear_contrarian_long(fgi={_fgi:.0f}):+{_contrarian_boost}"
            )
        elif direction in ("LONG", "BUY"):
            _regime_penalty = int(-8 * _fear_intensity)
            score += _regime_penalty
            penalties.append(f"fear_long_penalty(fgi={_fgi:.0f}):{_regime_penalty}")

    # Q5b. SHORT BIAS GATE — bear regime + extreme fear = 1.5x SHORT weight
    # Task from copilot-quant-audit (P1): when BTC<200MA AND FGI<30, weight SHORT picks
    # Rationale: both filters confirm bear regime; SHORT has +8pp edge system-wide, compounds in bear.
    _btc_regime = str(
        pick.get("btc_regime", pick.get("regime_at_entry", "")) or ""
    ).upper()
    _btc_below_200ma = (
        "BEAR" in _btc_regime
        or "DOWN" in _btc_regime
        or _btc_regime == "BEARISH"
        or pick.get("btc_below_200ma") is True
    )
    if _fgi > 0 and _fgi < 30 and _btc_below_200ma and direction in ("SHORT", "SELL"):
        # 1.5x weight realized as +12 score bonus (roughly 50% amplification
        # of the typical SHORT-leg signal score ~24)
        score += 12
        penalties.append(f"short_bias_gate(fgi={_fgi:.0f},btc_bear):+12")

    # Q6. MOMENTUM GAINER PATTERN BONUS (paradigm shift discovery 2026-04-01)
    # Peer analysis of 18 top crypto gainers revealed pumps are preceded by:
    #   RSI ~56 (neutral, NOT oversold), price near upper BB (67%), ATR < 3% (61%),
    #   ADX > 20 (89%), gradual volume increase (not spike).
    # This is the OPPOSITE of mean-reversion signals. Reward momentum/breakout
    # strategies that catch neutral-RSI setups with decent confidence.
    _MOMENTUM_KEYWORDS = ("momentum", "gainer", "breakout", "trend")
    _rsi = _float(pick.get("rsi", pick.get("rsi_14", 0)))
    _strat_lower = strategy.lower()
    if (
        40 <= _rsi <= 60
        and conf >= 0.60
        and direction in ("LONG", "BUY")
        and any(kw in _strat_lower for kw in _MOMENTUM_KEYWORDS)
    ):
        score += 8
        penalties.append(f"gainer_paradigm_bonus(rsi={_rsi:.1f}):+8")

    # Q7. TIME-OF-DAY EDGE (from 2,000 closed pick statistical analysis)
    # Night session 01-05 UTC: 61.1% WR vs 41.2% rest of day
    # Dead zones: 07-08 UTC (26% WR), 17-21 UTC (30% WR)
    # Autocorrelation lag-1 = +0.273 — wins cluster, time-of-day is a real edge.
    _ts_raw = (
        pick.get("created_at") or pick.get("timestamp") or pick.get("generated_at")
    )
    _pick_dt = None
    if _ts_raw:
        try:
            _pick_dt = datetime.fromisoformat(str(_ts_raw).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            _pick_dt = None
    if _pick_dt is not None:
        _utc_hour = _pick_dt.hour
        if 1 <= _utc_hour <= 5:
            score += 6
            penalties.append(f"night_session_edge(h={_utc_hour}):+6")
        elif _utc_hour == 23 or _utc_hour == 0:
            score += 3
            penalties.append(f"late_night_edge(h={_utc_hour}):+3")
        elif 7 <= _utc_hour <= 8:
            score -= 8
            penalties.append(f"dead_zone_morning(h={_utc_hour}):-8")
        elif 16 <= _utc_hour <= 17:
            # DATA 2026-04-03: 16:00=9.1% WR (77 trades), 17:00=16.1% WR (93 trades)
            score -= 15
            penalties.append(f"dead_zone_us_close(h={_utc_hour}):-15")
        elif 18 <= _utc_hour <= 21:
            score -= 6
            penalties.append(f"dead_zone_evening(h={_utc_hour}):-6")

        # Q7b. ASSET-CLASS SPECIFIC SAFETY WINDOWS (Audit 2026-04-05)
        # EQUITY: US Market Open (13-15 UTC) is the institutional edge for stocks.
        # FOREX: London/NY overlap (08-16 UTC) is the high-liquidity alpha peak.
        _ac_val = str(pick.get("asset_class", pick.get("mode", ""))).upper()
        if "EQUITY" in _ac_val or "STOCK" in _ac_val:
            if 13 <= _utc_hour <= 15:
                score += 12
                penalties.append(f"equity_us_open_bonus(h={_utc_hour}):+12")
        elif "FOREX" in _ac_val or "FX" in _ac_val:
            if 8 <= _utc_hour <= 16:
                score += 8
                penalties.append(f"forex_liquidity_bonus(h={_utc_hour}):+8")

        # 2026-05-16: CRYPTO UTC-hour edge per holographic-memory decision
        # crypto-hour-filter-20260516: 22 UTC → 61.2% WR n>1000 (strong edge)
        # 08-09 UTC → CRYPTO death zone, low WR. 08 already hit by dead_zone_morning;
        # 09 needs explicit CRYPTO penalty. Kill-switch: CRYPTO_HOUR_FILTER_DISABLED=1
        if "CRYPTO" in _ac_val and os.environ.get("CRYPTO_HOUR_FILTER_DISABLED", "0") != "1":
            if _utc_hour == 22:
                score += 8
                penalties.append(f"crypto_22utc_edge(h={_utc_hour}):+8")
            elif _utc_hour == 9:
                score -= 10
                penalties.append(f"crypto_09utc_death_zone(h={_utc_hour}):-10")

        # Penalize "Morning Noise" (06-12 UTC) - Identified as -$125 PnL drain
        if 6 <= _utc_hour <= 12 and not ("EQUITY" in _ac_val or "STOCK" in _ac_val):
            score -= 5
            penalties.append(f"morning_noise_penalty(h={_utc_hour}):-5")

        # Q8. DAY-OF-WEEK EDGE — UPDATED 2026-04-03 (1952 closed picks):
        # Tuesday: 50.5% WR (best, only profitable day)
        # Sunday: 14.2% WR over 281 trades (worst, massively significant)
        _dow = _pick_dt.weekday()  # 0=Monday ... 6=Sunday
        if _dow == 1:  # Tuesday (best day)
            score += 5
            penalties.append("tuesday_edge:50.5%WR:+5")
        elif _dow == 3:  # Thursday
            score += 4
            penalties.append("thursday_edge:61.9%WR:+4")
        elif _dow == 6:  # Sunday — 14.2% WR on 281 trades (2026-04-03 data)
            score -= 3
            penalties.append("sunday_penalty:32.8%WR:-3")
        elif (
            _dow == 4
        ):  # Friday — 41.3% WR on 387 trades (attribution_tracker 2026-04-04)
            # 18.1pp spread vs Wed (59.5% WR). Per attribution_report recommendation.
            # Data source: alpha_engine/data/attribution_report.json (1200 closed picks)
            score -= 9
            penalties.append("friday_penalty:41.3%WR:-9")
        elif _dow == 0:  # Monday
            score -= 3
            penalties.append("monday_penalty:40.8%WR:-3")

    # Q9. MULTI-SYMBOL ROBUSTNESS BONUS — the "super strategy" concept
    # A strategy that profits across 10+ symbols (ALL_SYMBOL tier) is far more
    # trustworthy than one profitable on a single symbol (likely curve-fit).
    # Data: st_fear_greed_contrarian = 69.4% WR across 17/19 symbols (ALL_SYMBOL).
    # SINGLE_SYMBOL strategies with low robustness are unreliable — penalize them.
    _tiers_data = _load_symbol_strength_tiers()
    _tier_details = _tiers_data.get("details", {})
    # Normalize strategy name for lookup (try exact, then lowercase)
    _tier_info = _tier_details.get(strategy) or _tier_details.get(strategy_l) or {}
    _sym_tier = str(_tier_info.get("tier", "")).upper()
    _sym_robustness = _float(_tier_info.get("robustness", 0))
    if _sym_tier == "ALL_SYMBOL":
        score += 12
        penalties.append(f"super_strategy_all_symbol({_sym_robustness:.2f}):+12")
    elif _sym_tier == "MULTI_SYMBOL":
        score += 8
        penalties.append(f"super_strategy_multi_symbol({_sym_robustness:.2f}):+8")
    elif _sym_tier == "FEW_SYMBOL":
        score += 4
        penalties.append(f"super_strategy_few_symbol({_sym_robustness:.2f}):+4")
    elif _sym_tier == "SINGLE_SYMBOL" and _sym_robustness < 0.3:
        score -= 5
        penalties.append(f"single_symbol_fragile({_sym_robustness:.2f}):-5")

    # Q10. MOVE EXHAUSTION PENALTY — Mercury AI item #7
    # Rationale: Entering LONG after a >3% up move = chasing; the asset has already
    # priced in momentum and reversal risk is elevated.  Similarly, entering SHORT
    # after a >3% down move = chasing the dump.  Subtract 10 points to discourage
    # regime-blind entries that ignore recent price displacement.
    _price_chg_24h = _float(pick.get("price_change_24h"))
    if pick.get("price_change_24h") is not None:
        if _price_chg_24h > 3.0 and direction in ("LONG", "BUY"):
            score -= 10
            penalties.append(f"move_exhaustion_long(24h={_price_chg_24h:+.1f}%):-10")
        elif _price_chg_24h < -3.0 and direction in ("SHORT", "SELL"):
            score -= 10
            penalties.append(f"move_exhaustion_short(24h={_price_chg_24h:+.1f}%):-10")

    # Q11. VOLATILITY SPIKE PENALTY — Mercury AI item #7
    # Rationale: When short-term (20d) volatility exceeds 2x the longer-term (60d)
    # baseline, the regime is unstable — wider candles, more stop-loss hunting, and
    # higher probability of SL hits.  Subtract 8 points to reflect the elevated
    # regime risk until volatility normalises.
    _vol_20d = _float(pick.get("volatility_20d"))
    _vol_60d = _float(pick.get("volatility_60d"))
    if (
        pick.get("volatility_20d") is not None
        and pick.get("volatility_60d") is not None
        and _vol_60d > 0
    ):
        if _vol_20d > 2.0 * _vol_60d:
            score -= 8
            penalties.append(
                f"volatility_spike(20d={_vol_20d:.4f}>2x60d={_vol_60d:.4f}):-8"
            )

    # Q12. MERCURY 2 UNIFIED SCORE — FROZEN (p=0.76, pure noise)
    # 46 trades, 39.1% WR, CI includes zero — no statistical significance.
    # All scoring boosts set to 0 until Mercury2 proves edge on fresh data.
    # Original: +6 for score>0.70, -6 for score<0.40, -4 for regime mismatch.
    pass  # Mercury 2 frozen — no scoring impact

    # Q13. STREAK MOMENTUM FILTER — autocorrelation lag-1 = +0.273
    # Rationale: Wins cluster (2,000-pick analysis). After 2 consecutive wins
    # for a strategy, next-pick WR rises ~10pp. Reward hot streaks, penalise cold.
    _streak = _STREAK_CACHE.get(strategy, 0)
    if _streak >= 3:
        score += 12
        penalties.append("streak_momentum:3+_consec_wins:+12")
    elif _streak >= 2:
        score += 8
        penalties.append("streak_momentum:2_consec_wins:+8")
    elif _streak <= -3:
        score -= 8
        penalties.append("cold_streak:3+_consec_losses:-8")

    # Q14. DIRECTION-SPECIFIC LOSER PENALTY
    # Some strategies win in one direction but lose in the other.
    # Data: rsi_overbought is 76% WR overall but only 29% on SHORTs.
    _strat_l = str(pick.get("strategy", pick.get("source", "")) or "").lower()
    _dir_up = str(pick.get("direction", "") or "").upper()
    for (ds_strat, ds_dir), ds_penalty in DIRECTION_SPECIFIC_LOSERS.items():
        if ds_strat.lower() in _strat_l and ds_dir == _dir_up:
            score += ds_penalty
            penalties.append(f"dir_specific_loser({ds_strat}+{ds_dir}):{ds_penalty}")
            break

    # Q15. VOL-OF-VOL FILTER (+0.27 Sharpe) — re-applied after rebase loss
    _atr_current = _float(pick.get("atr_14") or pick.get("atr") or 0)
    _atr_90p75 = _float(pick.get("atr_90d_p75") or 0)
    _fgi_q15 = _float(pick.get("fear_greed") or pick.get("fgi") or 50)
    if _atr_current > 0 and _atr_90p75 > 0 and _fgi_q15 >= 15:
        if _atr_current > _atr_90p75:
            score -= 10
            penalties.append(
                f"vol_of_vol(atr={_atr_current:.4f}>p75={_atr_90p75:.4f}):-10"
            )

    # Q16. EMBEDDED CARRY FILTER (+0.55 Sharpe) — re-applied after rebase loss
    _funding = _float(pick.get("funding_rate") or 0)
    if _funding != 0 and 15 <= _fgi_q15 <= 85:
        if direction in ("LONG", "BUY") and _funding > 0.0025:
            score -= 12
            penalties.append(f"carry_filter_long(funding={_funding:.4f}):-12")
        elif direction in ("SHORT", "SELL") and _funding < -0.0025:
            score -= 12
            penalties.append(f"carry_filter_short(funding={_funding:.4f}):-12")
        elif direction in ("LONG", "BUY") and _funding < -0.0008:
            score += 5
            penalties.append(f"carry_tailwind_long(funding={_funding:.4f}):+5")

    # HARD CAP: verified kill+failing picks cannot reach smart gate threshold.
    # When _killed_strategy=True (set by dashboard_generator from core_whitelist.json)
    # AND walk-forward confirms the strategy is FAILING/REJECTED/BROKEN, the source/
    # strategy static bonuses (+18, +15) must not override the live failure evidence.
    # Cap at 59 so the pick stays in active display (floor=40) but never hits smart
    # picks (Smart min=60). This prevents the 120-cap exploit seen on enhanced_ml_A_xgboost.
    # Data: 16 picks scored 120 from kills+failing strategies in stale payload (2026-04-05).
    if pick.get("_killed_strategy") and wf_verdict in {"FAILING", "REJECTED", "BROKEN"}:
        if score > 59.0:
            penalties.append(
                f"killed_failing_cap(was_{score:.0f}->59):-{score - 59:.0f}"
            )
            score = 59.0

    # ── REALIZED OUTPERFORMANCE RECLAIM (2026-04-05) ──
    # A pick that is ACTUALLY making money deserves to be ranked by its
    # market evidence, not by pre-trade penalties that have been disproven
    # by live P&L. Example caught by user: APEUSDT SHORT at score=0 but
    # +6.02% PnL after 40h — triple-counted concentration + stale penalties
    # zeroed out the score despite the pick being correct.
    #
    # Gates:
    #   - age_hours >= 1.0 prevents new-pick luck inflation
    #   - pnl_pct >= 2.0 prevents noise
    # Scales +2% -> +10, +5% -> +20, +10% -> +30 (capped)
    # Symmetric penalty for realized underperformance at pnl <= -3.0%
    _age_h = _float(pick.get("age_hours") or 0)
    _pnl_pct = _float(pick.get("pnl_pct") or pick.get("unrealized_pnl_pct") or 0)
    if _age_h >= 1.0 and _pnl_pct >= 2.0:
        _reclaim = min(30, int(10 + (_pnl_pct - 2.0) * 2))
        score += _reclaim
        penalties.append(
            f"realized_outperformance(+{_pnl_pct:.1f}%/{_age_h:.0f}h):+{_reclaim}"
        )
    elif _age_h >= 1.0 and _pnl_pct <= -3.0:
        _drain = min(20, int(2 + abs(_pnl_pct + 3.0) * 1.5))
        score -= _drain
        penalties.append(f"realized_underperformance({_pnl_pct:.1f}%):-{_drain}")

    # ── PREFERRED PAIR BONUS (HF-P0 ┬º2.4) ──
    # Whitelisted combos from cross_asset_edge_finder_results.json (Sharpe>=1.8).
    # Rewards empirically vetted (asset_class, strategy, symbol) combos without unbanning
    # whole strategies. +10 matches existing conf_peak/sweet_spot magnitude.
    if _matches_preferred_pair(pick):
        score += PREFERRED_PAIR_BONUS
        penalties.append(f"preferred_pair_edge:+{PREFERRED_PAIR_BONUS}")

    # ── CROSS-ASSET CONFLUENCE BONUS (HF-┬ºextra) ──
    # When the same underlying asset has aligned directional signals from 2+ different
    # asset classes (e.g., BTCUSDT LONG + BITO LONG + BTC1! LONG), apply +8 bonus.
    # _cross_asset_confluence is stamped by _compute_cross_asset_confluence() upstream.
    # Idempotency guard: only apply bonus once per pick, tracked via _cross_asset_bonus_applied.
    _confluence_n = pick.get("_cross_asset_confluence")
    if (
        _confluence_n
        and int(_confluence_n) >= 2
        and not pick.get("_cross_asset_bonus_applied")
    ):
        score += CROSS_ASSET_CONFLUENCE_BONUS
        pick["_cross_asset_bonus_applied"] = True
        penalties.append(
            f"cross_asset_confluence(n={int(_confluence_n)}):+{CROSS_ASSET_CONFLUENCE_BONUS}"
        )



    # Reduce correlated over-stacking so one row is not annihilated by multiple
    # confidence/direction toxic penalties that represent the same failure mode.
    _correlated_markers = (
        "long_overconf_combo",
        "direction_conflict",
        "confidence_trap",
        "conf_overconfident",
        "conf_extreme_overconfident",
        "toxic_combo",
    )
    _correlated_total = 0.0
    for _entry in penalties:
        if not any(_entry.startswith(_m) for _m in _correlated_markers):
            continue
        _m = re.search(r":([+-]?\d+(?:\.\d+)?)$", _entry)
        if not _m:
            continue
        _adj = _float(_m.group(1))
        if _adj < 0:
            _correlated_total += _adj
    if _correlated_total < -25.0:
        _rebate = round(-25.0 - _correlated_total, 1)
        score += _rebate
        penalties.append(f"correlated_penalty_cap:+{_rebate:.1f}")

    # Clamp to 0-120 (scores above 100 = SUPER_PICK — rare, high-conviction)
    score = max(0.0, min(120.0, score))

    # ── SUPER_PICK QUALIFICATION GATE (2026-04-05) ──
    # Previously the 100+ threshold was advisory only. Ml_crypto_pred flood of 14 picks
    # at score=120 with trust=5 and conf=0.78 exposed the gap. Now enforcing a real cap:
    # only picks meeting ALL super criteria can hold scores above 100; others capped at 100.
    # Super requirements: trust>=6, proven strategy track record, conf in sweet spot (0.65-0.84).
    if score > 100:
        _trust_val = _float(pick.get("trust_score") or pick.get("trust") or 0)
        _strat_lower = (strategy or "").lower()
        _qualifies = (
            _trust_val >= 6.0
            and conf >= 0.65
            and conf < 0.85
            and strat_fwd_wr >= 0.55
            and strat_fwd_trades >= 15
        )
        if not _qualifies:
            _old = score
            score = 100.0
            _reasons = []
            if _trust_val < 6.0:
                _reasons.append(f"trust={_trust_val:.0f}<6")
            if conf < 0.65 or conf >= 0.85:
                _reasons.append(f"conf={conf:.2f}_outside_sweet_spot")
            if strat_fwd_wr < 0.55 or strat_fwd_trades < 15:
                _reasons.append(
                    f"unproven_wr={strat_fwd_wr:.0%}_n={strat_fwd_trades:.0f}"
                )
            penalties.append(
                f"super_cap(was_{_old:.0f}->100,{'/'.join(_reasons)}):-{_old - 100:.0f}"
            )

    # ── SUPER_PICK DESIGNATION ──
    # Scores above 100 are extremely rare — every signal must align.
    # These are "once in a blue moon" trades with the highest historical probability.
    # Requirements: score > 100 AND proven strategy AND tight R:R AND high confidence
    is_super = False
    if score > 100:
        is_super = True
        pick["super_pick"] = True
        pick["super_pick_score"] = round(score, 1)
        penalties.append(f"SUPER_PICK(score={score:.0f})")
    elif score >= 85:
        # Near-super: all signals aligned but just below threshold
        # Check if it hits the golden combo: SHORT + highConf + tightRR = 80% WR
        if (
            direction in ("SHORT", "SELL")
            and conf >= 0.70
            and 0 < rr <= 1.5
            and strat_fwd_wr >= 0.55
            and strat_fwd_trades >= 10
        ):
            is_super = True
            score = min(score + 10, 120.0)
            pick["super_pick"] = True
            pick["super_pick_score"] = round(score, 1)
            penalties.append("SUPER_PICK(golden_combo_boost)")

    # ── SAFETY TAG ──
    # Based on historical WR of this strategy+symbol+direction combo.
    # "SAFE" = strategy has >65% WR on this symbol in this direction on 5+ trades.
    # Displayed as a tooltip badge on the dashboard.
    _safety = "UNKNOWN"
    _safety_reason = ""
    _sym_track_wr_val = _float(sym_track_wr) if sym_track_wr is not None else 0
    _sym_track_n = sym_track_total

    if _sym_track_n >= 10 and _sym_track_wr_val >= 70:
        _safety = "SAFE"
        _safety_reason = (
            f"Strategy WR {_sym_track_wr_val:.0f}% on {_sym} over {_sym_track_n} trades"
        )
    elif _sym_track_n >= 5 and _sym_track_wr_val >= 65:
        _safety = "SAFE"
        _safety_reason = (
            f"Strategy WR {_sym_track_wr_val:.0f}% on {_sym} over {_sym_track_n} trades"
        )
    elif strat_fwd_wr >= 0.65 and strat_fwd_trades >= 15:
        _safety = "SAFE"
        _safety_reason = (
            f"Strategy overall WR {strat_fwd_wr:.0%} over {strat_fwd_trades:.0f} trades"
        )
    elif strat_fwd_wr >= 0.55 and strat_fwd_trades >= 20:
        _safety = "LIKELY"
        _safety_reason = (
            f"Strategy WR {strat_fwd_wr:.0%} over {strat_fwd_trades:.0f} trades"
        )
    elif _sym_track_n >= 5 and _sym_track_wr_val < 40:
        _safety = "RISKY"
        _safety_reason = (
            f"Strategy WR {_sym_track_wr_val:.0f}% on {_sym} — poor history"
        )
    elif strat_fwd_wr > 0 and strat_fwd_wr < 0.35 and strat_fwd_trades >= 10:
        _safety = "RISKY"
        _safety_reason = f"Strategy WR {strat_fwd_wr:.0%} overall — low confidence"

    pick["safety"] = _safety
    pick["safety_reason"] = _safety_reason
    if _safety == "SAFE":
        penalties.append(f"safety_SAFE:{_safety_reason[:40]}")
    elif _safety == "RISKY":
        penalties.append(f"safety_RISKY:{_safety_reason[:40]}")

    # Write back
    pick["score"] = round(score, 1)
    pick["_penalties"] = penalties


# ── DATA-DRIVEN LOOKUP TABLES (from closed-pick analysis of 2,256 trades) ──

# ── FORWARD-TEST VIABLE STRATEGIES (2026-04-10 audit) ──
# Only 5 of 23 strategies passed forward testing with correlation > 0.45
# These strategies should receive scoring bonuses (defined early for reference)
# Populated dynamically from forward_test_results.json in production
_VIABLE_STRATEGIES_FORWARD = {
    "funding_rate_arbitrage": 20,      # Grade A, 0.92 correlation
    "pairs_trading_cointegration": 18, # Grade A-, 0.85 correlation
    "betting_against_beta": 18,        # Grade A-, 0.78 correlation
    "flash_crash_reversal": 15,        # Grade B+, 0.45 correlation
    "quality_minus_junk": 15,          # Grade B+, 0.82 correlation
    "commodity_cot_contrarian": 18,    # CFTC non-commercial contrarian; institutional COT edge
    "cftc_cot_commercial_signal": 20,  # CFTC commercial signal, PF 3.5 documented
    "multi_asset_cot": 18,             # COT source; externally validated
}

# Non-viable strategies that should be demoted (correlation < 0.4)
_DEMOTED_STRATEGIES_FORWARD = {
    # Add strategies with poor forward correlation here
    # These will receive -25 score penalty in _apply_score_penalties
}

# Per-asset-class source overrides — net delta applied ON TOP of _SOURCE_SYSTEM_SCORES.
# Use when a source has proven edge in one class but drag in another.
# Format: {(asset_class_upper, source_system_lower): delta}
# Evidence threshold: n >= 30, WR >= 60% post-resolver-v2 for a positive delta.
_SOURCE_ASSET_CLASS_OVERRIDES: dict[tuple[str, str], int] = {
    # 2026-05-16 COMMODITY swarm deep-dive: multi_asset_copytrader COMMODITY n=96 WR=93.8%
    # was PRE-DEDUP artifact (46x over-emission on CT=F cotton). Post-dedup: WR=40%, PF=0.17.
    # Also emits ZW=F/ZS=F (blacklisted grains) bypassing blacklist check. REMOVED +30 boost.
    # ("COMMODITY", "multi_asset_copytrader"): 30,  # REMOVED — pre-dedup artifact
    # multi_asset_cot: COMMODITY COT PF=20.54 was pre-dedup artifact (see multi_asset_cot audit).
    # Post-dedup after COT_DEDUP_GATE: PF=0.17, WR=40%. REMOVED +20 boost.
    # ("COMMODITY", "multi_asset_cot"): 20,  # REMOVED — pre-dedup artifact
    # commodity_cot_contrarian: proven edge (COT commercial signal, CFTC data-backed).
    # Not in global dict. Provide positive routing weight.
    ("COMMODITY", "commodity_cot_contrarian"): 18,
    # cta_replicator: global=-10; COMMODITY CTA momentum is academically validated.
    # Delta = +15 → net = +5 for COMMODITY. Conservative given thin live sample.
    ("COMMODITY", "cta_replicator"): 15,
    # multi_asset_scanner: global=-25 (16.9% WR overall, n=71 across all classes).
    # BUT EQUITY system WR=52.7% PF=1.41 post-resolver-v2 (CLAUDE.md 2026-05-03).
    # The global -25 was calibrated on a cross-class pool dominated by forex/commodity.
    # EQUITY-specific override: +25 delta → net=0 for EQUITY (neutral routing weight).
    # Rationale: EQUITY picks start at base=50-25=-25 pre-override → max ~30 final score,
    # never clearing the 40 floor. Net=0 restores EQUITY to neutral (base=50), letting
    # picks be judged on per-pick signals (R:R, confidence, geometry) not source drag.
    # Evidence: EQUITY closed n=421, WR=52.7% — adequate quality at class level.
    # Tighten back if EQUITY WR drops below 48% on next quarterly audit.
    ("EQUITY", "multi_asset_scanner"): 25,
    # ETF: same rationale as EQUITY. ETF closed n=87, WR=55.2%, PF=1.24.
    # multi_asset_scanner ETF picks score base=50-25=25; floor=35; 0 pass.
    # +20 delta → net=-5 for ETF: base=45, allows picks that clear per-pick tests.
    ("ETF", "multi_asset_scanner"): 20,
    # FUTURES multi_asset_copytrader: global=-10 but copper/platinum picks have genuine
    # momentum signal. HG=F pick: elite_score=25, source=-10 → base ~15, floor=20 (new).
    # Delta +15 → net=+5 for FUTURES: source contribution becomes neutral-positive.
    # Allows copper/platinum futures picks to clear the FUTURES floor of 20.
    ("FUTURES", "multi_asset_copytrader"): 15,
    # FUTURES probation penalty (-20 for forward_test_only+no_sample) is harsh for
    # copper/platinum which are newly admitted symbols. Add offset via multi_asset_cot.
    ("FUTURES", "multi_asset_cot"): 15,
    # --- EQUITY source boosts (2026-05-16, swarm deep-dive) ---
    # signal_validation EQUITY WR=59.5%, MomentumEMA=69.1% WR n=55 — raised +5→+10.
    ("EQUITY", "signal_validation"): 10,
    # kimi_riseoftheclaw EQUITY: rs-breakout WR=75% n=36, donchian-stock WR=78.6% n=14,
    # vol-contraction WR=64.7% n=17. Global +15 mixed with crypto; EQUITY-specific +8 delta.
    ("EQUITY", "kimi_riseoftheclaw"): 8,
    # super_signals EQUITY: picks are mislabeled CRYPTO (ZROUSDT, TIAUSDT, CHZUSDT).
    # These are killing EQUITY WR — strong penalize to route them out.
    ("EQUITY", "super_signals"): -20,
    # --- FOREX source penalties (2026-05-15 autopsy: reports/forex_mutation_autopsy_20260515.md) ---
    # multi_asset_scanner FOREX: WR=0%, n=11 — 0 wins in 11 picks. Net global+class = -50,
    # well below FOREX floor=60. Prevents scanner-routed FOREX picks from scoring through.
    ("FOREX", "multi_asset_scanner"): -25,
    # kimi_riseoftheclaw FOREX: WR=37.5%, n=56 — largest volume drag on FOREX class PF.
    ("FOREX", "kimi_riseoftheclaw"): -12,
    # alpha_engine FOREX: WR=29.2%, n=24 — consistent underperformer for this class.
    ("FOREX", "alpha_engine"): -8,
}

# Source systems ranked by historical WR and avg PnL
_SOURCE_SYSTEM_SCORES = {
    # Proven winners (>50% WR, positive PnL, 10+ trades)
    "revival_all": 20,  # 97.8% WR, +2.33% avg PnL
    "ml_crypto_pred": 5,  # DOWNGRADED 18->5 (2026-04-05): live audit 20% green, ejaguiar1 backtest
    # 31.3% WR on LONG. Historical 76.2% WR is stale/overfit.
    # Rolling 7d degradation -28 also applies = effectively negative.
    "kimi_signal_tracking": 12,  # 50.9% WR, +1.67% avg PnL
    "signal_validation": 10,  # 56.6% WR, +0.86% avg PnL
    "ml_crypto_pred_v12": -5,  # DOWNGRADED 5->-5: BLOCKED_SOURCE_SYSTEMS already bans it.
    # Multi-source / consensus
    "prediction_market_consensus": 14,  # UPGRADED 10->14 per claude-paper-tv (2/2 correct today, direct probability > derived)
    "polymarket_signals": 14,  # NEW: claude-paper-tv d252a77925 (2026-04-05)
    "pm_whale_signals": 10,  # NEW: per claude-paper-tv (PM whale intelligence)
    "cross_aggregation": 8,
    # 2026-04-05: Closed-pick analysis on 3017 trades reveals source skew
    "claude_gainer_st": 15,  # UPGRADED 10->15: W:L 2.05x, XRP 73% WR (35/48), drives 3 TV winners today
    "stocks_competition": 15,  # ELITE EQUITY (79.2% WR, PF 3.76, audit 2026-04-05)
    # 2026-05-09: DOWNGRADED 5 → -10 per swarm 4/4 + 3-axis autopsy.
    # 30d (2026-04-09 → 2026-05-09): n=1620, PF 1.00, sum +0.0 — "noise generator,
    # not loss generator." Per docs/MUTATION_THREE_AXIS_PROTOCOL.md autopsy:
    #   DIRECTION: LONG WR 47.8% +2.8 sum, SHORT WR 49.8% -4.5 sum (no flip>5pp)
    #   CATEGORY:  forex 50.8% -1.7, commodity 44.5% 0, equity 50% 0 — all flat
    #   STRATEGY:  no n>=30 path with PF>=1.2; futures_momentum (n=520, 44%, sum 0)
    #              dominant variant is breakeven; cftc_cot_commercial_signal high
    #              WR but small wins / big losses asymmetry
    # The "ELITE FOREX 55.7% WR PF 2.17" 2026-04-05 audit is stale — system has
    # decayed to flat. Penalty downsizes routing weight; not added to BLOCKED_
    # SOURCE_SYSTEMS yet (per mutate-before-kill protocol — kill only after a
    # 30d -PF window). RE-EVALUATE 2026-06-09. Refs: swarm_runs/next_steps_perf_
    # 2026-05-09/, reports/db_query_bank_2026-05-07/FINDINGS.md.
    "multi_asset_copytrader": -10,
    # 2026-05-14: DOWNGRADED 12→-20 per swarm master synthesis (3-engine consensus).
    # Live audit: PF=0.14, WR=42.9%, pnl=-11.67%. Old "67% WR" comment was stale
    # sector analysis, not live post-resolver-v2 data. Source already in
    # BLOCKED_ASSET_STRATEGY_PAIRS for EQUITY; score correction eliminates any
    # residual routing weight for other classes.
    "goldmine_stocks": -20,
    "alpha_engine": -8,  # INCREASED PENALTY -5->-8: 36.4% WR LONG (claude-paper-tv live validation),
    # ejaguiar1 backtest -161K cum. Only SHORT side has edge (66.7% WR n=9).
    # NEW SOURCES from today's TV winners (2026-04-05 lessons learned)
    "tsmom_strategy": 8,  # NEW: KITE SHORT won on ALL 5 books (+2.24 to +8.6%). tsmom_volscaled
    # produced leveraged-inverse-alt SHORTs that captured regime-driven decay.
    # 2026-05-09: UPSIZED 8 → 15 per swarm 4/4 + 30d data.
    # n=107, WR 68.2%, PF 2.92, sum +418.2% — top alpha source by sum_pnl. Volume
    # is criminally underweight (107 trades vs luxalgo_filters 746). Higher score
    # → routing prioritizes battleground signals first.
    # 2026-05-16: DOWNGRADED +15→+5: scm n=151, PF=1.05 (decayed from PF 2.92 in May-09 snapshot).
    # 164.7% concentration in BTCUSDT; ex-BTCUSDT pnl=-2.3%. Concentration risk HIGH.
    "battleground": 5,
    # 2026-05-09: NEW source — top alpha by sum_pnl 30d.
    # n=151, WR 67.5%, PF 3.45, sum +383.3%. Was missing from _SOURCE_SYSTEM_SCORES
    # so picks router treated as default-0. Adding +15 weight.
    "mega_mutation": 15,
    # 2026-05-09: NEW source distinct from blocked mercury2_fast.
    # n=74, WR 16.2%, PF 2.34, sum +116.5% — paradoxical low WR + high PF =
    # asymmetric wins (few big wins outweigh many small losses). Worth +12.
    # 2026-05-15: DOWNGRADED +12→0. Live audit n=144, WR=38.2%, avg_pnl=+0.15%.
    # Low WR despite positive avg_pnl (asymmetric wins) — neutral routing weight.
    # Original n=74 was too thin; n=144 is verdict-grade and shows WR well below 50%.
    "mercury2": 0,
    "contrarian_consensus": 8,  # NEW: BNBUSDT SHORT +3.96% (biggest single active winner, score was 0!)
    # 2026-05-15: NEW DRAG SOURCES identified from n=2891 CRYPTO closed audit.
    # copy_trader_highscore: n=99, WR=30.3%, avg_pnl=-0.23% — was not in dict (default 0).
    # Heavy WR drag: -22pp below system average. Adding penalty to reduce routing weight.
    "copy_trader_highscore": -18,
    # regime_terminal: n=65, WR=32.3%, avg_pnl=-0.05% — was not in dict (default 0).
    # Low WR across 65 CRYPTO trades. Adding penalty.
    "regime_terminal": -15,
    # Underperformers / Drains (penalty)
    # 2026-05-16 recalibration: claude_gainer now shows PF=2.23 WR=56.2% n=965 in verdict-grade
    # dashboard (post claude_gainer_st blacklist, 2026-05-01). The stale -50 was calibrated on
    # early ~10-pick data. With n=965 at T1-quality PF, the penalty actively suppresses good picks.
    # Resetting to +8 (conservative; matches aggregated_picks tier). Re-evaluate after 30-day tape.
    "claude_gainer": 8,   # 2026-05-16: PF=2.23 WR=56.2% n=965 (recalibrated from stale -50)
    "quan_engine": -15,  # 26.1% WR, -0.15% avg PnL, 962 picks. ejaguiar1 backtest confirms: 25% WR -45,611%
    "quan_engine_scalp": -15,  # Same system, dominant volume, drags everything down
    "rocket_scanner": -30,  # 0% WR on 5 live picks. BLOCKED_SOURCE_SYSTEMS already bans it.
    # 2026-04: Over-penalized source — luxalgo_confluence (64.4% WR) gets 0 source bonus
    # 2026-05-09: DOWNSIZED 10 → 5 per swarm 4/4 — volume vampire.
    # 2026-05-13: FURTHER DOWNSIZED 5 → -8 per live /audit recompute.
    # recent_closed verdict-grade window (n=3500, generated_at 2026-05-13T23:19Z):
    # CRYPTO luxalgo_filters n=665, WR 43.6%, PF 0.99, net_pnl -8.6pp.
    # Biggest-volume / smallest-edge pool by pp-loss in the entire system;
    # demote so the router prefers any other CRYPTO source over it.
    "luxalgo_filters": -8,
    # ── 2026-04-15: Missing source_system entries added (edge audit P1 fix) ──
    # 2026-05-16: DOWNGRADED mutation_lab +0→-15: scm n=22, PF=0.36, pnl=-18.6%. Loser.
    "mutation_lab": -15,
    # Proven winners
    "dna_rapid_fire_mutations": 0,  # DOWNGRADED +15→0: was n=10, WR=80% (thin). scm n=17, PF=1.03 (break-even).
    "signal_engine_mutations": 12,  # 63.6% WR, +0.96% avg PnL, n=11
    "super_signals": 8,  # 55.7% WR, +0.72% avg PnL, n=122
    "aggregated_picks": 8,  # RAISED 6->8: n=389, WR=77.6%, PF=6.90 (validate_resolved 2026-05-16).
    # AuditEnsemble_LONG n=105 WR=94.3%, VWAP Deviation n=35 WR=97.1%, Multi-TF n=76 WR=90.8%.
    # 2026-05-13: UPSIZED 4 → 15 per live /audit recompute. recent_closed
    # verdict-grade window shows kimi_riseoftheclaw is the platform's quiet
    # multi-class hero, top contributor by net pnl across 3 classes:
    #   EQUITY n=206, WR 56.8%, PF 2.09, net +335pp  ← #1 platform contributor
    #   CRYPTO n=94,  WR 58.1%, PF 1.70, net +108pp
    #   ETF    n=95,  WR 56.8%, PF 1.51, net +47.5pp
    # Old 2026-04-15 comment ("44.7% WR, +0.30% avg PnL, n=273, marginal edge")
    # was based on a different sample and is now stale; the live data
    # disagrees on WR (+12pp), PF (+1.4x), and net pnl per trade by 4-7x.
    "kimi_riseoftheclaw": 15,
    "baby_strats_forward": 2,  # 44.4% WR, +0.01% avg PnL, n=162 (huge volume, flat)
    "dna_winner_picks": 2,  # 41.7% WR, +0.14% avg PnL, n=24
    # Proven losers
    "rapid_fire": -5,  # 40.0% WR, -0.59% avg PnL, n=35
    # 2026-05-09: DOWNGRADED -5 → -15 per Q14 (PR #862 DB query bank).
    # 30d updated: PF 0.16 / WR 38.50% / n=200 — major drag, not "flat" per
    # stale 2026-04-15 audit (n=18). Stale comment was the bug.
    "non_crypto_consensus": -15,
    "alpha_engine_fast": -10,  # 39.5% WR, -0.14% avg PnL, n=81
    "cta_replicator": -10,  # 34.0% WR, -0.04% avg PnL, n=50
    "multi_asset_institutional": -15,  # 33.3% WR, -2.23% avg PnL, n=18
    "multi_asset_scanner": -25,  # 16.9% WR, -0.14% avg PnL, n=71
}

# Individual strategies with proven track records
_STRATEGY_SCORES = {
    "enhanced_ml_a_xgboost": -10,  # DOWNGRADED 15->-10 (2026-04-05): 30.2% WR closed, PF 0.65,
    # ejaguiar1 backtest -77K cum on ema9_pullback variant, live 20% green.
    # Rolling 7d degradation -32 also applies. Historical 70.5% WR is stale.
    "st_fear_greed_contrarian": 20,  # UPGRADED 12->20: CROWN JEWEL. 7 of 13 SHARP TOOLS, ejaguiar1 backtest
    # confirms across LTCUSDT(96%WR), BNBUSDT(93%), XRPUSDT(82%), DOTUSDT(77%).
    # Today's TV: drove AVAX+ADA+UNI wins. 524 closed trades, 62% WR.
    # BUG: currently scored at 5 due to score_booster regression (P0 open).
    "copy_hl_whale_24.5m": 12,  # 68.8% WR, +1.44% avg PnL, n=32
    "keltner_compression_expansion": 12,  # UPGRADED 10->12: ejaguiar1 backtest +1,196% cum (149 trades, 64% WR).
    # ETH variant 71% WR +571%. sol variant 58% WR +599%.
    "drawdown_recovery_rsi": 12,  # NEW: drove BTC+XRP+ETH LONG winners today. Dashboard 80% WR on XRP.
    # drawdown_recovery_rsi_eth 61% WR 137 trades +378% in ejaguiar1.
    "justin_breakout_volume_v2": 18,  # NEW: ejaguiar1 KING — 3,550 trades, 74% WR, +8,278% cumulative.
    # TRXUSDT SHORT 79% WR +6,221%. Multi-symbol consistent edge.
    "multi_period_rsi_confluence": 12,  # NEW: ejaguiar1 72% WR 173 trades +401% on BTCUSDT LONG.
    "tsmom_volscaled": 10,  # NEW: KITE SHORT winner on all 5 TV books today (+2-8% each).
    # Leveraged-inverse-alt SHORTs during weak-alt regime.
    "vwap_deviation_reversion": 10,  # NEW: ejaguiar1 62% WR +777% (volfilter variant).
    "st_rsi_vol_bounce": 10,  # NEW: UNIUSDT LONG 92% WR (n=13) per SHARP_TOOLS.
    "irb_hoffman": 8,  # NEW: ejaguiar1 45% WR but +6.04% avg PnL, +664% cum (high avg win).
    "autocorrelation_exploiter": 8,  # NEW: ejaguiar1 100% WR n=30, +12.19% avg. Small sample caveat.
    "momentumema": 8,  # 63.2% WR, +1.06% avg PnL
    "rsi2_bb_squeeze": 8,  # 52.4% WR, +0.010% (only profitable scalp)
    "meanreversionbb": 6,  # 54.4% WR, +0.80% avg PnL
    # 2026-04: Over-penalized winners identified by score-vs-PnL anomaly analysis
    "luxalgo_confluence": 15,  # 64.4% WR, 90 trades, +120.8% cumPnL, avgScore was 37.8
    "strong consensus": 10,  # 56.3% WR, 103 trades, +61.5% cumPnL
    "bollinger mr": 10,  # 53.8% WR, 80 trades, +59.7% cumPnL (source: stocks_competition)
    "stocks_rsi2_pullback": 8,  # 90.0% WR, 10 trades, +12.9% cumPnL
    "donchian-stock-breakout": 8,  # 80.0% WR, 5 trades, +33.3% cumPnL (small n)
    # 2026-05-16 swarm EQUITY deep-dive — kimi_riseoftheclaw EQUITY stars missing from dict:
    "ema-ribbon-momentum-scout": 12,  # n=15, WR=73.3%, PnL=+31.6%
    "vol-contraction-scout": 10,      # n=17, WR=64.7%, PnL=+44.0%
    "price-accel-scout": 10,          # n=16, WR=62.5%, PnL=+46.7%
    "gap-and-go-stocks": 8,           # n=9, WR=66.7%, PnL=+57.1% (small n, caution)
    # kimi EQUITY losers — penalize:
    "skyrocket-breakout-scalper": -15,  # n=14, WR=28.6%, PnL=-7.0%
    "ema-ribbon": -15,                  # n=5, WR=20.0%, PnL=-9.7%
    "pairs-trading": -12,               # n=5, WR=20.0%, PnL=-4.1%
        "macd_rsi_confluence": 6,  # 58.3% WR, 12 trades, +8.2% cumPnL
    # ── 2026-04-15: Missing strategy entries added (edge audit P1 fix) ──
    # Proven winners (WR >= 50% + positive PnL)
    "st_obv_support_divergence": 15,  # 70.8% WR, +1.22% avg PnL, n=72
    "markov_zone_transition": 15,  # 76.9% WR, +0.21% avg PnL, n=13
    "rs-breakout-scout": 14,  # 69.2% WR, +1.99% avg PnL, n=13
    "quality-minus-junk": 12,  # 63.6% WR, +0.68% avg PnL, n=22
    "vwap-reversion-scout": 12,  # 60.0% WR, +1.07% avg PnL, n=10
    "fx_smart_carry_trade_momentum": 12,  # 60.0% WR, +0.24% avg PnL, n=10
    "signal_engine_momentum_mut": 12,  # 63.6% WR, +0.96% avg PnL, n=11
    "crypto_mtf_ema_slope_alignment_v1": 12,  # 61.5% WR, +0.36% avg PnL, n=13
    "proven_vwap_mean_reversion": 10,  # 100% WR, +0.32% avg PnL, n=4 (exceptional WR)
    "rapid_momentum_filter_mut": 10,  # 75.0% WR, +1.58% avg PnL, n=8
    "strong consensus (alpha_engine, ml_crypto_pred)": 8,  # 56.3% WR, +0.60% avg PnL, n=103
    "rsi-divergence-scout": 8,  # 53.3% WR, +1.76% avg PnL, n=15
    "forex-rsi-ema-scout": 7,  # 57.1% WR, +0.32% avg PnL, n=14
    "post-earnings-rev-scout": 7,  # 58.3% WR, +0.46% avg PnL, n=12
    "meme-velocity": 6,  # 60.0% WR, +0.59% avg PnL, n=5
    "claude_ml_moderate_mut": 5,  # 50.0% WR, +0.39% avg PnL, n=14
    "breakout momentum": 4,  # 47.9% WR, +0.17% avg PnL, n=71
    "classic momentum": 4,  # 46.7% WR, +0.91% avg PnL, n=30
    "meta learner": 4,  # 46.7% WR, +0.83% avg PnL, n=15 (lowercase variant; 'Meta Learner' in killed)
    # Proven losers (WR < 40% + negative PnL)
    # 2026-05-09: DOWNGRADED -5 → -15 per Q14 (PR #862 DB query bank).
    # 30d updated: PF 0.16 / WR 38.50% / n=200 — major drag, not "flat" per
    # stale 2026-04-15 audit (n=18). Stale comment was the bug.
    "non_crypto_consensus": -15,
    "ema_stack_momentum": -15,  # 21.4% WR, n=14
    "carry-trade-momentum": -15,  # 26.7% WR, -0.14% avg PnL, n=15
    "dxy-reversal-scout": -15,  # 20.0% WR, -0.19% avg PnL, n=10
    "goldmine_1x_consensus": -15,  # 19.0% WR, -1.38% avg PnL, n=21 (crypto-blocked separately)
    "goldmine_3x_consensus": -15,  # 28.6% WR, -0.86% avg PnL, n=14
    "claude_gainer_1h": -20,  # 47.6% WR but -3.00% avg PnL, n=21 (huge tail losses)
    "community_london_breakout_v2_forex": -20,  # 0.0% WR, -0.50% avg PnL, n=16
    "betting-against-beta": -20,  # 23.1% WR, -1.08% avg PnL, n=13
    "call-surge-scout": -20,  # 16.7% WR, -2.09% avg PnL, n=12
    "quan_engine_swing": -25,  # 0.0% WR, -2.33% avg PnL, n=10
    "goldmine_2x_consensus": -25,  # 18.8% WR, -5.47% avg PnL, n=16
    "goldmine_4x_consensus": -25,  # 0.0% WR, -5.06% avg PnL, n=5
}

# Backtest-validated strategy bonuses (from 970-run backtest case study 2026-04-04)
# These strategies survived rigorous backtesting across multiple symbols/timeframes.
# Bonus is additive on top of any _STRATEGY_SCORES or _STRATEGY_FAMILY_SCORES match.
BACKTEST_VALIDATED_STRATEGIES = {
    "supertrend_vwma_confluence": 15,  # Sharpe 3.55, PF 2.00, 133 trades
    "short_only_contrarian": 12,  # Sharpe 3.36, PF 5.74
    "triple_confirmation": 12,  # Sharpe 2.87, PF 2.01, 82 trades
    "keltner_rsi2_squeeze": 10,  # Sharpe 2.62, PF 5.27
    "simplified_kimi_rsi2": 10,  # PF 2.17, simplified > complex
    "supertrend_optimized": 10,  # PF 4.99 (optimized params)
    "vwma_momentum_trend": 8,  # Sharpe 2.22, PF 2.18 (matches function name in proven_edge_strategies.py)
    "vwma_momentum": 8,  # Alias for legacy naming
}

# Strategy family patterns (partial match)
_STRATEGY_FAMILY_SCORES = {
    "enhanced_ml_": 10,  # ML enhanced family generally strong
    "copy_hl_whale": 8,  # Copy trader whale family
    "revival_": 8,  # Revival systems strong
    "quan_engine_scalp": -12,  # Scalp strategies underperform
}

# Symbol+Direction bonuses/penalties (data: 1000 closed dashboard picks, 2026-04-03)
# Updated 2026-04-04: KAS flip (+10), BTC/SOL/DOGE LONG degraded from recent 200 picks
SYMBOL_DIRECTION_BONUSES: Dict[tuple, int] = {
    ("LTCUSDT", "LONG"): 14,  # 92% WR, 13 trades
    ("AVAXUSDT", "LONG"): 12,  # 89% WR, 18 trades
    ("SEIUSDT", "LONG"): 11,  # 83% WR, 12 trades
    (
        "KASUSDT",
        "LONG",
    ): 10,  # FLIPPED: was -19 (12% WR overall) -> recent 13 trades 85% WR
    ("APTUSDT", "LONG"): 8,  # 76% WR, 29 trades
    ("BNBUSDT", "LONG"): 7,  # 73% WR, 22 trades
    ("XRPUSDT", "LONG"): 7,  # 72% WR, 18 trades
    ("UNIUSDT", "LONG"): 7,  # 71% WR, 28 trades
    ("HYPEUSDT", "LONG"): 6,  # 71% WR, 17 trades
    ("BTCUSDT", "SHORT"): 5,  # 55% WR, 62 trades
    ("XMR", "LONG"): -20,  # 0% WR, 23 trades
    ("TRXUSDT", "LONG"): -20,  # 8% WR, 25 trades
    ("ICPUSDT", "LONG"): -16,  # 17% WR, 23 trades
    ("SOLUSDT", "LONG"): -15,  # NEW: recent 1/10=10% WR -- severe degradation
    ("ONDOUSDT", "LONG"): -13,  # 24% WR, 21 trades
    ("BTCUSDT", "LONG"): -12,  # DEGRADED: recent 2/11=18% WR (was -5 at 38% overall)
    ("DOGEUSDT", "LONG"): -10,  # FLIPPED: was +13 (91% overall) -> recent 1/7=14% WR
}

# Strategy+Symbol combos with extreme edge (5+ trades)
STRATEGY_SYMBOL_BONUSES: Dict[tuple, int] = {
    ("st_fear_greed_contrarian", "AVAXUSDT"): 10,
    ("st_fear_greed_contrarian", "LTCUSDT"): 10,
    # NEARUSDT bonus REMOVED 2026-05-18: live WR=39.1% n=23 contradicts the +8 bonus.
    # Prior bonus was stale (based on earlier small-n window). Under monitoring.
    ("st_fear_greed_contrarian", "LINKUSDT"): 8,
    ("st_fear_greed_contrarian", "DOTUSDT"): 8,
    (
        "st_fear_greed_contrarian",
        "UNIUSDT",
    ): -15,  # STRENGTHENED: 0/4 WR, all SL/expired losses
    ("st_fear_greed_contrarian", "SOLUSDT"): -5,
    # OPUSDT penalty added 2026-05-18: n=20 WR=20% PnL=-14.04% (per mutation audit)
    ("st_fear_greed_contrarian", "OPUSDT"): -25,
    ("claude_gainer_1h", "XMR"): -25,
    ("enhanced_ml_A_xgboost", "TRXUSDT"): -20,
    ("quan_engine_scalp", "BTCUSDT"): -15,
    ("quan_engine_scalp", "KASUSDT"): -15,
    ("quan_engine_scalp", "ONDOUSDT"): -15,
    ("quan_engine_scalp", "ICPUSDT"): -15,
}

# Healthcare cluster + GS LONG-momentum blacklist (Phase 2-B, 2026-04-29)
# Per Phase 2-B EQUITY panel 9/9 UNANIMOUS systematic_sector_bias verdict
# (reports/HFPA_PHASE-2-findings-EQUITY-2026-04-29.md). Used by passes_active_gate
# to surgically reject LONG-momentum picks on these 4 symbols only — preserves
# SHORT exposure and non-momentum strategy types.
JNJ_HEALTHCARE_GS_LONG_MOMENTUM_BLACKLIST: frozenset = frozenset({
    "JNJ", "ABBV", "MRK", "GS",
})

# Strategy name tokens / exact strings that mark a momentum-flavored strategy.
# Both lower-case forms (config-file style) and exact strings observed in
# `strategy` field of recent_closed (e.g., "Classic Momentum", "Breakout Momentum")
# are included. _is_momentum_flavored() also does substring matching for tokens.
MOMENTUM_STRATEGY_FAMILIES: frozenset = frozenset({
    "classic_momentum", "breakout_momentum", "momentum",
    "donchian-stock-breakout", "rs-breakout-scout",
    "price-accel-scout", "vol-contraction-scout",
    "Classic Momentum", "Breakout Momentum",
})


def _is_momentum_flavored(strategy_name: str) -> bool:
    """Return True if strategy_name looks like a momentum/breakout strategy.

    Matches:
    - exact membership in MOMENTUM_STRATEGY_FAMILIES (case-insensitive),
    - substring tokens: 'momentum', 'breakout', 'accel', 'scout'.

    Used by the JNJ_HEALTHCARE_GS_LONG_MOMENTUM_BLACKLIST gate.
    """
    if not strategy_name:
        return False
    s = str(strategy_name).lower()
    if s in {x.lower() for x in MOMENTUM_STRATEGY_FAMILIES}:
        return True
    return any(token in s for token in ("momentum", "breakout", "accel", "scout"))


# T1-D proven-symbol score boosts (2026-04-15)
# Top 10 symbols with n >= 20 and WR >= 50% from closed ledger.
# Nudges picks on proven combos over Gate 1/2 thresholds without changing any floor.
# When a SYMBOL_DIRECTION_BONUS applies for the same symbol+direction, proven boost is skipped.
PROVEN_SYMBOL_BOOSTS: Dict[str, int] = {
    "BNBUSDT": +5,    # 83.9% WR, PF 12.70, n=31
    "CVX": +4,        # 72.4% WR, PF 2.25, n=29
    "XRPUSDT": +4,    # 69.4% WR, PF 4.43, n=36
    "OPUSDT": +3,     # 63.3% WR, PF 2.37, n=30
    "NEARUSDT": +3,   # 62.5% WR, PF 2.74, n=24
    "XOM": +3,        # 60.5% WR, PF 1.53, n=43
    "WLDUSDT": +3,    # 60.0% WR, PF 2.06, n=20
    "UNIUSDT": +2,    # 57.6% WR, PF 1.54, n=33
    "ARBUSDT": +2,    # 54.1% WR, PF 1.92, n=37
    "SOLUSDT": +2,    # 50.8% WR, PF 1.84, n=130
}


_DOW_GATE_ENABLED = os.environ.get("AUDIT_DOW_GATE", "0") == "1"

# 2026-05-11 SUPREME EDGE — day-of-week worst-day kill list per Kimi audit
# (reports/kimi_edge_audit_2026-05-11/day_of_week_performance.csv).
# CRYPTO: Monday avg -16.9% / Wednesday avg -13.9% (worst 2 days).
# MEMECOIN: Saturday avg -15.5%. Other classes: insufficient sample.
# Gate behavior: when AUDIT_DOW_GATE=1 env set + pick falls on worst day for
# its asset_class, require confidence>=0.70 normalized to pass. Default OFF.
_DOW_KILL = {
    "CRYPTO": {"Monday", "Wednesday"},
    "MEMECOIN": {"Saturday"},
}


def _passes_dow_gate(pick: Dict[str, Any]) -> bool:
    """SUPREME EDGE day-of-week gate (default OFF via AUDIT_DOW_GATE env)."""
    if not _DOW_GATE_ENABLED:
        return True
    asset_class = str(pick.get("asset_class", "") or "").upper().strip()
    kill_days = _DOW_KILL.get(asset_class)
    if not kill_days:
        return True
    # Derive day-of-week from created_at / timestamp
    try:
        ts = pick.get("created_at") or pick.get("timestamp") or ""
        if not ts:
            return True
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00").split("+")[0])
        dow = dt.strftime("%A")
    except Exception:
        return True
    if dow not in kill_days:
        return True
    # Worst-day pick — override only if confidence >= 0.70 normalized
    conf = _normalize_confidence(pick.get("confidence", 0))
    if conf < 0.70:
        logger.debug(f"DOW gate reject: {asset_class} {dow} conf={conf:.2f}")
        return False


# --- §15 DEDUP GATE: block picks with duplicate symbol+direction+strategy ---
# Addresses §15 trap #2: 352 dupe groups, BTCUSDT LONG = 565 simultaneous picks.
# This gate is applied at emission time (quality_gates), not just tagging (dashboard_generator).
_SEEN_PICK_KEYS: set = set()


def _dedup_gate_blocks(pick: Dict[str, Any], active_picks: Optional[List[Dict]] = None) -> Optional[str]:
    """Block picks that duplicate an already-active symbol+direction+strategy combo.
    
    Returns None if pass, or a reason string if blocked.
    """
    symbol = str(pick.get("symbol", "") or "").upper().strip()
    direction = str(pick.get("direction", "") or "").upper().strip()
    strategy = str(pick.get("strategy", "") or "").lower().strip()
    
    if not symbol or not direction:
        return None  # can't dedup without symbol+direction
    
    dedup_key = (symbol, direction, strategy)
    
    # Check against active picks if provided
    if active_picks:
        for active in active_picks:
            a_sym = str(active.get("symbol", "") or "").upper().strip()
            a_dir = str(active.get("direction", "") or "").upper().strip()
            a_str = str(active.get("strategy", "") or "").lower().strip()
            if (a_sym, a_dir, a_str) == dedup_key:
                return f"DEDUP: {symbol} {direction} {strategy} already active"
    
    # Check against seen keys (in-memory dedup for batch processing)
    if dedup_key in _SEEN_PICK_KEYS:
        return f"DEDUP: {symbol} {direction} {strategy} duplicate in batch"
    _SEEN_PICK_KEYS.add(dedup_key)
    
    return None
    return True


_PENNY_MEME_CLASSES = frozenset({"MEMECOIN", "PENNY_STOCK"})

# Per-class symbol kill list (2026-05-17). FOREX entries from the 2026-05-15
# mutation autopsy Axis 1 (reports/forex_mutation_autopsy_20260515.md):
# NZDUSD=X (16.7% WR / PF 0.32), EURJPY=X (PF 0.20), USDCHF=X (0 wins).
# These pairs drag class PF below 1 despite a 52% WR headline. Symbol-axis
# "pure mutation" companion to the FOREX directional gate.
BLOCKED_SYMBOLS_BY_CLASS: Dict[str, frozenset] = {
    # 2026-05-16: NZDUSD=X/EURJPY=X/USDCHF=X autopsy via FOREX mutation analysis
    # 2026-05-17: AUDUSD=X added — cta_replicator n=8 WR=0% PF=0.00
    "FOREX": frozenset({"NZDUSD=X", "EURJPY=X", "USDCHF=X", "AUDUSD=X"}),
}

# H-024b anti-carry FOREX LONG block (2026-05-18).
# H-024 harness (tools/hypothesis/h024_g10_carry_harness.py) confirmed:
#   AUDJPY=X LONG: n=95 WR=3%   GBPJPY=X LONG: n=94 WR=9%   CADJPY=X LONG: n=36 WR=3%
# (EURJPY=X already in BLOCKED_SYMBOLS_BY_CLASS — all-direction block.)
# SHORT side has insufficient data (n<10) — not blocked. Direction-specific.
# Kill-switch: FOREX_CARRY_LONG_GATE_ENABLED=0.
FOREX_CARRY_LONG_BLOCKED_SYMBOLS: frozenset = frozenset({
    "AUDJPY=X",   # n=95 WR=3%  carry unwind structural loser — H-024b
    "GBPJPY=X",   # n=94 WR=9%  carry unwind structural loser — H-024b
    "CADJPY=X",   # n=36 WR=3%  carry unwind structural loser — H-024b
})

# Source-system × symbol autopsy blocks (2026-05-17).
# cta_replicator COMMODITY losers per reports/FOREX_mutation_analysis_2026_05_17.md §Axis2:
#   CL=F: n=47, WR=19.1%, PF=0.39   NG=F: n=24, WR=0.0%   ZC=F: n=8, WR=0.0%
# Tunable via BLOCKED_SOURCE_SYMBOL_GATE_DISABLED=1.
BLOCKED_SOURCE_SYMBOL_PAIRS: frozenset = frozenset({
    ("cta_replicator", "CL=F"),
    ("cta_replicator", "NG=F"),
    ("cta_replicator", "ZC=F"),
})


def passes_forex_symbol_gate(pick: Dict[str, Any]) -> bool:
    """Return False for a FOREX pick on an autopsy-killed symbol.

    Kill-switch: ``FOREX_SYMBOL_GATE_ENABLED=0`` disables (returns True for
    everything). Default enabled. Case-insensitive on the symbol; only FOREX
    is affected — other classes always pass.

    H-024b (2026-05-18): additionally blocks LONG picks on high-carry JPY crosses
    (AUDJPY, GBPJPY, CADJPY) that show catastrophic WR (3-9%) from carry unwind.
    Kill-switch: ``FOREX_CARRY_LONG_GATE_ENABLED=0``.
    """
    import os as _os_fsg

    if (_os_fsg.environ.get("FOREX_SYMBOL_GATE_ENABLED", "1") or "1") in (
        "0", "false", "FALSE", "False"
    ):
        return True
    ac = str(pick.get("asset_class", "") or "").strip().upper()
    if ac != "FOREX":
        return True
    sym = str(pick.get("symbol", "") or "").strip().upper()
    if sym in BLOCKED_SYMBOLS_BY_CLASS.get("FOREX", frozenset()):
        return False
    # H-024b: block LONG direction on high-carry JPY cross pairs
    if (_os_fsg.environ.get("FOREX_CARRY_LONG_GATE_ENABLED", "1") or "1") not in (
        "0", "false", "FALSE", "False"
    ):
        direction = str(pick.get("direction", pick.get("side", "")) or "").upper()
        if direction in ("LONG", "BUY") and sym in FOREX_CARRY_LONG_BLOCKED_SYMBOLS:
            return False
    return True


def _get_forex_carry_yield(symbol: str) -> Optional[float]:
    """Return annualized carry-yield differential for a FOREX symbol.

    Looks up ``alpha_engine.config.FOREX_SYMBOLS`` (base - quote).
    Returns ``None`` if symbol is unknown or lookup fails.
    """
    try:
        from alpha_engine.config import FOREX_SYMBOLS as _fx_cfg
    except Exception:
        return None
    _sym = str(symbol or "").strip().upper()
    _meta = _fx_cfg.get(_sym)
    if not _meta:
        return None
    return float(_meta.get("carry_yield_diff", 0))


def _get_pick_ema20(pick: Dict[str, Any]) -> Optional[float]:
    """Extract EMA20 from a pick dict (top-level or nested in ``extra``)."""
    for key in ("ema_20", "ema20", "ema20_val"):
        val = pick.get(key)
        if val is not None:
            return float(val)
    _extra = pick.get("extra") or {}
    if isinstance(_extra, dict):
        for key in ("ema_20", "ema20", "ema20_val"):
            val = _extra.get(key)
            if val is not None:
                return float(val)
    return None


def evaluate_forex_carry_ema_filter(pick: Dict[str, Any]) -> Tuple[float, str]:
    """
    DRAFT — FOREX Carry + EMA Filter (2026-05-16).

    Applies only when ``asset_class == "FOREX"``.
    Checks two structural edge conditions:

    1. **Carry alignment** — the pick direction must match the positive
       interest-rate differential (long the high-yielder, short the low-yielder).
    2. **EMA trend alignment** — price must be on the "right" side of the
       20-period EMA (above for LONG, below for SHORT).

    Scoring:
      - Both fail  →  -20 penalty (``forex_carry_ema_both_fail``)
      - Carry only fails → -10 (``forex_carry_against``)
      - EMA only fails   → -10 (``forex_ema_misaligned``)
      - Either passes or data is missing → 0 / no penalty

    Kill-switch: ``FOREX_CARRY_EMA_FILTER_DISABLED=1`` (default OFF).
    When disabled the function always returns ``(0.0, "")``.

    .. note::
       This helper is **NOT YET WIRED** into ``_apply_score_penalties`` or
       ``passes_active_gate``. It is staged for integration after a live
       back-test confirms PF>1.0 / WR>45 / n>30 on the filtered subset.
    """
    import os as _os_cef

    if _os_cef.environ.get("FOREX_CARRY_EMA_FILTER_DISABLED", "0") == "1":
        return 0.0, ""

    _ac = str(pick.get("asset_class", "") or "").strip().upper()
    if _ac != "FOREX":
        return 0.0, ""

    _sym = str(pick.get("symbol", "") or "").strip().upper()
    _dir = str(pick.get("direction", pick.get("side", "")) or "").strip().upper()

    # We need a canonical direction to evaluate
    if _dir in ("LONG", "BUY"):
        _is_long = True
    elif _dir in ("SHORT", "SELL"):
        _is_long = False
    else:
        return 0.0, ""

    # ── Carry check ──
    _carry = _get_forex_carry_yield(_sym)
    _carry_ok: Optional[bool] = None
    if _carry is not None:
        _carry_ok = (_is_long and _carry > 0) or (not _is_long and _carry < 0)

    # ── EMA20 alignment check ──
    _price = _float(pick.get("entry_price") or pick.get("price") or pick.get("close") or 0)
    _ema20 = _get_pick_ema20(pick)
    _ema_ok: Optional[bool] = None
    if _price > 0 and _ema20 is not None and _ema20 > 0:
        _ema_ok = (_is_long and _price > _ema20) or (not _is_long and _price < _ema20)

    # ── Scoring ──
    # If we have neither signal, we can't penalize — fail-open.
    if _carry_ok is None and _ema_ok is None:
        return 0.0, ""

    _carry_fail = _carry_ok is False
    _ema_fail = _ema_ok is False

    if _carry_fail and _ema_fail:
        return -20.0, f"forex_carry_ema_both_fail(carry={_carry:+.2f},ema20={_ema20:.4f},price={_price:.4f}):-20"
    elif _carry_fail:
        return -10.0, f"forex_carry_against(carry={_carry:+.2f},dir={_dir}):-10"
    elif _ema_fail:
        return -10.0, f"forex_ema_misaligned(ema20={_ema20:.4f},price={_price:.4f},dir={_dir}):-10"

    return 0.0, ""


def passes_penny_meme_class_gate(pick: Dict[str, Any]) -> bool:
    """Class-wide penny/meme gate (2026-05-15).

    Returns False for any pick whose ``asset_class`` is MEMECOIN or
    PENNY_STOCK (case-insensitive). The repo previously had only
    strategy-PAIR blocks for MEMECOIN — ``PENNY_STOCK`` was entirely
    ungated, so any strategy emitting a penny-stock pick passed.

    Kill-switch: ``PENNY_MEME_CLASS_GATE_ENABLED=0`` disables the gate
    (returns True for everything). Default is enabled.
    """
    import os as _os_pmg

    enabled = (
        _os_pmg.environ.get("PENNY_MEME_CLASS_GATE_ENABLED", "1") or "1"
    ) not in ("0", "false", "FALSE", "False")
    if not enabled:
        return True
    ac = str(pick.get("asset_class", "") or "").strip().upper()
    return ac not in _PENNY_MEME_CLASSES


def passes_speculative_equity_gate(pick: Dict[str, Any]) -> bool:
    """Block production EQUITY picks on penny/meme/gap-risk symbols.

    EAGLE 2026-05-27: PENNY_STOCK/MEMECOIN classes are gated separately;
    this catches mis-tagged EQUITY rows on speculative tickers (GME, NIO, …).

    Kill-switch: ``EQUITY_SPECULATIVE_GATE_ENABLED=0``.
    """
    import os as _os_seg

    if (_os_seg.environ.get("EQUITY_SPECULATIVE_GATE_ENABLED", "1") or "1") in (
        "0", "false", "FALSE", "False"
    ):
        return True
    ac = str(pick.get("asset_class") or pick.get("category") or "").strip().upper()
    if ac != "EQUITY":
        return True
    sym = str(pick.get("symbol") or pick.get("ticker") or "").strip().upper()
    if not sym:
        return True
    try:
        from alpha_engine.config import is_research_only_speculative
        if is_research_only_speculative(sym):
            return False
    except ImportError:
        pass
    return True


def passes_vix_regime_active_gate(pick: Dict[str, Any]) -> bool:
    """VIX regime gate on active admission (EQUITY + ETF).

    Mirrors ``passes_smart_gate`` VIX sidecar so high-VIX picks never reach
    Active Picks. Default ON via ``VIX_REGIME_ACTIVE_GATE_ENABLED=1``.

    Kill-switch: ``VIX_REGIME_ACTIVE_GATE_ENABLED=0``.
    """
    import os as _os_vag

    if (_os_vag.environ.get("VIX_REGIME_ACTIVE_GATE_ENABLED", "1") or "1") in (
        "0", "false", "FALSE", "False"
    ):
        return True
    # ── 2026-05-28: per-class hard VIX gates (highest-evidence single filter per
    # TMX validation report — backtest PF 2.82→5.37 / MDD 24%→7.3% on 30 LC universe
    # 2015-2026 when EQUITY VIX<22 is enforced). ETF overlay uses VIX<25 (QW-2 in
    # the same report). Independent kill-switches:
    #   EQUITY_VIX_GATE_ENABLED — default ON, rejects EQUITY picks when VIX > 22.
    #   ETF_VIX_GATE_ENABLED    — default ON, rejects ETF picks when VIX > 25.
    # Fail-open on missing VIX (is_vix_above_threshold returns False when fetch
    # fails). Reject reason "equity_vix_gate_high_vix" surfaces in pick rationale.
    #
    # FREEZE-EXEMPTION DECLARATION (per swarm review 2026-05-28):
    # The thresholds 22.0 (EQUITY) and 25.0 (ETF) are *regime-gate parameters*, NOT
    # Smart Picks score floors. They are NOT members of the THRESHOLD_FREEZE set
    # (SMART_PICKS_MIN_SCORE / SMART_PICKS_MAX_CONFIDENCE / etc. — see the freeze
    # block at the top of this file, frozen through 2026-08-18). Adding/tuning
    # *regime* gates does not violate the freeze; the freeze constrains pick-score
    # admission thresholds only.
    try:
        from audit_trail.vix_regime_gate import is_vix_above_threshold as _vix_gt
        _ac_pcg = str(pick.get("asset_class", "") or "").strip().upper()
        _truthy_pcg = ("1", "true", "yes", "on", "t", "y")
        if _ac_pcg == "EQUITY":
            _eq_flag = (_os_vag.environ.get("EQUITY_VIX_GATE_ENABLED", "1") or "1").strip().lower()
            if _eq_flag in _truthy_pcg and _vix_gt(22.0):
                pick["_hf_quality_gate_reason"] = (
                    pick.get("_hf_quality_gate_reason") or "equity_vix_gate_high_vix"
                )
                logger.info(
                    "Pick rejected: equity_vix_gate_high_vix (symbol=%s VIX>22.0)",
                    pick.get("symbol", "?"),
                )
                return False
        elif _ac_pcg == "ETF":
            _etf_flag = (_os_vag.environ.get("ETF_VIX_GATE_ENABLED", "1") or "1").strip().lower()
            if _etf_flag in _truthy_pcg and _vix_gt(25.0):
                pick["_hf_quality_gate_reason"] = (
                    pick.get("_hf_quality_gate_reason") or "equity_vix_gate_high_vix"
                )
                logger.info(
                    "Pick rejected: equity_vix_gate_high_vix [ETF] (symbol=%s VIX>25.0)",
                    pick.get("symbol", "?"),
                )
                return False
    except ImportError:
        pass  # vix_regime_gate module unavailable — fail-open
    except Exception:
        pass  # fail-open on any unexpected error
    # Existing combined VIX+YC + legacy single-threshold equity gate (preserved
    # for backward compatibility — uses VIX_REGIME_GATE_ENABLED / YC_REGIME_GATE_ENABLED).
    try:
        from audit_trail.vix_regime_gate import (
            should_reject_combined as _vix_combined,
            should_reject_equity_pick as _vix_reject,
        )
        if _vix_combined(pick) or _vix_reject(pick):
            pick["_hf_quality_gate_reason"] = pick.get("_hf_quality_gate_reason") or "vix_regime_active"
            return False
    except ImportError:
        pass
    except Exception:
        pass  # fail-open
    return True
# Wires alpha_engine/meta_labeler.py into the production admission gate in
# SHADOW-LOG mode. This NEVER rejects a pick — it only computes P(win) via the
# meta-labeler heuristic/ML model, stamps the pick, and appends one line to a
# shadow log so we can measure what an enforcing gate WOULD do before flipping
# it on. Enforcement is a deliberate follow-up (see META_LABEL_GATE_ENFORCE).
META_LABEL_SHADOW_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "audit_dashboard", "data", "meta_label_shadow_log.json",
)
META_LABEL_DEFAULT_THRESHOLD = 0.55
# Module-level singleton so we don't rebuild/retrain the labeler per pick.
_META_LABELER_SINGLETON: Any = None
_META_LABELER_INIT_FAILED = False


def _get_meta_labeler() -> Any:
    """Lazily build a MetaLabeler. Returns None on any failure (fail-soft)."""
    global _META_LABELER_SINGLETON, _META_LABELER_INIT_FAILED
    if _META_LABELER_SINGLETON is not None:
        return _META_LABELER_SINGLETON
    if _META_LABELER_INIT_FAILED:
        return None
    try:
        from alpha_engine.meta_labeler import MetaLabeler
        labeler = MetaLabeler()
        # Try to load a pre-trained model; if absent, MetaLabeler.score_pick()
        # transparently falls back to its rule-based heuristic_score(). Either
        # way score_pick() returns a valid P(win) in [0, 1].
        try:
            labeler.load()
        except Exception:
            pass
        _META_LABELER_SINGLETON = labeler
        return labeler
    except Exception:
        _META_LABELER_INIT_FAILED = True
        return None


def meta_label_gate(pick: Dict[str, Any]) -> Dict[str, Any]:
    """
    A1 scaffold — meta-labeler SHADOW gate (NO enforcement).

    Computes P(win) for ``pick`` via the meta-labeler, stamps
    ``pick['_meta_label_pwin']`` and ``pick['_meta_label_verdict']``
    ('PASS' / 'WOULD_REJECT' vs the threshold), and appends one line to the
    shadow log JSON. It NEVER rejects: the return dict is informational only
    and callers MUST NOT use it to change a pass/fail outcome.

    Env vars:
      * META_LABEL_GATE=1          -> enable shadow mode (default OFF).
      * META_LABEL_THRESHOLD=0.55  -> verdict cutoff (default 0.55).
      * META_LABEL_GATE_ENFORCE=1  -> enforce mode; passes_active_gate() rejects
                                      picks with verdict==WOULD_REJECT.

    Fail-soft: any exception is swallowed and the pick is left untouched.

    Returns a dict: {enabled, pwin, verdict, threshold} (best-effort).
    """
    result: Dict[str, Any] = {
        "enabled": False, "pwin": None, "verdict": "SKIP",
        "threshold": META_LABEL_DEFAULT_THRESHOLD,
    }
    try:
        # Default OFF (opt-in shadow) — enable with META_LABEL_GATE=1. Never enforces.
        if os.environ.get("META_LABEL_GATE", "0") not in ("1", "true", "TRUE", "True"):
            return result
        result["enabled"] = True

        try:
            threshold = float(os.environ.get(
                "META_LABEL_THRESHOLD", str(META_LABEL_DEFAULT_THRESHOLD)))
        except (TypeError, ValueError):
            threshold = META_LABEL_DEFAULT_THRESHOLD
        result["threshold"] = threshold

        labeler = _get_meta_labeler()
        if labeler is None:
            return result  # fail-soft: labeler unavailable -> no-op

        pwin = float(labeler.score_pick(pick))
        verdict = "PASS" if pwin >= threshold else "WOULD_REJECT"
        result["pwin"] = round(pwin, 4)
        result["verdict"] = verdict

        # Stamp the pick (informational; does not influence the gate outcome).
        pick["_meta_label_pwin"] = round(pwin, 4)
        pick["_meta_label_verdict"] = verdict

        # Append one line to the shadow log (best-effort, fail-soft).
        try:
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "id": pick.get("id"),
                "symbol": pick.get("symbol"),
                "strategy": pick.get("strategy"),
                "asset_class": pick.get("asset_class"),
                "pwin": result["pwin"],
                "threshold": threshold,
                "verdict": verdict,
                "model": getattr(labeler, "model_type", "unknown"),
            }
            os.makedirs(os.path.dirname(META_LABEL_SHADOW_LOG_PATH), exist_ok=True)
            log_rows: List[Dict[str, Any]] = []
            if os.path.exists(META_LABEL_SHADOW_LOG_PATH):
                try:
                    with open(META_LABEL_SHADOW_LOG_PATH, "r", encoding="utf-8") as _f:
                        loaded = json.load(_f)
                    if isinstance(loaded, list):
                        log_rows = loaded
                except Exception:
                    log_rows = []  # corrupt log -> start fresh, never raise
            log_rows.append(entry)
            # Cap the log so it can't grow unbounded on a hot path.
            if len(log_rows) > 5000:
                log_rows = log_rows[-5000:]
            with open(META_LABEL_SHADOW_LOG_PATH, "w", encoding="utf-8") as _f:
                json.dump(log_rows, _f, indent=2, default=str)
        except Exception:
            pass  # fail-soft: logging must never break admission

        return result
    except Exception:
        # Fail-soft: any error -> no-op, pick is untouched, gate unaffected.
        return result


def passes_active_gate(pick: Dict[str, Any]) -> bool:
    """
    Active Picks display gate (dashboard visibility).

    Crypto: permissive — quality is mostly score-based; only structural /
    catastrophic / stale-with-flat-PnL rows are hard-rejected.

    Non-crypto: stricter — blocked asset├ùstrategy/source pairs, trust_score < 4,
    and raw dashboard score < 55 unless audited history bypass applies.
    """
    # ── FUTURES MONITOR (2026-05-18): tag monitored strategies, allow through ──
    # Operator directive: futures strategies unblocked for stats accumulation.
    # Picks pass gates but are tagged with _monitor_mode=True and _sizing_override=zero.
    # The sizing layer must respect _sizing_override before allocating capital.
    tag_futures_monitor(pick)

    # ── BABY STRATEGY MONITOR (2026-05-28): shadow mode for 6 new baby strategies ──
    # These strategies are wired into the scanner but run in shadow/monitor mode.
    # Picks are tagged _monitor_mode=True, _monitor_tag="BABY_SHADOW", and
    # _sizing_override="zero" so they accumulate MySQL stats without surfacing
    # on the live dashboard or triggering trading signals.
    # Promotion criteria: n>=20, WR>=50%, PF>=1.2, per-strategy manual review.
    tag_baby_monitor(pick)


    # ── M-110: Pick Lifecycle Logger — entry scan (fail-soft, 2026-05-18) ──
    # Assigns a stable pick_id to every pick entering passes_active_gate().
    # Picks that pass get stage='passed_gate' stamped at function exit.
    # Picks that are filtered stay in 'scanned' stage (implicit rejection indicator).
    # FilterTracebackEngine.log_filter() called at major named gate rejections below.
    _pll_m110 = None
    _pll_tracer_m110 = None
    _pll_pick_id_m110 = ""
    try:
        from alpha_engine.pick_lifecycle_logger import (
            get_logger as _pll_get_logger_m110,
            get_tracer as _pll_get_tracer_m110,
            PickEvent as _PllPickEvent_m110,
        )
        _pll_m110 = _pll_get_logger_m110()
        _pll_tracer_m110 = _pll_get_tracer_m110()
        _pll_pick_id_m110 = _pll_m110.log_scan(_PllPickEvent_m110(
            symbol=str(pick.get("symbol", "") or ""),
            asset_class=str(pick.get("asset_class", "") or ""),
            strategy=str(pick.get("strategy", "") or ""),
            source_system=str(pick.get("source_system", "") or ""),
            direction=str(pick.get("direction", pick.get("side", "")) or ""),
            confidence=pick.get("confidence"),
        ))
        pick["_pick_lifecycle_id"] = _pll_pick_id_m110
    except Exception:
        pass  # fail-soft: lifecycle logging must never affect gate decisions

    # ── A1 (2026-05-16 → 2026-05-17): meta-labeler gate (shadow default ON) ──
    # Shadow mode: scores every pick, stamps _meta_label_pwin, appends to log.
    # Enforcement: set META_LABEL_GATE_ENFORCE=1 to reject WOULD_REJECT picks.
    # Disable entirely: META_LABEL_GATE=0. Fail-soft inside meta_label_gate().
    try:
        _ml_result = meta_label_gate(pick)
        if (
            os.environ.get("META_LABEL_GATE_ENFORCE", "0") == "1"
            and _ml_result.get("enabled")
            and _ml_result.get("verdict") == "WOULD_REJECT"
        ):
            logger.info(
                "Pick rejected: meta_label_gate WOULD_REJECT pwin=%.3f threshold=%.2f symbol=%s",
                _ml_result.get("pwin", 0),
                _ml_result.get("threshold", 0.55),
                pick.get("symbol", "?"),
            )
            pick["_hf_quality_gate_reason"] = "meta_label_reject"
            try:
                if _pll_tracer_m110 and _pll_pick_id_m110:
                    _pll_tracer_m110.log_filter(_pll_pick_id_m110, "meta_label", "meta_label_reject", pick_values={"symbol": pick.get("symbol"), "pwin": _ml_result.get("pwin")})
            except Exception:
                pass
            return False
    except Exception:
        pass  # fail-soft: meta_label gate must never affect admission on error

    # ── M-049: Safety status STOP gate (2026-05-15) ──
    # When safety_status verdict == STOP (Binance CB open, severe drift, etc.),
    # reject ALL picks — no fills should be emitted during a system halt.
    # Kill-switch: SAFETY_HALT_GATE_ENABLED=0 (default 1 = ON). Fail-open.
    try:
        if os.environ.get("SAFETY_HALT_GATE_ENABLED", "1") not in ("0", "false", "FALSE", "False"):
            _safety_verdict = _get_safety_status_verdict()
            if _safety_verdict == "STOP":
                logger.info("Pick rejected: safety_status=STOP (symbol=%s)", pick.get("symbol", "?"))
                return False
    except Exception:
        pass  # fail-open: never block picks on safety gate error

    # ── M-108: magnitude-sanity gate (2026-05-18) ──
    # Reject picks whose implied TP/SL move is fantasy for the asset class
    # (e.g. ml_enhanced FETUSDT ~40% TP on a 1-day crypto horizon). Sits
    # upstream of the statistical tests — they catch noise, not un-reachable
    # targets. Kill-switch: MAGNITUDE_SANITY_GATE_ENABLED=0 (default 1). Fail-open.
    try:
        if os.environ.get("MAGNITUDE_SANITY_GATE_ENABLED", "1") not in ("0", "false", "FALSE", "False"):
            from alpha_engine.magnitude_sanity_gate import is_magnitude_plausible
            _mag_ok, _mag_reason = is_magnitude_plausible(pick)
            if not _mag_ok:
                logger.info("Pick rejected: %s (symbol=%s)", _mag_reason, pick.get("symbol", "?"))
                pick["_hf_quality_gate_reason"] = "magnitude_implausible"
                try:
                    if _pll_tracer_m110 and _pll_pick_id_m110:
                        _pll_tracer_m110.log_filter(_pll_pick_id_m110, "magnitude_sanity", f"magnitude_implausible:{_mag_reason}", rule_id="RULE-SANITY", pick_values={"symbol": symbol})
                except Exception:
                    pass
                return False
    except Exception:
        pass  # fail-open: never block picks on magnitude-gate error

    # ── 2026-05-17: FOREX Directional Gate (design in tools/swarm_v2/_task_forex_directional_gate.md) ──
    # Autopsy 2026-05-15 Axis 2 + action_items_2026-05-15: FOREX LONG = 29.4% WR /
    # PF 0.80 is the class drag; SHORT has real edge (PF 8.11). Highest-leverage
    # mutation — block low-conviction FOREX LONGs. Env FOREX_DIRECTIONAL_GATE_ENABLED=1
    # (default). Fail-open.
    try:
        import os as _os_fdg
        if _os_fdg.environ.get(
            "FOREX_DIRECTIONAL_GATE_ENABLED", "1"
        ) not in ("0", "false", "FALSE", "False"):
            _fdg_ac = str(pick.get("asset_class", "")).upper().strip()
            _fdg_dir = str(pick.get("direction", pick.get("side", ""))).lower().strip()
            if _fdg_ac == "FOREX" and _fdg_dir in ("long", "buy"):
                _fdg_elite = float(pick.get("elite_score", pick.get("score", 0)) or 0)
                _fdg_conf = float(pick.get("confidence", 0) or 0)
                if _fdg_elite < 75 or _fdg_conf < 0.75:
                    logger.info(
                        "FOREX LONG rejected by directional gate "
                        "(elite=%.1f conf=%.2f symbol=%s)",
                        _fdg_elite, _fdg_conf, pick.get("symbol", "?"))
                    return False
    except Exception:
        pass  # fail-open

    # ── 2026-05-17: FOREX Symbol Gate (design in tools/swarm_v2/_task_forex_symbol_gate.md) ──
    # Autopsy 2026-05-15 Axis 1: NZDUSD=X / EURJPY=X / USDCHF=X drag the class
    # PF below 1. Symbol-axis companion to the directional gate. Fail-open.
    try:
        if not passes_forex_symbol_gate(pick):
            logger.info(
                "Pick rejected: FOREX symbol gate (symbol=%s) — 2026-05-15 autopsy kill",
                pick.get("symbol", "?"))
            return False
    except Exception:
        pass  # fail-open

    if not _passes_dow_gate(pick):
        return False
    # Auto-generate ID if missing
    pick_id = str(pick.get("id", "") or "").strip()
    if not pick_id or pick_id.lower() in ("", "none", "null", "nan"):
        sym = pick.get("symbol", "UNK")
        strat = pick.get("strategy", "unk")
        ts = pick.get("created_at", pick.get("timestamp", ""))[:16]
        pick["id"] = f"{sym}_{strat}_{ts}".replace(" ", "_")

    # Must have a symbol
    symbol = str(pick.get("symbol", "") or "").strip()
    if not symbol:
        logger.debug("Pick rejected: no symbol")
        try:
            if _pll_tracer_m110 and _pll_pick_id_m110:
                _pll_tracer_m110.log_filter(_pll_pick_id_m110, "format_validation", "no_symbol", rule_id="RULE-FMT")
        except Exception:
            pass
        return False
    if is_corrupted_outcome_row(pick):
        logger.debug("Pick rejected: known corrupted outcome row")
        try:
            if _pll_tracer_m110 and _pll_pick_id_m110:
                _pll_tracer_m110.log_filter(_pll_pick_id_m110, "format_validation", "corrupted_outcome_row", rule_id="RULE-FMT", pick_values={"symbol": pick.get("symbol")})
        except Exception:
            pass
        return False

    # Class-wide penny/meme gate (2026-05-15). MEMECOIN had only
    # strategy-PAIR blocks; PENNY_STOCK was entirely ungated. Reject both
    # classes outright. Kill-switch: PENNY_MEME_CLASS_GATE_ENABLED=0.
    try:
        if not passes_penny_meme_class_gate(pick):
            logger.debug(
                "Pick rejected: penny/meme class-wide gate (symbol=%s class=%s)",
                symbol, pick.get("asset_class"))
            return False
    except Exception:
        pass  # fail-open: never break admission on this gate

    # Speculative EQUITY quarantine (EAGLE 2026-05-27). Blocks GME/AMC/NIO/etc.
    # mis-tagged as EQUITY. Kill-switch: EQUITY_SPECULATIVE_GATE_ENABLED=0.
    try:
        if not passes_speculative_equity_gate(pick):
            logger.debug(
                "Pick rejected: speculative equity gate (symbol=%s)",
                pick.get("symbol"),
            )
            return False
    except Exception:
        pass

    # VIX regime on active admission (EQUITY/ETF). Kill-switch: VIX_REGIME_ACTIVE_GATE_ENABLED=0.
    try:
        if not passes_vix_regime_active_gate(pick):
            logger.debug(
                "Pick rejected: vix regime active gate (symbol=%s class=%s)",
                pick.get("symbol"), pick.get("asset_class"),
            )
            return False
    except Exception:
        pass

    # Source-system × symbol gate (2026-05-17). BLOCKED_SOURCE_SYMBOL_PAIRS
    # covers cta_replicator COMMODITY losers: CL=F (n=47, WR=19.1%, PF=0.39),
    # NG=F (n=24, WR=0%), ZC=F (n=8, WR=0%). Evidence in
    # reports/FOREX_mutation_analysis_2026_05_17.md §Axis2.
    # Kill-switch: BLOCKED_SOURCE_SYMBOL_GATE_DISABLED=1. Fail-open.
    try:
        import os as _os_bss
        if _os_bss.environ.get("BLOCKED_SOURCE_SYMBOL_GATE_DISABLED", "0") not in (
            "1", "true", "TRUE", "True"
        ):
            _bss_src = str(pick.get("source_system") or "").strip().lower()
            _bss_sym = str(pick.get("symbol") or "").strip().upper()
            if (_bss_src, _bss_sym) in {
                (s.lower(), sym) for s, sym in BLOCKED_SOURCE_SYMBOL_PAIRS
            }:
                logger.debug(
                    "Pick rejected: BLOCKED_SOURCE_SYMBOL_PAIRS source=%s symbol=%s",
                    _bss_src, _bss_sym)
                return False
    except Exception:
        pass  # fail-open

    # ── WIN_RATE_TRAP_BLACKLIST gate (2026-05-27 EAGLE P2-02) ──
    # Symbols where WR>=50% but sum_pnl<0 — the classic "small wins,
    # catastrophic losses" asymmetry. Default-off (opt-in); symbols may
    # already be caught by score/trust gates. Enable: WIN_RATE_TRAP_GATE_ENABLED=1
    try:
        if os.environ.get("WIN_RATE_TRAP_GATE_ENABLED", "0") == "1":
            _wrt_sym = str(pick.get("symbol") or "").strip().upper()
            if _wrt_sym and _wrt_sym in WIN_RATE_TRAP_BLACKLIST:
                logger.debug(
                    "Pick rejected: WIN_RATE_TRAP_BLACKLIST symbol=%s",
                    _wrt_sym)
                return False
    except Exception:
        pass  # fail-open: never block picks on gate error

    # Direction-triple gate (2026-05-15). BLOCKED_DIRECTION_TRIPLES
    # historically only scrubbed aggregation rows (_is_historical_blocked_pick)
    # — it never rejected new emissions, despite the dict's own comment saying
    # it should. Wire it at admission: FOREX LONG losers + the pre-existing
    # CRYPTO anti-edge triples are now hard-blocked. Kill-switch:
    # DIRECTION_TRIPLE_GATE_DISABLED=1. Fail-open.
    try:
        import os as _os_dtg
        if _os_dtg.environ.get(
            "DIRECTION_TRIPLE_GATE_DISABLED", "0"
        ) not in ("1", "true", "TRUE", "True"):
            _dtg_class = str(pick.get("asset_class", "") or "").strip().upper()
            _dtg_strat = str(pick.get("strategy", "") or "").strip()
            _dtg_dir = _normalize_direction(pick.get("direction", ""))
            if _dtg_dir and (_dtg_class, _dtg_strat, _dtg_dir) in BLOCKED_DIRECTION_TRIPLES:
                logger.debug(
                    "Pick rejected: BLOCKED_DIRECTION_TRIPLES %s/%s/%s",
                    _dtg_class, _dtg_strat, _dtg_dir)
                try:
                    if _pll_tracer_m110 and _pll_pick_id_m110:
                        _pll_tracer_m110.log_filter(_pll_pick_id_m110, "direction_triples", f"blocked:{_dtg_class}/{_dtg_strat}/{_dtg_dir}", rule_id="RULE-BLOCK", pick_values={"symbol": pick.get("symbol")})
                except Exception:
                    pass
                return False
    except Exception:
        pass  # fail-open: never break admission on this gate

    # ── Kill gate (2026-05-15): statistically-justified strategy kill at admission ──
    # Previously only called from commodity_kill_switch.py + fx_kill_switch.py.
    # Wired here so any pick carrying embedded strategy stats (wins, n, asset_class)
    # is blocked at the central admission gate when evidence clearly warrants a kill.
    # Fail-open: missing stats or any exception skips the gate (thin classes like
    # BOND n=11 / FUTURES n=0 will always get INSUFFICIENT_EVIDENCE — safe).
    # Kill-switch: KILL_GATE_ENABLED=0
    try:
        import os as _os_kg
        if _os_kg.environ.get("KILL_GATE_ENABLED", "1") not in ("0", "false", "FALSE", "False"):
            from audit_trail.kill_gate import evaluate_kill as _evaluate_kill
            _stats_kg = pick.get("stats") or {}
            _wins_kg = _stats_kg.get("wins") if _stats_kg else pick.get("wins")
            _n_kg = _stats_kg.get("n") if _stats_kg else pick.get("n")
            _ac_kg = str(pick.get("asset_class", "") or "").strip().upper()
            if _wins_kg is not None and _n_kg is not None:
                _allow_kill, _verdict_kg, _detail_kg = _evaluate_kill(
                    int(_wins_kg), int(_n_kg), _ac_kg
                )
                if _allow_kill:
                    logger.info(
                        "Pick rejected: kill gate %s — %s (symbol=%s strategy=%s)",
                        _verdict_kg, _detail_kg, symbol, pick.get("strategy", ""),
                    )
                    return False
    except Exception:
        pass  # fail-open: never break admission on kill gate error

    # ── M-001: CRYPTO liquid-core whitelist + BTC UTC death-zone (2026-05-28) ──
    # EAGLE plan M-001. Addresses CRYPTO 47% raw skew + 29% WR quan_engine drag:
    # of n=229 CRYPTO picks only 1 lands on the canonical edge
    # (crypto_liquidity_wick_reversal_v1); the rest is illiquid-alt long-tail.
    # Two gates, both CRYPTO-only, both fail-open, both env-kill-switchable
    # (CRYPTO_LIQUID_CORE_ENABLED / CRYPTO_BTC_HOUR_GATE_ENABLED, default ON):
    #   (a) symbol must be in top-25 by 30-day ADV (LIQUID_CORE_TOP_25)
    #   (b) entry_hour_utc must not be in [9, 10, 18, 21]
    try:
        _ac_m001 = str(pick.get("asset_class", "") or "").strip().upper()
        if _ac_m001 == "CRYPTO":
            from alpha_engine.crypto_liquid_core import (
                is_in_liquid_core as _is_in_liquid_core_m001,
                is_in_btc_death_zone as _is_in_btc_death_zone_m001,
            )
            _sym_m001 = pick.get("symbol", "") or ""
            if not _is_in_liquid_core_m001(_sym_m001):
                logger.info(
                    "Pick rejected: crypto_not_liquid_core symbol=%s strategy=%s",
                    _sym_m001, pick.get("strategy", ""),
                )
                pick["_hf_quality_gate_reason"] = "crypto_not_liquid_core"
                try:
                    if _pll_tracer_m110 and _pll_pick_id_m110:
                        _pll_tracer_m110.log_filter(
                            _pll_pick_id_m110, "crypto_liquid_core",
                            "crypto_not_liquid_core", rule_id="M-001",
                            pick_values={"symbol": _sym_m001},
                        )
                except Exception:
                    pass
                return False
            _sub_m001 = pick.get("submitted_at") or pick.get("signal_ts") or ""
            if _is_in_btc_death_zone_m001(_sub_m001):
                logger.info(
                    "Pick rejected: crypto_btc_death_zone symbol=%s submitted_at=%s",
                    _sym_m001, _sub_m001,
                )
                pick["_hf_quality_gate_reason"] = "crypto_btc_death_zone"
                try:
                    if _pll_tracer_m110 and _pll_pick_id_m110:
                        _pll_tracer_m110.log_filter(
                            _pll_pick_id_m110, "crypto_btc_death_zone",
                            "crypto_btc_death_zone", rule_id="M-001",
                            pick_values={"symbol": _sym_m001, "submitted_at": _sub_m001},
                        )
                except Exception:
                    pass
                return False
    except Exception:
        pass  # fail-open: never block picks on M-001 import/parse error

    # ── CRYPTO dynamic quarantine (2026-05-15) ──
    # Uses module-level cache (_get_crypto_quarantine_strategies) to avoid hot-path
    # file I/O. Cache invalidated on file mtime change. Kill-switch: CRYPTO_QUARANTINE=0
    try:
        if os.environ.get("CRYPTO_QUARANTINE", "1") not in ("0", "false", "FALSE", "False"):
            _ac_cq = str(pick.get("asset_class", "") or "").strip().upper()
            if _ac_cq == "CRYPTO":
                _cq_strategies = _get_crypto_quarantine_strategies()
                _strat_cq = str(pick.get("strategy", "") or "").strip().lower()
                if _strat_cq and _strat_cq in _cq_strategies:
                    logger.debug(
                        "Pick rejected: CRYPTO dynamic quarantine strategy=%s", _strat_cq)
                    return False
    except Exception:
        pass  # fail-open

    # ── M-004: CRYPTO source-system quarantine WARN (2026-05-15) ──
    # Stamps picks with _source_quarantine_warn=True when the source_system is:
    #   - CRYPTO asset class
    #   - WR < 40% (well below T2 50% target)
    #   - volume share > 10% of CRYPTO class total (high-drag potential)
    # Does NOT hard-reject (PF has improved above 1.0 after volume caps).
    # Observational only — default OFF. Enable: SOURCE_QUARANTINE_WARN_ENABLED=1.
    # Fails open: if dashboard_data.json is missing/stale the stamp is skipped.
    # Cache: 60s TTL shared with safety_status pattern (_SOURCE_QUARANTINE_STATS_CACHE).
    try:
        import os as _os_sqw
        if _os_sqw.environ.get(
            "SOURCE_QUARANTINE_WARN_ENABLED", "0"
        ) not in ("0", "false", "FALSE", "False"):
            _ac_sqw = str(pick.get("asset_class", "") or "").strip().upper()
            if _ac_sqw == "CRYPTO":
                _src_sqw = str(pick.get("source_system") or "").strip().lower()
                if _src_sqw:
                    _sqw_stats = _get_source_quarantine_stats()
                    _sqw_entry = _sqw_stats.get((_src_sqw, "CRYPTO"))
                    if _sqw_entry is not None:
                        _sqw_wr = _sqw_entry.get("wr", 100.0)
                        _sqw_vol = _sqw_entry.get("vol_share", 0.0)
                        if _sqw_wr < 40.0 and _sqw_vol > 0.10:
                            pick["_source_quarantine_warn"] = True
                            logger.debug(
                                "M-004 source_quarantine_warn stamped: "
                                "source=%s wr=%.1f%% vol_share=%.1f%%",
                                _src_sqw, _sqw_wr, _sqw_vol * 100.0,
                            )
    except Exception:
        pass  # fail-open: never break admission on source quarantine warn error

    # P0.5-4 CRYPTO confidence-band guard (2026-05-14, threshold corrected 2026-05-16).
    # Reports/p0b_crypto_confidence_inversion_repro_2026-05-13.md
    # reproduces a directional inversion on CRYPTO:
    #   bottom band (0-25% confidence) WR 53.7%
    #   top band    (85-100% confidence) WR 34.5% aggregate
    #
    # 2026-05-16 sub-band correction (Kimi live-site analysis, findtorontoevents.ca/audit):
    #   0.85-0.90 band: WR 82%, PF 11.8 -- PROVEN EDGE (was incorrectly blocked)
    #   0.90-1.00 band: WR 14%           -- anti-predictive (keep blocked)
    # Threshold raised from 0.85 to 0.90. Tunable via CRYPTO_HIGH_CONF_GUARD_THRESHOLD.
    # Kill-switch: env CRYPTO_HIGH_CONF_GUARD_ENABLED=0.
    try:
        import os as _os_chc
        _chc_enabled = (_os_chc.environ.get(
            "CRYPTO_HIGH_CONF_GUARD_ENABLED", "1") or "1") not in ("0","false","FALSE","False")
        if _chc_enabled:
            _ac_chc = str(pick.get("asset_class", "CRYPTO") or "CRYPTO").upper()
            if _ac_chc == "CRYPTO":
                try:
                    _conf_chc = float(pick.get("confidence", 0) or 0)
                except (TypeError, ValueError):
                    _conf_chc = 0.0
                _chc_threshold = 0.90
                try:
                    _chc_threshold = float(_os_chc.environ.get(
                        "CRYPTO_HIGH_CONF_GUARD_THRESHOLD", "0.90"))
                except (TypeError, ValueError):
                    _chc_threshold = 0.90
                if _conf_chc > _chc_threshold:
                    logger.debug(
                        "Pick rejected: CRYPTO confidence=%.3f > %.2f (inversion guard)",
                        _conf_chc, _chc_threshold)
                    return False
    except Exception:
        # Fail-open: if the guard itself errors, do not block picks.
        pass

    # ── Phase J: ML Calibration Auto-Quarantine (all asset classes, 2026-05-15) ──
    # High raw confidence (≥0.9) is in the inverted tail — empirical WR drops to ~14%.
    # OPT-IN: default OFF pending a linked evidence report (set ML_CONFIDENCE_QUARANTINE_ENABLED=1).
    try:
        import os as _os_mlq
        if (_os_mlq.environ.get("ML_CONFIDENCE_QUARANTINE_ENABLED", "0")
                not in ("0", "false", "FALSE", "False")):
            _conf_mlq = _normalize_confidence(pick.get("confidence", 0))
            if _conf_mlq >= 0.90:
                logger.debug(
                    "Pick rejected: confidence=%.3f >= 0.90 (Phase J quarantine)",
                    _conf_mlq)
                return False
    except Exception:
        pass

    # ── M-034: CRYPTO confidence-inversion gate (2026-05-15) ──
    # Empirical: for CRYPTO picks from cloud-agent / super_signals source systems,
    # confidence ≥ 0.85 is anti-correlated with WR (WR drops ~14% at 0.85-0.95 band).
    # Gate: block CRYPTO picks from known anti-correlated sources when confidence ≥ 0.85.
    # Enable: CRYPTO_CONF_INVERSION_GATE=1 (default OFF — shadow first, enable after 30d live verify).
    # Affected sources: super_signals, ml_enhanced (these are the primary inverted-confidence emitters).
    try:
        import os as _os_m034
        _M034_INVERSION_SOURCES = frozenset({
            "super_signals", "luxalgo_filters",
            # ml_enhanced restored 2026-05-18 (EDGE_VERDICT_2026-05-18):
            # the INJ/FET/DYDX 85-100% WR that prompted its 2026-05-16
            # removal is a placeholder-stat artifact, not real edge.
            "ml_enhanced",
        })
        if (_os_m034.environ.get("CRYPTO_CONF_INVERSION_GATE", "0")
                not in ("0", "false", "FALSE", "False")):
            _m034_ac = str(pick.get("asset_class", "") or "").upper()
            if _m034_ac == "CRYPTO":
                _m034_src = str(pick.get("source_system", "") or "").lower()
                if _m034_src in _M034_INVERSION_SOURCES:
                    _conf_m034 = _normalize_confidence(pick.get("confidence", 0))
                    if _conf_m034 >= 0.85:
                        logger.info(
                            "M-034 confidence-inversion gate: CRYPTO/%s conf=%.3f >= 0.85 — rejected",
                            _m034_src, _conf_m034,
                        )
                        return False
        else:
            # Shadow-mode: gate is OFF — log picks that WOULD be blocked so we can
            # accumulate n≥30 evidence before enabling on 2026-06-15.
            _m034_ac_sh = str(pick.get("asset_class", "") or "").upper()
            if _m034_ac_sh == "CRYPTO":
                _m034_src_sh = str(pick.get("source_system", "") or "").lower()
                if _m034_src_sh in _M034_INVERSION_SOURCES:
                    _conf_m034_sh = _normalize_confidence(pick.get("confidence", 0))
                    if _conf_m034_sh >= 0.85:
                        import json as _json_m034
                        from pathlib import Path as _Path_m034
                        from datetime import datetime as _dt_m034, timezone as _tz_m034
                        _m034_log = (
                            _Path_m034(__file__).parent.parent
                            / "alpha_engine" / "data" / "shadow_blocked_m034.jsonl"
                        )
                        try:
                            with open(_m034_log, "a", encoding="utf-8") as _fh_m034:
                                _fh_m034.write(_json_m034.dumps({
                                    "ts": _dt_m034.now(_tz_m034.utc).isoformat(),
                                    "symbol": pick.get("symbol"),
                                    "strategy": pick.get("strategy"),
                                    "source_system": pick.get("source_system"),
                                    "confidence": pick.get("confidence"),
                                    "asset_class": pick.get("asset_class"),
                                }) + "\n")
                        except Exception:
                            pass
                        logger.debug(
                            "M-034 SHADOW: would-block CRYPTO/%s conf=%.3f >= 0.85 (gate OFF, review 2026-06-15)",
                            _m034_src_sh, _conf_m034_sh,
                        )
    except Exception:
        pass

    # ── M-035: CRYPTO confidence overfit cliff — hard gate (2026-05-17) ──
    # Expert finding: CRYPTO picks with confidence > 0.90 have WR=14.4% (overfit).
    # This gate is distinct from the softer P0.5-4 guard above — M-035 is a
    # named, auditable gate with a clear mutation ID and env-var kill-switch.
    # Kill-switch: CRYPTO_CONF_OVERFIT_GATE_ENABLED=0. Fail-open.
    try:
        import os as _os_m035
        if _os_m035.environ.get(
            "CRYPTO_CONF_OVERFIT_GATE_ENABLED", "1"
        ) not in ("0", "false", "FALSE", "False"):
            _m035_ac = str(pick.get("asset_class", "") or "").upper()
            if _m035_ac == "CRYPTO":
                try:
                    _m035_conf = float(pick.get("confidence") or 0)
                except (TypeError, ValueError):
                    _m035_conf = 0.0
                try:
                    from alpha_engine.config import CRYPTO_MAX_CONFIDENCE as _m035_max_conf
                except ImportError:
                    _m035_max_conf = 0.90
                _m035_threshold = float(
                    _os_m035.environ.get("CRYPTO_MAX_CONFIDENCE", str(_m035_max_conf))
                )
                if _m035_conf > _m035_threshold:
                    logger.info(
                        "M-035 crypto_conf_overfit_cliff: confidence=%.3f > %.2f (WR=14.4%%) "
                        "— rejected (symbol=%s)",
                        _m035_conf, _m035_threshold, pick.get("symbol", "?"),
                    )
                    return False
    except Exception:
        pass  # fail-open: never block picks on gate error

    # ── M-036: CRYPTO direction="BUY" hard-blocked (2026-05-17) ──
    # Expert finding: CRYPTO direction="BUY" PF=0.38 / WR=28.9% vs LONG PF=3.14 / WR=54.9%.
    # "BUY" is anti-predictive for CRYPTO; only LONG / SHORT are valid.
    # Kill-switch: CRYPTO_BUY_DIRECTION_GATE_ENABLED=0. Fail-open.
    try:
        import os as _os_m036
        if _os_m036.environ.get(
            "CRYPTO_BUY_DIRECTION_GATE_ENABLED", "1"
        ) not in ("0", "false", "FALSE", "False"):
            _m036_ac = str(pick.get("asset_class", "") or "").upper()
            if _m036_ac == "CRYPTO":
                _m036_dir = str(pick.get("direction", "") or "").upper().strip()
                try:
                    from alpha_engine.config import CRYPTO_BLOCKED_DIRECTIONS as _m036_blocked
                except ImportError:
                    _m036_blocked = frozenset({"BUY"})
                if _m036_dir in _m036_blocked:
                    logger.info(
                        "M-036 crypto_buy_direction_blocked: direction=%s (PF=0.38 vs LONG PF=3.14) "
                        "— rejected (symbol=%s)",
                        _m036_dir, pick.get("symbol", "?"),
                    )
                    return False
    except Exception:
        pass  # fail-open: never block picks on gate error

    # ── M-037: CRYPTO ml_score floor (2026-05-17) ──
    # Expert finding: bottom 30% of ml_score CRYPTO picks have WR=32.5%;
    # top 30% (ml_score >= 0.65) have WR=60%. Gate is env-var overridable.
    # Kill-switch: CRYPTO_ML_SCORE_GATE_ENABLED=0. Fail-open (picks without
    # ml_score populated are NOT blocked — fill-rate may be partial).
    try:
        import os as _os_m037
        if _os_m037.environ.get(
            "CRYPTO_ML_SCORE_GATE_ENABLED", "1"
        ) not in ("0", "false", "FALSE", "False"):
            _m037_ac = str(pick.get("asset_class", "") or "").upper()
            if _m037_ac == "CRYPTO":
                _m037_ml = pick.get("ml_score")
                if _m037_ml is not None:
                    try:
                        _m037_ml = float(_m037_ml)
                    except (TypeError, ValueError):
                        _m037_ml = None
                # Treat ml_score=0 as "not populated" — a probability model
                # never outputs exactly 0.0 for a real pick; zero is the default
                # fill value for picks whose source doesn't emit ml_score yet.
                # We use > 0 (not > epsilon) so any real non-zero score (e.g.
                # 0.001) IS evaluated against the floor and blocked if below it.
                if _m037_ml is not None and _m037_ml > 0:
                    try:
                        from alpha_engine.config import MIN_ML_SCORE_CRYPTO as _m037_floor
                    except ImportError:
                        _m037_floor = 0.65
                    _m037_min = float(
                        _os_m037.environ.get("MIN_ML_SCORE_CRYPTO", str(_m037_floor))
                    )
                    if _m037_ml < _m037_min:
                        logger.info(
                            "M-037 crypto_ml_score_below_floor: ml_score=%.3f < %.2f "
                            "(bottom-30%% tier WR=32.5%%) — rejected (symbol=%s)",
                            _m037_ml, _m037_min, pick.get("symbol", "?"),
                        )
                        return False
    except Exception:
        pass  # fail-open: never block picks on gate error

    # ── M-038: NUPL regime filter — block CRYPTO LONG in euphoria (2026-05-17) ──
    # Expert finding: NUPL > 0.75 historically precedes major corrections (Adamant/Glassnode).
    # Source: Coin Metrics Community API (free) via tools.research.nupl_regime.
    # Shadow mode by default (NUPL_GATE_ENFORCE=0) — logs but does NOT block until
    # Coin Metrics API reliability is confirmed in production. Enable: NUPL_GATE_ENFORCE=1.
    # Threshold tunable: NUPL_EUPHORIA_THRESHOLD (default 0.75).
    # Fails open when NUPL API unavailable. Kill-switch: NUPL_GATE_ENFORCE=0 (already default).
    try:
        _m038_ac = str(pick.get("asset_class", "") or "").upper()
        _m038_dir = str(pick.get("direction", pick.get("side", "")) or "").upper().strip()
        if _m038_ac == "CRYPTO" and _m038_dir in ("LONG", "BUY"):
            from tools.research.nupl_regime import is_crypto_long_blocked_by_nupl
            _nupl_blocked, _nupl_reason = is_crypto_long_blocked_by_nupl()
            if _nupl_blocked:
                logger.info(
                    "M-038 NUPL euphoria gate: CRYPTO LONG rejected — %s (symbol=%s)",
                    _nupl_reason, pick.get("symbol", "?"),
                )
                return False
    except Exception:
        pass  # fail-open: never block picks on NUPL gate error

    # ── M-039: Exchange spread divergence filter (shadow mode, 2026-05-17) ──
    # When the same CRYPTO asset trades at significantly different prices across
    # exchanges, it often signals a false breakout or manipulation.
    # Default OFF (EXCHANGE_DIVERGENCE_GATE=0) — enable when multi-exchange feed wired.
    # Fails open on any exception. Stub: is_exchange_divergence_high always returns False
    # until live multi-exchange price data is plumbed in.
    try:
        import os as _os_m039
        if _os_m039.environ.get("EXCHANGE_DIVERGENCE_GATE", "0") not in ("0", "false", "FALSE", "False"):
            _m039_ac = str(pick.get("asset_class", "") or "").upper()
            if _m039_ac == "CRYPTO":
                _m039_sym = str(pick.get("symbol", "") or "")
                from coinglass_strategies.data_fetcher import is_exchange_divergence_high
                if is_exchange_divergence_high(_m039_sym):
                    logger.info(
                        "M-039 exchange_spread_divergence: CRYPTO pick rejected "
                        "(symbol=%s)",
                        _m039_sym,
                    )
                    return False
    except Exception:
        pass  # fail-open: never block picks on exchange divergence gate error

    # ── M-040: OBI Order Flow Imbalance signal (shadow mode, 2026-05-17) ──
    # OBI = (bid_vol - ask_vol) / (bid_vol + ask_vol); OFI = rolling z-score.
    # Cold-start safe: returns blocked=False for first 12 samples (first ~12h).
    # Shadow mode default (OBI_GATE_ENFORCE=0): logs to
    #   audit_dashboard/data/obi_shadow_log.json but does NOT block picks.
    # Enable enforcement after 30-day shadow validates signal quality:
    #   OBI_GATE_ENFORCE=1 + OBI_SELL_THRESHOLD=-2.0
    # Kill-switch: OBI_SHADOW_LOG=0 disables logging; OBI_GATE_ENFORCE=0 (default)
    # keeps shadow-only. Fail-open: any import/runtime error is silently swallowed.
    if str(pick.get("asset_class", "") or "").upper() == "CRYPTO" and os.getenv("OBI_SHADOW_LOG", "1") == "1":
        try:
            from crypto_signal_engine.obiflow import evaluate_obi_signal as _eval_obi
            _obi = _eval_obi(symbol)  # bid/ask not available at gate time — cold-start safe
            if _obi.get("blocked"):
                logger.info(
                    "M-040 obi_sell_pressure: OFI z=%.2f < threshold (symbol=%s) — rejected",
                    _obi.get("ofi_zscore", 0.0), symbol,
                )
                return False
        except Exception:
            pass  # never let OBI break the gate

    # ── KS concept-drift auto-pause gate (2026-05-14) ──
    # When KS_D > DRIFT_PAUSE_RATIO × critical, CRYPTO and FOREX emissions are
    # paused. Current live state: KS_D/critical = 6.6× (SEVERE). Fail-open.
    # Kill-switch: DRIFT_PAUSE_GATE_ENABLED=0.
    # M-028: Dry-run mode — set DRIFT_PAUSE_DRY_RUN=1 to emit a recommendation
    # stamp (pick["_drift_pause_recommend"]="sizing_allowed=false") WITHOUT
    # physically blocking the fill. Default "0" = hard-reject (existing behavior).
    try:
        import os as _os_dpg
        _dpg_enabled = _os_dpg.environ.get(
            "DRIFT_PAUSE_GATE_ENABLED", "1") not in ("0", "false", "FALSE", "False")
        if _dpg_enabled:
            _dpg_class = str(pick.get("asset_class", "") or "").upper()
            if _dpg_class in ("CRYPTO", "FOREX"):
                _drift_ratio = _get_concept_drift_ratio()
                if _drift_ratio > _DRIFT_PAUSE_RATIO:
                    _dpg_dry_run = _os_dpg.environ.get(
                        "DRIFT_PAUSE_DRY_RUN", "0") not in ("0", "false", "FALSE", "False")
                    if _dpg_dry_run:
                        # Dry-run: stamp recommendation but do NOT block the pick
                        pick["_drift_pause_recommend"] = "sizing_allowed=false"
                        logger.info(
                            "Drift-pause DRY-RUN: sizing_allowed=false recommendation "
                            "stamped (not blocking) symbol=%s class=%s KS_ratio=%.2f > %.1f",
                            symbol, _dpg_class, _drift_ratio, _DRIFT_PAUSE_RATIO,
                        )
                    else:
                        logger.info(
                            "Pick rejected: concept-drift auto-pause symbol=%s "
                            "class=%s KS_ratio=%.2f > %.1f",
                            symbol, _dpg_class, _drift_ratio, _DRIFT_PAUSE_RATIO,
                        )
                        return False
    except Exception:
        pass  # fail-open: never break admission on drift gate

    # M-028: 15m timeframe quarantine (default shadow=stamp-only, enforce via TIMEFRAME_15M_GATE=1).
    # All 15m ML models scored as OVERFIT_LIKELY in anti_overfit_audit.json (DSR<0.5), except
    # DYDXUSDT_15m (already in BLOCKED_SYMBOLS). Score penalty -30 exists in calculate_smart_score
    # but doesn't block at active-picks level. This gate makes enforcement explicit.
    # Whitelist: strategies where operator has confirmed edge (TIMEFRAME_15M_WHITELIST env var,
    # comma-separated). Kill-switch: TIMEFRAME_15M_GATE=0. Fail-open always.
    try:
        if os.environ.get("TIMEFRAME_15M_GATE", "0") not in ("0", "false", "FALSE", "False"):
            if _is_15m_model(strategy):
                _whitelist_raw = os.environ.get("TIMEFRAME_15M_WHITELIST", "")
                _whitelist = {s.strip().lower() for s in _whitelist_raw.split(",") if s.strip()}
                if strategy.lower() not in _whitelist:
                    logger.debug(
                        "Pick rejected: M-028 15m timeframe quarantine strategy=%s; "
                        "set TIMEFRAME_15M_WHITELIST=%s to exempt",
                        strategy, strategy,
                    )
                    return False
    except Exception:
        pass  # fail-open: never break admission on timeframe gate

    # M-004: CRYPTO drag auto-quarantine. Source systems with >40% vol concentration
    # AND PF<1 in a given asset class are quarantined (default shadow=log-only).
    # Enforcement: CRYPTO_CONCENTRATION_GATE=1. Kill-switch: =0. Fail-open always.
    # Data source: audit_trail/data/system_concentration.json (written by dashboard_generator).
    # No current CRYPTO system exceeds 40% concentration — this is a guard for future regressions.
    try:
        _m4_gate_enabled = os.environ.get("CRYPTO_CONCENTRATION_GATE", "0") not in (
            "0", "false", "FALSE", "False"
        )
        _m4_source = str(pick.get("source_system") or "").strip().lower()
        _m4_ac = str(pick.get("asset_class") or "").upper().strip()
        if _m4_source and _m4_ac:
            _m4_conc = _cached_system_concentration()
            _m4_cls = _m4_conc.get(_m4_ac, {})
            _m4_sys = _m4_cls.get(_m4_source, {})
            _m4_vol_pct = float(_m4_sys.get("vol_pct") or 0)
            _m4_pf = _m4_sys.get("pf")
            _m4_pf_val = float(_m4_pf) if _m4_pf is not None else None
            if _m4_vol_pct > 40.0 and _m4_pf_val is not None and _m4_pf_val < 1.0:
                if _m4_gate_enabled:
                    pick["_hf_quality_gate_reason"] = "m004_crypto_concentration_quarantine"
                    logger.debug(
                        "Pick rejected: M-004 concentration quarantine source=%s class=%s vol=%.1f%% PF=%.2f",
                        _m4_source, _m4_ac, _m4_vol_pct, _m4_pf_val,
                    )
                    return False
                else:
                    logger.debug(
                        "Pick shadow-rejected (M-004 shadow): source=%s class=%s vol=%.1f%% PF=%.2f "
                        "(set CRYPTO_CONCENTRATION_GATE=1 to enforce)",
                        _m4_source, _m4_ac, _m4_vol_pct, _m4_pf_val,
                    )
    except Exception:
        pass  # fail-open: never block picks on concentration cache error

    # M-013: Concentration cap (default ON, 2026-05-15). Per-symbol share cap:
    # CRYPTO≤15%, COMMODITY≤30%, EQUITY≤10%, ETF≤15%, FOREX≤20%, BOND≤50%, FUTURES≤30%.
    # MIN_ACTIVE_FOR_CAP=10 prevents cold-start lockout for low-n classes.
    # Kill-switch: CONCENTRATION_CAP_ENABLED=0. Caller: passes_active_gate.
    try:
        import os as _os_cc
        if _os_cc.environ.get("CONCENTRATION_CAP_ENABLED", "1") not in ("0", "false", "FALSE", "False"):
            _active_pc = _cached_active_picks_snapshot()
            from alpha_engine.concentration_cap import passes_concentration_cap as _pcc
            _cc_ok, _cc_why = _pcc(
                pick.get("asset_class") or "",
                pick.get("symbol") or "",
                _active_pc,
            )
            if not _cc_ok:
                logger.debug("Pick rejected: %s", _cc_why)
                return False
    except Exception:  # pragma: no cover - never let cap fail the gate
        pass

    # Charter §7 P0.5-4 sector + duplicate-symbol concentration check (opt-in,
    # default OFF). Complementary to passes_concentration_cap above:
    #   - passes_concentration_cap = per-symbol % share (hard cap)
    #   - validate_concentration   = per-sector notional + duplicate symbol
    # Activation: env flag `CHARTER_CONCENTRATION_ENFORCE=1`. When the flag is
    # off, production_scanner still stamps `_charter_concentration_warn` per
    # PR #976 (warn-only). When PR #982's risk-budget allocator is wired
    # downstream, this flag flips on to promote warn → hard-reject.
    # Spec: reports/swarm_verdict_round_2026-05-13T23Z.md P0.5-4.
    try:
        import os as _os_cc7
        if _os_cc7.environ.get("CHARTER_CONCENTRATION_ENFORCE", "0") == "1":
            from alpha_engine.charter_position_sizer import (
                validate_concentration as _vc,
            )
            _active_for_charter = _cached_active_picks_snapshot()
            _ok7, _reason7 = _vc(pick, _active_for_charter)
            if not _ok7:
                logger.debug("Pick rejected: charter concentration: %s", _reason7)
                return False
    except Exception:  # pragma: no cover - never let charter cap fail the gate
        pass

    # Must not be closed/resolved
    status = str(pick.get("status", "")).upper().strip()
    if status and status not in {"OPEN", "ACTIVE", "PENDING", "LIVE", ""}:
        logger.debug(f"Pick rejected: closed status={status}")
        return False

    # ── Defense-in-depth CRYPTO_BANNED_SYMBOLS check (Issue #622) ──
    # Per memory `feedback_gate_at_execution_not_generation` and the 2026-04-28
    # BANNED-tier active-gate investigation: ban enforcement at pick-generation
    # time alone is not enough — picks must be re-checked at execution
    # (active-gate) time too. PR #613's Kimi review observed DOGEUSDT in
    # S-tier active picks despite being entry #1 in CRYPTO_BANNED_SYMBOLS.
    # Root cause: passes_hedge_fund_gate (which checks the ban) is only
    # called from passes_smart_gate, NOT from passes_active_gate. So a pick
    # could fail smart-gate but still appear in active.
    #
    # Gated on the same HF_QUALITY_GATE_ENABLED flag as the upstream gate so
    # operators get a single rollback switch (default-on, set "0" to bypass).
    if os.environ.get("HF_QUALITY_GATE_ENABLED", "1") != "0":
        try:
            from alpha_engine.hedge_fund_quality_gate import CRYPTO_BANNED_SYMBOLS
            if symbol.upper() in CRYPTO_BANNED_SYMBOLS:
                _reason = f"banned_symbol: {symbol.upper()} (active-gate defense-in-depth)"
                pick["_hf_quality_gate_pass"] = False
                pick["_hf_quality_gate_reason"] = _reason
                logger.debug(f"Pick rejected: {_reason}")
                return False
        except ImportError:
            pass

    # ── Phase 2-A CRYPTO SHORT regime-gate / kill-switch (default-OFF) ──
    # Panel finding (7/8, 2026-04-29): CRYPTO SHORT n=448 PF 1.000 (break-even).
    # Two opt-in env-flags (both default-off ÔåÆ no behavior change):
    #   CRYPTO_SHORT_DISABLED=1 ÔåÆ kill all crypto SHORTs
    #   CRYPTO_SHORT_REGIME_GATE_ENABLED=1 ÔåÆ block crypto SHORTs in BULL regime
    # FOREX/EQUITY/COMMODITY SHORTs and CRYPTO LONGs are unaffected.
    _short_block_reason = _crypto_short_gate_block_reason(pick)
    if _short_block_reason is not None:
        logger.debug("Pick rejected: %s (%s)", _short_block_reason, symbol)
        try:
            if _pll_tracer_m110 and _pll_pick_id_m110:
                _pll_tracer_m110.log_filter(_pll_pick_id_m110, "regime_gate", f"crypto_short:{_short_block_reason}", rule_id="RULE-REGIME", pick_values={"symbol": symbol, "direction": pick.get("direction")})
        except Exception:
            pass
        return False

    # ── Concept-drift auto-pause gate (P0 2026-05-14) ──
    # 3/3 swarm consensus: per-class threshold D > 2 * ks_critical_05; system-wide
    # severe at D > 3 * critical. Fail-open on stale/missing payload. Default ON.
    # Override: DRIFT_AUTO_PAUSE_DISABLED=1
    _drift_reason = _passes_drift_auto_pause_gate(pick)
    if _drift_reason is not None:
        logger.debug("Pick rejected by drift gate: %s (%s)", _drift_reason, symbol)
        try:
            if _pll_tracer_m110 and _pll_pick_id_m110:
                _pll_tracer_m110.log_filter(_pll_pick_id_m110, "drift_gate", f"drift_auto_pause:{_drift_reason}", rule_id="RULE-REGIME", pick_values={"symbol": symbol, "asset_class": pick.get("asset_class")})
        except Exception:
            pass
        return False

    # ── M-016 + M-029: Live-vs-backtest WR drift circuit breaker + dry-run stamp ──
    # BT_WR_DRIFT_GATE_ENABLED=1 → hard block (Phase 4.2, M-016).
    # BT_WR_DRIFT_DRY_RUN=1 (when gate OFF) → stamp recommendation without blocking
    #   (Phase 4.1, M-029 auto-flip dry-run). Enable one at a time.
    _bt_wr_drift_reason = _passes_bt_wr_drift_gate(pick)
    if _bt_wr_drift_reason is not None:
        logger.debug("Pick rejected by BT-WR drift gate: %s (%s)", _bt_wr_drift_reason, symbol)
        try:
            if _pll_tracer_m110 and _pll_pick_id_m110:
                _pll_tracer_m110.log_filter(_pll_pick_id_m110, "bt_wr_drift_gate", f"drift:{_bt_wr_drift_reason}", rule_id="RULE-REGIME", pick_values={"symbol": symbol, "strategy": pick.get("strategy")})
        except Exception:
            pass
        return False
    elif os.environ.get("BT_WR_DRIFT_DRY_RUN", "0") not in ("0", "false", "FALSE", "False"):
        # M-029: gate is OFF but dry-run is ON — check if pick would be blocked and stamp it
        _strategy_l = str(pick.get("strategy", "") or "").lower()
        if _strategy_l and _strategy_l in _load_bt_wr_drift_state():
            pick["_bt_wr_drift_recommend"] = "sizing_allowed=false"
            logger.info(
                "M-029 BT-WR drift DRY-RUN: sizing_allowed=false recommendation "
                "stamped (not blocking) symbol=%s strategy=%s",
                symbol, _strategy_l,
            )

    # ── B13 per-asset-class regime filter sidecar (default-OFF) ──
    # REGIME_FILTER_ENABLED=0 by default → zero production impact until opted in.
    # All errors degrade gracefully (permissive).
    try:
        from audit_trail.regime_filter import passes_regime_filter as _passes_regime_filter
        _regime_block = _passes_regime_filter(pick)
        if _regime_block:
            logger.debug("Pick rejected by regime filter: %s (%s)", _regime_block, symbol)
            try:
                if _pll_tracer_m110 and _pll_pick_id_m110:
                    _pll_tracer_m110.log_filter(_pll_pick_id_m110, "regime_gate", f"regime_filter:{_regime_block}", rule_id="RULE-REGIME", pick_values={"symbol": symbol, "asset_class": pick.get("asset_class")})
            except Exception:
                pass
            return False
    except Exception:  # noqa: BLE001 — any error is permissive
        pass

    # Hard-block BANNED/AVOID trust tiers — catastrophic trust picks must never display
    _pick_trust_tier = str(pick.get("trust_tier", "") or "").upper()
    if _pick_trust_tier in BLOCKED_ACTIVE_TRUST_TIERS:
        # Per Gate 1 Q4 = A (5/5 UNANIMOUS panel + 8-stream consensus
        # 2026-04-29): the trust-tier model is calibrated for CRYPTO and
        # produces INVERTED results on every other class. Recent 3500
        # closed picks confirm:
        #   EQUITY UNTRUSTED: n=185 WR 58.9% sum +$246.23 (TOP)
        #   EQUITY BANNED:    n=143 WR 47.6% sum  +$51.05 (positive!)
        #   EQUITY RELIABLE:  n= 26 WR 61.5% sum  -$10.51 (LOSING)
        # CRYPTO behaves normally (RELIABLE +$107, BANNED -$57).
        #
        # Default-on bypass: trust-tier gate is now SKIPPED for FOREX,
        # COMMODITY, EQUITY, ETF, BOND, and FUTURES. CRYPTO is unchanged.
        # Each non-CRYPTO class can be re-enabled via dedicated env flag
        # if research validates a class-specific trust model:
        #   TRUST_TIER_GATE_FORCE_<CLASS>_ENABLED=1
        #
        # Back-compat: PR #508's EQUITY_TRUST_TIER_EXEMPT_ENABLED=1 still
        # works (deprecated; EQUITY now bypassed by default anyway).
        _ac_trust_exempt = str(pick.get("asset_class", "") or "").upper().strip()
        # Deprecated PR #508 flag — kept for back-compat. When set to "1"
        # for EQUITY, behaves exactly as before (bypass trust-tier gate).
        _legacy_equity_flag_on = (
            _ac_trust_exempt == "EQUITY"
            and os.environ.get("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "0") == "1"
        )
        # Default-on bypass for non-CRYPTO classes unless operator has
        # explicitly force-re-enabled trust-tier gate for this class.
        _force_flag = f"TRUST_TIER_GATE_FORCE_{_ac_trust_exempt}_ENABLED"
        _non_crypto_default_bypass = (
            _ac_trust_exempt in NON_CRYPTO_TRUST_EXEMPT_CLASSES
            and os.environ.get(_force_flag, "0") != "1"
        )
        if _legacy_equity_flag_on or _non_crypto_default_bypass:
            logger.debug(
                "Trust-tier gate bypassed (Q4=A unanimous, default-on for "
                "non-CRYPTO; class=%s tier=%s symbol=%s)",
                _ac_trust_exempt, _pick_trust_tier, symbol,
            )
            # fall through — skip the trust-tier hard-block
        else:
            logger.debug(f"Pick rejected: trust_tier={_pick_trust_tier} blocked ({symbol})")
            return False

    # GC=F Bad Data Protection (audit session 2026-04-05; revised post-diagnostic)
    # Total Active Futures Audit confirmed Gold (GC=F) entry ~4702.
    if symbol.upper() == "GC=F":
        entry = _float(pick.get("entry_price", 0))
        if entry > 0 and (entry < 800 or entry > 12000):
            logger.debug(f"Pick rejected: insane gold entry {entry}")
            return False

    # Block symbols with known data quality issues (redenomination, bad feeds).
    # UEPS long-horizon (3y+) value picks bypass this when the env flag is ON;
    # short-term feed issues don't apply to a 3-year holding period.
    # Kill-switch: UNIVERSAL_BLOCKED_SYMBOLS_GATE_DISABLED=1 bypasses this gate.
    if os.environ.get("UNIVERSAL_BLOCKED_SYMBOLS_GATE_DISABLED", "0") != "1":
        if symbol.upper() in BLOCKED_SYMBOLS:
            _ueps_bypass = (
                _ueps_long_horizon_bypass_active(pick)
                and symbol.upper() in _DATA_QUALITY_BLOCKS
            )
            if not _ueps_bypass:
                logger.debug(f"Pick rejected: blocked symbol {symbol} (data quality issue)")
                try:
                    if _pll_tracer_m110 and _pll_pick_id_m110:
                        _pll_tracer_m110.log_filter(_pll_pick_id_m110, "symbol_blocklist", f"blocked_symbol:{symbol}", rule_id="RULE-BLOCK", pick_values={"symbol": symbol})
                except Exception:
                    pass
                return False

    # ── JPY-cross BUY-direction surgical kill (Phase 2-C 6/7 panel, 2026-04-29) ──
    # Per Phase 2-C FOREX panel (reports/HFPA_PHASE-2-findings-FOREX-2026-04-29.md):
    # JPY-cross pairs (CADJPY/EURJPY/NZDJPY/GBPJPY/AUDJPY) BUY-direction picks drove
    # the ENTIRE -45.43% jpy_cross 30d loss. Local verification (recent_closed):
    #   CADJPY=X BUY n=1  sum=-7.54%
    #   EURJPY=X BUY n=1  sum=-13.55%
    #   NZDJPY=X BUY n=3  sum=-20.69%
    #   AUDJPY=X BUY n=1  sum=-3.65%
    # vs LONG (n=102 +5.66%) and SHORT (n=158 +3.74%) which are profitable.
    # USDJPY=X excluded (n=64 PF 9.50 historical — keep).
    # Default-on. Rollback: JPY_CROSS_BUY_KILL_DISABLED=1
    _jpy_ac = str(pick.get("asset_class", "") or "").upper()
    _jpy_dir = str(pick.get("direction", "") or "").upper()
    if (
        _jpy_ac == "FOREX"
        and symbol.upper() in JPY_CROSS_PAIRS
        and _jpy_dir in ("BUY", "LONG", "BULLISH")
        and os.environ.get("JPY_CROSS_BUY_KILL_DISABLED", "0") != "1"
    ):
        logger.debug(
            "Pick rejected: jpy_cross_buy_killed (%s %s) — Phase 2-C 6/7 panel",
            symbol, _jpy_dir,
        )
        return False
    # ---- FOREX SHORT-only gate ---- Phase 2-F, 2026-05-14 ----
    # FOREX LONG has 21% WR vs SHORT 57% WR -- massive asymmetric edge.
    # Block all FOREX LONG picks regardless of strategy.
    # Default-on. Rollback: FOREX_SHORT_ONLY_GATE_DISABLED=1
    _fx_smart_ac = str(pick.get("asset_class", "") or "").upper()
    _fx_smart_dir = str(pick.get("direction", "") or "").upper()
    if (
        _fx_smart_ac == "FOREX"
        and _fx_smart_dir in ("BUY", "LONG", "BULLISH")
        and os.environ.get("FOREX_SHORT_ONLY_GATE_DISABLED", "0") != "1"
    ):
        logger.debug(
            "Smart gate: forex_short_only_blocked (%s %s) -- FOREX LONG anti-edge (21%% WR vs 57%% SHORT)",
            pick.get("symbol", "?"), _fx_smart_dir,
        )
        return False

    # ── FOREX session liquidity gate (2026-05-17, M-078) ──
    # FOOLPROOF line 133: convert London/NY overlap from +8 bonus to hard gate.
    # Empirical: picks outside 08-16 UTC are low-liquidity retail noise.
    # Only SHORT picks reach this gate (FOREX LONG already blocked above).
    # Rollback: FOREX_SESSION_GATE_DISABLED=1
    if (
        str(pick.get("asset_class", "") or "").upper() == "FOREX"
        and os.environ.get("FOREX_SESSION_GATE_DISABLED", "0") != "1"
    ):
        _fx_ts_raw = (
            pick.get("created_at") or pick.get("timestamp") or pick.get("generated_at")
        )
        _fx_hour = None
        if _fx_ts_raw:
            try:
                from datetime import datetime as _fx_dt_cls
                _fx_dt = _fx_dt_cls.fromisoformat(str(_fx_ts_raw).replace("Z", "+00:00"))
                _fx_hour = _fx_dt.hour
            except (ValueError, TypeError):
                _fx_hour = None
        # Fail-closed: reject if timestamp missing or unparseable (can't verify session)
        if _fx_hour is None or not (8 <= _fx_hour <= 16):
            logger.debug(
                "Smart gate: forex_session_gate blocked (%s h=%s UTC) — outside London/NY overlap 08-16 UTC",
                pick.get("symbol", "?"), _fx_hour,
            )
            return False

    # ── CONNORS_RSI2 shadow emission (2026-05-17, M-068) ──
    # connors_rsi2_scanner has validated backtest: WR=75.7%, n=74, Sharpe=4.84
    # (walk_forward_gate.py). Zero live picks because elite_score gate ≥55 blocks
    # ~95% of its signals. Shadow mode logs picks to connors_rsi2_shadow_log.jsonl
    # WITHOUT adding them to active_picks. Review gate: 2026-06-17.
    # Enable: CONNORS_RSI2_SHADOW=1 (default 0 = OFF). Fail-open.
    try:
        import os as _os_crs
        if _os_crs.environ.get("CONNORS_RSI2_SHADOW", "0") == "1":
            _crs_strat = str(pick.get("strategy") or pick.get("source_system") or "")
            _crs_ac = str(pick.get("asset_class", "") or "").upper().strip()
            if _crs_ac == "EQUITY" and _crs_strat == "connors_rsi2_scanner":
                import json as _json_crs
                from pathlib import Path as _Path_crs
                from datetime import datetime as _dt_crs, timezone as _tz_crs
                _shadow_path = _Path_crs(__file__).parent.parent / "alpha_engine" / "data" / "connors_rsi2_shadow_log.jsonl"
                _shadow_entry = {
                    **pick,
                    "_shadow": True,
                    "_shadow_logged_at": _dt_crs.now(_tz_crs.utc).isoformat(),
                    "_shadow_strategy": "connors_rsi2_scanner",
                }
                with open(_shadow_path, "a", encoding="utf-8") as _f_crs:
                    _f_crs.write(_json_crs.dumps(_shadow_entry) + "\n")
                pick["_connors_shadow_logged"] = True
                logger.debug(
                    "connors_rsi2 SHADOW logged: symbol=%s elite_score=%s",
                    pick.get("symbol", "?"), pick.get("elite_score"),
                )
    except Exception:
        pass  # fail-open: shadow logging must never block admission

    # ── EQUITY elite_score gate >= 55 (2026-05-16) ──
    # Verified on n=44 EQUITY closed picks (alpha_engine/data/closed_picks.json):
    #   elite_score <40:   n= 9  WR=22.2%
    #   elite_score 40-54: n=33  WR=36.4%   combined below-55: n=42 WR=33.3%
    #   elite_score 55-69: n= 1  WR=100.0%
    #   elite_score 70+:   n= 1  WR=100.0%
    # Below-55 band: n=42 >= 30 (criterion met) and WR=33.3% < 45% (criterion met).
    # Gate uses elite_score (0-100 composite); ml_composite_score as fallback.
    # Note: EQUITY picks do NOT carry gatekeeper_score; raw ml_score is 0.0-1.0
    # and is NOT comparable to the 55 threshold -- elite_score is the correct field.
    # Kill-switch: EQUITY_ML_SCORE_GATE_ENABLED=0 (default 1 = ON). Fail-open.
    try:
        import os as _os_emsg
        if _os_emsg.environ.get("EQUITY_ML_SCORE_GATE_ENABLED", "1") not in (
            "0", "false", "FALSE", "False"
        ):
            _emsg_ac = str(pick.get("asset_class", "") or "").upper().strip()
            if _emsg_ac == "EQUITY":
                _emsg_score = pick.get("elite_score") or pick.get("ml_composite_score")
                if _emsg_score is not None:
                    try:
                        _emsg_score_f = float(_emsg_score)
                    except (TypeError, ValueError):
                        _emsg_score_f = None
                    if _emsg_score_f is not None and _emsg_score_f < 55:
                        logger.debug(
                            "Pick rejected: EQUITY elite_score=%.1f < 55 (symbol=%s)",
                            _emsg_score_f, symbol,
                        )
                        return False
    except Exception:
        pass  # fail-open: never break admission on this gate

    # ── EQUITY_BLOCKED_SYMBOLS gate (2026-05-16) ──
    # EQUITY_BLOCKED_SYMBOLS was defined at line ~1376 but never enforced.
    # XLE/XOM: energy stocks confirmed 0W/4L from goldmine_stocks (now source-blocked).
    # CVX promoted to PROBATION — blocked here only until review 2026-07-01.
    # Kill-switch: EQUITY_SYMBOL_GATE_DISABLED=1 (default 0 = ON). Fail-open.
    try:
        if os.environ.get("EQUITY_SYMBOL_GATE_DISABLED", "0") not in ("1", "true", "True"):
            _esg_ac = str(pick.get("asset_class", "") or "").upper().strip()
            if _esg_ac == "EQUITY":
                _esg_sym = str(pick.get("symbol", "") or "").upper().strip()
                if _esg_sym in EQUITY_BLOCKED_SYMBOLS:
                    logger.debug(
                        "Pick rejected: EQUITY_BLOCKED_SYMBOLS (symbol=%s)", _esg_sym
                    )
                    return False
    except Exception:
        pass  # fail-open

    # ── ETF surgical blacklist — IWM + GLD (Phase 2-E 6/6 unanimous, 2026-04-29) ──
    # See ETF_BLACKLIST docstring above. IWM (small-cap, n=16, sum -11.67%) +
    # GLD (gold, n=11, WR 36.4%, sum -6.23%) drag the sector ETF (XLK/XLE/QQQ/
    # SOXX) edge. Preserves all other ETFs including broad-market SPY.
    # Default-on. Rollback: ETF_IWM_GLD_KILL_DISABLED=1
    _etf_ac = str(pick.get("asset_class", "") or "").upper().strip()
    if (
        _etf_ac == "ETF"
        and symbol.upper() in ETF_BLACKLIST
        and os.environ.get("ETF_IWM_GLD_KILL_DISABLED", "0") != "1"
    ):
        logger.debug(
            "Pick rejected: etf_iwm_gld_killed (%s) — Phase 2-E 6/6 panel",
            symbol,
        )
        return False

    # ── COMMODITY sub-class blacklist (Phase 2-D 2026-04-29) ──
    # See COMMODITY_BLACKLIST docstring above. Default-on; rollback flag
    # COMMODITY_SUBCLASS_KILL_DISABLED=1 restores legacy permissive behavior.
    _commodity_ac = str(pick.get("asset_class", "") or "").upper().strip()
    if (
        _commodity_ac in ("COMMODITY", "COMMODITIES")
        and symbol.upper() in COMMODITY_BLACKLIST
        and os.environ.get("COMMODITY_SUBCLASS_KILL_DISABLED", "0") != "1"
    ):
        logger.debug(
            "Pick rejected: commodity_subclass_killed (%s) — Phase 2-D 7/7 panel",
            symbol,
        )
        return False

    # ── wf_verdict=FAILING hard block (2026-04-28) ──
    # Per Copilot deep-dive (copilot/deep-dive-subagents-bad-classes branch) +
    # GitHub Cloud agent independent confirmation: walk-forward validator's
    # FAILING bucket has empirically catastrophic realized performance.
    # Local smoke (audit_dashboard/data/dashboard_data.json, recent_closed n=1194):
    #   WR=35.6%, PF=0.742, cum pnl_pct=-224.8%
    # Missing wf_verdict defaults to PASS (15.7% of corpus, don't false-reject).
    # Only blocks the explicit FAILING label.
    #
    # Safety env-var (added 2026-04-28 per 4/5 external-AI consensus,
    # reports/external_ai_review_pr480_wf_verdict_2026_04_28.md):
    #   WF_VERDICT_FAILING_BLOCK_ENABLED defaults to "1" (block ON, current behavior).
    #   Set to "0" for fast rollback if WR drops on next 7d of fresh picks.
    # Rationale: wf_verdict is computed from POST-TRADE strategy-aggregate data
    # (alpha_engine/walkforward_validator.py:53, back-stamped via
    # audit_trail/dashboard_generator.py:11898), so the n=1194 historical smoke
    # is partially tautological — env-var allows quick rollback without code change.
    # Hoist wf_verdict read so both blocks below can use it independently.
    _wf_raw = pick.get("wf_verdict")
    _wf_norm = str(_wf_raw or "").upper().strip()

    if os.environ.get("WF_VERDICT_FAILING_BLOCK_ENABLED", "1") == "1":
        if _wf_norm == "FAILING":
            logger.debug(
                "Pick rejected: wf_verdict=FAILING (%s %s) — n=1194 WR=35.6%% PF=0.742",
                symbol, pick.get("strategy", ""),
            )
            try:
                if _pll_tracer_m110 and _pll_pick_id_m110:
                    _pll_tracer_m110.log_filter(_pll_pick_id_m110, "tier_gate", "wf_verdict=FAILING", rule_id="RULE-TIER", pick_values={"symbol": symbol, "strategy": pick.get("strategy"), "wf_verdict": _wf_norm})
            except Exception:
                pass
            return False

    # ── Null wf_verdict opt-in block (2026-04-29) ──
    # Per 4-AI panel unanimous P0 verdict
    # (reports/findings_validation_synthesis_2026_04_29.md, Finding 1):
    # PR #480's FAILING-only block is functionally inert because 87% of
    # currently-active picks have wf_verdict=null — the gate only catches
    # 4/29 of them. Panel recommendation: "Treat null wf_verdict as
    # FAILING in the gate; reject ingestion or default-fail at the emitter."
    #
    # ROLLBACK SEMANTICS (per cross-AI pre-merge review): this block lives
    # OUTSIDE the WF_VERDICT_FAILING_BLOCK_ENABLED guard so disabling
    # PR #480's FAILING block (rollback to "0") does NOT silently disable
    # the null block. Each flag is independently controlled.
    #
    # Safety: this flag is DEFAULT-OFF. Flipping ON before backfilling the
    # 3 high-null emitters (alpha_engine_fast 39/39 null, aggregated_picks
    # 21/22 null, kimi_riseoftheclaw 119/285 null) would block ~87% of
    # currently-emitted picks. Operator flips on AFTER >=95% backfill.
    if (
        os.environ.get("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "0") == "1"
        and (_wf_raw is None or _wf_norm == "")
    ):
        logger.debug(
            "Pick rejected: wf_verdict=null treated as FAILING (%s %s) — opt-in flag ON",
            symbol, pick.get("strategy", ""),
        )
        try:
            if _pll_tracer_m110 and _pll_pick_id_m110:
                _pll_tracer_m110.log_filter(_pll_pick_id_m110, "tier_gate", "wf_verdict=null_treated_as_FAILING", rule_id="RULE-TIER", pick_values={"symbol": symbol, "strategy": pick.get("strategy")})
        except Exception:
            pass
        return False

    # ── Blocker 2 defense-in-depth (2026-04-22): hard-reject EXEMPT_FROM_SAFETY_GATES ──
    # Per reports/HC_GATE_BLOCKER_2_PLACEHOLDER_STATS_DIAGNOSIS_2026_04_22.md,
    # clone_hl_copy_* picks carry clone_safety_mode="EXEMPT_FROM_SAFETY_GATES"
    # AND placeholder stats (score ≈ forward_trades ≈ forward_wr, all derived from
    # the source whale's historical WR not the clone's own closed trades).
    # Safety gates exist for a reason — no strategy should ever bypass them.
    # This is restrictive-only (can't cause false negatives) and fully reversible.
    _safety_mode = str(pick.get("clone_safety_mode", "") or "").upper()
    if _safety_mode == "EXEMPT_FROM_SAFETY_GATES":
        logger.debug(
            "Pick rejected: clone_safety_mode=EXEMPT_FROM_SAFETY_GATES (%s %s)",
            symbol, pick.get("strategy", ""),
        )
        try:
            if _pll_tracer_m110 and _pll_pick_id_m110:
                _pll_tracer_m110.log_filter(_pll_pick_id_m110, "clone_safety_mode", "EXEMPT_FROM_SAFETY_GATES", rule_id="RULE-BLOCK", pick_values={"symbol": symbol, "strategy": pick.get("strategy")})
        except Exception:
            pass
        return False

    # Block specific losing strategies per asset class (2026-04-14)
    # Per TESTING_PROTOCOL ┬º7 and docs/strategy_audits/stocks_competition_2026-04-14.md
    _strategy = str(pick.get("strategy", "") or "").strip()
    _asset_class = str(pick.get("asset_class", "") or "").upper().strip()
    if is_strategy_blocked(_strategy, _asset_class):
        logger.debug(
            "Pick rejected: strategy=%s blocked for asset_class=%s (%s)",
            _strategy, _asset_class, symbol
        )
        return False

    # ── Healthcare cluster + GS LONG-momentum blacklist (Phase 2-B, 2026-04-29) ──
    # Per Phase 2-B EQUITY panel 9/9 UNANIMOUS systematic_sector_bias verdict
    # (reports/HFPA_PHASE-2-findings-EQUITY-2026-04-29.md), 6/3 preferred surgical
    # blacklist over sector-wide pharma ban.
    #
    # EQUITY 30d data (audit_dashboard/data/dashboard_data.json closed picks):
    #   JNJ:  n=23 LONG WR 13.0% sum -44.21% (8.2% of all EQUITY losses)
    #         dominant drag: stocks_competition Breakout Momentum 0/7 -18.70%,
    #         goldmine_stocks goldmine_6x_consensus 0/4 -18.54%
    #   ABBV: n=6  LONG WR 16.7% sum -12.99% (Bollinger MR + goldmine drag)
    #   MRK:  n=22 LONG WR 54.5% sum +2.66% overall, but goldmine_6x_consensus
    #         0/1 -4.22% (already killed via PR #514 goldmine_stocks). Defensive
    #         consistency: keep on momentum blacklist for sector-cohort symmetry.
    #   GS:   n=1  LONG WR 0.0% sum -2.02% (small n, panel cohort symmetry)
    #
    # Surgical: blocks LONG-direction on momentum-flavored strategies for these
    # 4 symbols only. Preserves SHORT exposure (panel: 5/4 stay long-only but
    # keep optionality). Other strategies (mean-reversion, dividend, etc.) still
    # allowed on these symbols.
    #
    # Default-on. Rollback: HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED=1
    if (
        _asset_class == "EQUITY"
        and symbol.upper() in JNJ_HEALTHCARE_GS_LONG_MOMENTUM_BLACKLIST
        and str(pick.get("direction", "") or "").upper() == "LONG"
        and _is_momentum_flavored(_strategy)
        and os.environ.get("HEALTHCARE_LONG_MOMENTUM_BLACKLIST_DISABLED", "0") != "1"
    ):
        logger.debug(
            "Pick rejected: healthcare_long_momentum_blacklisted (%s LONG strategy=%s)",
            symbol, _strategy,
        )
        return False

    # ── elite_grade D/F hard block (Action 1, 2026-04-12) ──
    # Data from filter analysis on 3,500 closed picks:
    #   Grade D: n=789 WR 30.9% PF 0.62 total PnL -419%
    #   Grade F: n=82  WR 32.9% PF 0.35 total PnL -90%
    # Combined: 871 picks (25%) losing -509% PnL. Blocking these lifts the
    # remaining pool PF from 1.24 to ~2.0+. Verified via Playwright on live
    # site + confirmed by cursor peer coordination in CHATWITHIT.MD.
    _pick_grade = str(pick.get("elite_grade", "") or "").upper()
    # UEPS long-horizon (3y+) value picks bypass elite_grade D when flag ON;
    # elite_grade is calibrated for short-term momentum, not 3y value picks.
    # Grade F is still blocked unconditionally.
    #
    # 2026-05-03: BOND/ETF exemption — Phase 3 remediation.
    # Bond strategies naturally score lower (no crypto boosters, lower vol).
    # Elite_grade D/F was blocking TLT (ml_score 0.859), IEF (0.839), LQD (0.743)
    # despite T2-quality metrics (PF 1.72, WR 50%). Exempting BOND and ETF
    # classes from this gate until non-crypto scoring is fully calibrated.
    # See ROOT_CAUSE_ANALYSIS_NON_CRYPTO.md Root Cause #6.
    _ac_grade = (pick.get("asset_class") or pick.get("category") or "").upper().strip()
    _is_bond_etf_exempt = _ac_grade in ("BOND", "ETF")
    # COMMODITY + FUTURES exemption (2026-05-14): revised 2026-05-16 swarm deep-dive.
    # multi_asset_cot + multi_asset_copytrader REMOVED — their "PF=20.54/WR=93.8%"
    # were pre-dedup artifacts (46x CT=F over-emission). Post-dedup: PF=0.17, WR=40%.
    # commodity_cot_contrarian kept (COT commercial signal, CFTC-backed, not artifact).
    # cta_replicator kept (academically validated CTA momentum, separate methodology).
    _is_commodity_futures_exempt = _ac_grade in ("COMMODITY", "COMMODITIES", "FUTURES") and str(
        pick.get("source_system", "") or ""
    ).lower() in {
        "commodity_cot_contrarian",
        "cta_replicator",
    }
    _is_bond_etf_exempt = _is_bond_etf_exempt or _is_commodity_futures_exempt
    if _pick_grade == "F" and not _is_bond_etf_exempt:
        logger.debug(
            "Pick rejected: elite_grade=%s hard-blocked (%s %s)",
            _pick_grade, symbol, pick.get("strategy", ""),
        )
        return False
    elif _pick_grade == "F" and _is_bond_etf_exempt:
        logger.debug(
            "Pick exempt: elite_grade=%s bond/ETF exemption (%s %s)",
            _pick_grade, symbol, pick.get("strategy", ""),
        )
    elif _pick_grade == "D" and not _ueps_long_horizon_bypass_active(pick) and not _is_bond_etf_exempt:
        logger.debug(
            "Pick rejected: elite_grade=%s hard-blocked (%s %s)",
            _pick_grade, symbol, pick.get("strategy", ""),
        )
        return False

    # ── Phase 1 confidence gate REVERTED 2026-04-22 (see PR #323 diagnosis) ──
    # The "confidence < 0.80 reject" gate added by PR #253 was removed because
    # the data it cited proved confidence is ANTI-predictive, not monotone:
    #   conf 0.00–0.55: WR 42.8% (BEST)     ← the gate was rejecting these
    #   conf 0.65–0.75: WR 26.2% (WORST)    ← the gate was KEEPING these
    #   conf 0.75–0.85: mean PnL −2.20%
    #   conf 0.85+:     WR 36.6%
    # Rejecting everything <0.80 was selecting for losing picks. Root cause of
    # the 2026-04-22 "only 5 active picks on /audit" incident: 15/90 false
    # rejects here + 21/90 false rejects at score<=0 (see Fix 2 below).
    # Unanimous 4-model consensus (gpt-oss-120b, kimi-k2.5, deepseek-v3.2,
    # glm-4.6) recommended full revert over shadow-mode or narrowing.
    #
    # The dead-zone gate below (reject ONLY 0.65–0.75 band) is retained — it
    # targets the actually-worst band and stays in shadow mode by default.
    _ac_upper = str(pick.get("asset_class", "") or "").upper()

    # ── Phase 1 confidence dead-zone gate (PR #291 deep investigation, 2026-04-21) ──
    # The 0.65–0.75 confidence band is a non-monotonic dead zone on crypto.
    # Cross-section (n=1695 closed crypto picks):
    #   conf 0.00–0.55: n=138  WR 42.8%
    #   conf 0.55–0.65: n=301  WR 41.9%
    #   conf 0.65–0.75: n=820  WR 26.2%   ← worst band, largest sample
    #   conf 0.75–0.85: n=365  WR 34.2%   mean PnL −2.20%
    #   conf 0.85–1.01: n=71   WR 36.6%
    # Within HC-pass crypto (n=121, post Kimi calibration): same pattern —
    # conf 0.55–0.65 → 67.3% WR, conf 0.65–0.75 → 20.0% WR.
    # The band absorbs picks from systems with mediocre score+trust but no real
    # alpha; rejecting it drops ~17% of HC volume in exchange for higher mean WR.
    #
    # Env-tunable:
    #   PHASE1_CONF_DEADZONE_ENABLED  (1/0/shadow, default 1 for CRYPTO)
    #   PHASE1_CONF_DEADZONE_LOW      (float, default 0.65)
    #   PHASE1_CONF_DEADZONE_HIGH     (float, default 0.75)
    #
    # Related: updates/2026-04-21-deep-strategy-investigation-by-asset-class.md (§7).
    _dz_mode = os.environ.get("PHASE1_CONF_DEADZONE_ENABLED", "shadow").lower()
    if _dz_mode != "0" and _ac_upper == "CRYPTO":
        try:
            _dz_lo = float(os.environ.get("PHASE1_CONF_DEADZONE_LOW", "0.65"))
            _dz_hi = float(os.environ.get("PHASE1_CONF_DEADZONE_HIGH", "0.75"))
        except ValueError:
            _dz_lo, _dz_hi = 0.65, 0.75
        _raw_dz_conf = pick.get("confidence")
        if _raw_dz_conf is not None:
            try:
                _dz_conf = float(_raw_dz_conf)
            except (TypeError, ValueError):
                _dz_conf = None
            if _dz_conf is not None and _dz_lo <= _dz_conf < _dz_hi:
                if _dz_mode == "shadow":
                    pick["_phase1_dz_shadow_reject"] = (
                        f"confidence={_dz_conf:.3f} in dead zone [{_dz_lo}, {_dz_hi})"
                    )
                else:
                    logger.debug(
                        "Pick rejected: confidence=%.3f in dead zone [%.2f, %.2f) (%s %s)",
                        _dz_conf, _dz_lo, _dz_hi, symbol, pick.get("strategy", ""),
                    )
                    try:
                        if _pll_tracer_m110 and _pll_pick_id_m110:
                            _pll_tracer_m110.log_filter(_pll_pick_id_m110, "confidence_threshold", f"dead_zone:{_dz_conf:.3f}_in[{_dz_lo:.2f},{_dz_hi:.2f})", rule_id="RULE-THRESH", pick_values={"symbol": symbol, "confidence": _dz_conf})
                    except Exception:
                        pass
                    return False

    # ── Phase 1 time-of-day gate (2026-04-17 deep-dive + 2026-04-21 PR #291 expansion) ──
    # Two death windows on crypto:
    #
    #   Window A: 08:00–11:00 UTC (original 2026-04-17 finding, n=697 −164% cum)
    #   Window B: 16:00–21:00 UTC (PR #291 deep investigation, n=460 over 6 hours):
    #     16:00 UTC n=60  WR 20.0% mean −0.76%
    #     17:00 UTC n=55  WR 18.2% mean −0.77%
    #     18:00 UTC n=81  WR 25.9% mean −0.48%
    #     19:00 UTC n=83  WR 19.3% mean −0.87%
    #     20:00 UTC n=117 WR 17.1% mean −1.03%   ← worst single hour in dataset
    #     21:00 UTC n=64  WR 20.3% mean −0.71%
    #
    # By contrast, 22:00–23:00 UTC is the BEST window (WR 63–72%, mean +0.81–1.08%).
    # Filter excludes 10 hours total (45% of trading day); leaves 22-07 UTC + 12-15 UTC
    # which is where ~60% of the productive volume lives.
    #
    # Env-tunable:
    #   PHASE1_TOD_GATE_HOURS   (CSV of UTC hours to block, default "8,9,10,11,16,17,18,19,20,21")
    #   PHASE1_TOD_GATE_ENABLED (1/0/shadow, default 1 for CRYPTO)
    #
    # Related: PR #291 deep-investigation, feedback_quick_guess_horizons.md,
    # project_clean_data_symbol_wr.md (22 UTC best, 08-09 + 16-21 worst).
    _tod_mode = os.environ.get("PHASE1_TOD_GATE_ENABLED", "shadow").lower()
    if _tod_mode != "0" and _ac_upper == "CRYPTO":
        _hours_env = os.environ.get(
            "PHASE1_TOD_GATE_HOURS", "8,9,10,11,16,17,18,19,20,21"
        )
        try:
            _blocked_hours = {int(h.strip()) for h in _hours_env.split(",") if h.strip()}
        except ValueError:
            _blocked_hours = {8, 9, 10, 11, 16, 17, 18, 19, 20, 21}
        # Use the pick's intended entry moment; fall back to the row timestamp
        _entry_ts = (
            pick.get("entry_time")
            or pick.get("opened_at")
            or pick.get("timestamp")
            or pick.get("created_at")
        )
        _entry_hour = None
        if _entry_ts:
            try:
                _entry_dt = datetime.fromisoformat(
                    str(_entry_ts).replace("Z", "+00:00")
                )
                if _entry_dt.tzinfo is not None:
                    _entry_dt = _entry_dt.astimezone(timezone.utc)
                _entry_hour = _entry_dt.hour
            except Exception:
                _entry_hour = None
        if _entry_hour is None:
            # Use current UTC hour as best guess — prevents stale picks from slipping
            # past the window check when the source omits a timestamp.
            _entry_hour = datetime.now(timezone.utc).hour
        if _entry_hour in _blocked_hours:
            if _tod_mode == "shadow":
                pick["_phase1_tod_shadow_reject"] = (
                    f"entry_hour={_entry_hour:02d}:00Z in blocked window "
                    f"{sorted(_blocked_hours)}"
                )
            else:
                logger.debug(
                    "Pick rejected: entry_hour=%02d:00Z in Phase1 block window %s (%s %s)",
                    _entry_hour, sorted(_blocked_hours), symbol,
                    pick.get("strategy", ""),
                )
                return False

    # ── PSI drift gate (task J / handoff P1) ──
    # Bind on alpha_engine/feature_health.py PSI output. When ANY feature has
    # drifted beyond PSI_BLOCK_THRESHOLD (0.25), downstream ML scores and
    # rule-based features keyed on that distribution become unreliable. Env-
    # gated for staged rollout (matches signal_ts_strict / bear_day_strict):
    #   PSI_GATE_STRICT=shadow (default) — log + tag pick, do NOT reject
    #   PSI_GATE_STRICT=1               — hard reject while drift is active
    #   PSI_GATE_STRICT=0               — disable entirely
    # SHADOW — remove after 48h forward observation
    try:
        _psi_mode = os.environ.get("PSI_GATE_STRICT", "shadow").lower()
        if _psi_mode != "0":
            _max_psi, _drifted_feats = _get_max_psi()
            if _max_psi > PSI_BLOCK_THRESHOLD:
                if _psi_mode == "1":
                    logger.info(
                        "PICK_REJECTED psi_gate_strict symbol=%s strategy=%s "
                        "max_psi=%.3f drifted=%s",
                        symbol, pick.get("strategy", ""), _max_psi,
                        ",".join(_drifted_feats[:5]),
                    )
                    return False
                # shadow mode: tag without rejecting
                pick["_psi_shadow_reject"] = (
                    f"max_psi={_max_psi:.3f} > {PSI_BLOCK_THRESHOLD} "
                    f"(drifted: {','.join(_drifted_feats[:3])})"
                )
    except Exception:
        pass  # never break admission on this gate

    # ── COT lag-correction + MATCH + friction-adjusted DSR gate (M-008/M-021) ──
    # COMMODITY picks from multi_asset_cot are gated on:
    #   1. 3-day CFTC publication lag applied to effective_date (no look-ahead bias).
    #   2. MATCH verdict: commercial and speculator net positioning must be opposite.
    #   3. Friction-adjusted DSR >= COT_DSR_FLOOR (default 0.50). Friction is
    #      8 bps (0.0008) — see tools/cot_lag_corrector.FRICTION_RATE for
    #      derivation. Prior value 0.08 (800 bps) was 100x too high.
    #
    # Env-gated for staged rollout:
    #   COT_MATCH_GATE_ENABLED = shadow (default) — log + tag pick, do NOT reject
    #   COT_MATCH_GATE_ENABLED = 1                — hard reject on non-MATCH or low DSR
    #   COT_MATCH_GATE_ENABLED = 0                — disable entirely (tests default)
    #
    # Wire-Up Rule compliance: production caller is this function (passes_active_gate).
    # The gate is COMMODITY-scoped only. All other asset classes bypass.
    try:
        _cot_gate_mode = os.environ.get("COT_MATCH_GATE_ENABLED", "shadow").lower()
        if _cot_gate_mode != "0":
            _cot_ac = str(pick.get("asset_class", "") or "").upper()
            if _cot_ac == "COMMODITY":
                from tools.cot_lag_corrector import check_cot_gate as _check_cot_gate
                _cot_ok, _cot_reason = _check_cot_gate(pick)
                if not _cot_ok:
                    if _cot_gate_mode == "1":
                        logger.info(
                            "PICK_REJECTED cot_gate symbol=%s strategy=%s reason=%s",
                            symbol, pick.get("strategy", ""), _cot_reason,
                        )
                        return False
                    # shadow mode: tag without rejecting
                    pick["_cot_shadow_reject"] = _cot_reason
                    logger.debug(
                        "COT gate shadow-reject symbol=%s reason=%s", symbol, _cot_reason
                    )
    except Exception:
        pass  # fail-open: never block picks on COT gate errors

    # ── COT dedup guard (PR-#994, 2026-05-15): 1-pick-per-symbol-per-72h ──
    # Prevents multi_asset_cot / cot_positioning from emitting repeated picks on
    # the same symbol across consecutive CFTC weekly release cycles, which inflated
    # COMMODITY n=130 to appear as genuine trades rather than repeated signals.
    # Observed: CT=F (cotton) was 94.3% of COMMODITY picks; after dedup WR=40%/PF=0.17.
    # Logic: if any pick for the same symbol from the same COT source_system is already
    # in the active_picks cache AND was admitted within COT_DEDUP_WINDOW_HOURS, reject.
    # Fail-open (exceptions never block picks). Kill-switch: COT_DEDUP_GATE_ENABLED=0.
    try:
        import os as _os_cot_dedup
        if _os_cot_dedup.environ.get("COT_DEDUP_GATE_ENABLED", "1") not in (
            "0", "false", "FALSE", "False"
        ):
            _cot_ss = str(pick.get("source_system", "") or "").lower().strip()
            _cot_ac = str(pick.get("asset_class", "") or "").upper().strip()
            if _cot_ss in COT_DEDUP_SYSTEMS and _cot_ac in ("COMMODITY", "COMMODITIES", "FUTURES"):
                import time as _time_cot
                _now_cot = _time_cot.time()
                _dedup_sym = str(pick.get("symbol", "") or "").upper().strip()
                _active_cot = _cached_active_picks_snapshot()
                for _ap in _active_cot:
                    if not isinstance(_ap, dict):
                        continue
                    if str(_ap.get("source_system", "") or "").lower().strip() != _cot_ss:
                        continue
                    if str(_ap.get("symbol", "") or "").upper().strip() != _dedup_sym:
                        continue
                    # Same source_system + same symbol — check admission age
                    _ap_ts = _ap.get("admitted_at") or _ap.get("timestamp") or _ap.get("created_at") or 0
                    if isinstance(_ap_ts, str):
                        try:
                            import datetime as _dt_cot
                            _ap_ts = _dt_cot.datetime.fromisoformat(
                                _ap_ts.replace("Z", "+00:00")
                            ).timestamp()
                        except Exception:
                            _ap_ts = 0
                    _age_hours = (_now_cot - float(_ap_ts or 0)) / 3600.0
                    if 0 < _age_hours < COT_DEDUP_WINDOW_HOURS:
                        logger.info(
                            "PICK_REJECTED cot_dedup symbol=%s source=%s age=%.1fh < %dh window",
                            _dedup_sym, _cot_ss, _age_hours, COT_DEDUP_WINDOW_HOURS,
                        )
                        return False
    except Exception:
        pass  # fail-open: never block picks on COT dedup errors

    # ── M-001: COT data staleness gate (2026-05-18) ─────────────────────────────
    # CFTC publishes weekly (Friday ~3:30pm ET for prior Tuesday positions).
    # If a pick's latest_cot_date is > COT_STALE_DAYS (default 10) days old,
    # the COT data is stale (likely a missed release or fetch failure).
    # Shadow mode (default): stamp _cot_data_stale=True, never block.
    # Enforce: COT_STALE_GATE_ENFORCE=1 → hard reject COMMODITY/COT picks.
    # Kill-switch: COT_STALE_GATE_DISABLED=1.
    try:
        import os as _os_m001
        _m001_ac = str(pick.get("asset_class", "") or "").upper().strip()
        _m001_ss = str(pick.get("source_system", "") or "").lower().strip()
        _m001_cot_sources = {"cot_positioning", "multi_asset_cot", "cftc_cot_commercial_signal"}
        if (
            _m001_ac == "COMMODITY"
            and _m001_ss in _m001_cot_sources
            and _os_m001.environ.get("COT_STALE_GATE_DISABLED", "0") not in ("1", "true", "True", "TRUE")
        ):
            _m001_cot_date_str = str(
                pick.get("latest_cot_date")
                or (pick.get("extra") or {}).get("latest_cot_date")
                or ""
            ).strip()
            if _m001_cot_date_str:
                import datetime as _dt_m001
                _m001_stale_days = int(_os_m001.environ.get("COT_STALE_DAYS", "10"))
                try:
                    _m001_cot_dt = _dt_m001.datetime.strptime(_m001_cot_date_str[:10], "%Y-%m-%d")
                    _m001_age_days = (_dt_m001.datetime.utcnow() - _m001_cot_dt).days
                    if _m001_age_days > _m001_stale_days:
                        _m001_enforce = _os_m001.environ.get("COT_STALE_GATE_ENFORCE", "1") == "1"
                        if _m001_enforce:
                            logger.info(
                                "M-001 cot_stale_gate: REJECTED %s cot_date=%s age=%dd > %dd",
                                pick.get("symbol", ""), _m001_cot_date_str,
                                _m001_age_days, _m001_stale_days,
                            )
                            return False
                        else:
                            pick["_cot_data_stale"] = True
                            pick["_cot_data_age_days"] = _m001_age_days
                            logger.debug(
                                "M-001 cot_stale_gate: SHADOW %s cot_date=%s age=%dd > %dd (set COT_STALE_GATE_ENFORCE=1 to enforce)",
                                pick.get("symbol", ""), _m001_cot_date_str,
                                _m001_age_days, _m001_stale_days,
                            )
                except ValueError:
                    pass  # unparseable date → skip staleness check
    except Exception:
        pass  # fail-open

    # ── M-002: CT=F weekly signal concentration cap (2026-05-18) ─────────────────
    # CT=F (Cotton) represented 44.6% of COMMODITY signals in the 7-day window
    # on 2026-05-18 — above the 40% cap. PBO is invalid when a single symbol
    # dominates (single-name autocorrelation). Gate checks CLOSED + ACTIVE
    # COMMODITY picks from the last 7 days; blocks new CT=F if share > 40%.
    # Enforce-by-default (COMMODITY_CTF_WEEKLY_CAP=1). Promoted from shadow 2026-05-18:
    # CT=F at 46.2% blocks PBO computation (single-name autocorrelation). Required for
    # COMMODITY MONEY_READY path (M-005 PBO gate). Kill: COMMODITY_CTF_WEEKLY_CAP=off.
    # Downgrade to shadow: COMMODITY_CTF_WEEKLY_CAP=shadow. Fail-open.
    if str(pick.get("asset_class", "") or "").upper() == "COMMODITY":
        try:
            import os as _os_m002
            _m002_mode = _os_m002.environ.get("COMMODITY_CTF_WEEKLY_CAP", "1").lower()
            if _m002_mode not in ("off", "0", "disabled"):
                _m002_sym = str(pick.get("symbol", "") or "").upper().strip()
                if _m002_sym == "CT=F":
                    _m002_window_days = int(_os_m002.environ.get("CTF_WEEKLY_WINDOW_DAYS", "7"))
                    _m002_cap = float(_os_m002.environ.get("CTF_WEEKLY_CAP_PCT", "0.40"))
                    import json as _json_m002
                    import datetime as _dt_m002
                    from pathlib import Path as _Path_m002
                    _data_root_m002 = _Path_m002(__file__).resolve().parent.parent / "alpha_engine" / "data"
                    _cutoff_m002 = _dt_m002.datetime.utcnow() - _dt_m002.timedelta(days=_m002_window_days)

                    def _m002_pick_dt(p: dict) -> _dt_m002.datetime:
                        ts = p.get("timestamp") or p.get("created_at") or ""
                        try:
                            return _dt_m002.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).replace(tzinfo=None)
                        except Exception:
                            return _dt_m002.datetime.min

                    _closed_path_m002 = _Path_m002(
                        _os_m002.environ.get("CTF_CLOSED_PICKS_PATH", str(_data_root_m002 / "closed_picks.json"))
                    )
                    _active_path_m002 = _Path_m002(
                        _os_m002.environ.get("CTF_ACTIVE_PICKS_PATH", str(_data_root_m002 / "active_picks.json"))
                    )
                    _all_picks_m002: list = []
                    if _active_path_m002.exists():
                        _all_picks_m002 += _json_m002.loads(_active_path_m002.read_text(encoding="utf-8"))
                    if _closed_path_m002.exists():
                        _all_picks_m002 += _json_m002.loads(_closed_path_m002.read_text(encoding="utf-8"))

                    _recent_comm_m002 = [
                        p for p in _all_picks_m002
                        if str(p.get("asset_class", "") or "").upper() == "COMMODITY"
                        and _m002_pick_dt(p) >= _cutoff_m002
                    ]
                    _total_m002 = len(_recent_comm_m002)
                    if _total_m002 >= 10:
                        _ctf_count_m002 = sum(
                            1 for p in _recent_comm_m002
                            if str(p.get("symbol", "") or "").upper() == "CT=F"
                        )
                        _ctf_share_m002 = _ctf_count_m002 / _total_m002
                        if _ctf_share_m002 >= _m002_cap:
                            if _m002_mode == "1":
                                logger.info(
                                    "M-002 ctf_weekly_cap: REJECTED CT=F — %dd window %.1f%% >= %.0f%% cap (n=%d)",
                                    _m002_window_days, _ctf_share_m002 * 100,
                                    _m002_cap * 100, _total_m002,
                                )
                                return False
                            else:
                                pick["_ctf_weekly_concentration"] = round(_ctf_share_m002 * 100, 1)
                                logger.debug(
                                    "M-002 ctf_weekly_cap: SHADOW CT=F=%.1f%% >= %.0f%% in %dd window (set COMMODITY_CTF_WEEKLY_CAP=1 to enforce)",
                                    _ctf_share_m002 * 100, _m002_cap * 100, _m002_window_days,
                                )
        except Exception:
            pass  # fail-open

    # Block specific strategy+symbol pairs with proven 0% WR
    strategy = str(pick.get("strategy", "") or "")
    # Raw dashboard score before penalties (elite_score must not satisfy min-score tests)
    raw_active_score = _float(pick.get("score", 0))
    if (strategy, symbol.upper()) in BLOCKED_STRATEGY_SYMBOL_PAIRS:
        logger.debug(
            f"Pick rejected: blocked strategy+symbol pair ({strategy}, {symbol})"
        )
        return False

    # ── Matrix CSV gates (system ├ù symbol block / optional allow-only) ──
    _mx_block, _mx_reason = matrix_symbol_gate_blocks(pick)
    if _mx_block:
        logger.debug("Pick rejected: matrix symbol gate (%s)", _mx_reason)
        return False

    # ── SANDBOX experiments: relabel passing picks (strategy + trust_tier) ──
    apply_sandbox_experiment_relabels(pick)
    strategy = str(pick.get("strategy", "") or "")

    # ── Mutation filter: enforce symbol-lock / direction-filter for CANDIDATE mutations ──
    if _MUTATIONS_AVAILABLE and strategy in ALL_MUTATIONS:
        direction = str(pick.get("direction", "") or "").upper()
        allowed, mutation_reason = check_mutation_filter(strategy, symbol, direction)
        if not allowed:
            logger.debug(f"Pick rejected by mutation filter: {mutation_reason}")
            return False

    # ── Mutation re-attribution: if a BANNED parent strategy has a viable mutation,
    #    re-attribute the pick to the mutation variant instead of hard-blocking ──
    if _MUTATIONS_AVAILABLE and strategy.lower() in _KILLED_STRATEGIES_LOWER:
        direction = str(pick.get("direction", "") or "").upper()
        variant_id = get_mutation_for_parent(strategy, symbol, direction)
        if variant_id:
            logger.info(
                f"Pick re-attributed from banned {strategy} to mutation {variant_id} "
                f"(symbol={symbol}, direction={direction})"
            )
            pick["strategy"] = variant_id
            pick["_original_strategy"] = strategy
            pick["_mutation_applied"] = True
            strategy = variant_id  # update local var for downstream checks

    # PnL sanity check — flag picks with impossible PnL values
    _pnl = _float(pick.get("pnl_pct", 0))
    if _pnl < PNL_SANITY_MIN or _pnl > PNL_SANITY_MAX:
        logger.warning(
            f"Pick {symbol} has insane PnL={_pnl}% — likely data quality issue"
        )
        # Don't hard-reject but flag and penalize heavily
        pick["_pnl_anomaly"] = True
        current_score = _float(pick.get("score", 50))
        pick["score"] = max(0, current_score - 50)

    # R:R sanity check — reject mathematically impossible or exploitative R:R
    # Gated by AUDIT_PICK_SANITY_GATE (matching pick_sanity gate behavior)
    if _audit_pick_sanity_gate_enabled():
        entry_price = _float(pick.get("entry_price", 0))
        tp_price = _float(pick.get("take_profit", 0))
        sl_price = _float(pick.get("stop_loss", 0))
        if entry_price > 0 and tp_price > 0 and sl_price > 0:
            risk = abs(entry_price - sl_price)
            reward = abs(tp_price - entry_price)
            if risk > 0:
                rr = reward / risk
                if rr > 20 or rr < 0.1:
                    logger.debug(
                        "Pick rejected: insane R:R=%.2f (entry=%.4f tp=%.4f sl=%.4f) %s",
                        rr, entry_price, tp_price, sl_price, symbol,
                    )
                    return False

    # Trade geometry check — gated by AUDIT_PICK_SANITY_GATE
    if _audit_pick_sanity_gate_enabled():
        if not _has_valid_trade_geometry(pick):
            logger.debug("Pick rejected: invalid crypto trade geometry")
            return False

    if (
        _audit_pick_sanity_gate_enabled()
        and _PICK_SANITY_PASS is not None
        and not _pick_sanity_gate_exempt(pick)
        and not _PICK_SANITY_PASS(pick)
    ):
        logger.debug("Pick rejected: pick_sanity (AUDIT_PICK_SANITY_GATE)")
        return False

    # Apply score penalties (quality signals adjust score, not visibility)
    _apply_score_penalties(pick)

    # Strict-mode copy-trade verification hard reject (opt-in). When
    # COPYTRADE_VERIFICATION_STRICT=1 and verify_copy_pick returned FAIL inside
    # _apply_score_penalties, the pick is flagged and must be dropped.
    if pick.get("_copytrade_verification_rejected"):
        logger.debug("Pick rejected: copytrade verification FAIL (strict mode)")
        return False

    asset_class = str(pick.get("asset_class", "CRYPTO")).upper()
    source_sys = str(pick.get("source_system", pick.get("source", "")) or "")

    # ETF: hard ban REMOVED 2026-04-19. Was a "Phase 1 rehab" emergency measure that
    # became permanent by neglect. ETF n=4 is thin, but the hard ban created a data
    # starvation catch-22 - no picks can flow to build the forward history needed to
    # justify unblocking. ETF also removed from BLOCKED_ASSET_CLASSES (was -60).
    # Quality filtering now relies on normal score penalties + soft gates instead.

    # ── Pair-level exception carve-out (B19, 2026-05-02) ──
    # Carve-out scope is intentionally narrow: it can bypass score/forward-WR
    # floors only. It must NOT bypass hard blocklists (asset×strategy/source,
    # blocked symbols/systems, strategy kill switches, trust-tier catastrophics).
    _pair_exc_active = _PAIR_EXCEPTIONS_AVAILABLE and should_pair_exception_pass(pick)

    # Hard-block toxic asset×strategy / asset×source combinations (penalties alone are not enough)
    if (asset_class, strategy) in BLOCKED_ASSET_STRATEGY_PAIRS:
        logger.debug("Pick rejected: blocked asset class + strategy")
        try:
            if _pll_tracer_m110 and _pll_pick_id_m110:
                _pll_tracer_m110.log_filter(_pll_pick_id_m110, "asset_strategy_pairs", f"blocked:{asset_class}/{strategy}", rule_id="RULE-BLOCK", pick_values={"symbol": pick.get("symbol"), "asset_class": asset_class, "strategy": strategy})
        except Exception:
            pass
        return False
    if (asset_class, source_sys) in BLOCKED_ASSET_SOURCE_PAIRS:
        logger.debug("Pick rejected: blocked asset class + source system")
        try:
            if _pll_tracer_m110 and _pll_pick_id_m110:
                _pll_tracer_m110.log_filter(_pll_pick_id_m110, "source_system_blocklist", f"blocked:{asset_class}/{source_sys}", rule_id="RULE-BLOCK", pick_values={"symbol": pick.get("symbol"), "source_system": source_sys})
        except Exception:
            pass
        return False

    # ── T2-01 emitter registry gate (pf_registry whitelist + toxic kill, 2026-05-19) ──
    try:
        from alpha_engine.emitter_whitelist import passes_emitter_registry_gate
        if not passes_emitter_registry_gate(pick):
            logger.debug(
                "Pick rejected: emitter_registry_gate %s",
                pick.get("_hf_quality_gate_reason", ""),
            )
            try:
                if _pll_tracer_m110 and _pll_pick_id_m110:
                    _pll_tracer_m110.log_filter(
                        _pll_pick_id_m110,
                        "emitter_registry_gate",
                        str(pick.get("_hf_quality_gate_reason", "blocked")),
                        rule_id="RULE-EMITTER-REGISTRY",
                        pick_values={"symbol": pick.get("symbol"), "strategy": strategy},
                    )
            except Exception:
                pass
            return False
    except Exception as _emitter_err:
        logger.warning("emitter_registry_gate import/call failed (fail-open): %s", _emitter_err)

    # 2026-05-13 NS-C (4-engine swarm UNANIMOUS SHIP) + NS-E (3-of-4 SHIP):
    # Two execution-gate filters added at this layer per memory
    # feedback_gate_at_execution_not_generation (gates must fire at exec,
    # not just intake).
    #
    # Reviewer fixes 2026-05-13 (cavecrew-reviewer a4675164325a20c2e):
    #   - parse: accept space-separated ISO, Unix epoch, and Z-suffix
    #   - env: truthy helper accepts "1"/"true"/"yes"/"on"
    #   - audit: set _hf_quality_gate_reason before return False
    #
    # NS-C: CRYPTO UTC-hour seasonal filter. UPDATED 2026-05-13.
    # Prior memory project_clean_data_symbol_wr claimed 22 UTC = 61.2% WR peak +
    # 08-09 UTC death zone. tools/backtest_btc_utc_hour_filter.py (BTC-only)
    # showed 6 UTC = 23.1% WR / PF 0.06 — the empirically-worst hour. 4-engine
    # swarm review 2026-05-13 split 2/2 on REPLACE vs ADD: 2 engines flagged
    # original (8,9) memory may still hold for non-BTC symbols (Asia-open
    # liquidity dynamics). Conservative resolution: reject 6 UTC (new evidence)
    # AND retain (8,9) (original memory not falsified for full CRYPTO universe).
    # Estimated CRYPTO WR lift: +1.11pp (BTC backtest) + retained (8,9) coverage.
    def _truthy(v: str | None, default: str = "0") -> bool:
        s = str(v if v is not None else default).strip().lower()
        return s in ("1", "true", "yes", "on", "t", "y")

    if str(asset_class).upper() == "CRYPTO" and _truthy(
        os.environ.get("CRYPTO_UTC_HOUR_FILTER"), "1"
    ):
        _ts = pick.get("created_at") or pick.get("timestamp")
        if _ts:
            _hr = None
            try:
                if isinstance(_ts, (int, float)):
                    _hr = datetime.fromtimestamp(float(_ts), tz=timezone.utc).hour
                else:
                    _ts_str = str(_ts).replace("Z", "+00:00").replace(" ", "T", 1)
                    _dt_obj = datetime.fromisoformat(_ts_str)
                    if _dt_obj.tzinfo is None:
                        _dt_obj = _dt_obj.replace(tzinfo=timezone.utc)
                    _hr = _dt_obj.hour
            except (ValueError, TypeError, OSError):
                _hr = None
            if _hr is not None and _hr in (6, 8, 9):
                pick["_hf_quality_gate_reason"] = (
                    f"ns_c_crypto_utc_death_zone_hr{_hr}"
                )
                logger.debug(
                    "Pick rejected: CRYPTO UTC death-zone hour %d (NS-C filter)", _hr
                )
                return False

    # NS-D: ml_crypto_pred LONG-side reject. Per AA-1 autopsy 2026-05-13:
    # LONG sub-strategy = 3W/22L = 12.0% WR; SHORT sub-strategy = 6W/1L =
    # 85.7% WR (n=7, thin). 4/4-engine swarm consensus 2026-05-13: Option A
    # (hard REJECT LONG) preserves the working SHORT side and is one-line
    # reversible. Expected PF lift: ~0.22 (system 1.25 -> ~1.55 projected).
    # See reports/aa1_ml_crypto_pred_autopsy_20260513.md + reports/
    # swarm_revalid_20260513/swarm_ml_impl/.
    if _truthy(os.environ.get("ML_CRYPTO_PRED_LONG_REJECT"), "1"):
        _src_lower = str(pick.get("source_system", "") or "").strip().lower()
        if _src_lower in ("ml_crypto_pred", "ml_crypto_predictor"):
            _dir_upper = str(
                pick.get("direction") or pick.get("signal_type") or ""
            ).strip().upper()
            if _dir_upper in ("LONG", "BUY"):
                pick["_hf_quality_gate_reason"] = (
                    "ns_d_ml_crypto_pred_long_reject"
                )
                logger.debug(
                    "Pick rejected: ml_crypto_pred LONG (NS-D filter — "
                    "12%% WR vs 85.7%% SHORT per AA-1 autopsy)"
                )
                return False

    # NS-F: CRYPTO LONG-in-BEAR regime reject (Edge #11). Per CRYPTO swarm
    # 2026-05-13 + memory feedback_long_source_bias: 7 production sources are
    # 99-100% LONG-only; their LONGs bleed when BTC 4h is bearish. Existing
    # elite_scorer applies a -8 to -14 score penalty but no hard reject.
    # 3/4-engine swarm consensus 2026-05-13: Option A (universal CRYPTO LONG
    # in BEAR reject) — simplest, no hardcoded source list to maintain.
    # Reads pick['btc_regime'] already populated upstream (conviction_stack).
    # Preserves all SHORT signals (working side). Expected PF lift: ~0.14.
    # See reports/swarm_revalid_20260513/swarm_edge11_impl/.
    if str(asset_class).upper() == "CRYPTO" and _truthy(
        os.environ.get("BTC_BEAR_LONG_REJECT"), "1"
    ):
        _dir_f = str(
            pick.get("direction") or pick.get("signal_type") or ""
        ).strip().upper()
        if _dir_f in ("LONG", "BUY"):
            _btc_reg_f = str(
                pick.get("btc_regime") or pick.get("regime_at_entry") or ""
            ).strip().upper()
            _is_bear = (
                "BEAR" in _btc_reg_f
                or "DOWN" in _btc_reg_f
                or _btc_reg_f == "BEARISH"
                or pick.get("btc_below_200ma") is True
            )
            if _is_bear:
                pick["_hf_quality_gate_reason"] = "ns_f_btc_bear_long_reject"
                logger.debug(
                    "Pick rejected: CRYPTO LONG in BEAR BTC regime "
                    "(NS-F filter — Edge #11)"
                )
                return False

    # NS-E / M-007: FOREX hard-disable until carry-factor (Edge #14) rehab.
    # PF=0.87 / sizing_allowed bug fixed 2026-05-15 (dashboard_generator:5455).
    # Default flipped ON (was "0") per user approval 2026-05-15: no FOREX
    # emissions until carry backtest achieves PF>1.0 / WR>45 / n>30.
    # Override: FOREX_HARD_DISABLE=0 to re-enable after carry ships.
    #
    # FOREX_COPYTRADER_ENABLE=1 (default OFF): bypasses this gate ONLY
    # for source_system=multi_asset_copytrader. DO NOT ENABLE — all-time
    # closed_picks shows WR=16.5%, PF=0.23, n=696. Prior comment citing
    # WR=64.7% was erroneous (no timestamp filter worked on closed_picks).
    # Enable ONLY if n≥30 clean per-source with verified WR≥50%, PF≥1.5.
    _forex_bypass_src = str(pick.get("source_system") or "").strip().lower()
    _forex_copytrader_exempt = (
        os.environ.get("FOREX_COPYTRADER_ENABLE", "0") == "1"
        and _forex_bypass_src == "multi_asset_copytrader"
    )
    if str(asset_class).upper() == "FOREX" and _truthy(
        os.environ.get("FOREX_HARD_DISABLE"), "1"
    ) and not _forex_copytrader_exempt:
        pick["_hf_quality_gate_reason"] = "ns_e_forex_hard_disable"
        # F-003: emit INFO (not DEBUG) so FOREX hard-disable appears in the audit trail.
        # Ticket: MASTER_ACTION_PLAN_2026-05-18 F-001/F-003.
        # Rationale: docs/FOREX_HARD_DISABLE_RATIONALE.md (PF=0.27/WR=46.4%/n=1169).
        # Re-enable criteria: FOREX_HARD_DISABLE=0 ONLY after carry-factor backtest
        # achieves PF>1.0 / WR>45% / n>=30.
        logger.info(
            "Pick rejected: FOREX_HARD_DISABLE=1 [F-001/F-003] "
            "(symbol=%s, source=%s) — see docs/FOREX_HARD_DISABLE_RATIONALE.md",
            str(pick.get("symbol", "")),
            str(pick.get("source_system", "")),
        )
        return False

    # ── CRYPTO production LONG block (MASTERPLAN 2026-06-05, INCIDENT CRYPTO directional) ──
    # Tournament + trading_picks: LONG ~33–43% WR vs SHORT ~54–67%. EAGLE-4 flips in
    # production_scanner only; emitters that bypass the scanner still surface LONGs.
    # Default ON. Exempt picks already flipped (_eagle4_flipped) or explicit override.
    _crypto_ac = str(asset_class or pick.get("category") or "").upper()
    _crypto_dir = str(pick.get("direction") or pick.get("side") or "").upper()
    if (
        _crypto_ac == "CRYPTO"
        and _crypto_dir in ("LONG", "BUY")
        and _truthy(os.environ.get("CRYPTO_PRODUCTION_BLOCK_LONG"), "1")
        and not pick.get("_eagle4_flipped")
        and os.environ.get("CRYPTO_PRODUCTION_BLOCK_LONG_OVERRIDE", "0") != "1"
    ):
        pick["_hf_quality_gate_reason"] = "crypto_production_block_long"
        logger.info(
            "Pick rejected: CRYPTO_PRODUCTION_BLOCK_LONG=1 (symbol=%s, source=%s)",
            str(pick.get("symbol", "")),
            str(pick.get("source_system", "")),
        )
        try:
            if _pll_tracer_m110 and _pll_pick_id_m110:
                _pll_tracer_m110.log_filter(
                    _pll_pick_id_m110,
                    "crypto_direction",
                    "crypto_production_block_long",
                    pick_values={"symbol": pick.get("symbol"), "direction": _crypto_dir},
                )
        except Exception:
            pass
        return False

    # Ghost-row cohort surgical block — (asset_class, strategy, symbol) tuples
    # for known constant-pnl template emissions (see BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES
    # definition for evidence). Catches MATIC quan_engine, ROBO funding_rate_carry,
    # etc. without blanket-blocking the whole strategy class.
    _ghost_sym = str(pick.get("symbol", "") or "").upper().strip()
    if _ghost_sym and (asset_class, strategy, _ghost_sym) in BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES:
        logger.debug("Pick rejected: ghost-row cohort (class+strategy+symbol triple)")
        try:
            if _pll_tracer_m110 and _pll_pick_id_m110:
                _pll_tracer_m110.log_filter(_pll_pick_id_m110, "asset_strategy_symbol_triples", f"ghost_row_cohort ({asset_class},{strategy},{_ghost_sym})", rule_id="RULE-BLOCK", pick_values={"symbol": _ghost_sym, "strategy": strategy, "asset_class": asset_class})
        except Exception:
            pass
        return False

    # Non-crypto: require moderate trust + minimum raw score (audited history can bypass)
    # Scanner-generated picks (multi_asset, stocks_competition, multi_asset_copytrader, etc.)
    # arrive without pre-computed scores — only apply the raw-score floor when the pick
    # has an EXPLICIT score field (raw_active_score > 0). Unscored picks are scored by
    # _apply_score_penalties and their quality is evaluated post-scoring.
    _NC_SCORE_EXEMPT_SOURCES = {
        "multi_asset",
        "multi_asset_institutional",
        "stocks_competition",
        "fast_stocks_competition",
        "stocks_forex_comp",
        "goldmine_stocks",
        # 2026-04-05: copy-trader sources arrive with raw_active_score 20-44 after
        # _apply_score_penalties and were hitting the >=55 non-crypto floor, dropping
        # 68/69 active copytrader picks from dashboard. They're scored via their own
        # pipeline (per claude-copytrader-merge investigation, docs/COPYTRADER_MERGE_BUG_20260405.md).
        "multi_asset_copytrader",
        "cta_replicator",
        # 2026-05-04: kimi_riseoftheclaw PRUNED from NC exemption (cross-class).
        # 7d forward check (2026-04-28..2026-05-04): n=45, WR=42.2% < 55% floor,
        # PF=0.980 (sub-1), avg_pnl=-0.0380%. Noise share=0% (no resolver artifact).
        # Exemption was added 2026-04-29 on 30d historic stats (WR 79%, PF 7.4, n=82)
        # but forward window has decayed well below the 55% WR floor.
        # See reports/nc_exemption_7d_forward_check_2026_05_04.md.
        # Re-add only after a fresh 7d forward-WR check >= 55% per test_kimi_promotion_unblock.py.
    }
    if (
        asset_class in ("FOREX", "EQUITY", "COMMODITY", "FUTURES", "ETF", "BOND")
        and os.environ.get("PER_ASSET_QUALITY_ACTIVE_PERMISSIVE", "1") == "0"
    ):
        trust_score = _float(pick.get("trust_score", 0))
        if trust_score > 0 and trust_score < ACTIVE_NON_CRYPTO_MIN_TRUST_SCORE:
            logger.debug(
                "Pick rejected: non-crypto trust_score < %s",
                ACTIVE_NON_CRYPTO_MIN_TRUST_SCORE,
            )
            try:
                if _pll_tracer_m110 and _pll_pick_id_m110:
                    _pll_tracer_m110.log_filter(_pll_pick_id_m110, "confidence_threshold", f"trust_score={trust_score:.0f}<{ACTIVE_NON_CRYPTO_MIN_TRUST_SCORE}", rule_id="RULE-THRESH", pick_values={"symbol": pick.get("symbol"), "trust_score": trust_score})
            except Exception:
                pass
            return False
        if source_sys not in _NC_SCORE_EXEMPT_SOURCES:
            # Only apply floor for picks that have an explicit pre-penalty score.
            # raw_active_score == 0 means unscored (no score field) — not bad score.
            # UEPS long-horizon (3y+) value picks bypass the 55 floor when flag ON;
            # the floor is calibrated for short-term technical scoring.
            if (
                raw_active_score > 0
                and raw_active_score < ACTIVE_DISPLAY_NON_CRYPTO_MIN_RAW_SCORE
                and not _pair_exc_active
                and not _non_crypto_active_raw_score_bypass(pick)
                and not _ueps_long_horizon_bypass_active(pick)
            ):
                logger.debug(
                    "Pick rejected: non-crypto raw score below active-display floor"
                )
                try:
                    if _pll_tracer_m110 and _pll_pick_id_m110:
                        _pll_tracer_m110.log_filter(_pll_pick_id_m110, "score_booster", f"raw_score={raw_active_score:.0f}<{ACTIVE_DISPLAY_NON_CRYPTO_MIN_RAW_SCORE}", rule_id="RULE-THRESH", pick_values={"symbol": pick.get("symbol"), "raw_active_score": raw_active_score, "asset_class": asset_class})
                except Exception:
                    pass
                return False

    # ── Non-Crypto Quality Gate ──
    # Non-crypto gets softer gates — let picks through but penalize via score.
    # The previous hard-reject at score<70 for unproven pairs was too aggressive.
    if (
        asset_class in ("FOREX", "EQUITY", "COMMODITY")
        and os.environ.get("PER_ASSET_QUALITY_ACTIVE_PERMISSIVE", "1") == "0"
    ):
        sym_track_wr = pick.get("sym_track_wr")
        sym_track_total = _int(pick.get("sym_track_total", 0))
        # Only hard-reject: proven catastrophic failure (WR < 20% on 10+ trades)
        if sym_track_total >= 10 and (sym_track_wr or 0) < 20:
            logger.debug(
                f"Non-crypto reject: catastrophic symbol track ({sym_track_wr}%)"
            )
            return False

    # ── Crypto Active Display Gate ──
    # Philosophy: ALL crypto picks reach the dashboard. Quality is expressed
    # through score (sort order), not visibility. The previous 7-filter
    # hard-gate rejected 96% of picks (364 ÔåÆ 14), starving the dashboard.
    # Only hard-reject picks with proven catastrophic symbol-level failure.
    if (
        asset_class == "CRYPTO"
        and os.environ.get("PER_ASSET_QUALITY_ACTIVE_PERMISSIVE", "1") == "0"
    ):
        sym_track_wr = _float(pick.get("sym_track_wr", 0))
        sym_track_total = _int(pick.get("sym_track_total", 0))
        # Only hard-reject: proven 0% WR on this specific strategy+symbol with enough data
        if sym_track_total >= 10 and sym_track_wr < 20:
            return False

    # Large-sample forward-WR floor: once a cohort has enough forward evidence,
    # sub-edge win rates should not stay in the active feed just because the
    # pick is fresh or the score pipeline is noisy.
    edge_wr = _effective_forward_wr_ratio(pick)
    edge_trades = _effective_forward_trades(pick)
    if (
        asset_class == "CRYPTO"
        and os.environ.get("PER_ASSET_QUALITY_ACTIVE_PERMISSIVE", "1") == "0"
    ):
        if (
            edge_trades >= ACTIVE_CRYPTO_MIN_FORWARD_TRADES
            and 0 < edge_wr < ACTIVE_CRYPTO_MIN_FORWARD_WR
            and not _pair_exc_active
        ):
            logger.debug(
                "Pick rejected: crypto forward WR %.1f%% on %d trades below %.1f%% floor",
                edge_wr * 100.0,
                edge_trades,
                ACTIVE_CRYPTO_MIN_FORWARD_WR * 100.0,
            )
            return False
    elif (
        asset_class in ("FOREX", "EQUITY", "COMMODITY", "FUTURES", "ETF", "BOND")
        and os.environ.get("PER_ASSET_QUALITY_ACTIVE_PERMISSIVE", "1") == "0"
    ):
        _nc_wr_floor = active_non_crypto_forward_wr_floor(asset_class)
        if (
            edge_trades >= ACTIVE_NON_CRYPTO_MIN_FORWARD_TRADES
            and 0 < edge_wr < _nc_wr_floor
            and not _pair_exc_active
        ):
            logger.debug(
                "Pick rejected: non-crypto forward WR %.1f%% on %d trades below %.1f%% floor (%s)",
                edge_wr * 100.0,
                edge_trades,
                _nc_wr_floor * 100.0,
                asset_class,
            )
            return False

    # ── v101.1 Dashboard Visibility Sync: Hard-rejects from template.html ──

    # 1. Blocked source systems (proven losers)
    source_lower = str(pick.get("source_system", "") or "").lower().strip()
    if source_lower in BLOCKED_SOURCE_SYSTEMS:
        logger.debug(f"Pick rejected: blocked source system {source_lower}")
        return False

    # 2. Rapid_fire noise filter (score < 10)
    if source_lower == "rapid_fire":
        # Check initial score BEFORE penalties (it will get capped later)
        score_val, _ = _extract_final_score(pick)
        if score_val < RAPID_FIRE_MIN_SCORE:
            logger.debug("Pick rejected: rapid_fire noise (score < 10)")
            return False

    # 3. Entry price range (broken entries)
    entry_price = _float(pick.get("entry_price", 0))
    if entry_price <= 0:
        logger.debug("Pick rejected: missing entry price")
        return False
    if entry_price > MAX_ENTRY_PRICE:
        logger.debug(f"Pick rejected: insane entry price={entry_price}")
        return False

    # 4. Age-based staleness (if not winning)
    # Picks older than crypto/non-crypto hard max age with |PnL| < 1% are hidden
    created_ts = (
        pick.get("created_at") or pick.get("timestamp") or pick.get("generated_at")
    )
    if created_ts:
        age_hours = _calculate_age_hours(created_ts)
        pnl = _float(pick.get("pnl_pct") or pick.get("unrealized_pnl_pct", 0))

        is_nc = asset_class in {
            "FOREX",
            "EQUITY",
            "COMMODITY",
            "FUTURES",
            "BOND",
            "ETF",
        }
        max_age_h = (
            NON_CRYPTO_HARD_MAX_AGE_HOURS_VISIBLE
            if is_nc
            else CRYPTO_HARD_MAX_AGE_HOURS
        )

        if age_hours > max_age_h and abs(pnl) < STALENESS_PNL_LIMIT:
            logger.debug(
                f"Pick rejected: stale pick (age={age_hours:.1f}h, pnl={pnl:.2f}%)"
            )
            return False

    # ── M-097: Book-level symbol direction-conflict gate (2026-05-18) ──────────
    # Finding (reports/opposing_legs_finding_2026-05-18.md): 17% of CRYPTO symbols
    # carry opposing LONG+SHORT picks simultaneously, mechanically yielding ~0 alpha
    # minus fees. Gate runs before permissive-mode exit so it applies to all picks.
    # Shadow mode (BOOK_CONFLICT_GATE=0, default): stamp _book_direction_conflict=True.
    # Enforce mode (BOOK_CONFLICT_GATE=1): reject lower-conviction conflicting picks.
    # Kill-switch: BOOK_CONFLICT_GATE_DISABLED=1. Fail-open on any error.
    try:
        import os as _os_m097
        if _os_m097.environ.get("BOOK_CONFLICT_GATE_DISABLED", "0") not in ("1", "true", "TRUE", "True"):
            _m097_ac = str(pick.get("asset_class", "") or "").upper().strip()
            _m097_sym = str(pick.get("symbol", "") or "").upper().strip()
            _m097_dir = str(pick.get("direction", "") or "").upper().strip()
            if _m097_sym and _m097_dir in ("LONG", "SHORT", "BUY", "SELL"):
                _m097_oppose = {"LONG": ("SHORT", "SELL"), "BUY": ("SHORT", "SELL"),
                                "SHORT": ("LONG", "BUY"), "SELL": ("LONG", "BUY")}
                _m097_opp_dirs = _m097_oppose.get(_m097_dir, ())
                import json as _json_m097
                from pathlib import Path as _Path_m097
                _m097_ap_override = _os_m097.environ.get("BOOK_CONFLICT_ACTIVE_PICKS_PATH", "")
                _m097_ap_path = (
                    _Path_m097(_m097_ap_override) if _m097_ap_override
                    else _Path_m097(__file__).resolve().parent.parent / "alpha_engine" / "data" / "active_picks.json"
                )
                if _m097_ap_path.exists():
                    _m097_active = _json_m097.loads(_m097_ap_path.read_text(encoding="utf-8"))
                    _m097_conflicts = [
                        p for p in _m097_active
                        if (str(p.get("symbol", "") or "").upper() == _m097_sym
                            and str(p.get("asset_class", "") or "").upper() == _m097_ac
                            and str(p.get("status", "") or "").upper() == "OPEN"
                            and str(p.get("direction", "") or "").upper() in _m097_opp_dirs)
                    ]
                    if _m097_conflicts:
                        _m097_enforce = _os_m097.environ.get("BOOK_CONFLICT_GATE", "0") not in ("0", "false", "FALSE", "False")
                        _m097_new_conf = float(pick.get("confidence", 0) or 0)
                        _m097_max_exist_conf = max(float(p.get("confidence", 0) or 0) for p in _m097_conflicts)
                        if _m097_enforce and _m097_new_conf < _m097_max_exist_conf:
                            logger.info(
                                "M-097 book_direction_conflict: REJECTED %s %s conf=%.2f < existing %s conf=%.2f (symbol=%s)",
                                _m097_dir, _m097_ac, _m097_new_conf, _m097_opp_dirs, _m097_max_exist_conf, _m097_sym,
                            )
                            return False
                        else:
                            pick["_book_direction_conflict"] = True
                            logger.info(
                                "M-097 book_direction_conflict: SHADOW %s %s conf=%.2f vs existing %s conf=%.2f (symbol=%s) — set BOOK_CONFLICT_GATE=1 to enforce",
                                _m097_dir, _m097_ac, _m097_new_conf, _m097_opp_dirs, _m097_max_exist_conf, _m097_sym,
                            )
    except Exception:
        pass  # fail-open: never block picks on gate error

    # ── M-098: ETF VIX regime gate (E-005 promoted to enforce 2026-05-18) ──────
    # Block new ETF picks when VIX >= threshold (default 25.0).
    # Rationale: ETF sector rotation edge collapses in high-volatility regimes;
    # MASTER_ACTION_PLAN E-005 (P0). All 8 tests pass; VIX=19.09 at promotion time.
    # Enforce mode (ETF_VIX_GATE=1, default): hard-reject ETF pick when VIX >= threshold.
    # Shadow mode (ETF_VIX_GATE=0): stamp _etf_vix_regime_block=True only.
    # Kill-switch: ETF_VIX_GATE_DISABLED=1 skips entirely. Fail-open on any error.
    # Dual-gate note (2026-05-18): PR-E1 below fires at VIX≥20; M-098 fires at VIX≥25.
    # Effective blocking threshold is 20 (PR-E1). M-098 is defense-in-depth for VIX≥25
    # if PR-E1 is disabled. Do NOT remove M-098 without first disabling PR-E1.
    # Bond ETF exemption (2026-05-18, E-007): TLT/IEF/SHY/LQD/AGG rally in risk-off VIX spikes;
    # blocking them is counterproductive. Exempt by symbol regardless of asset_class tag.
    _M098_BOND_ETF_EXEMPT = frozenset({"TLT","IEF","SHY","LQD","AGG","BND","HYG","EMB","TLH","GOVT","JNK","MUB","TIP","BNDX"})
    try:
        import os as _os_m098
        _m098_ac = str(pick.get("asset_class", "") or "").upper().strip()
        _m098_sym = str(pick.get("symbol", "") or "").upper().strip()
        if _m098_ac == "ETF" and _m098_sym not in _M098_BOND_ETF_EXEMPT and _os_m098.environ.get("ETF_VIX_GATE_DISABLED", "0") not in ("1", "true", "TRUE", "True"):
            from audit_trail.vix_regime_gate import get_cached_vix as _get_vix_m098
            _m098_vix = _get_vix_m098()
            _m098_thresh = float(_os_m098.environ.get("ETF_VIX_GATE_THRESHOLD", "25.0"))
            if _m098_vix is not None and _m098_vix >= _m098_thresh:
                _m098_enforce = _os_m098.environ.get("ETF_VIX_GATE", "1") not in ("0", "false", "FALSE", "False")
                # E-006: structured exception log (every trigger, shadow or enforce)
                try:
                    import json as _json_m098
                    import datetime as _dt_m098
                    from pathlib import Path as _Path_m098
                    _m098_log = _Path_m098("reports") / "etf_vix_gate_log.jsonl"
                    _m098_log.parent.mkdir(exist_ok=True)
                    with open(_m098_log, "a", encoding="utf-8") as _m098_lf:
                        _m098_lf.write(_json_m098.dumps({
                            "ts": _dt_m098.datetime.now(_dt_m098.timezone.utc).isoformat(),
                            "symbol": str(pick.get("symbol", "") or ""),
                            "strategy": str(pick.get("strategy", "") or ""),
                            "vix_value": _m098_vix,
                            "threshold": _m098_thresh,
                            "mode": "enforce" if _m098_enforce else "shadow",
                            "blocked": _m098_enforce,
                        }) + "\n")
                except Exception:
                    pass
                if _m098_enforce:
                    logger.info(
                        "M-098 etf_vix_gate: REJECTED ETF pick vix=%.1f >= threshold=%.1f (symbol=%s)",
                        _m098_vix, _m098_thresh, pick.get("symbol", ""),
                    )
                    return False
                else:
                    pick["_etf_vix_regime_block"] = True
                    logger.debug(
                        "M-098 etf_vix_gate: SHADOW ETF pick vix=%.1f >= threshold=%.1f (symbol=%s) — set ETF_VIX_GATE=1 to enforce",
                        _m098_vix, _m098_thresh, pick.get("symbol", ""),
                    )
    except Exception:
        pass  # fail-open: never block picks on gate error

    if os.environ.get("PER_ASSET_QUALITY_ACTIVE_PERMISSIVE", "1") != "0":
        return True

    # Score floor gate: score < 40 = 33.9% WR on 372 picks (TESTING_PROTOCOL ┬º13)
    # Score <= 0 is NOT "unscored" — it is a failed/bad score and must be rejected.
    # Only exempt sources (synthetic strategy names that collide with kill list)
    # bypass the floor; all others must have a positive score above the floor.
    _SCORE_FLOOR_EXEMPT_SOURCES = {
        "goldmine_stocks",
        "stocks_competition",
        "fast_stocks_competition",
        "stocks_forex_comp",
        "multi_asset_copytrader",
        "cta_replicator",
    }
    source_sys_fl = str(pick.get("source_system", "") or "").lower()
    if source_sys_fl in _SCORE_FLOOR_EXEMPT_SOURCES:
        return True  # exempt from universal 40 floor (synthetic strategy names collide with kill list)
    # UEPS long-horizon (3y+) value scoring is calibrated lower than short-term
    # technical scoring; bypass the universal 40 floor when flag ON.
    if _ueps_long_horizon_bypass_active(pick):
        return True
    _raw_floor = ACTIVE_DISPLAY_CRYPTO_MIN_RAW_SCORE if asset_class == "CRYPTO" else 40

    # Fix 2 (PR #323, 2026-04-22): Exempt pre-score active candidates from the
    # score<=0 hard reject. Restores the contract codified by
    # test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive in
    # tests/test_dashboard_generator.py. Prediction-market-consensus picks
    # enter the active book before elite/score_booster have run and must not
    # be collapsed prematurely. Trust-tier BANNED/AVOID remain hard-blocked.
    # (Inlined to avoid circular import from audit_trail.dashboard_generator.)
    _pre_score_blocked = {"BANNED", "AVOID"}
    _pre_score_trust_tier = str(pick.get("trust_tier", "") or "").strip().upper()
    _pre_score_trust_label = str(pick.get("trust_label", "") or "").strip().upper()
    _pre_score_strategy = str(pick.get("strategy", "") or "").strip().lower()
    _is_pre_score_candidate = (
        _pre_score_trust_tier not in _pre_score_blocked
        and _pre_score_trust_label not in _pre_score_blocked
        and bool(_pre_score_strategy)
        and _pre_score_strategy not in {"none", "null", "unknown"}
    )
    if raw_active_score <= 0 and _is_pre_score_candidate:
        return True  # pre-score PM candidate — quality expressed via sort order, not visibility
    if _pair_exc_active:
        pick["exception_carve_out"] = True
        logger.debug(
            "Pair exception carve-out granted (active floors bypassed) for %s %s %s",
            pick.get("strategy"), symbol, pick.get("direction"),
        )
        return True
    if raw_active_score <= 0:
        logger.debug(
            f"Pick rejected: score={raw_active_score:.1f} is null/zero/negative ({symbol})"
        )
        return False
    if raw_active_score < _raw_floor:
        logger.debug(
            f"Pick rejected: score={raw_active_score:.1f} below raw display floor {_raw_floor} ({symbol})"
        )
        return False

    # ── M-103: Post-Cost Expectancy shadow gate (PR-03, 2026-05-18) ──────────────
    # Flags picks where gross edge is consumed by estimated transaction costs.
    # Uses win_rate + rr_ratio from pick metadata to compute gross_expectancy,
    # then deducts per-asset-class cost from transaction_cost_model.py.
    #
    # POST_COST_GATE_MODE=shadow (default): tag pick, no rejection.
    # POST_COST_GATE_MODE=hard_reject      : reject picks with post_cost_exp <= 0.
    # POST_COST_GATE_MODE=off              : disable entirely (tests, sidecar missing).
    try:
        _pce_mode = os.environ.get("POST_COST_GATE_MODE", "shadow").lower()
        if _pce_mode != "off":
            from audit_trail.transaction_cost_model import get_cost_assumption_for_pick as _get_cost
            _pce_wr_raw = _float(
                pick.get("fwd_win_rate") or pick.get("bt_win_rate") or pick.get("win_rate") or 0
            )
            # Normalize: picks store win_rate as percentage (0-100); convert to fraction (0-1)
            _pce_wr = _pce_wr_raw / 100.0 if _pce_wr_raw > 1.0 else _pce_wr_raw
            _pce_rr = _float(pick.get("rr_ratio") or pick.get("rr") or pick.get("risk_reward") or 0)
            # Only compute when both inputs are meaningful
            if 0 < _pce_wr < 1 and _pce_rr > 0:
                # Kelly-style gross expectancy per unit risk
                _pce_gross = _pce_wr * _pce_rr - (1.0 - _pce_wr)
                _pce_cost = _get_cost(pick)
                _pce_post = _pce_gross - (_pce_cost.total_cost_pct if _pce_cost else 0.0)
                pick["_post_cost_gross_exp"] = round(_pce_gross, 4)
                pick["_post_cost_exp"] = round(_pce_post, 4)
                if _pce_post <= 0.0:
                    if _pce_mode == "hard_reject":
                        logger.info(
                            "PICK_REJECTED post_cost_gate symbol=%s gross=%.4f post=%.4f",
                            symbol, _pce_gross, _pce_post,
                        )
                        return False
                    pick["_post_cost_shadow_reject"] = True
                    logger.debug(
                        "post_cost_shadow_reject symbol=%s gross=%.4f post=%.4f",
                        symbol, _pce_gross, _pce_post,
                    )
    except Exception:
        pass  # fail-open: never block picks on cost-gate errors

    # ── M-109: RR High Gate (2026-05-18, promoted to enforce after 4-engine swarm) ──
    # Walk-forward harness (n=2,575): RR>1.5 predicts losers monotonically.
    #   RR 1.5-2.0: WR=30.9%  RR 2.0-3.0: WR=18.4%  RR 3.5+: WR=5.7%
    # EV at RR 1.5-2.0: 0.309×1.5 − 0.691×1.0 = −0.228 per unit (definitively negative).
    # Swarm verdict 2026-05-18 (swarm_runs/run_20260518T200203Z): APPROVE ENFORCE
    # (deepseek+kilo APPROVE; claude+gemini REJECT on implementation concerns only;
    # EV math is definitive — this is purely a monotone anti-signal, not noise).
    # Kill-switch: RR_HIGH_GATE_ENABLED=0. Default enforce: RR_HIGH_GATE_ENFORCE=1.
    try:
        if os.environ.get("RR_HIGH_GATE_ENABLED", "1") not in ("0", "false", "FALSE", "False"):
            _rr_val = None
            for _rr_key in ("risk_reward", "rr", "rr_ratio"):
                _rr_raw = pick.get(_rr_key)
                if _rr_raw is not None:
                    try:
                        _rr_val = float(_rr_raw)
                        break
                    except (TypeError, ValueError):
                        pass
            if _rr_val is not None and _rr_val > 1.5:
                pick["_rr_high_flag"] = True
                pick["_rr_value"] = round(_rr_val, 2)
                if os.environ.get("RR_HIGH_GATE_ENFORCE", "1") not in ("0", "false", "FALSE", "False"):
                    logger.info(
                        "Pick rejected: M-109 RR high gate rr=%.2f symbol=%s",
                        _rr_val, pick.get("symbol", "?"),
                    )
                    return False
    except Exception:
        pass  # fail-open: never block picks on RR gate error

    return True


# Transaction Cost Clearance gate implemented below (2026-05-14).
# Rejects picks where gross edge is consumed by fees + slippage + spread.
# See try/except ImportError block after VIX regime gate.
def passes_smart_gate(pick: Dict[str, Any]) -> bool:
    """
    Smart Picks gate — selects high-conviction picks using the golden
    criteria derived from 2,256+ closed pick analysis.

    Golden combo (68.2% WR, +4.67% avg PnL):
      PROVEN trust + agreement 1-2 + score 40-69

    Additional qualifiers from cross-AI analysis:
      - No SCALP mode (24.8% WR drag)
      - No panic health (24% WR)
      - Strategy fwd WR >= 35% if known
      - Prefer SWING mode, HTF alignment, R:R 2.0-3.0
    """
    if not passes_active_gate(pick):
        return False

    # ── Anti-overfit validator (DSR/PBO) — OPT-IN, default-OFF ──
    # Kimi P1 wire-up 2026-05-12. Engage with ANTI_OVERFIT_VALIDATOR_ENABLED=1.
    # Rejects when DSR < 0.95 OR PBO > 0.50 given pick.returns_history.
    if _anti_overfit_reject(pick):
        return False

    # ── Phase 2-A CRYPTO SHORT regime-gate / kill-switch (defense-in-depth) ──
    # passes_active_gate already enforces this, but mirror the rule in Smart so
    # that any future code path bypassing active still respects the panel verdict.
    # Both flags default-OFF.
    _smart_short_reason = _crypto_short_gate_block_reason(pick)
    if _smart_short_reason is not None:
        logger.debug("Smart gate: %s", _smart_short_reason)
        return False

    # ── Concept-drift auto-pause (defense-in-depth, mirrors active gate) ──
    _smart_drift_reason = _passes_drift_auto_pause_gate(pick)
    if _smart_drift_reason is not None:
        logger.debug("Smart gate drift pause: %s", _smart_drift_reason)
        return False

    # ── JPY-cross BUY-direction surgical kill — defense-in-depth (Phase 2-C, 2026-04-29) ──
    # passes_active_gate already enforces this, but mirror the rule in Smart so that
    # any future code path bypassing active still respects the panel verdict.
    # Default-on. Rollback: JPY_CROSS_BUY_KILL_DISABLED=1
    _jpy_smart_sym = str(pick.get("symbol", "") or "").upper()
    _jpy_smart_ac = str(pick.get("asset_class", "") or "").upper()
    _jpy_smart_dir = str(pick.get("direction", "") or "").upper()
    if (
        _jpy_smart_ac == "FOREX"
        and _jpy_smart_sym in JPY_CROSS_PAIRS
        and _jpy_smart_dir in ("BUY", "LONG", "BULLISH")
        and os.environ.get("JPY_CROSS_BUY_KILL_DISABLED", "0") != "1"
    ):
        logger.debug(
            "Smart gate: jpy_cross_buy_killed (%s %s) — Phase 2-C 6/7 panel",
            _jpy_smart_sym, _jpy_smart_dir,
        )
        return False

    # ── ETF surgical blacklist — defense-in-depth (Phase 2-E, 2026-04-29) ──
    # passes_active_gate already enforces this, but mirror the rule in Smart so
    # any future code path bypassing active still respects the panel verdict.
    # Default-on. Rollback: ETF_IWM_GLD_KILL_DISABLED=1
    _etf_smart_sym = str(pick.get("symbol", "") or "").upper().strip()
    _etf_smart_ac = str(pick.get("asset_class", "") or "").upper().strip()
    if (
        _etf_smart_ac == "ETF"
        and _etf_smart_sym in ETF_BLACKLIST
        and os.environ.get("ETF_IWM_GLD_KILL_DISABLED", "0") != "1"
    ):
        logger.debug(
            "Smart gate: etf_iwm_gld_killed (%s) — Phase 2-E 6/6 panel",
            _etf_smart_sym,
        )
        return False

    # ── COMMODITY sub-class blacklist — defense-in-depth (Phase 2-D, 2026-04-29) ──
    _comm_smart_sym = str(pick.get("symbol", "") or "").upper().strip()
    _comm_smart_ac = str(pick.get("asset_class", "") or "").upper().strip()
    if (
        _comm_smart_ac in ("COMMODITY", "COMMODITIES")
        and _comm_smart_sym in COMMODITY_BLACKLIST
        and os.environ.get("COMMODITY_SUBCLASS_KILL_DISABLED", "0") != "1"
    ):
        logger.debug(
            "Smart gate: commodity_subclass_killed (%s) — Phase 2-D 7/7 panel",
            _comm_smart_sym,
        )
        return False

    # ── VIX regime gate (opt-in sidecar, EQUITY + ETF) ──
    # Per reports/equity_vix_regime_breakthrough_20260513.md + reports/
    # etf_vix_regime_breakthrough_20260513.md: VIX<22 filter delivers TIER-1 PF
    # on BOTH EQUITY top-5 momentum (PF 4.55 / Sharpe 1.98 / MDD 16.8%) AND ETF
    # sector top-3 rotation (PF 3.32 / Sharpe 1.68 / MDD 11.8%). Pattern transfers
    # across classes. Default OFF via VIX_REGIME_GATE_ENABLED=1. See
    # audit_trail/vix_regime_gate.py for full Wiring Plan.
    try:
        from audit_trail.vix_regime_gate import (
            should_reject_equity_pick as _vix_reject,
            should_reject_combined as _combined_reject,
        )
        # Combined VIX+YC takes precedence when YC_REGIME_GATE_ENABLED=1.
        # Per reports/equity_vix_yc_combined_super_breakthrough_20260513.md:
        # VIX<22 AND YC>0 = PF 4.98 / Sharpe 2.08 vs VIX<22-only PF 4.55.
        if _combined_reject(pick):
            pick["_hf_quality_gate_reason"] = "vix_yc_regime_combined"
            logger.debug(
                "Smart gate: vix_yc_regime_combined (EQUITY/ETF; VIX>thr OR YC<thr)"
            )
            try:
                if _pll_tracer_m110 and _pll_pick_id_m110:
                    _pll_tracer_m110.log_filter(_pll_pick_id_m110, "regime_gate", "vix_yc_regime_combined", rule_id="RULE-REGIME", pick_values={"symbol": pick.get("symbol"), "asset_class": pick.get("asset_class")})
            except Exception:
                pass
            return False
        if _vix_reject(pick):
            pick["_hf_quality_gate_reason"] = "vix_regime_high_vol"
            logger.debug(
                "Smart gate: vix_regime_high_vol (EQUITY/ETF pick rejected; VIX > threshold)"
            )
            try:
                if _pll_tracer_m110 and _pll_pick_id_m110:
                    _pll_tracer_m110.log_filter(_pll_pick_id_m110, "regime_gate", "vix_regime_high_vol", rule_id="RULE-REGIME", pick_values={"symbol": pick.get("symbol"), "asset_class": pick.get("asset_class")})
            except Exception:
                pass
            return False
    except ImportError:
        # Sidecar module missing — preserve current behavior (no-op)
        pass

    # Gate: Transaction Cost Clearance (P1 per kilocode vet 2026-05-14)
    # Reject picks where gross edge is consumed by transaction costs (fees + slippage + spread).
    # Uses per-asset-class cost buckets from alpha_engine/transaction_costs.py.
    #
    # Skipped when:
    #   - pick has no realized pnl_pct (prospective/active pick at scoring time;
    #     cost-clearance is a CLOSED-pick verdict, not an OPEN-pick verdict)
    #   - TRANSACTION_COST_GATE_DISABLED=1 (test fixtures + opt-in rollout)
    if os.environ.get("TRANSACTION_COST_GATE_DISABLED", "0") != "1":
        # Only apply to CLOSED picks — open/active picks have mark-to-market pnl_pct
        # (unrealized), not realized. status=OPEN or blank → skip gate (fail-open).
        _pick_status = str(pick.get("status") or "").upper().strip()
        _is_closed_pick = _pick_status in ("CLOSED", "RESOLVED", "EXPIRED", "STOPPED",
                                           "TARGET_HIT", "SL_HIT", "TP_HIT", "WIN", "LOSS")
        _has_realized_pnl = _is_closed_pick and any(
            pick.get(k) is not None for k in ("pnl_pct", "net_pnl_pct", "unrealized_pnl_pct")
        )
        if _has_realized_pnl:
            try:
                from audit_trail.transaction_cost_model import apply_costs_to_pick
                _cost_enriched = apply_costs_to_pick(pick)
                if not _cost_enriched.get("cost_cleared", True):
                    pick["_hf_quality_gate_reason"] = "transaction_cost_gate"
                    logger.debug("Smart gate: transaction cost gate — cost_cleared=False")
                    return False
            except ImportError:
                pass  # transaction_cost_model sidecar not available — skip gate

    # HF Threshold A: exclude from Smart Picks when forward WR lags BT by >15pp (n>=20)
    if pick.get("_hf_threshold_a"):
        logger.debug("Smart gate: HF threshold A (BT/FWD decay)")
        return False

    if not _has_source_provenance(pick):
        logger.debug("Smart gate: missing source provenance")
        return False

    score = _float(pick.get("score", 0))

    # Concentrated track records: keep in Active, exclude from Smart unless verified PM/copy
    if not _is_verified_pm_or_copy_pick(pick):
        if _concentration_penalty(pick) >= 10:
            logger.debug(
                "Smart gate: concentration penalty too high for non-verified pick"
            )
            return False
        if _concentration_risk(pick) == "HIGH":
            logger.debug("Smart gate: HIGH concentration risk for non-verified pick")
            return False

    # ── Pair-level exception carve-out (B19, 2026-05-02) ──
    # Narrow scope: bypass score floor + R:R floor + forward-WR floor only.
    # Does NOT bypass provenance, concentration risk, SCALP/panic, trust-tier,
    # or any hard blocks in passes_active_gate.
    _pair_exc_active = _PAIR_EXCEPTIONS_AVAILABLE and should_pair_exception_pass(pick)
    if _pair_exc_active:
        pick["exception_carve_out"] = True

    # Primary: score threshold (all quality signals already baked in)
    # EQUITY uses a lower threshold — score 30-50 = 66.7% WR PF 2.61 (different distribution from crypto)
    # FOREX uses a HIGHER threshold — MC sweep (n=367) shows 16% WR baseline, p=0.999 (catastrophic)
    _ac = _normalize_asset_class(pick.get("asset_class", "CRYPTO"))
    _cfg = ASSET_CLASS_SMART_THRESHOLDS.get(
        _ac, ASSET_CLASS_SMART_THRESHOLDS["CRYPTO"]
    )
    # COMMODITY forward_validated exemption — NARROW LIST ONLY (2026-05-28).
    # multi_asset_cot + multi_asset_copytrader REMOVED: falsified 6.33x over-emission
    # (46 raw signals / 6 unique CFTC weeks; see cot_paper_pilot autopsy + lines 7665-7667).
    # commodity_cot_contrarian kept: CFTC-backed commercial signal, post-dedup review.
    _fv_source = str(pick.get("source_system") or "").lower()
    _COMMODITY_FV_EXEMPT = frozenset({
        "commodity_cot_contrarian",
    })
    # ETF/EQUITY new-source cold-start exemption (2026-05-16):
    # etf_sector_rotation + leveraged_etf_decay: zero closed picks, permanent cold-start.
    # stocksunify2: 18 active EQUITY picks, scores 75-100, zero resolved → cold-start trap.
    # All three use academically validated strategy logic with no adverse closed-pick evidence.
    _ETF_FV_EXEMPT = frozenset({"etf_sector_rotation", "leveraged_etf_decay"})
    _EQUITY_FV_EXEMPT = frozenset({"stocksunify2"})
    _fv_ac = _normalize_asset_class(pick.get("asset_class", "CRYPTO"))
    _fv_exempt = (
        (_fv_ac == "COMMODITY" and _fv_source in _COMMODITY_FV_EXEMPT)
        or (_fv_ac == "ETF" and _fv_source in _ETF_FV_EXEMPT)
        or (_fv_ac == "EQUITY" and _fv_source in _EQUITY_FV_EXEMPT)
    )
    if not bool(pick.get("forward_validated")) and not _fv_exempt:
        pick["_smart_reject_reasons"] = ["forward_validated=false"]
        return False

    # 2026-04-14 edge convergence: LONG-only constraint for CRYPTO Smart Picks.
    # SHORT crypto PF 1.54 underperformed LONG crypto PF 1.91 baseline in 7d
    # window; LONG+Score>=50+Trust>=3 composite reached PF 5.48. See
    # SMART_PICKS_CRYPTO_LONG_ONLY docstring above for full rationale.
    if SMART_PICKS_CRYPTO_LONG_ONLY and _ac == "CRYPTO":
        _direction = str(pick.get("direction") or pick.get("signal_type") or "").upper()
        if _direction not in ("LONG", "BUY"):
            logger.debug(
                "Smart gate: CRYPTO SHORT rejected (SMART_PICKS_CRYPTO_LONG_ONLY)"
            )
            return False
    # Per-asset-class min_trades / min_fwr floors (PR #644).
    # Pulled from ASSET_CLASS_SMART_THRESHOLDS (`_cfg` resolved above). These
    # are independent of the score-floor gate that follows; rejecting on
    # under-traded or sub-WR forward evidence preempts the score path.
    edge_wr = _effective_forward_wr_ratio(pick)
    edge_trades = _effective_forward_trades(pick)
    _asset_reasons: List[str] = []
    if _cfg.get("min_trades", 0) > 0 and edge_trades < _cfg["min_trades"]:
        _asset_reasons.append(f"forward_trades<{_cfg['min_trades']}")
    if edge_wr > 0 and edge_wr < _cfg.get("min_fwr", 0):
        _asset_reasons.append(f"forward_wr<{_cfg['min_fwr']}")
    if _asset_reasons and not _pair_exc_active:
        pick["_smart_reject_reasons"] = _asset_reasons
        return False

    # Per-asset-class floors via get_effective_min_score() (Phase 3 wire-up
    # 2026-05-03). Consults STRATEGY_SCORE_OVERRIDES first (lower floors for
    # 16 proven non-crypto strategies that earn trust through track record,
    # not booster enrichment), falls back to per-class default.
    # Rollback: STRATEGY_SCORE_OVERRIDES_DISABLED=1 forces class-only floor.
    if os.environ.get("STRATEGY_SCORE_OVERRIDES_DISABLED", "0") == "1":
        _strategy_name_for_floor = ""
    else:
        _strategy_name_for_floor = str(pick.get("strategy", "") or "").strip()
    _min_score = get_effective_min_score(_strategy_name_for_floor, _ac or "CRYPTO")
    if _ac == "FOREX":
        # 2026-04-14: Forex edge comes from FwdWR≥50, not Score+Trust
        # (Score≥50+Trust≥3 HURTS forex: PF 0.46 on n=49 vs baseline PF 2.02)
        # FwdWR≥50 gives PF 1.62 on n=466, beats random. Apply as additional gate.
        _fwd_wr = _effective_forward_wr_ratio(pick) * 100.0
        if _fwd_wr > 0 and _fwd_wr < 50 and not _pair_exc_active:
            return False

    # Forward-validated strategy bypass: if the strategy has strong forward
    # evidence, waive the min score gate.  Tightened from original 10/55% and
    # 20/50% thresholds - those let in strategies with too few trades to be
    # statistically meaningful.  30+ trades at 55% WR or 50+ at 50% WR are
    # robust enough to trust despite low composite scores.
    _bypass_edge_wr = _effective_forward_wr_ratio(pick)
    _bypass_edge_trades = _effective_forward_trades(pick)
    _forward_bypass = (
        (_bypass_edge_trades >= 50 and _bypass_edge_wr >= 0.50)
        or (_bypass_edge_trades >= 30 and _bypass_edge_wr >= 0.55)
    )

    # Source-trust bypass for COMMODITY picks — REVOKED 2026-05-29 (completes PR #34).
    # The three COT sources previously trusted here (multi_asset_cot,
    # multi_asset_copytrader, commodity_cot_contrarian) were FALSIFIED by M-095:
    # their headline stats (PF 20.54 / WR 93.8%) are a COT-publication LOOK-AHEAD
    # LEAKAGE artifact — deduped + ex-CT=F they are n=20 / WR 30% / PF 0.51 (a loser).
    # PR #34 revoked the FV-exempt carve-out but left these two bypass whitelists
    # intact; emptying them stops the falsified sources from skipping the score floor.
    # (Restore a source here only with a clean, dedup-checked, forward-validated record.)
    _COMMODITY_TRUSTED_SOURCES: frozenset[str] = frozenset()
    # COMMODITY_NON_BLACKLIST: symbols that are NOT in COMMODITY_BLACKLIST.
    # HG=F (n=168 WR=47% KEEP) and PL=F (n=138 WR=44.9% KEEP) — Phase 2-D panel.
    _COMMODITY_NON_BLACKLIST_SYMBOLS = frozenset({"HG=F", "PL=F"})
    _sym_for_bypass = str(pick.get("symbol", "") or "").upper()
    _source_for_bypass = str(pick.get("source_system", "") or "").lower()
    _source_trust_bypass = (
        # COMMODITY class from trusted source
        (_ac == "COMMODITY" and _source_for_bypass in _COMMODITY_TRUSTED_SOURCES)
        # OR: FUTURES-classified pick for a known COMMODITY non-blacklisted symbol
        or (
            _ac == "FUTURES"
            and _sym_for_bypass in _COMMODITY_NON_BLACKLIST_SYMBOLS
            and _source_for_bypass in _COMMODITY_TRUSTED_SOURCES
        )
    )

    if score < _min_score and not _forward_bypass and not _pair_exc_active and not _source_trust_bypass:
        return False

    # ETF elite_score floor enforcement (swarm round 3 finding 2026-05-13).
    # Reports/swarm_round_2_etf_commodity_triage_2026-05-13.md identified
    # that goldmine_stocks emitted an ETF pick with elite_score=20 (far
    # below the documented ETF floor). The floor was documented but never
    # enforced. This is the admission-time root-cause fix, NOT a strategy
    # blacklist — picks from any system are rejected for an ETF asset class
    # if their elite_score is below ETF_ELITE_FLOOR.
    #
    # 2026-05-14 default 50 → 35 per /audit recompute (live data 23:19Z):
    # ETF n=106, WR 56.6%, PF 1.41; walk-forward OOS WR 74.0% with
    # consistency 100%. ETF is the system's strongest walk-forward signal
    # by consistency; v2 Supreme Plan P1-C tasks floor loosening to push
    # PF over the T2 floor of 1.5 (currently 0.09 short). The
    # forward_bypass guard at line ~5739-5742 still protects against
    # weak-edge picks (requires n>=50 @ WR>=50% or n>=30 @ WR>=55%).
    if _ac == "ETF":
        _etf_elite_raw = pick.get("elite_score")
        _etf_elite = None  # None = field absent → gate skipped (only enforce when score present)
        if _etf_elite_raw is not None:
            try:
                _etf_elite = float(_etf_elite_raw)
            except (TypeError, ValueError):
                _etf_elite = None
        _etf_floor = float(os.environ.get("ETF_ELITE_FLOOR", "35") or 35)
        if _etf_elite is not None and _etf_elite < _etf_floor and not _forward_bypass and not _pair_exc_active:
            logger.debug("Pick rejected: ETF elite_score=%.0f < floor=%.0f",
                         _etf_elite, _etf_floor)
            return False

    # ── ETF tight gate (P1, expert_feedback_action_plan_2026-05-17.md) ──
    # ETF confirmed PF=2.25 / WR=66.7% at n=75 with standard floor (35).
    # ETF_TIGHT_GATE=1 raises score requirement to 60 for real-money sizing.
    # Default ON: n=105 confirmed >= 100 threshold (2026-05-17, swarm verdict).
    # Kill-switch: ETF_TIGHT_GATE=0 to revert to floor=35.
    if _ac == "ETF" and os.environ.get("ETF_TIGHT_GATE", "1") == "1":
        try:
            _etf_tight_score = float(pick.get("score", 0) or 0)
        except (TypeError, ValueError):
            _etf_tight_score = 0.0
        from alpha_engine.config import SMART_PICKS_MIN_SCORE_ETF_TIGHT as _ETF_TIGHT_FLOOR
        if _etf_tight_score < _ETF_TIGHT_FLOOR and not _forward_bypass and not _pair_exc_active:
            logger.debug(
                "Pick rejected: ETF tight gate score=%.0f < floor=%.0f",
                _etf_tight_score, _ETF_TIGHT_FLOOR,
            )
            return False

    # ── PR-E1: ETF VIX<25 gate (2026-05-18, Kimi PR-E1 / swarm consensus) ──────
    # Backtest evidence (Kimi MASTER_ACTION_PLAN): when VIX≥25, ETF PF drops
    # sharply (high-vol regimes crush sector momentum). Gate: block ALL ETF picks
    # when VIX≥20. Enforce mode (default ON 2026-05-18): hard-rejects ETF picks
    # when VIX≥20. Kill-switch: ETF_VIX_GATE_ENFORCE=0 to revert to shadow mode.
    # Kill-switch: ETF_VIX_GATE_ENABLED=0. Fail-open (no VIX data → skip gate).
    # Threshold lowered from 25.0 → 20.0 per swarm calibration (2026-05-18):
    # 25.0 only fires in extreme vol events; 20.0 catches early stress regime.
    # Bond ETF symbols rally during VIX spikes (risk-off flight-to-safety); exempt them
    # from both ETF VIX gates (M-098 + PR-E1). E-007 analysis 2026-05-18.
    _PRE1_BOND_ETF_EXEMPT = frozenset({"TLT","IEF","SHY","LQD","AGG","BND","HYG","EMB","TLH","GOVT","JNK","MUB","TIP","BNDX"})
    if _ac == "ETF" and str(pick.get("symbol","") or "").upper().strip() not in _PRE1_BOND_ETF_EXEMPT and os.environ.get("ETF_VIX_GATE_ENABLED", "1") not in ("0", "false", "FALSE", "False"):
        try:
            from audit_trail.vix_regime_gate import get_cached_vix as _get_vix_etf
            _etf_vix = _get_vix_etf()
            _etf_vix_thr = float(os.environ.get("ETF_VIX_GATE_THRESHOLD", "20.0"))
            if _etf_vix is not None and _etf_vix >= _etf_vix_thr:
                _etf_vix_enforce = os.environ.get("ETF_VIX_GATE_ENFORCE", "1") not in ("0", "false", "FALSE", "False")
                if _etf_vix_enforce:
                    logger.info(
                        "PR-E1 ETF VIX gate: REJECTED VIX=%.1f >= %.1f (symbol=%s)",
                        _etf_vix, _etf_vix_thr, pick.get("symbol", "?"),
                    )
                    try:
                        if _pll_tracer_m110 and _pll_pick_id_m110:
                            _pll_tracer_m110.log_filter(_pll_pick_id_m110, "regime_gate", f"ETF_VIX_GATE:vix={_etf_vix:.1f}>={_etf_vix_thr:.1f}", rule_id="RULE-REGIME", pick_values={"symbol": pick.get("symbol"), "vix": _etf_vix})
                    except Exception:
                        pass
                    return False
                else:
                    pick["_etf_vix_gate_shadow"] = True
                    pick["_etf_vix_value"] = _etf_vix
                    logger.debug(
                        "PR-E1 ETF VIX gate: SHADOW VIX=%.1f >= %.1f (symbol=%s) — set ETF_VIX_GATE_ENFORCE=1 to enforce",
                        _etf_vix, _etf_vix_thr, pick.get("symbol", "?"),
                    )
        except Exception:
            pass  # fail-open: VIX data unavailable → skip gate

    # ── M-041: Swarm single-tier gate (2026-05-17) ─────────────────────────────
    # 22/38 swarm picks have tier=single (1/1 vote) and zero WR/PF backing.
    # Default ON. Bypass for _forward_bypass (proven single-source strategies).
    # Kill-switch: SWARM_TIER_GATE=0.
    if os.environ.get("SWARM_TIER_GATE", "1") == "1":
        try:
            _swarm_tier = str(pick.get("swarm_tier", "") or "").lower()
            if _swarm_tier == "single" and not _forward_bypass and not _pair_exc_active:
                logger.debug(
                    "M-041 swarm_single_tier_block: tier=single has no forward validation (symbol=%s)",
                    pick.get("symbol", "?"),
                )
                return False
        except Exception:
            pass  # fail-open

    # ── M-044: CRYPTO minimum signal age (2026-05-17) ──────────────────────────
    # Swarm finding: many CRYPTO picks are within first 24h of signal generation.
    # Early-lifecycle trades have lower WR — filter until signal ages 24h.
    # Default OFF (CRYPTO_MIN_TRADE_AGE=0). Enable: CRYPTO_MIN_TRADE_AGE=24.
    if _ac == "CRYPTO":
        try:
            _min_age_h = int(os.environ.get("CRYPTO_MIN_TRADE_AGE", "0"))
            if _min_age_h > 0:
                from datetime import datetime as _dt_m044, timezone as _tz_m044
                _sig_ts = pick.get("signal_timestamp", pick.get("created_at", pick.get("entry_time", "")))
                if _sig_ts:
                    _sig_dt = _dt_m044.fromisoformat(str(_sig_ts).rstrip("Z")).replace(tzinfo=_tz_m044.utc)
                    _age_h = (_dt_m044.now(_tz_m044.utc) - _sig_dt).total_seconds() / 3600
                    if _age_h < _min_age_h:
                        logger.debug(
                            "M-044 crypto_min_trade_age: signal age %.1fh < %dh floor (symbol=%s)",
                            _age_h, _min_age_h, pick.get("symbol", "?"),
                        )
                        return False
        except Exception:
            pass  # fail-open: bad timestamp → skip gate

    # ── CRYPTO source-consensus floor (P1, expert_feedback_action_plan_2026-05-17.md) ──
    # Expert finding: 7,766 CRYPTO picks but only ~250-300 are T1.
    # Require >= CRYPTO_MIN_SOURCE_CONSENSUS source systems to agree before
    # promoting to smart picks. Default=3, overridable via env-var.
    # This targets the 25x signal overproduction driving 47.2% class-wide WR.
    if _ac == "CRYPTO":
        from alpha_engine.config import CRYPTO_MIN_SOURCE_CONSENSUS as _CRYPTO_MIN_SC
        _crypto_src_systems = pick.get("source_systems", [])
        if isinstance(_crypto_src_systems, str):
            _crypto_src_systems = [s.strip() for s in _crypto_src_systems.split(",") if s.strip()]
        _crypto_agreement = _float(pick.get("agreement_count", 0))
        _crypto_n_sources = max(len(_crypto_src_systems), int(_crypto_agreement))
        if _crypto_n_sources < _CRYPTO_MIN_SC and not _forward_bypass and not _pair_exc_active:
            logger.debug(
                "Pick rejected: CRYPTO source consensus %d < floor %d",
                _crypto_n_sources, _CRYPTO_MIN_SC,
            )
            return False

    # Golden criteria disqualifiers — picks that empirically lose
    mode = str(pick.get("mode", pick.get("trade_mode", "")) or "").upper()
    health = str(pick.get("health_at_entry", "") or "").lower()

    # SCALP mode: 24.8% WR — exclude from Smart Picks entirely
    if mode == "SCALP":
        return False

    # Panic health: 24% WR — not Smart Pick material
    if health == "panic":
        return False

    rr = _trade_rr(pick)
    if rr < SMART_PICKS_MIN_RR and not _pair_exc_active:
        return False

    # R:R ceiling — data shows R:R >= 2.0 has lower hit rate (TP too far)
    rr = _float(pick.get("rr", pick.get("rr_ratio", pick.get("risk_reward", 0))))
    if rr > SMART_PICKS_MAX_RR and rr > 0:
        logger.debug(f"Smart gate: R:R {rr} exceeds ceiling {SMART_PICKS_MAX_RR}")
        return False

    conf = _normalize_confidence(pick.get("confidence", 0))
    _raw_trust_score = pick.get("trust_score")
    trust_score = _float(_raw_trust_score) if _raw_trust_score is not None else None
    trust_label = str(pick.get("trust_label", "") or "").upper()
    trust_tier = _trust_tier(pick)
    wf_verdict = _wf_verdict(pick)
    tech_bucket = _technical_alignment_bucket(pick)
    sym_track_wr = _float(pick.get("sym_track_wr", 0))
    sym_track_total = _int(pick.get("sym_track_total", 0))

    if conf < SMART_PICKS_MIN_CONFIDENCE:
        return False
    # NEW: ML score filter (decile test shows ml_score < 0.50 = 22% WR Kill Zone)
    ml_score = pick.get("ml_score")
    if ml_score is not None and ml_score < SMART_PICKS_MIN_ML_SCORE:
        logger.debug(
            f"Pick rejected: ml_score {ml_score:.2f} < {SMART_PICKS_MIN_ML_SCORE} (Kill Zone)"
        )
        return False
    if conf > SMART_PICKS_MAX_CONFIDENCE and not (
        edge_trades >= 10 and edge_wr >= 0.60
    ):
        return False
    # Only block on numeric trust_score if the field is explicitly set.
    # trust_score=None means "unrated by registry" — not the same as bad.
    # tier/label checks below still protect against explicitly bad picks.
    if trust_score is not None and trust_score < SMART_PICKS_MIN_TRUST_SCORE:
        return False
    if (
        trust_label in BLOCKED_ACTIVE_TRUST_LABELS
        or trust_tier in BLOCKED_ACTIVE_TRUST_TIERS
    ):
        # See passes_active_gate trust-tier comment for the full rationale
        # (Gate 1 Q4 = A unanimous, 2026-04-29): trust-tier model is
        # calibrated for CRYPTO; INVERTED on EQUITY/FOREX/etc.
        # Default-on bypass for non-CRYPTO classes; CRYPTO unchanged.
        # Back-compat: PR #508 EQUITY_TRUST_TIER_EXEMPT_ENABLED=1 still works.
        _ac_smart_exempt = str(pick.get("asset_class", "") or "").upper().strip()
        _legacy_equity_flag_on = (
            _ac_smart_exempt == "EQUITY"
            and os.environ.get("EQUITY_TRUST_TIER_EXEMPT_ENABLED", "0") == "1"
        )
        _force_flag = f"TRUST_TIER_GATE_FORCE_{_ac_smart_exempt}_ENABLED"
        _non_crypto_default_bypass = (
            _ac_smart_exempt in NON_CRYPTO_TRUST_EXEMPT_CLASSES
            and os.environ.get(_force_flag, "0") != "1"
        )
        if not (_legacy_equity_flag_on or _non_crypto_default_bypass):
            return False
    if _has_direction_conflict(pick):
        return False
    if sym_track_total >= 3 and sym_track_wr < 45:
        return False
    # Hard-block only REJECTED/BROKEN; FAILING is a soft penalty (score already penalizes it)
    if wf_verdict in {"REJECTED", "BROKEN"}:
        return False
    if tech_bucket in {"strong_opposition", "weak_opposition"}:
        return False
    if tech_bucket in {"no_support", "weak_support"}:
        proven_contrarian = trust_score >= 7 and (
            wf_verdict in {"VIABLE", "STRONG", "ELITE"}
            or (edge_trades >= 20 and edge_wr >= 0.55)
        )
        if not proven_contrarian:
            return False

    # Forward-test viability check: only accept picks from viable strategies
    strategy_lc = str(pick.get("strategy", "")).lower()
    is_viable = any(vs in strategy_lc for vs in _VIABLE_STRATEGIES_FORWARD.keys())
    is_demoted = any(ds in strategy_lc for ds in _DEMOTED_STRATEGIES_FORWARD.keys())
    
    # For non-crypto assets, be stricter - require forward validation
    if _ac not in ("CRYPTO", "") and not is_viable and edge_trades < 10:
        logger.debug("Smart gate: non-crypto strategy lacks forward validation")
        return False
    
    # Strategy with known poor forward WR: not Smart Pick material
    strat_fwd_wr = max(
        _ratio(pick.get("strat_fwd_wr")),
        _ratio(pick.get("strategy_fwd_wr")),
        _ratio(pick.get("forward_wr")),
    )
    strat_fwd_trades = max(
        _float(pick.get("strat_fwd_trades", 0)),
        _float(pick.get("strategy_fwd_trades", 0)),
        _float(pick.get("forward_trades", 0)),
    )
    if (
        strat_fwd_wr > 0
        and strat_fwd_wr < 0.35
        and strat_fwd_trades >= 10
        and not _pair_exc_active
    ):
        return False

    # Consensus rows need real edge, not just many agreeing sources.
    if _is_consensus_pick(pick) and edge_trades >= 10 and edge_wr < 0.45 and not _pair_exc_active:
        return False

    # Trust/high-conviction rework:
    # require minimum realized evidence for non-verified sources and block
    # drifted picks currently underperforming in live window.
    # COMMODITY COT trusted-source exemption — REVOKED 2026-05-29 (completes PR #34).
    # These COT sources were FALSIFIED by M-095 (look-ahead leakage: deduped ex-CT=F
    # n=20 / WR 30% / PF 0.51). They must NOT skip the convergence forward-trade gate.
    _CONV_TRUSTED: frozenset[str] = frozenset()
    _conv_cot_exempt = (
        _normalize_asset_class(pick.get("asset_class", "")) == "COMMODITY"
        and str(pick.get("source_system") or "").lower() in _CONV_TRUSTED
    )
    if not _is_verified_pm_or_copy_pick(pick) and not _conv_cot_exempt:
        if edge_trades < 5:
            return False
        if edge_wr < 0.45 and not _pair_exc_active:
            return False

    _age_h = _float(pick.get("age_hours") or 0)
    _live_pnl = _float(pick.get("pnl_pct") or pick.get("unrealized_pnl_pct") or 0)
    if _age_h >= 1.0 and _live_pnl <= -2.0:
        return False

    pick["high_conviction_gate_passed"] = bool(
        edge_trades >= 10
        and edge_wr >= 0.55
        and score >= (_min_score + 8)
        and not _has_direction_conflict(pick)
        and wf_verdict in {"VIABLE", "STRONG", "ELITE"}
    )

    # ── HF Quality Gate companion (PR feat/wire-hf-quality-gate-default-on-2026-04-28) ──
    # Per `reports/HEDGE_FUND_EDGE_FINDINGS_2026_04_22.md` thresholds, AND-combined
    # with smart-gate so it can only ever tighten, never loosen. Default-ON as of
    # 2026-04-28 per 4-of-5 external-AI consensus
    # (`reports/external_ai_review_hf_gate_default_on_2026_04_28.md`); flip to OFF
    # by setting `HF_QUALITY_GATE_ENABLED=0`. Soft-fails on any error so smart-gate
    # behavior is never broken if the sidecar module raises.
    #
    # Guardrails (mandatory from external-AI consensus):
    #   1) 50-pick rolling circuit-breaker — auto-bypasses if reject rate > 50%
    #   2) 200-pick attribution audit log — written to audit_trail/data/hf_gate_telemetry.json
    #   3) Per-asset-class reject counters — same telemetry file
    #   4) Pre-flip re-smoke gate — tools/run_hf_gate_smoke.py (CLI guard)
    if os.environ.get("HF_QUALITY_GATE_ENABLED", "1") == "1":
        try:
            from alpha_engine.hedge_fund_quality_gate import passes_hedge_fund_gate
            from audit_trail import hf_gate_telemetry as _hfgt

            if _hfgt._should_circuit_break_hf_gate():
                _hfgt.record_circuit_breaker_trip()
                logger.warning(
                    "Smart gate: HF circuit-breaker tripped, skipping HF gate this cycle"
                )
                pick["_hf_quality_gate_pass"] = None
                pick["_hf_quality_gate_reason"] = "circuit_breaker_tripped"
                # Flush telemetry so the trip is visible to dashboards/CI.
                _hfgt._flush_telemetry_to_disk()
                # Skip HF gate this cycle but continue down the rest of smart-gate.
            else:
                hf_ok, hf_reason = passes_hedge_fund_gate(pick)
                pick["_hf_quality_gate_pass"] = bool(hf_ok)
                if not hf_ok:
                    pick["_hf_quality_gate_reason"] = hf_reason
                    logger.debug(f"Smart gate: HF quality gate rejected — {hf_reason}")
                _hfgt.record_hf_gate_decision(pick, bool(hf_ok), hf_reason)
                _hfgt._flush_telemetry_to_disk()
                if not hf_ok:
                    return False
        except Exception as exc:  # pragma: no cover — safety net only
            logger.debug(f"Smart gate: HF quality gate raised, soft-failing: {exc}")

    # ── Opt-in HF Audit Strict Smart Gate (Wave 2 wiring 2026-04-28) ──
    # Lazy/fail-safe wrapper around audit_trail.hf_strict_smart_gate. Only
    # consulted when env flag HF_AUDIT_SMART_STRICT=1; on any import or
    # call exception we swallow and proceed (no behavior change). The
    # helper itself short-circuits to None unless its own config has
    # ``enabled=true`` in config/hf_audit_smart_strict.json, so this is
    # double-gated. Imports are deliberately local to keep module-level
    # import-time behavior of quality_gates unchanged.
    try:
        if os.environ.get("HF_AUDIT_SMART_STRICT", "") == "1":
            try:
                from audit_trail.hf_strict_smart_gate import (
                    strict_smart_gate_fail_reason,
                )
                reason = strict_smart_gate_fail_reason(pick)
                if reason:
                    logger.debug(
                        f"Smart gate: strict mode rejected ({reason})"
                    )
                    return False
            except Exception as exc:  # pragma: no cover — fail-safe
                logger.debug(
                    f"Smart gate: strict helper raised, soft-failing: {exc}"
                )
    except Exception as exc:  # pragma: no cover — outer fail-safe
        logger.debug(f"Smart gate: strict env-check raised, soft-failing: {exc}")

    # ── PCG5 portfolio gates (LIVE enforcement when enforce_mode=True) ──
    # NOTE: This call has a live hard-reject path. It is NOT shadow-only.
    # Distinguish from the pcg5_gates shadow at lines ~6699-6708 which is shadow-only.
    # Wire-Up Rule compliance: caller = passes_smart_gate (portfolio gate runs at
    # smart-picks level, not basic active level).
    # Shadow mode: logs to pcg5_log.json but does NOT reject (PCG5_ENFORCE=0 default).
    # Enforce mode: set PCG5_ENFORCE=1 to honor REJECT verdicts.
    try:
        from audit_trail.portfolio_gates import evaluate_pick as _pcg5_evaluate
        _pcg5_result = _pcg5_evaluate(pick)
        _pcg5_action = _pcg5_result.get("action", "APPROVE")
        _pcg5_enforce = _pcg5_result.get("enforce_mode", False)
        if _pcg5_enforce and _pcg5_action == "REJECT":
            logger.info(
                "Smart gate: PCG-5 REJECT symbol=%s reason=%s",
                pick.get("symbol", ""),
                "; ".join(_pcg5_result.get("reasons", []))[:120],
            )
            return False
    except Exception:
        pass  # fail-open: never break smart gate on PCG-5 error

    # ── per_class_trainer shadow mode (2026-05-15, Wire-Up Rule compliance) ──
    # Predicts per-asset-class pick quality using ML model trained on closed picks.
    # SHADOW ONLY: never rejects; logs prediction to ml_gatekeeper/data/per_class_gates.json
    # for 30-day data collection. Enforce after 30d with PER_CLASS_ML_ENFORCE=1.
    # Individual try/except — failure here never masks pcg5_gates below.
    try:
        if _PCT_TRAINER_AVAILABLE and os.environ.get("PER_CLASS_ML_SHADOW", "1") == "1":
            _pct_ac = str(pick.get("asset_class", "CRYPTO") or "CRYPTO").upper()
            _pct_result = _pct_predict_fn(pick, _pct_ac)
            pick["_ml_per_class_score"] = _pct_result.get("ml_per_class_score")
            pick["_ml_per_class_pass"] = _pct_result.get("ml_per_class_pass")
            pick["_ml_per_class_status"] = _pct_result.get("ml_per_class_status", "shadow")
            if os.environ.get("PER_CLASS_ML_ENFORCE", "0") == "1":
                if _pct_result.get("ml_per_class_pass") is False:
                    pick["_hf_quality_gate_reason"] = "per_class_ml_gate"
                    logger.debug(
                        "Smart gate: per_class_ml_gate REJECT ac=%s score=%.3f thr=%.3f",
                        _pct_ac,
                        _pct_result.get("ml_per_class_score", 0) or 0,
                        _pct_result.get("ml_per_class_threshold", 0) or 0,
                    )
                    return False
    except Exception:
        pass  # fail-open: shadow only — no pick ever rejected on import failure

    # ── pcg5_gates shadow log (2026-05-15, wire-up via pcg5_gates.py) ──
    # Evaluates G1-G5 portfolio gates and writes to pcg5_log.json without rejecting.
    # Individual try/except so pcg5 failure never masks per_class_trainer above.
    try:
        from audit_trail.pcg5_gates import passes_pcg5_gate as _pcg5_shadow
        _pcg5_shadow_result = _pcg5_shadow(pick)
        pick["_pcg5_verdict"] = _pcg5_shadow_result.get("verdict", "APPROVE")
        pick["_pcg5_gates_triggered"] = _pcg5_shadow_result.get("gates_triggered", [])
    except Exception:
        pass  # fail-open: shadow only

    # ── M-042: COMMODITY SHORT-only gate (2026-05-17) ──────────────────────────
    # SHORT-only: PF=2.10/WR=58.06% (n=62) vs base PF=1.92/WR=55.22% (n=67).
    # LONG trades drag the class down. Default ON.
    # Kill-switch: COMMODITY_SHORT_ONLY=0 to allow LONG commodity picks.
    if _ac == "COMMODITY" and os.environ.get("COMMODITY_SHORT_ONLY", "1") == "1":
        try:
            _cmd_dir = str(pick.get("direction", "") or "").upper()
            if _cmd_dir in ("LONG", "BUY"):
                logger.debug(
                    "M-042 commodity_short_only: COMMODITY LONG blocked (SHORT-only PF=2.10 > LONG-included PF=1.92)"
                )
                return False
        except Exception:
            pass  # fail-open

    # ── M-043: BOND minimum n gate (2026-05-17) ────────────────────────────────
    # BOND n=18 is below charter floor of 20. Block until accumulation clears floor.
    # Default ON. Kill-switch: BOND_MIN_N_GATE=0 to allow all BOND picks.
    # Threshold tunable via BOND_MIN_N env var (default 20).
    if _ac == "BOND" and os.environ.get("BOND_MIN_N_GATE", "1") == "1":
        try:
            import json as _json_m043
            from pathlib import Path as _Path_m043
            _dd_path = _Path_m043(__file__).resolve().parents[1] / "audit_dashboard" / "data" / "dashboard_data.json"
            if _dd_path.exists():
                _dd = _json_m043.loads(_dd_path.read_text(encoding="utf-8"))
                _bond_n = 0
                for _cls in (_dd.get("performance", {}).get("asset_class_health") or []):
                    if str(_cls.get("asset_class", "")).upper() == "BOND":
                        _bond_n = int(_cls.get("n", 0))
                        break
                _bond_min_n = int(os.environ.get("BOND_MIN_N", "20"))
                if 0 < _bond_n < _bond_min_n:
                    logger.debug(
                        "M-043 bond_min_n: BOND blocked — n=%d below charter floor %d",
                        _bond_n, _bond_min_n,
                    )
                    return False
        except Exception:
            pass  # fail-open: if dashboard_data.json unreadable, allow BOND picks

    # ── M-045: EQUITY VIX regime filter (2026-05-17) ────────────────────────────
    # Block EQUITY picks when VIX exceeds high-volatility threshold.
    # Backtest: EQUITY picks during VIX>25 regime have PF<0.8 vs PF=1.41 overall.
    # Fail-open: if VIX unavailable, picks pass. Default OFF (shadow) — enable with
    # EQUITY_VIX_FILTER=1. Threshold configurable via EQUITY_VIX_FILTER_THRESHOLD.
    if _ac == "EQUITY" and os.environ.get("EQUITY_VIX_FILTER", "0") == "1":
        try:
            from audit_trail.vix_regime_gate import get_cached_vix as _get_vix_m045
            _vix_m045 = _get_vix_m045()
            _vix_ceil = float(os.environ.get("EQUITY_VIX_FILTER_THRESHOLD", "25.0"))
            _blocked_m045 = _vix_m045 is not None and _vix_m045 > _vix_ceil
            if _blocked_m045:
                logger.debug(
                    "M-045 equity_vix_filter: EQUITY blocked — VIX=%.1f > %.1f threshold (symbol=%s)",
                    _vix_m045, _vix_ceil, _sym,
                )
            # Shadow log: append each evaluation for trigger-rate monitoring
            try:
                import json as _json_m045
                import datetime as _dt_m045
                from pathlib import Path as _Path_m045
                _vlog = _Path_m045("reports") / "vix_gate_shadow_log.jsonl"
                _vlog.parent.mkdir(exist_ok=True)
                with open(_vlog, "a", encoding="utf-8") as _vf:
                    _vf.write(_json_m045.dumps({
                        "ts": _dt_m045.datetime.now(_dt_m045.timezone.utc).isoformat(),
                        "symbol": _sym,
                        "vix_value": _vix_m045,
                        "threshold": _vix_ceil,
                        "blocked": _blocked_m045,
                    }) + "\n")
            except Exception:
                pass
            if _blocked_m045:
                return False
        except Exception:
            pass  # fail-open: VIX unavailable → allow pick

    # ── M-046: COMMODITY per-source concentration cap (2026-05-17) ──────────────
    # Swarm review flagged: cftc_cot_commercial_signal = 51.6% of COMMODITY picks
    # (HHI=0.485, threshold 0.25). Single-strategy failure = 51.6% position loss.
    # Cap: no single source_system may exceed COMMODITY_MAX_SOURCE_PCT (default 30%)
    # of the total unresolved (OPEN) COMMODITY picks in active_picks.json.
    # Fail-open: if pick count unavailable, allow pick. Default OFF (shadow).
    # Enable with COMMODITY_SOURCE_CAP=1.
    if _ac == "COMMODITY" and os.environ.get("COMMODITY_SOURCE_CAP", "0") == "1":
        try:
            _src = str(pick.get("source_system") or "").strip().lower()
            _cap_pct = float(os.environ.get("COMMODITY_MAX_SOURCE_PCT", "0.30"))
            import json as _json_m046
            from pathlib import Path as _Path_m046
            _ap = _Path_m046(__file__).resolve().parent.parent / "alpha_engine" / "data" / "active_picks.json"
            if _ap.exists():
                _all_comm = [
                    p for p in _json_m046.loads(_ap.read_text())
                    if str(p.get("asset_class") or "").upper() == "COMMODITY"
                    and str(p.get("status") or "").upper() == "OPEN"
                ]
                _total_comm = len(_all_comm)
                if _total_comm >= 5:
                    _src_count = sum(
                        1 for p in _all_comm
                        if str(p.get("source_system") or "").strip().lower() == _src
                    )
                    _src_share = _src_count / _total_comm
                    if _src_share >= _cap_pct:
                        logger.debug(
                            "M-046 commodity_source_cap: blocked %s — source '%s' at %.1f%% (cap=%.0f%%, n=%d)",
                            _sym, _src, _src_share * 100, _cap_pct * 100, _total_comm,
                        )
                        return False
        except Exception:
            pass  # fail-open

    # ── M-096: CT=F symbol concentration cap for COMMODITY (2026-05-18) ──────────
    # CT=F (Cotton futures) represents ~84.9% of OPEN COMMODITY picks, blocking PBO
    # computation (single-name autocorrelation dominates). Cap at 40% max share.
    # 3-round swarm calibration 2026-05-18: 35% over-restricts WR=78% best edge;
    # 50% insufficient protection; 40% = 4/10 picks, limits catastrophic drawdown
    # while preserving 4 high-WR CT=F slots. Enforce ON default.
    # Kill: COMMODITY_CTF_CAP=0. Shadow only: COMMODITY_CTF_CAP=shadow.
    if _ac == "COMMODITY" and os.environ.get("COMMODITY_CTF_CAP", "1") not in ("", "skip"):
        try:
            _m096_sym = str(pick.get("symbol", "") or "").upper().strip()
            if _m096_sym == "CT=F":
                _ctf_enforce = os.environ.get("COMMODITY_CTF_CAP", "1") not in ("0", "shadow", "false", "False")
                _ctf_max_pct = float(os.environ.get("COMMODITY_CTF_MAX_PCT", "0.40"))
                import json as _json_m096
                from pathlib import Path as _Path_m096
                _ap_m096_override = os.environ.get("COMMODITY_CTF_ACTIVE_PICKS_PATH", "")
                _ap_m096 = (
                    _Path_m096(_ap_m096_override)
                    if _ap_m096_override
                    else _Path_m096(__file__).resolve().parent.parent / "alpha_engine" / "data" / "active_picks.json"
                )
                if _ap_m096.exists():
                    _all_comm_m096 = [
                        p for p in _json_m096.loads(_ap_m096.read_text())
                        if str(p.get("asset_class") or "").upper() == "COMMODITY"
                        and str(p.get("status") or "").upper() == "OPEN"
                    ]
                    _total_m096 = len(_all_comm_m096)
                    if _total_m096 >= 5:
                        _ctf_count = sum(
                            1 for p in _all_comm_m096
                            if str(p.get("symbol") or "").upper() == "CT=F"
                        )
                        _ctf_share = _ctf_count / _total_m096
                        if _ctf_share >= _ctf_max_pct:
                            if _ctf_enforce:
                                logger.info(
                                    "M-096 ctf_concentration_cap: REJECTED CT=F — %.1f%% >= %.0f%% cap (n=%d)",
                                    _ctf_share * 100, _ctf_max_pct * 100, _total_m096,
                                )
                                return False
                            else:
                                pick["_ctf_concentration_shadow"] = True
                                pick["_ctf_concentration_pct"] = round(_ctf_share * 100, 1)
                                logger.debug(
                                    "M-096 ctf_concentration_cap: SHADOW CT=F=%.1f%% >= %.0f%% (set COMMODITY_CTF_CAP=1 to enforce)",
                                    _ctf_share * 100, _ctf_max_pct * 100,
                                )
        except Exception:
            pass  # fail-open

    # ── M-047: EQUITY shadow floor at elite_score>=50 (2026-05-17) ──────────────
    # OOS data shows elite>=45 gives PF=2.20 (n=39 OOS) — promising but small.
    # Shadow gate: log picks that pass the current >=55 floor but ALSO pass >=50
    # so we can accumulate OOS n without changing production behavior.
    # Logging only — never blocks. Enable with EQUITY_SHADOW_FLOOR_50=1.
    if _ac == "EQUITY" and os.environ.get("EQUITY_SHADOW_FLOOR_50", "0") == "1":
        try:
            _elite = float(pick.get("elite_score") or pick.get("score") or 0)
            if 50 <= _elite < 55:
                logger.info(
                    "M-047 equity_shadow_floor_50: SHADOW-PASS symbol=%s elite=%.0f (passes>=50, fails>=55)",
                    _sym, _elite,
                )
                # Append to shadow log for OOS accumulation
                from pathlib import Path as _Path_m047
                import json as _json_m047
                _slog = _Path_m047("reports") / "equity_shadow_floor_log.jsonl"
                _slog.parent.mkdir(exist_ok=True)
                with open(_slog, "a", encoding="utf-8") as _sf:
                    import datetime as _dt_m047
                    _sf.write(_json_m047.dumps({
                        "ts": _dt_m047.datetime.now(_dt_m047.timezone.utc).isoformat(),
                        "symbol": _sym,
                        "elite_score": _elite,
                        "source_system": pick.get("source_system"),
                    }) + "\n")
        except Exception:
            pass  # fail-open: logging never blocks

    # M-110: Mark pick as having passed the active gate (lifecycle traceability)
    try:
        if _pll_m110 and _pll_pick_id_m110:
            _pll_m110.transition_stage(_pll_pick_id_m110, "passed_gate")
    except Exception:
        pass

    return True


def _is_verified_pm_or_copy_pick(pick: Dict[str, Any]) -> bool:
    """Return True for audited PM / pro-trader style sources we want to surface."""
    return _verified_pm_or_copy_bonus(pick) > 0


def _verified_pm_or_copy_bonus(pick: Dict[str, Any]) -> int:
    """Ranking bonus for verified PM / auditable pro-trader sources."""
    source = str(pick.get("source_system", "") or "").lower()
    strategy = str(pick.get("strategy", "") or "").lower()

    if source == "prediction_market_consensus":
        return 16
    # 2026-04-05 what-if: Polymarket direct signals were 2/2 correct (BTC LONG + ETH SHORT)
    # while pm_whale BTC SHORT consensus FAILED (BTC drifted +0.30% today). Direct
    # Polymarket probability > whale-derived aggregates. Reweighting.
    if source == "polymarket_signals" and strategy.startswith("copy_pm_"):
        return 16  # was 14 - direct PM with copy strategy = highest non-consensus
    if source == "polymarket_signals":
        return 14  # was 10 - direct PM probability validated on 2026-04-05
    if source == "pm_kalshi_signals":
        return 12
    if source == "pm_whale_signals" and strategy.startswith("copy_pm_"):
        return 12  # was 15 - reduced relative to direct Polymarket
    if source == "pm_whale_signals":
        return 10  # was 12 - whale aggregates can miss actual resolution
    if strategy.startswith("copy_pm_"):
        return 12
    if source == "multi_asset_copytrader" and strategy in {
        "forex_rsi2_mean_reversion",
        "stocks_rsi2_pullback",
        "cftc_cot_commercial_signal",
    }:
        return 10
    return 0


def calculate_smart_score(pick: Dict[str, Any]) -> float:
    """
    Calculate a 0-100 Smart Score for ranking Smart Picks.

    Weights derived from golden criteria analysis (2,256+ closed picks,
    cross-validated by Claude, ChatGPT-Codex, KiloCode, Copilot):

    Component weights (total = 100):
      Base score (penalty-adjusted)    30 pts  — already encodes 13 factors
      R:R quality                      15 pts  — 2.0-3.0 = 71.6% WR (strongest)
      Strategy track record            15 pts  — largest Q1-Q4 WR spread
      Trust tier                       12 pts  — Spearman r=0.21
      Confidence sweet spot            10 pts  — 0.7-0.8 = 61.8% WR
      Technical alignment              10 pts  — 2/3+ = 76-86% WR
      Multi-source consensus            8 pts  — 5 strats = 44.7% WR
    """
    if not _has_valid_trade_geometry(pick):
        return 0.0

    score = 0.0
    edge_wr = _effective_forward_wr_ratio(pick)
    edge_trades = _effective_forward_trades(pick)
    proven_edge = edge_trades >= 10 and edge_wr >= 0.60
    decent_edge = edge_trades >= 5 and edge_wr >= 0.50
    weak_edge = edge_trades >= 10 and 0 < edge_wr < 0.35

    # 1. Base score (0-30 pts) — already encodes source system, strategy,
    #    trust, consensus, HTF, mode, health, overfit, etc.
    # 2026-04-19: Recalibrated per Phase B of AUDIT_PREDICTION_SYSTEM_ENHANCEMENT_PLAN.
    # Raw-score Spearman vs PnL only +0.08; linear pass-through propagates miscalibration.
    # Piecewise capped mapping discounts low/mid raw scores, caps top scores at 30.
    raw = _float(pick.get("score", 0))
    if raw <= 0:
        base = 0.0
    elif raw <= 40:        # bottom decile territory
        base = raw * 0.10
    elif raw <= 70:        # middle deciles
        base = raw * 0.20
    else:                  # top deciles
        base = min(raw * 0.30, 30.0)

    # Copy-trader cap: 0.8x when non-BTC-major (mirrors alpha_engine/elite_scorer cap philosophy)
    strategy_lower = str(pick.get("strategy", "")).lower()
    is_copy = pick.get("_is_copy_pick") is True or strategy_lower.startswith("copy_hl")
    symbol = str(pick.get("symbol", "")).upper()
    is_btc_major = symbol in {"BTC", "ETH", "SOL", "BTCUSDT", "ETHUSDT", "SOLUSDT", "BTC-USD", "ETH-USD", "SOL-USD"}
    if is_copy and not is_btc_major:
        base *= 0.8
    score += base

    # 2. R:R quality (0-15 pts) — strongest single technical signal
    entry = _float(pick.get("entry_price", 0))
    tp = _float(pick.get("take_profit", 0))
    sl = _float(pick.get("stop_loss", 0))
    rr = _trade_rr(pick)
    if 2.0 <= rr <= 3.0:
        score += 15  # Sweet spot: 71.6% WR
    elif 1.5 <= rr < 2.0:
        score += 10
    elif 1.0 <= rr < 1.5:
        score += 6
    elif rr > 3.0:
        score += 8  # Good but not as reliable as 2-3x
    elif rr > 0:
        score += 2

    # 3. Strategy forward WR (0-15 pts) — largest Q1-Q4 spread
    strat_fwd_wr = edge_wr
    strat_fwd_trades = edge_trades
    if strat_fwd_wr >= 0.60 and strat_fwd_trades >= 10:
        score += 15
    elif strat_fwd_wr >= 0.50 and strat_fwd_trades >= 5:
        score += 10
    elif strat_fwd_wr >= 0.40 and strat_fwd_trades >= 5:
        score += 5
    elif strat_fwd_wr > 0 and strat_fwd_wr < 0.35:
        pass  # No bonus for poor track records

    # 4. Edge confidence — Probabilistic Sharpe Ratio (0-12 pts)
    # 2026-04-28: Replaced the legacy trust-tier component (PROVEN/RELIABLE
    # categorical) with a PSR-based score per source_system. Rationale:
    #   - Trust tier was a hand-tuned 4-bucket discretisation of the same
    #     underlying signal (does this source have realised edge?).
    #   - PSR = P(true_sharpe > 0) is a continuous, statistically grounded
    #     measure that auto-penalises short track records (small n -> wide
    #     standard error -> PSR clusters near 0.5).
    #   - Bailey & Lopez de Prado (2014) treat PSR > 0.95 as "publishable
    #     confidence in the edge"; our top point (12) maps to that floor.
    #
    # Mapping (see alpha_engine.risk_metrics.psr_points docstring):
    #   PSR <=0.20 -> 0,  PSR=0.50 -> 6,  PSR=0.80 -> 9,  PSR>=0.95 -> 12.
    #   (linear between anchors)
    #
    # Backwards compat: if a source has < MIN_TRADES_FOR_PSR (30) closed
    # trades, PSR is unreliable and we fall back to the legacy trust-tier
    # mapping so newly-onboarded sources are not silently zero-pointed.
    trust_score_val = _float(pick.get("trust_score", 0))
    trust_label = str(pick.get("trust_label", "") or "").upper()
    trust_tier_val = _trust_tier(pick)

    # Compute legacy fallback (used when PSR is unreliable due to n<30).
    if trust_tier_val == "PROVEN" or trust_label == "PROVEN":
        _legacy_trust_pts = 5.0 if weak_edge else 15.0
    elif trust_score_val >= 7:
        _legacy_trust_pts = 10.0
    elif trust_score_val >= 5:
        _legacy_trust_pts = 6.0
    else:
        _legacy_trust_pts = 0.0

    try:
        from alpha_engine.risk_metrics import psr_points as _psr_points
        _src = pick.get("source_system") or pick.get("source") or ""
        score += _psr_points(str(_src), fallback_pts=_legacy_trust_pts)
    except Exception:
        # Defensive: if PSR module/data unavailable, never crash the score
        # path — degrade gracefully to legacy trust-tier scoring.
        score += _legacy_trust_pts

    # 2026-04-05: SWING x RELIABLE biggest fixable bleed - 36.4% WR on n=1043.
    # Apply -8 penalty specifically to SWING timeframe picks from RELIABLE tier.
    _tf_upper = str(pick.get("trade_timeframe", "") or "").upper()
    if _tf_upper == "SWING" and (
        trust_tier_val == "RELIABLE" or trust_label == "RELIABLE"
    ):
        score -= 8
        # No append to penalties list here (not in that function scope)

    # 2026-04-05: Cursor factor-ranking confirms RELIABLE tier is TOXIC across
    # all timeframes: 36.1% WR on n=1377 CRYPTO closed (-7.3pp vs baseline).
    # Apply -5 general penalty on CRYPTO RELIABLE picks not already caught by SWING combo.
    _asset_cls = str(pick.get("asset_class", "") or "").upper()
    if (
        _asset_cls == "CRYPTO"
        and _tf_upper != "SWING"
        and (trust_tier_val == "RELIABLE" or trust_label == "RELIABLE")
    ):
        score -= 5

    # 2026-04-05: grade=A on CRYPTO = 70.2% WR on n=84 (+26.8pp) per Cursor data.
    # Strong signal, rare occurrence. Boost to capture edge.
    _pick_grade = str(pick.get("grade", "") or "").upper()
    if _pick_grade == "A" and _asset_cls in ("CRYPTO", "EQUITY"):
        score += 8

    # POSITION timeframe on CRYPTO = 31.5% WR (-12pp lift). Anti-signal.
    if _asset_cls == "CRYPTO" and _tf_upper == "POSITION":
        score -= 5

    # 5. Confidence sweet spot (0-10 pts) — 0.7-0.8 = 61.8% WR
    # 2026-05-11 SUPREME EDGE P0 #9: use _normalize_confidence (not _float) to
    # defend against the 0-10 scale leakage in trading_picks (~2k mixed-scale
    # rows per tools/audit_confidence_schema.py). Without normalization, a
    # legacy 10.000 confidence inflates this component to 10 pts despite the
    # underlying signal being calibration-inverted per P0 #9 verify.
    conf = _normalize_confidence(pick.get("confidence", 0))
    if 0.70 <= conf <= 0.80:
        score += 10  # Empirical sweet spot
    elif 0.55 <= conf < 0.70:
        score += 5
    elif 0.80 < conf <= 0.90:
        score += 6
    elif conf > SMART_PICKS_MAX_CONFIDENCE and not proven_edge:
        score -= 6
    # 0.6-0.7 is NOT penalized here (already done in base score)

    # 6. Technical alignment (0-10 pts) — 2/3+ alignment = 76-86% WR
    tech_bucket = _technical_alignment_bucket(pick)
    if tech_bucket == "full_support":
        score += 10
    elif tech_bucket == "strong_support":
        score += 8
    elif tech_bucket == "weak_support":
        score += 2
    elif tech_bucket == "no_support":
        score -= 6
    elif tech_bucket == "weak_opposition":
        score -= 8
    elif tech_bucket == "strong_opposition":
        score -= 12

    # 7. Multi-source consensus (0-8 pts)
    # Consensus only deserves a meaningful bonus when the track record supports it.
    agreement = _float(pick.get("agreement_count", 0))
    source_systems = pick.get("source_systems", [])
    if isinstance(source_systems, str):
        source_systems = [s.strip() for s in source_systems.split(",") if s.strip()]
    n_sources = max(len(source_systems), int(agreement))
    if n_sources >= 5:
        if proven_edge:
            score += 4
        elif decent_edge:
            score += 2
        elif weak_edge:
            score -= 4
        else:
            score += 1
    elif n_sources >= 3:
        if proven_edge or decent_edge:
            score += 4
        elif weak_edge:
            score -= 3
        else:
            score += 2
    elif n_sources == 2:
        if proven_edge or decent_edge:
            score += 3
        elif weak_edge:
            score -= 1
        else:
            score += 1

    # Bonuses for verified/proven sources
    verified_alpha_bonus = _verified_pm_or_copy_bonus(pick)
    if verified_alpha_bonus:
        score += min(verified_alpha_bonus * 0.5, 8)

    strategy = pick.get("strategy", "")
    if strategy in PROVEN_INVERSE_STRATEGIES:
        score += 5

    concentration_penalty = _concentration_penalty(pick)
    if concentration_penalty:
        score -= concentration_penalty

    wf_verdict = _wf_verdict(pick)
    if wf_verdict in {"ELITE", "STRONG"}:
        score += 6
    elif wf_verdict == "VIABLE":
        score += 3
    elif wf_verdict in {"DECAYING", "WEAK", "WARNING"}:
        score -= 5
    elif wf_verdict in {"FAILING", "REJECTED", "BROKEN"}:
        score -= 12

    if _has_direction_conflict(pick):
        score -= 10

    # 2026-04-28 (opt-in): Hurst-regime mismatch penalty.
    # Penalize strategies that are regime-incompatible when a pick already
    # carries a usable Hurst value from upstream feature enrichment.
    if str(os.getenv("HURST_REGIME_PENALTY_ENABLED", "0")).strip().lower() in ("1", "true", "yes", "on"):
        h_val = _float(pick.get("hurst_exponent", 0))
        if h_val <= 0:
            extra = pick.get("extra")
            if isinstance(extra, dict):
                h_val = _float(extra.get("hurst", 0))
        if 0 < h_val < 1:
            regime = "RANDOM_WALK"
            if h_val > 0.55:
                regime = "TRENDING"
            elif h_val < 0.45:
                regime = "MEAN_REVERTING"
            try:
                from tools.hurst_regime import strategy_regime_match
                if not strategy_regime_match(str(strategy), regime):
                    score -= 6
            except Exception:
                # Keep scorer robust if optional helper module is unavailable.
                pass

    clamped = round(max(0.0, min(score, 100)), 1)

    # Drift-aware multiplier (post-hoc wrapper).
    # Halves (or scales 0.5..1.0) the score when the pick's source_system has a
    # forward-WR drop > DRIFT_THRESHOLD_PP vs its longer baseline. Read-once cache,
    # O(1) per call. Defensive: a missing/broken drift module never breaks scoring.
    # See alpha_engine/drift_aware_scoring.py and reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md.
    try:
        from alpha_engine.drift_aware_scoring import apply_drift_aware_multiplier
        clamped = apply_drift_aware_multiplier(clamped, pick.get("source_system"))
    except Exception:  # pragma: no cover - never let drift wiring break scoring
        pass

    # Per-asset-class scoring overlay (opt-in, default OFF). Wire-Up Rule:
    # caller is this function — `audit_trail/quality_gates.py::calculate_smart_score`.
    # Activation env flag: `PER_ASSET_CLASS_SCORING_ENABLED=1`. Shadow:
    # `PER_ASSET_CLASS_SCORING_SHADOW=1` stamps `smart_score_v2_shadow` on
    # the pick dict but returns the legacy clamped. Blend ratio configurable
    # via `PER_ASSET_CLASS_SCORING_BLEND` (default 0.4 = 60% new + 40% legacy).
    # IC justification: tools/predictor_ic_reproducer.py 2026-05-13.
    # Wire-up validated by swarm round 2 (4/4 APPROVE).
    try:
        from alpha_engine.per_asset_class_predictor import (
            is_enabled as _pacp_enabled,
            is_shadow_mode as _pacp_shadow,
            per_asset_class_smart_score as _pacp_score,
        )
        if _pacp_enabled():
            import os as _os_p
            try:
                _blend = float(_os_p.environ.get("PER_ASSET_CLASS_SCORING_BLEND", "0.4"))
            except (TypeError, ValueError):
                _blend = 0.4
            _blend = max(0.0, min(1.0, _blend))
            # Enrich trust_score on-demand if not already set by production_scanner.
            # trust_score is the highest-IC feature (ρ=+0.154); without it the PACP
            # computes with 0 in the 35% slot, producing systematically wrong scores.
            if pick.get("trust_score") is None:
                try:
                    from alpha_engine.trust_score import compute_trust_score as _compute_ts
                    _ts_result = _compute_ts(pick)
                    pick["trust_score"] = _ts_result.get("trust_score", 0)
                    pick["trust_label"] = _ts_result.get("trust_label", "")
                except Exception:
                    pass
            # IDEA-A: stamp sector_rs_score on EQUITY picks before scoring
            try:
                from alpha_engine.equity_sector_rs import stamp_pick as _stamp_srs
                _stamp_srs(pick)
            except Exception:
                pass
            # IDEA-A: stamp earnings_surprise_score on EQUITY picks before scoring
            try:
                from alpha_engine.equity_earnings_surprise import stamp_pick as _stamp_eps
                _stamp_eps(pick)
            except Exception:
                pass
            # IDEA-A: stamp bdi_momentum_score on bulk COMMODITY picks before scoring
            try:
                from alpha_engine.commodity_bdi import stamp_pick as _stamp_bdi
                _stamp_bdi(pick)
            except Exception:
                pass
            # IDEA-A: stamp crop_condition_score on CT=F picks before scoring
            try:
                from alpha_engine.commodity_crop_condition import stamp_pick as _stamp_crop
                _stamp_crop(pick)
            except Exception:
                pass
            adjusted = _pacp_score(pick, base_smart_score=clamped, blend_with_base=_blend)
            adjusted = round(max(0.0, min(100.0, adjusted)), 1)
            if _pacp_shadow():
                pick["smart_score_v2_shadow"] = adjusted
                return clamped
            return adjusted
    except Exception:  # pragma: no cover - never let overlay break scoring
        pass

    return clamped


def classify_pick_quality(pick: Dict[str, Any]) -> str:
    """
    DEPRECATED — use classify_pick_quality_v2.

    Uses a single global score threshold (SMART_PICKS_MIN_SCORE=50), which
    diverges from passes_smart_gate's per-asset floors + crypto LONG-only +
    forex forward-WR + RR + SCALP/panic exclusions. Kept for backward compat.
    """
    if not passes_active_gate(pick):
        return "REJECTED"
    score = _float(pick.get("score", 0))
    if score >= SMART_PICKS_MIN_SCORE:
        return "SMART"
    return "ACTIVE"


def classify_pick_quality_v2(pick: Dict[str, Any]) -> str:
    """
    Single source of truth for SMART/ACTIVE/REJECTED classification.

    Delegates to passes_active_gate + passes_smart_gate so analytics labels
    match production behavior. For post-hoc analytics on closed picks, clones
    status='ACTIVE' so the classifier evaluates at-issue quality regardless
    of current resolved state.

    Returns: 'SMART' | 'ACTIVE' | 'REJECTED'
    """
    if not isinstance(pick, dict):
        return "REJECTED"
    clone = dict(pick)
    clone["status"] = "ACTIVE"
    if not passes_active_gate(clone):
        return "REJECTED"
    if passes_smart_gate(clone):
        return "SMART"
    return "ACTIVE"


def get_pick_rationale(pick: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate human-readable rationale for why a pick passed/failed gates.
    """
    rationale = {
        "quality_tier": classify_pick_quality(pick),
        "smart_score": calculate_smart_score(pick),
        "checks": {},
        "passed_all": True,
    }

    # Active gate checks
    checks = {
        "has_valid_status": str(pick.get("status", "")).upper()
        in {"", "OPEN", "ACTIVE", "PENDING", "LIVE"},
        "has_entry_price": _float(pick.get("entry_price", 0)) > 0,
        "has_tp_sl": _float(pick.get("take_profit", 0)) > 0
        and _float(pick.get("stop_loss", 0)) > 0,
        "valid_trade_geometry": _has_valid_trade_geometry(pick),
        "not_killed": pick.get("strategy", "").lower() not in _KILLED_STRATEGIES_LOWER,
        "not_15m": not _is_15m_model(pick.get("strategy", "")),
        "fresh_enough": True,  # Would need timestamp check
        "allowed_tier": _get_strategy_tier(pick.get("strategy", ""))
        in ALLOWED_SOURCE_TIERS,
    }

    # Smart gate checks (if applicable)
    if all(checks.values()):
        score = _smart_floor_score(pick)
        conf = _normalize_confidence(pick.get("confidence", 0))
        ml = _float(pick.get("ml_score", 0))

        smart_checks = {
            "high_score": score >= SMART_PICKS_MIN_SCORE,
            "confidence_sweet_spot": SMART_PICKS_MIN_CONFIDENCE
            <= conf
            <= SMART_PICKS_MAX_CONFIDENCE,
            "ml_validated": ml >= SMART_PICKS_MIN_ML_SCORE,
            "trustworthy": (
                pick.get("trust_score") in (None, "")
                or _float(pick.get("trust_score")) >= SMART_PICKS_MIN_TRUST_SCORE
            )
            and str(pick.get("trust_label", "") or "").upper() not in {"LOW", "AVOID"}
            and _trust_tier(pick) not in BLOCKED_ACTIVE_TRUST_TIERS,
            "good_rr": True,  # Would need calculation
        }
        checks.update(smart_checks)
        rationale["passed_all_smart"] = all(smart_checks.values())

    rationale["checks"] = checks
    rationale["passed_all"] = all(checks.values())

    return rationale


def concept_gate_shadow_audit(pick: Dict[str, Any]) -> Dict[str, Any]:
    """Return concept-family metadata for gate explainability (B5 / Cursor Phase 3).

    Read-only helper — does NOT change ``passes_active_gate`` behaviour.
    When ``CONCEPT_SCORING_SHADOW=0`` (default), returns ``shadow_on=False``
    and ``concept_pts=0`` so callers get a no-op result safely.
    """
    try:
        from alpha_engine.concept_scorer import compute_concept_modifier
        result = compute_concept_modifier(pick, strategy_perf=None)
        return {
            "concept_family": result.get("family", pick.get("concept_family") or "standard"),
            "concept_pts": result.get("pts", 0),
            "shadow_on": result.get("shadow_on", False),
            "gated": result.get("gated", False),
            "reason": result.get("reason", ""),
        }
    except Exception:
        return {
            "concept_family": pick.get("concept_family") or "standard",
            "concept_pts": 0,
            "shadow_on": False,
            "gated": False,
            "reason": "concept_scorer unavailable",
        }


# ──────────────────────────────────────────────────────────────────────────────
# Open-Bloat Health Monitor (swarm Round C, 2026-05-14)
# ──────────────────────────────────────────────────────────────────────────────
def check_open_bloat_health(
    active_picks: List[Dict[str, Any]],
    threshold_warn: float = 0.90,
    threshold_pause: float = 0.95,
) -> Dict[str, Any]:
    """Check for open-bloat: high ratio of OPEN picks means WR is being inflated.

    When >90% of picks are OPEN (never closed), reported WR is effectively 0%
    meaningful signal — the system is in "open-bloat" state. Failure mode #3
    from the proactive monitoring swarm (2026-05-14).

    Returns:
        {
            "total": int,
            "open_count": int,
            "open_pct": float,
            "status": "healthy" | "warn" | "pause",
            "action": str,
            "by_class": { "CRYPTO": {"open_pct": float, "total": int}, ... }
        }
    """
    if not active_picks:
        return {"total": 0, "open_count": 0, "open_pct": 0.0, "status": "healthy", "action": "no picks"}

    total = len(active_picks)
    open_statuses = {"open", "active", "pending", "", None}
    open_count = sum(
        1 for p in active_picks
        if str(p.get("status", "") or "").lower() in open_statuses
    )
    open_pct = open_count / total if total > 0 else 0.0

    # Per-class breakdown
    by_class: Dict[str, Any] = {}
    for p in active_picks:
        cls = str(p.get("asset_class") or p.get("category") or "UNKNOWN").upper()
        by_class.setdefault(cls, {"open": 0, "total": 0})
        by_class[cls]["total"] += 1
        if str(p.get("status", "") or "").lower() in open_statuses:
            by_class[cls]["open"] += 1
    for cls, counts in by_class.items():
        t = counts["total"]
        counts["open_pct"] = round(counts["open"] / t, 3) if t > 0 else 0.0

    if open_pct >= threshold_pause:
        status = "pause"
        action = f"PAUSE new emissions — open bloat {open_pct:.0%} >= {threshold_pause:.0%} threshold"
    elif open_pct >= threshold_warn:
        status = "warn"
        action = f"WARN — open bloat {open_pct:.0%} >= {threshold_warn:.0%}; WR may be inflated"
    else:
        status = "healthy"
        action = "OK"

    result = {
        "total": total,
        "open_count": open_count,
        "open_pct": round(open_pct, 4),
        "status": status,
        "action": action,
        "by_class": by_class,
    }
    logger.info("[OPEN_BLOAT] %s: %d/%d open (%.1f%%) — %s", status, open_count, total, open_pct * 100, action)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Source Score Staleness Audit (swarm Round C failure mode #4, 2026-05-14)
# ──────────────────────────────────────────────────────────────────────────────
def audit_source_score_staleness(
    closed_picks: List[Dict[str, Any]],
    min_n: int = 20,
    stale_threshold_pf: float = 0.80,
) -> List[Dict[str, Any]]:
    """Detect source systems where _SOURCE_SYSTEM_SCORES is stale vs live performance.

    Failure mode #4: goldmine_stocks had score +12 (comment: "67% WR")
    but live PF=0.14, WR=42.9%. Stale score → routing continues sending volume
    to dead source.

    Args:
        closed_picks: Resolved closed picks with pnl_pct and source_system fields.
        min_n: Minimum closed picks to compute a verdict (avoid noise).
        stale_threshold_pf: If live PF < this AND score > 0, flag as stale.

    Returns:
        List of dicts: {source, score_in_registry, live_pf, live_wr, live_n,
                        verdict, action_recommended}
    """
    # Compute live PF per source_system from closed picks
    from collections import defaultdict
    source_stats: Dict[str, Any] = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl_sum": 0.0, "n": 0})
    for p in closed_picks:
        src = str(p.get("source_system") or "").lower().strip()
        if not src:
            continue
        pnl = float(p.get("pnl_pct", 0) or 0)
        stats = source_stats[src]
        stats["n"] += 1
        stats["pnl_sum"] += pnl
        if pnl > 0:
            stats["wins"] += 1
        elif pnl < 0:
            stats["losses"] += 1

    flags = []
    for src, stats in source_stats.items():
        n = stats["n"]
        if n < min_n:
            continue
        wins = stats["wins"]
        losses = stats["losses"]
        wr = wins / n if n > 0 else 0.0
        gross_wins = sum(
            float(p.get("pnl_pct", 0) or 0)
            for p in closed_picks
            if str(p.get("source_system") or "").lower() == src and float(p.get("pnl_pct", 0) or 0) > 0
        )
        gross_losses = abs(sum(
            float(p.get("pnl_pct", 0) or 0)
            for p in closed_picks
            if str(p.get("source_system") or "").lower() == src and float(p.get("pnl_pct", 0) or 0) < 0
        ))
        live_pf = gross_wins / gross_losses if gross_losses > 0 else (9.99 if gross_wins > 0 else 0.0)

        registry_score = _SOURCE_SYSTEM_SCORES.get(src, 0)
        verdict = "ok"
        action = ""

        if live_pf < stale_threshold_pf and registry_score > 0:
            verdict = "STALE_POSITIVE"
            action = f"Score {registry_score:+d} is POSITIVE but live PF={live_pf:.2f} — audit and downgrade"
        elif live_pf > 2.0 and registry_score < 0:
            verdict = "STALE_NEGATIVE"
            action = f"Score {registry_score:+d} is NEGATIVE but live PF={live_pf:.2f} — consider upgrade"
        elif src not in _SOURCE_SYSTEM_SCORES and live_pf < 0.80:
            verdict = "MISSING_BAD"
            action = f"Source not in registry, live PF={live_pf:.2f} — add negative score"

        if verdict != "ok":
            flags.append({
                "source": src,
                "score_in_registry": registry_score,
                "live_pf": round(live_pf, 3),
                "live_wr": round(wr, 3),
                "live_n": n,
                "verdict": verdict,
                "action_recommended": action,
            })

    # Sort by severity (worst stale_positive first)
    flags.sort(key=lambda x: x.get("live_pf", 0))
    if flags:
        logger.warning("[SOURCE_SCORE_AUDIT] %d stale scores detected: %s",
                       len(flags), [f["source"] for f in flags])
    return flags


# ===================================================================
# A1 scaffold self-test — meta_label_gate SHADOW mode
# ===================================================================
# Run: python -m audit_trail.quality_gates  (from repo root)
# Proves the shadow gate stamps fields and NEVER rejects.
if __name__ == "__main__":
    import copy as _copy

    _sample = {
        "id": "TEST_META_LABEL_1",
        "symbol": "BTCUSDT",
        "strategy": "rsi_macd_confluence",
        "asset_class": "CRYPTO",
        "confidence": 0.72,
        "risk_reward": 2.5,
        "confluence_score": 3,
        "timestamp": "2026-05-16T12:00:00Z",
    }

    print("A1 meta_label_gate self-test")
    print("-" * 50)

    # 1. Disabled by default (META_LABEL_GATE unset/0) -> no-op, no stamp.
    os.environ.pop("META_LABEL_GATE", None)
    _p = _copy.deepcopy(_sample)
    _r = meta_label_gate(_p)
    assert _r["enabled"] is False, "default should be disabled"
    assert "_meta_label_pwin" not in _p, "disabled gate must not stamp"
    print("[ok] default OFF: no stamp, enabled=False")

    # 2. Enabled SHADOW mode -> stamps fields, returns a verdict.
    os.environ["META_LABEL_GATE"] = "1"
    _p2 = _copy.deepcopy(_sample)
    _before = passes_active_gate(_copy.deepcopy(_sample))  # reference outcome
    _r2 = meta_label_gate(_p2)
    if _r2["enabled"] and _r2["pwin"] is not None:
        assert "_meta_label_pwin" in _p2, "enabled gate must stamp pwin"
        assert "_meta_label_verdict" in _p2, "enabled gate must stamp verdict"
        assert _p2["_meta_label_verdict"] in ("PASS", "WOULD_REJECT")
        assert 0.0 <= _p2["_meta_label_pwin"] <= 1.0
        print(f"[ok] SHADOW ON: pwin={_p2['_meta_label_pwin']} "
              f"verdict={_p2['_meta_label_verdict']}")
    else:
        print("[ok] SHADOW ON: labeler unavailable -> fail-soft no-op")

    # 3. Shadow gate NEVER changes the admission outcome.
    _after = passes_active_gate(_copy.deepcopy(_sample))
    assert _before == _after, "shadow gate must not change passes_active_gate outcome"
    print(f"[ok] passes_active_gate outcome unchanged ({_before})")

    os.environ.pop("META_LABEL_GATE", None)
    print("-" * 50)
    print("A1 self-test PASSED")


# ═══════════════════════════════════════════════════════════════════════════════
# A9 — Emitter/Resolver Idempotency Guard
# ═══════════════════════════════════════════════════════════════════════════════
# 41% of raw closed rows were duplicate re-emissions (pf_registry_2026-05-17).
# Winners re-emit more than losers, asymmetrically inflating PF/WR/DSR.
# This gate stamps a deterministic dedup_key on every pick and blocks
# re-emissions at the admission boundary.
# ═══════════════════════════════════════════════════════════════════════════════

def passes_emitter_dedup_gate(
    pick: Dict[str, Any],
    existing_keys: Optional[Set[str]] = None,
) -> tuple[bool, str, str]:
    """Return (passes, reason, dedup_key) for a single pick.

    Computes (or reuses) ``pick['dedup_key']`` and rejects the pick if that
    key is already present in ``existing_keys``.  When ``existing_keys`` is
    omitted the gate is a no-op (always passes) — this lets callers that only
    want the side-effect of stamping ``dedup_key`` use the same function.

    The key is a stable hash of
    ``(asset_class, strategy, symbol, direction, entry_bar, entry_price~2dp)``
    so two re-emissions of the same signal collapse even when they carry
    fresh ``id`` values.

    Fail-soft: if ``emitter_dedup`` is missing or crashes, the pick passes
    and the returned ``dedup_key`` is an empty string.
    """
    try:
        from alpha_engine.emitter_dedup import ensure_dedup_key
    except Exception:
        return True, "emitter_dedup_unavailable", ""

    try:
        key = ensure_dedup_key(pick)
    except Exception:
        return True, "dedup_key_compute_failed", ""

    if existing_keys is not None and key and key in existing_keys:
        return False, f"duplicate_re_emission(dedup_key={key})", key

    return True, "fresh_emission", key


def dedup_picks_list(
    picks: List[Dict[str, Any]], *, label: str = "picks"
) -> tuple[List[Dict[str, Any]], int, Set[str]]:
    """Drop duplicate re-emissions from *picks* using deterministic dedup_key.

    Returns ``(deduped_list, blocked_count, seen_keys)``.
    Stamps ``dedup_key`` on every pick (in place), keeps the FIRST occurrence
    of each key, and logs an alert when any duplicates are blocked.

    This is the canonical ledger-writer guard: call it immediately before
    persisting any closed-pick list.
    """
    try:
        from alpha_engine.emitter_dedup import dedup_closed_picks
    except Exception:
        logger.warning("[EMITTER_DEDUP] emitter_dedup unavailable — skipping dedup for %s", label)
        return picks, 0, set()

    deduped, blocked = dedup_closed_picks(picks, label=label)
    seen: Set[str] = set()
    for p in deduped:
        k = p.get("dedup_key", "")
        if k:
            seen.add(k)
    return deduped, blocked, seen


# ── Self-test ──
if __name__ == "__main__" and __import__("sys").argv[-1] == "--a9-self-test":
    import os
    os.environ["EMITTER_DEDUP"] = "1"
    _base = {
        "asset_class": "CRYPTO", "strategy": "test_strat",
        "symbol": "BTCUSDT", "direction": "LONG",
        "entry_time": "2026-05-17T00:00:00Z", "entry_price": 64000.01,
    }
    # fresh pick passes
    _p1 = dict(_base)
    _ok, _reason, _key = passes_emitter_dedup_gate(_p1)
    assert _ok and _reason == "fresh_emission" and _key, "fresh pick should pass"
    assert _p1.get("dedup_key") == _key, "dedup_key should be stamped"
    # duplicate is blocked
    _p2 = dict(_base)
    _p2["id"] = "fresh-id"
    _ok2, _reason2, _key2 = passes_emitter_dedup_gate(_p2, existing_keys={_key})
    assert not _ok2 and "duplicate_re_emission" in _reason2, "duplicate should be blocked"
    # dedup list
    _d, _b, _s = dedup_picks_list([dict(_base), dict(_base)], label="selftest")
    assert len(_d) == 1 and _b == 1, "list dedup should drop one"
    print("A9 self-test PASSED")
