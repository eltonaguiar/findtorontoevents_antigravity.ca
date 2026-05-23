#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Forward Validator
===================================
The core validation loop. Runs every cycle to:
  1. Load active picks from JSON (persisted in git)
  2. Fetch current live prices from yfinance
  3. Track MFE (max favorable excursion) and MAE (max adverse excursion)
  4. Check TP / SL / trailing stop / max hold expiry
  5. Close picks that trigger, record exact outcomes
  6. Compute per-strategy stats (win rate, Sharpe, avg PnL, etc.)
  7. Feed results to strategy_tweaker for automatic parameter adjustment

Persistence: JSON files committed to git after each GH Actions run.
No SQLite dependency for pick tracking (SQLite doesn't survive GH Actions).

Usage:
  python forward_validator.py                  # Validate all open picks
  python forward_validator.py --generate       # Generate new picks (calls scanner)
  python forward_validator.py --report         # Performance report only
  python forward_validator.py --full-cycle     # Generate + validate + tweak
"""

from __future__ import annotations

import sys
_orig_print = print
def print(*args, **kwargs):
    """Robust print that survives closed stderr/stdout on Windows."""
    try:
        _orig_print(*args, **kwargs)
    except (ValueError, OSError):
        pass

# Force UTF-8 for subprocess/Windows output stability
if sys.platform == "win32":
    import os
    os.environ.setdefault("PYTHONUTF8", "1")
    # try:
    #     sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    #     sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    # except Exception:
    #     pass

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import math
import numpy as np

from alpha_engine.strategy_suppression import is_row_killed, is_strategy_killed, load_kill_list


def _emitter_registry_blocks_signal(signal: dict) -> bool:
    """T2-01: block toxic (class, strategy) at emission time in forward_validator."""
    try:
        from alpha_engine.emitter_whitelist import passes_emitter_registry_gate
        probe = {
            "asset_class": signal.get("asset_class", "CRYPTO"),
            "strategy": signal.get("strategy") or signal.get("strategy_name"),
            "source_system": signal.get("source_system") or signal.get("source"),
            "symbol": signal.get("symbol"),
        }
        return not passes_emitter_registry_gate(probe)
    except Exception:
        return False


def binomial_p_value(wins: int, total: int, null_hypothesis: float = 0.5) -> float:
    """One-sided binomial test: is win rate significantly better than chance?
    Returns p-value. Lower = more confident the edge is real.
    """
    if total < 5:
        return 1.0
    observed_rate = wins / total
    if observed_rate <= null_hypothesis:
        return 1.0
    se = math.sqrt(null_hypothesis * (1 - null_hypothesis) / total)
    if se == 0:
        return 1.0
    z = (observed_rate - null_hypothesis) / se
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return p


def _sanitize_for_json(obj):
    """Recursively replace NaN/Infinity with None so json.dump never emits invalid tokens."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    # numpy scalars
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


def _repair_standard_streams() -> list[str]:
    """Disabled: caused I/O operation on closed file errors on Windows."""
    return []


def _normalize_quan_strategy_name(raw_strategy, mode=None) -> str:
    """Collapse quan_engine metadata to stable strategy IDs."""
    strategy_text = str(raw_strategy or "").strip().lower()
    mode_text = str(mode or "").strip().lower()
    combined = f"{strategy_text} {mode_text}".strip()

    if combined.startswith("quan_engine_"):
        return combined.split()[0]
    if "position" in combined:
        return "quan_engine_position"
    if "swing" in combined:
        return "quan_engine_swing"
    if "scalp" in combined:
        return "quan_engine_scalp"
    return "quan_engine_consensus"


def _backfill_quan_closed_metadata(picks: list[dict]) -> bool:
    """Repair legacy quan_engine closed picks so tiering/scoring can use them."""
    dirty = False
    quan_picks: list[dict] = []

    for pick in picks:
        source_system = str(pick.get("source_system", "") or "").lower()
        source = str(pick.get("source", "") or "").lower()
        strategy = str(pick.get("strategy", "") or "")
        if source_system != "quan_engine" and source != "quan_engine" and not strategy.startswith("quan_engine_"):
            continue

        if not pick.get("source_system"):
            pick["source_system"] = "quan_engine"
            dirty = True
        if not pick.get("source"):
            pick["source"] = "quan_engine"
            dirty = True

        normalized_strategy = _normalize_quan_strategy_name(
            pick.get("strategy"),
            pick.get("quan_mode") or pick.get("mode") or pick.get("trade_timeframe"),
        )
        if pick.get("strategy") != normalized_strategy:
            pick["strategy"] = normalized_strategy
            dirty = True

        direction = str(pick.get("direction") or pick.get("signal_type") or "").upper()
        if direction in {"BUY", "LONG"}:
            direction = "LONG"
        elif direction in {"SELL", "SHORT"}:
            direction = "SHORT"
        if direction and not pick.get("signal_type"):
            pick["signal_type"] = direction
            dirty = True

        quan_picks.append(pick)

    missing_scores = [pick for pick in quan_picks if pick.get("elite_score") is None]
    if missing_scores:
        enrich_picks_with_elite_score(missing_scores, DATA_DIR)
        dirty = True

    return dirty
import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    DATA_DIR, ALL_SYMBOLS, CATEGORY_RISK, TRAILING_STOP,
    TRAIL_ACTIVATE_PCT, CRYPTO_SYMBOLS, FOREX_SYMBOLS,
    FAST_MODE, STRATEGY_WEIGHT_OVERRIDES, DEFAULT_ALLOCATION,
    STARTING_CAPITAL,
    resolve_yf_symbols,
)
from position_sizing import annotate_signal_with_kelly, get_position_size
from elite_scorer import enrich_picks_with_elite_score

# --- Gate modules (Tasks 1-3: VPIN, Cooldown, Deflated Sharpe) ---
try:
    from vpin_detector import calculate_vpin
except ImportError:
    calculate_vpin = None

try:
    from enhanced_strategies import should_skip_due_to_losses
except ImportError:
    should_skip_due_to_losses = None

try:
    from deflated_sharpe import returns_stats, sharpe_variance, deflated_sharpe_ratio
except ImportError:
    returns_stats = None
    sharpe_variance = None
    deflated_sharpe_ratio = None

try:
    from validation.monte_carlo import MonteCarloSimulator
    _mc_simulator = MonteCarloSimulator(n_simulations=1000, random_seed=42)
except ImportError:
    _mc_simulator = None

try:
    from garch_volatility import get_garch_forecast
except ImportError:
    get_garch_forecast = None

try:
    from sl_calibrator import apply_calibrated_sl_tp, recalibrate as recalibrate_sl
except ImportError:
    apply_calibrated_sl_tp = None
    recalibrate_sl = None

try:
    from entry_optimizer import compute_entry_timing_score
except ImportError:
    compute_entry_timing_score = None

try:
    from hold_duration_optimizer import adjust_risk_for_duration as _adjust_risk_for_duration
except ImportError:
    _adjust_risk_for_duration = None

try:
    from smart_entry import SmartEntryDetector
    _smart_entry_detector = SmartEntryDetector()
except ImportError:
    _smart_entry_detector = None

try:
    from execution_cost import compute_net_edge
except ImportError:
    compute_net_edge = None

try:
    from pattern_predictor import PatternPredictor
    _pattern_predictor = PatternPredictor(min_samples=5)
    _pattern_predictor_loaded = _pattern_predictor.load()
except ImportError:
    _pattern_predictor = None
    _pattern_predictor_loaded = False

# --- Priority 1: OBI Velocity for elite_score adjustment ---
try:
    from obi_velocity import compute_obi_velocity_batch
except ImportError:
    compute_obi_velocity_batch = None

# --- Priority 2: Conformal Prediction for position sizing ---
try:
    from conformal_sizing import ConformalSizer
    _conformal_sizer = ConformalSizer(coverage=0.90, min_calibration=30)
except ImportError:
    _conformal_sizer = None

# --- Priority 3: Shadow Tracker for blocked signal research ---
try:
    from shadow_tracker import record_blocked_signal, resolve_shadow_outcomes, get_gate_shadow_stats
except ImportError:
    record_blocked_signal = None
    resolve_shadow_outcomes = None
    get_gate_shadow_stats = None

# --- Fast Regime Detector (sub-minute microstructure ensemble) ---
try:
    from fast_regime_detector import (
        get_fast_regime, get_regime_for_symbol, regime_to_numeric,
    )
    _HAS_FAST_REGIME = True
except ImportError:
    _HAS_FAST_REGIME = False

# ---------------------------------------------------------------------------
# File paths (JSON -- persisted in git)
# ---------------------------------------------------------------------------
_SUFFIX = "_fast" if FAST_MODE else ""
ACTIVE_PICKS_PATH = DATA_DIR / f"active_picks{_SUFFIX}.json"
CLOSED_PICKS_PATH = DATA_DIR / f"closed_picks{_SUFFIX}.json"
# Append-only JSONL archive of closed picks that fall off the hot-file
# retention cap (see save_closed_picks). Added 2026-04-19 per code review
# Finding 4 so historical outcomes are never silently lost.
CLOSED_PICKS_ARCHIVE_PATH = DATA_DIR / f"closed_picks{_SUFFIX}.archive.jsonl"
STRATEGY_PERFORMANCE_PATH = DATA_DIR / "strategy_performance.json"
VALIDATION_LOG_PATH = DATA_DIR / "validation_log.json"
TWEAKS_PATH = DATA_DIR / "strategy_tweaks.json"
CORE_WHITELIST_PATH = DATA_DIR / "core_whitelist.json"

# Fallback whitelist path (trading/data/ is the canonical source)
_CORE_WHITELIST_FALLBACK = Path(__file__).resolve().parent.parent / "trading" / "data" / "core_whitelist.json"


def _load_core_whitelist_kill_list() -> set[str]:
    """Load kill_list from core_whitelist.json. Returns set of strategy names to suppress.

    Tries alpha_engine/data/core_whitelist.json first, falls back to trading/data/.
    If neither exists, returns empty set (graceful fallback).
    """
    kill = load_kill_list(str(CORE_WHITELIST_PATH))
    if not kill:
        kill = load_kill_list(str(_CORE_WHITELIST_FALLBACK))
    if kill:
        print(f"  [WHITELIST] Loaded {len(kill)} killed strategy entries")
    return kill


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# White's Reality Check -- multiple hypothesis testing for strategy alpha
# ---------------------------------------------------------------------------

def run_white_reality_check(closed_picks_path: Path = None) -> dict[str, float]:
    """
    Run White's Reality Check on all strategies in closed_picks.json.

    Groups closed picks by strategy, computes per-strategy return series,
    and calls MonteCarloSimulator.whites_reality_check() with
    n_strategies_tested = total number of distinct strategies.

    Returns:
        dict of {strategy_name: adjusted_p_value}
        Strategies with adjusted p-value > 0.05 are NOT significant after
        multiple testing correction (i.e., likely data-snooped).
    """
    if _mc_simulator is None:
        return {}

    try:
        import pandas as pd
    except ImportError:
        return {}

    fpath = closed_picks_path or CLOSED_PICKS_PATH
    if not fpath.exists():
        return {}

    try:
        with open(fpath, "r") as f:
            picks = json.load(f)
    except Exception:
        return {}

    # Group returns by strategy (excluding outlier symbols for honest metrics)
    from collections import defaultdict
    try:
        from elite_scorer import OUTLIER_SYMBOLS
    except ImportError:
        OUTLIER_SYMBOLS = {"FETUSDT", "RENDERUSDT"}
    strat_returns: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        strat = p.get("strategy", "")
        pnl = p.get("pnl_pct")
        symbol = str(p.get("symbol", "") or "").upper()
        if strat and pnl is not None and symbol not in OUTLIER_SYMBOLS:
            strat_returns[strat].append(float(pnl) / 100.0)

    n_strategies_tested = max(len(strat_returns), 1)
    results: dict[str, float] = {}

    # Use zero-return series as benchmark (no benchmark alpha)
    for strat, rets in strat_returns.items():
        if len(rets) < 10:
            continue  # Too few trades for meaningful test
        try:
            strategy_series = pd.Series(rets)
            benchmark_series = pd.Series([0.0] * len(rets))
            wrc = _mc_simulator.whites_reality_check(
                strategy_returns=strategy_series,
                benchmark_returns=benchmark_series,
                n_strategies_tested=n_strategies_tested,
            )
            results[strat] = wrc["p_value_adjusted"]
        except Exception:
            continue

    return results


# ---------------------------------------------------------------------------
# Forward-Test Gate -- Action 1.3 Remediation
# ---------------------------------------------------------------------------
# Requires >= 30 forward trades with WR > 50% before publishing validated
# signals. New strategies are NOT blocked -- they accumulate data in
# "unvalidated" mode so they can eventually graduate.
# ---------------------------------------------------------------------------

FORWARD_GATE_MIN_TRADES = 50  # Raised per cross-AI consensus (Kimi: 4 trades is noise, need 50+)
FORWARD_GATE_MIN_WR = 0.45    # Lowered from 0.50 -- 45% WR is still above random for crypto

# Per-asset-class min-trade overrides. BOND ETFs have lower idiosyncratic
# volatility, so 10 closed trades carry roughly the statistical weight of 50
# crypto trades. Per reports/bond_root_cause_2026-05-12.md Layer 2 (BR-2).
# Keys are lowercase asset_class names. Unlisted classes use the global
# FORWARD_GATE_MIN_TRADES.
FORWARD_GATE_OVERRIDES: dict[str, int] = {
    "bond": 10,
    "bonds": 10,
    # EQUITY charter floor: 20 (vs 50 for crypto). EQUITY picks are ~10× fewer
    # than crypto picks; 50-trade floor would lock out all EQUITY strategies.
    # stocks_rsi2_pullback has 37 closed picks → passes at 20 but not 50.
    # 2026-05-17: lowered from global 50 to match charter floor for sizing.
    "equity": 20,
    "equities": 20,
    # ETF: same rationale — slower accumulation, lower absolute n is still
    # statistically significant given lower variance vs crypto.
    "etf": 15,
    "etfs": 15,
}

# Source systems whose forward validation is handled externally (dashboard DB)
# and whose picks should be marked forward_validated=True when the pick itself
# carries a strat_fwd_wr field >= the forward gate WR floor.
# kimi_riseoftheclaw: 0 picks in closed_picks.json (tracked in dashboard MySQL
# only); rs-breakout-scout n=36 WR=75%, donchian-stock-breakout n=14 WR=78.6%
# verified from recent_closed — evidence of real edge exists, just not in the
# local closed_picks.json that compute_all_strategy_stats reads.
FORWARD_GATE_PASSTHROUGH_SOURCES: set[str] = {
    "kimi_riseoftheclaw",
}

# ---------------------------------------------------------------------------
# Winner Filter Gate -- based on research from 8,457 closed picks
# ---------------------------------------------------------------------------
# Filters picks for quality AFTER elite scoring, BEFORE final emission.
# Configurable and lenient by default to allow data flow.
# ---------------------------------------------------------------------------

WINNER_FILTER_ENABLED = True

WINNER_FILTER_CONFIG = {
    # Asset class: 2026-04-18 expanded from ["crypto","meme"] to multi-asset.
    # Original block was set when equity 35.7% WR / forex 31.4% WR dominated.
    # Per multi-agent diagnosis (Cursor + Kimi + Codebuff + Copilot + Codex +
    # Antigravity, see updates/2026-04-18-non-crypto-synthesis-and-action-plan.md):
    # the winner filter was the upstream "crypto-only mode" gate that prevented
    # any non-crypto signal from being emitted. Downstream gates now do the
    # actual quality work:
    #   - production_scanner Gate 0 still blocks equity/stock/commodity
    #     (these had real-PnL bleed; lifted later when supply pipeline ready)
    #   - hc_filter.js per-class floors at 40% (commit 8e97a8500d)
    #   - _is_valid_resolved_pick filters historical blocked rows + price
    #     corruption (commits 7b26754686, 44d4182a30, 19b8eda365)
    #   - BLOCKED_STRATEGIES + BLOCKED_ASSET_STRATEGY_PAIRS hit toxic
    #     per-(asset_class, strategy) combos
    # bond/etf/futures/forex are LOW-RISK to open here: production_scanner
    # Gate 0 doesn't block them, and current historical performance is
    # acceptable (BOND PF=1.6, COMMODITY PF=1.06, ETF/FOREX still building).
    # equity/stock/commodity included for completeness — they remain blocked
    # at Gate 0 in production_scanner so this expansion has no immediate
    # effect for those classes; the change documents intent for when Gate 0
    # transitions to per-strategy logic.
    "allowed_asset_classes": [
        "crypto", "meme",
        "forex", "fx",
        "equity", "stock", "stocks",
        "commodity", "commodities",
        "futures", "future",
        "etf",
        "bond", "bonds",
        "index",
    ],

    # 2026-03-24: Confidence cap raised from 0.75 to 0.85. Data shows
    # 0.75-0.80 = 79.2% WR (best bucket). Only >0.85 shows overfit (9.1% WR).
    "confidence_min": 0.55,
    "confidence_max": 0.85,

    # R:R ratio: below 1.5 = bad risk, above 3.0 = unreachable TP (29.7% WR)
    "rr_min": 1.5,
    "rr_max": 3.0,

    # Banned source systems (consistently losing strategies)
    # 2026-03-24 AUDIT: added 5 weak performers from closed picks analysis
    "banned_systems": {
        "rapid_fire", "stocks_competition", "mercury2_fast",
        "penny_momentum", "meme_social_momentum",
        "forex_carry_trade", "forex_session_breakout",
        "forex_dxy_correlation", "intermarket_rotation",
        # Added Mar 24: verified WR < 35% on 5+ trades from closed_picks.json
        "winner_pattern_precursor",   # 17.7% WR on 96 trades — proven loser
        "volume_spike_backfill",      # 30.0% WR on 50 trades — consistent loser
        "hl_momentum_continuation",   # 20.0% WR on 5 trades
    },

    # Time gate: Fixed per cross-AI consensus (Kimi: UTC 13-16 is highest volume, not death zone)
    # Real low-volume hours are UTC 21:00-00:00 (post-NY close, pre-Asia open)
    "death_zone_start_utc": 21,
    "death_zone_end_utc": 24,  # 21 <= hour < 24 captures hours 21,22,23
    "death_zone_penalty": 10,  # score penalty during actual low-volume hours

    # M-082: Per-strategy confidence_max overrides (provisional until n≥20 per strategy).
    # Strategies here bypass the global confidence_max ceiling ONLY.
    # All other checks (confidence_min, rr, banned_systems) still apply.
    # cross_sectional_reversal: always outputs conf≥0.86; 5/5 forward-test wins blocked
    # by the 0.85 ceiling (avg +5.88% PnL if traded). Shadow tracker data 2026-05-17 AP.
    "strategy_confidence_max_overrides": {
        "cross_sectional_reversal": 0.95,  # provisional; review at n=20 forward tests
    },
}

WINNER_FILTER_STATS = {
    "total_evaluated": 0,
    "passed": 0,
    "blocked_asset_class": 0,
    "blocked_confidence": 0,
    "blocked_rr": 0,
    "blocked_system": 0,
    "soft_penalized_time": 0,
    "trade_worthy_count": 0,
    "leverage_worthy_count": 0,
}


def _reset_winner_filter_stats():
    """Reset stats at the start of each scan cycle."""
    for k in WINNER_FILTER_STATS:
        WINNER_FILTER_STATS[k] = 0


def apply_winner_filter(signal: dict) -> tuple[bool, str]:
    """Apply the winner filter gate to a signal.

    Returns:
        (passes, reason) -- passes=True if signal should proceed,
        reason describes why it was blocked or passed.
    """
    if not WINNER_FILTER_ENABLED:
        return True, "winner_filter_disabled"

    cfg = WINNER_FILTER_CONFIG
    WINNER_FILTER_STATS["total_evaluated"] += 1

    # --- Check 1: Asset class ---
    category = str(signal.get("category", "")).lower()
    if category and category not in cfg["allowed_asset_classes"]:
        WINNER_FILTER_STATS["blocked_asset_class"] += 1
        return False, f"asset_class={category} not in {cfg['allowed_asset_classes']}"

    # --- Check 2: Confidence sweet spot ---
    confidence = signal.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            confidence = None
    if confidence is not None:
        strategy_name = str(signal.get("strategy") or signal.get("source_system") or "")
        overrides = cfg.get("strategy_confidence_max_overrides", {})
        conf_max = overrides.get(strategy_name, cfg["confidence_max"])
        if confidence < cfg["confidence_min"]:
            WINNER_FILTER_STATS["blocked_confidence"] += 1
            return False, f"confidence={confidence:.3f} < {cfg['confidence_min']} (noise zone)"
        if confidence > conf_max:
            WINNER_FILTER_STATS["blocked_confidence"] += 1
            return False, f"confidence={confidence:.3f} > {conf_max} (overfit zone)"

    # --- Check 3: R:R ratio ---
    rr = signal.get("risk_reward")
    if rr is not None:
        try:
            rr = float(rr)
        except (ValueError, TypeError):
            rr = None
    # If R:R field is missing (common for clone/copy-trader picks), compute from TP/SL/entry.
    # Without this, clone_hl_copy_* picks bypass the filter entirely (bug: ETHUSDT R:R=0.4x slipping through).
    if rr is None or rr <= 0:
        try:
            ep = float(signal.get("entry_price") or 0)
            tp = float(signal.get("take_profit") or 0)
            sl = float(signal.get("stop_loss") or 0)
            if ep > 0 and tp > 0 and sl > 0 and abs(ep - sl) > 0:
                rr = abs(tp - ep) / abs(ep - sl)
            else:
                rr = None
        except (TypeError, ValueError, ZeroDivisionError):
            rr = None
    if rr is not None and rr > 0:
        if rr < cfg["rr_min"]:
            WINNER_FILTER_STATS["blocked_rr"] += 1
            return False, f"R:R={rr:.2f} < {cfg['rr_min']} (bad risk)"
        if rr > cfg["rr_max"]:
            WINNER_FILTER_STATS["blocked_rr"] += 1
            return False, f"R:R={rr:.2f} > {cfg['rr_max']} (unreachable TP)"

    # --- Check 4: Banned systems ---
    strategy = str(signal.get("strategy", "")).lower()
    if strategy in cfg["banned_systems"]:
        WINNER_FILTER_STATS["blocked_system"] += 1
        return False, f"strategy={strategy} is banned (consistently losing)"

    # --- Check 5: Time gate (SOFT -- penalty only, not a hard block) ---
    try:
        now_utc = datetime.now(timezone.utc)
        if cfg["death_zone_start_utc"] <= now_utc.hour < cfg["death_zone_end_utc"]:
            # Apply score penalty instead of blocking
            current_score = signal.get("elite_score")
            if isinstance(current_score, (int, float)):
                signal["elite_score"] = current_score - cfg["death_zone_penalty"]
                signal["winner_filter_time_penalty"] = cfg["death_zone_penalty"]
            WINNER_FILTER_STATS["soft_penalized_time"] += 1
    except Exception:
        pass  # Time check failure must not block picks

    WINNER_FILTER_STATS["passed"] += 1
    return True, "passed"


def print_winner_filter_summary():
    """Print winner filter stats at end of scan cycle."""
    stats = WINNER_FILTER_STATS
    total = stats["total_evaluated"]
    passed = stats["passed"]
    blocked = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0
    print(f"\n  [WINNER FILTER SUMMARY]")
    print(f"    Winner Filter: {passed} passed, {blocked} blocked ({pass_rate:.0f}% pass rate)")
    print(f"    Blocked by asset class:  {stats['blocked_asset_class']}")
    print(f"    Blocked by confidence:   {stats['blocked_confidence']}")
    print(f"    Blocked by R:R ratio:    {stats['blocked_rr']}")
    print(f"    Blocked by banned system:{stats['blocked_system']}")
    print(f"    Soft-penalized (time):   {stats['soft_penalized_time']}")
    print(f"    Trade-worthy picks:      {stats['trade_worthy_count']}")
    print(f"    Leverage-worthy picks:   {stats['leverage_worthy_count']}")


def passes_forward_gate(strategy_name: str, strategy_stats: dict,
                        min_trades: int = FORWARD_GATE_MIN_TRADES,
                        min_wr: float = FORWARD_GATE_MIN_WR
                        ) -> tuple[bool, str, int, float]:
    """
    Check if a strategy has enough forward-test data to be published
    as a validated signal.

    Args:
        strategy_name: Strategy identifier (for logging).
        strategy_stats: Dict from compute_all_strategy_stats() with keys:
                        'wins', 'losses', 'closed_picks', 'win_rate'.
        min_trades:     Minimum closed trades required (default 30).
        min_wr:         Minimum win rate required (default 0.50 = 50%).

    Returns:
        (passes, reason, trade_count, win_rate)
    """
    wins = int(strategy_stats.get("wins", 0))
    losses = int(strategy_stats.get("losses", 0))
    total = int(strategy_stats.get("closed_picks", wins + losses))

    wr = strategy_stats.get("win_rate", (wins / total if total > 0 else 0.0))

    if total < min_trades:
        return (False,
                f"insufficient_data ({total}/{min_trades} trades)",
                total, float(wr))
    if wr < min_wr:
        return (False,
                f"low_wr ({wr:.1%} < {min_wr:.0%})",
                total, float(wr))
    return (True, "validated", total, float(wr))


def annotate_picks_with_forward_gate(picks: list[dict],
                                     perf: dict) -> int:
    """
    Annotate every pick in *picks* with forward-test gate metadata
    using strategy performance data.

    Args:
        picks: List of pick dicts (active or new), each with a 'strategy' key.
        perf:  Output of compute_all_strategy_stats().

    Returns the number of picks that passed the gate.
    """
    validated_count = 0
    for pick in picks:
        strategy = pick.get("strategy", "")
        # Collision-safe lookup (issue #173): prefer the per-(source_system,
        # strategy) row from ``by_source_system`` so a losing feeder's picks
        # don't get gated on a winning feeder's inflated merged aggregate
        # (and vice versa). Fall back to the legacy by-name row when the
        # pick has no source_system or when the new subkey is absent
        # (e.g. reading an old strategy_performance.json before the next
        # scheduled validator run has regenerated it under the new schema).
        src = pick.get("source_system", "") or ""
        legacy_row = perf.get(strategy, {}) or {}
        stats = {}
        if src:
            stats = (legacy_row.get("by_source_system") or {}).get(src) or {}
        if not stats:
            stats = legacy_row

        # Passthrough: source systems tracked in dashboard DB but not in
        # closed_picks.json. If the pick carries a strat_fwd_wr field that
        # already satisfies the WR floor, trust that external evidence.
        if src in FORWARD_GATE_PASSTHROUGH_SOURCES:
            _ext_wr = float(pick.get("strat_fwd_wr") or pick.get("forward_wr") or 0)
            if _ext_wr >= FORWARD_GATE_MIN_WR * 100:
                pick["forward_validated"] = True
                pick["forward_status"] = "PASSTHROUGH_EXTERNAL_SOURCE"
                pick["forward_trades"] = pick.get("forward_trades", 0)
                pick["forward_wr"] = round(_ext_wr / 100, 4)
                validated_count += 1
                continue

        # Per-class min_trades override: BOND/EQUITY/ETF use lower floors.
        ac = str(pick.get("asset_class", "") or "").lower()
        _min_trades = FORWARD_GATE_OVERRIDES.get(ac, FORWARD_GATE_MIN_TRADES)
        gate_pass, gate_reason, trade_count, win_rate = passes_forward_gate(
            strategy, stats, min_trades=_min_trades)

        # Laplace Smoothing: (wins + 1) / (total + 2)
        # Prevents 100% WR for 1 trade (becomes 66%), 0% for 1 trade (becomes 33%)
        wins = int(stats.get("wins", 0))
        total = int(stats.get("closed_picks", stats.get("wins", 0) + stats.get("losses", 0)))
        smoothed_wr = (wins + 1) / (total + 2)

        pick["forward_validated"] = gate_pass
        pick["forward_status"] = gate_reason
        pick["forward_trades"] = total
        pick["forward_wr"] = round(smoothed_wr, 4)

        if gate_pass:
            validated_count += 1

    return validated_count


# ---------------------------------------------------------------------------
# JSON persistence
# ---------------------------------------------------------------------------

def load_active_picks() -> list[dict]:
    if ACTIVE_PICKS_PATH.exists():
        with open(ACTIVE_PICKS_PATH) as f:
            return json.load(f)
    return []


def save_active_picks(picks: list[dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # -- Core whitelist kill-list filter --
    # Suppress signals from strategies on the kill list before writing.
    kill_list = _load_core_whitelist_kill_list()
    if kill_list:
        before_count = len(picks)
        picks = [p for p in picks if not is_row_killed(p, kill_list)]
        killed = before_count - len(picks)
        if killed:
            print(f"  [WHITELIST] Filtered {killed} picks from killed strategies before save")

    # -- BLOCKED_SYMBOLS defense-in-depth filter --
    # 11 emitters write to active_picks.json without going through production_scanner's
    # blocked-symbol gate. Filter here so the canonical save path is protected.
    # Wrapped in try/except so a missing import never crashes the save.
    try:
        from audit_trail.quality_gates import BLOCKED_SYMBOLS as _BLOCKED_SYMBOLS
        _before = len(picks)
        picks = [p for p in picks if str(p.get("symbol", "") or "").upper() not in _BLOCKED_SYMBOLS]
        _removed = _before - len(picks)
        if _removed:
            print(f"  [BLOCKED_SYMBOLS] Filtered {_removed} blocked picks before save")
    except Exception:
        pass  # fail-open: never let a missing import crash the save

    # -- Per-symbol caps & conflict resolution --
    # Max 2 picks per symbol. If LONG+SHORT conflict, keep the majority direction.
    # Added 2026-03-12: NIO had 6 picks, WIF had 7 (4 LONG + 1 SHORT), AUDJPY had 6.
    MAX_PER_SYMBOL = 2
    from collections import defaultdict
    sym_groups = defaultdict(list)
    for p in picks:
        sym_groups[p.get("symbol", "")].append(p)

    capped = []
    for sym, group in sym_groups.items():
        if len(group) <= MAX_PER_SYMBOL:
            capped.extend(group)
            continue

        # Resolve conflicts: count directions
        longs = [p for p in group if p.get("direction", "").upper() in ("LONG", "BUY")]
        shorts = [p for p in group if p.get("direction", "").upper() in ("SHORT", "SELL")]

        # Keep majority direction only
        if longs and shorts:
            majority = longs if len(longs) >= len(shorts) else shorts
            minority_count = len(group) - len(majority)
            print(f"  [CONFLICT] {sym}: {len(longs)}L/{len(shorts)}S -- dropping {minority_count} minority picks")
            group = majority

        # Cap to MAX_PER_SYMBOL (keep highest confidence)
        if len(group) > MAX_PER_SYMBOL:
            group.sort(key=lambda p: float(p.get("confidence", 0)), reverse=True)
            dropped = len(group) - MAX_PER_SYMBOL
            group = group[:MAX_PER_SYMBOL]
            print(f"  [CAP] {sym}: capped from {dropped + MAX_PER_SYMBOL} to {MAX_PER_SYMBOL} picks")

        capped.extend(group)

    if len(capped) < len(picks):
        print(f"  [DEDUP] Reduced active picks from {len(picks)} to {len(capped)} (caps + conflict resolution)")
    picks = capped

    # --- Hard portfolio cap (FIX: enforce regardless of which system writes) ---
    # PRIORITY: Proven strategies (statistically significant p<0.05) are NEVER trimmed
    PROVEN_STRATEGIES = {
        'ml_enhanced_BNBUSDT_15m_B_lightgbm',
        'ml_enhanced_FETUSDT_1d_B_lightgbm',
        'ml_enhanced_RENDERUSDT_1h_D_ensemble_stack',
        'ml_enhanced_RENDERUSDT_4h_D_ensemble_stack',
        'copy_hl_NMTD_25M',
        'stocks_rsi2_pullback',            # Top equities (80% WR)
        'myfxbook_retail_contrarian',      # Top forex
        'world_class_strategies_v21',      # Institutional rescue
    }
    MAX_PICKS = 100  # raised from 40 to accommodate 50% non-crypto representation (Apr 3 2026)
    if len(picks) > MAX_PICKS:
        before = len(picks)
        proven = [p for p in picks if any(s in p.get('strategy', '') for s in PROVEN_STRATEGIES)]
        others = [p for p in picks if not any(s in p.get('strategy', '') for s in PROVEN_STRATEGIES)]
        others = sorted(others, key=lambda p: float(p.get('ml_composite', p.get('elite_score', 0)) or 0), reverse=True)
        remaining_slots = MAX_PICKS - len(proven)
        picks = proven + others[:max(0, remaining_slots)]
        print(f"  [PORTFOLIO CAP] Trimmed from {before} to {len(picks)} (kept {len(proven)} proven, {len(picks)-len(proven)} others)")

    with open(ACTIVE_PICKS_PATH, "w") as f:
        json.dump(_sanitize_for_json(picks), f, indent=2)


def load_closed_picks() -> list[dict]:
    if CLOSED_PICKS_PATH.exists():
        with open(CLOSED_PICKS_PATH) as f:
            picks = json.load(f)
        # Backfill missing closed_at from last_checked or exit_date
        dirty = False
        for p in picks:
            if not p.get("closed_at") and p.get("last_checked"):
                p["closed_at"] = p["last_checked"]
                dirty = True
        # Normalize pnl_pct: some strategies write percentages (e.g. -62.18)
        # instead of decimals (e.g. -0.6218). Standardize to decimal format.
        for p in picks:
            pnl = p.get('pnl_pct')
            if pnl is not None and abs(pnl) > 1.0:
                p['pnl_pct'] = round(pnl / 100.0, 6)
                dirty = True
        # Normalize confidence: some strategies write percentages (e.g. 62.7)
        # instead of decimals (e.g. 0.627). Standardize to 0.0-1.0.
        for p in picks:
            conf = p.get('confidence', 0)
            if conf is not None and conf > 1.0:
                p['confidence'] = round(conf / 100.0, 4)
                dirty = True
        if _backfill_quan_closed_metadata(picks):
            dirty = True
        if dirty:
            with open(CLOSED_PICKS_PATH, "w") as f:
                json.dump(picks, f, indent=2)
        return picks
    return []


# Hot-file retention cap: keep the most recent N closed picks in the JSON
# file that validators / dashboards load on every cycle. Older picks are
# rotated to CLOSED_PICKS_ARCHIVE_PATH (append-only JSONL) so nothing is
# ever silently lost. Raise only after confirming downstream consumers can
# handle the larger working set.
CLOSED_PICKS_RETENTION = 500
# Archive dedup guard: max lines to scan from the tail of the JSONL archive
# when checking for already-archived pick IDs. Picks being archived are
# always recent, so a bounded tail-read is sufficient. The file I/O is
# still O(n) (every line is read), but only the last N lines are parsed
# as JSON -- saving CPU on large archives.
ARCHIVE_DEDUP_TAIL_LINES = 1000


def save_closed_picks(picks: list[dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # A9 (2026-05-17): emitter/resolver idempotency. Re-emissions get a FRESH
    # id every cycle, so the id-dedup below cannot catch them -- 41% of the
    # ledger was duplicate re-emissions (reports/pf_registry_2026-05-17.md).
    # Stamp a deterministic dedup_key and drop re-emissions BEFORE writing.
    # Env-gated (EMITTER_DEDUP=1 default ON), fail-soft -- never crashes.
    try:
        from alpha_engine.emitter_dedup import dedup_closed_picks as _a9_dedup
        picks, _ = _a9_dedup(picks, label="closed_picks(hot)")
    except Exception as _a9_err:  # pragma: no cover - defensive
        print(f"  [EMITTER_DEDUP] WARNING: import/guard failed ({_a9_err})")
    # Deduplicate by pick ID -- prevents phantom duplicates from re-opening
    seen_ids = set()
    deduped = []
    for p in picks:
        pid = p.get("id", "")
        if pid in seen_ids:
            continue
        seen_ids.add(pid)
        deduped.append(p)
    if len(deduped) < len(picks):
        print(f"  [DEDUP] Removed {len(picks) - len(deduped)} duplicate closed picks")

    # Archive picks that will be dropped by the retention cap so historical
    # outcomes are never silently lost (2026-04-19 code review, Finding 4).
    # Format: newline-delimited JSON (JSONL), one pick per line, append-only.
    # Read via:
    #     for line in open(CLOSED_PICKS_ARCHIVE_PATH): json.loads(line)
    # Each pick is archived exactly once, at the cycle where it falls off the
    # hot file (later save_closed_picks calls load the already-trimmed hot
    # file, so the same pick cannot be archived twice).
    if len(deduped) > CLOSED_PICKS_RETENTION:
        to_archive = deduped[:-CLOSED_PICKS_RETENTION]
        # 2026-04-22 DEFENSIVE: deduplicate against existing archive so a
        # hot-file rotation that runs twice (e.g. two validator processes
        # racing) cannot write the same pick twice. Each pick is archived
        # at most once because the hot file is trimmed after archival, but
        # a crash between archive-write and hot-file-write could leave
        # duplicates on the next cycle. Guard by pick ID.
        # Bounded tail-read: only parse last N lines of archive (picks being
        # archived are always recent; old IDs are irrelevant). File I/O is
        # still O(n) but JSON parsing is bounded to ARCHIVE_DEDUP_TAIL_LINES.
        _already_archived_ids: set[str] = set()
        try:
            if CLOSED_PICKS_ARCHIVE_PATH.exists():
                from collections import deque
                with open(CLOSED_PICKS_ARCHIVE_PATH, "r", encoding="utf-8") as _rf:
                    _tail = deque(_rf, maxlen=ARCHIVE_DEDUP_TAIL_LINES)
                for _line in _tail:
                    _line = _line.strip()
                    if not _line:
                        continue
                    try:
                        _existing = json.loads(_line)
                        _pid = _existing.get("id", "")
                        if _pid:
                            _already_archived_ids.add(_pid)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass  # Malformed archive is not fatal; skip dedup check
        _new_to_archive = [
            p for p in to_archive
            if p.get("id", "") not in _already_archived_ids
        ]
        try:
            with open(CLOSED_PICKS_ARCHIVE_PATH, "a", encoding="utf-8") as af:
                for pick in _new_to_archive:
                    af.write(json.dumps(_sanitize_for_json(pick), ensure_ascii=False))
                    af.write("\n")
            if _new_to_archive:
                print(f"  [ARCHIVE] Appended {len(_new_to_archive)} closed picks to {CLOSED_PICKS_ARCHIVE_PATH.name}")
            if len(_new_to_archive) < len(to_archive):
                print(f"  [ARCHIVE] Skipped {len(to_archive) - len(_new_to_archive)} already-archived picks (dedup guard)")
        except Exception as _arch_err:
            # Archive failure must never block the validator; log and continue.
            print(f"  [ARCHIVE] WARNING: failed to archive {len(to_archive)} picks: {_arch_err}")

    # Trim hot file to the retention cap (archive above preserves the rest).
    with open(CLOSED_PICKS_PATH, "w") as f:
        json.dump(_sanitize_for_json(deduped[-CLOSED_PICKS_RETENTION:]), f, indent=2)


def load_strategy_performance() -> dict:
    if STRATEGY_PERFORMANCE_PATH.exists():
        with open(STRATEGY_PERFORMANCE_PATH) as f:
            return json.load(f)
    return {}


def save_strategy_performance(perf: dict):
    """Merge-write to strategy_performance.json (UPSERT semantics).

    Prevent regression-to-empty: if new output has fewer strategies than
    existing file, log warning and either merge OR fail-loud. Never silently
    shrink coverage. Ref: PR #257/#258 regression findings.

    Historical bug (PR #257/#258): this used atomic_write_json which REPLACED
    the file. When validator ran on a partial closed_picks source (e.g. FAST
    mode reading closed_picks_fast.json, or a cycle where validate_picks only
    touched a few strategies), the full-coverage file was overwritten with the
    subset — coverage collapsed 161 -> 5 strategies, breaking every Wilson LB
    consumer (elite_scorer, dashboard, conviction_stack).

    Now uses merge_write_json: reads existing -> merges new entries on top ->
    atomic write. Each merged entry gets `last_seen` stamped for the 30-day
    prune cron (`tools/prune_strategy_performance.py`) to age out dead
    strategies. Never removes entries in a single cycle.
    """
    sanitized = _sanitize_for_json(perf) if perf else {}
    if not isinstance(sanitized, dict):
        sanitized = {}

    # --- Regression guard: warn loudly if new pass shrinks coverage ---
    try:
        existing = load_strategy_performance()
    except Exception:
        existing = {}
    existing_n = len(existing) if isinstance(existing, dict) else 0
    new_n = len(sanitized)
    if existing_n > 0 and new_n < existing_n:
        print(
            f"  [PERF-GUARD] new pass has {new_n} strategies, existing has "
            f"{existing_n}. Merging (not replacing) to preserve historical "
            f"entries. Ref: PR #257/#258."
        )

    try:
        from alpha_engine.atomic_json import merge_write_json
        merge_write_json(STRATEGY_PERFORMANCE_PATH, sanitized, indent=2)
        return
    except ImportError:
        pass
    except Exception as e:
        print(f"  [PERF-GUARD] merge_write_json failed ({e!r}); falling back to atomic overwrite with manual merge")

    # Defensive fallback: manual merge + atomic write if atomic_json helpers
    # are unavailable. Still preserves UPSERT semantics.
    try:
        from alpha_engine.atomic_json import atomic_write_json
        merged = {**(existing if isinstance(existing, dict) else {}), **sanitized}
        atomic_write_json(STRATEGY_PERFORMANCE_PATH, merged, indent=2)
    except ImportError:
        merged = {**(existing if isinstance(existing, dict) else {}), **sanitized}
        with open(STRATEGY_PERFORMANCE_PATH, "w") as f:
            json.dump(merged, f, indent=2)


def load_tweaks() -> dict:
    if TWEAKS_PATH.exists():
        with open(TWEAKS_PATH) as f:
            return json.load(f)
    return {}


def append_validation_log(entries: list[dict]):
    log = []
    if VALIDATION_LOG_PATH.exists():
        with open(VALIDATION_LOG_PATH) as f:
            log = json.load(f)
    log.extend(entries)
    # Keep last 300 entries
    with open(VALIDATION_LOG_PATH, "w") as f:
        json.dump(log[-300:], f, indent=2)


# ---------------------------------------------------------------------------
# Price fetching
# ---------------------------------------------------------------------------

def _normalize_to_yahoo(symbol: str) -> str:
    """Convert Binance-style XXXUSDT to Yahoo-style XXX-USD for yfinance."""
    sym = symbol.strip().upper()
    if sym.endswith("USDT"):
        base = sym[:-4]  # FETUSDT -> FET
        return f"{base}-USD"
    return sym


def fetch_current_prices(symbols: list[str]) -> dict[str, dict]:
    """Fetch current OHLCV for symbols. Returns {symbol: {price, high, low, open}}.

    Handles both Yahoo-style (FET-USD) and Binance-style (FETUSDT) symbols.
    Results are keyed by the ORIGINAL symbol name so callers don't need to know
    which format was used.
    """
    prices = {}
    if not symbols:
        return prices

    # Build mapping: original_symbol -> yahoo_symbol
    orig_to_yahoo = {}
    yahoo_to_orig = {}
    for sym in symbols:
        yahoo = _normalize_to_yahoo(sym)
        orig_to_yahoo[sym] = yahoo
        yahoo_to_orig[yahoo] = sym

    yahoo_symbols = list(set(orig_to_yahoo.values()))
    tickers = " ".join(yahoo_symbols)
    try:
        raw = yf.download(tickers, period="5d", interval="1d",
                          group_by="ticker", auto_adjust=True,
                          threads=True, progress=False)
    except Exception as e:
        print(f"  [WARN] yfinance download failed: {e}")
        return prices

    for yahoo_sym in yahoo_symbols:
        try:
            if len(yahoo_symbols) == 1:
                df = raw
            else:
                df = raw[yahoo_sym] if yahoo_sym in raw.columns.get_level_values(0) else None

            if df is None or df.empty:
                continue
            df = df.dropna(subset=["Close"])
            if len(df) < 2:
                continue

            last = df.iloc[-1]
            prev = df.iloc[-2]
            price_data = {
                "price": float(last["Close"]),
                "high": float(last["High"]),
                "low": float(last["Low"]),
                "open": float(last["Open"]),
                "prev_close": float(prev["Close"]),
                "high_5d": float(df["High"].max()),
                "low_5d": float(df["Low"].min()),
            }

            # Map back to ALL original symbols that resolve to this yahoo symbol
            for orig_sym, y_sym in orig_to_yahoo.items():
                if y_sym == yahoo_sym:
                    prices[orig_sym] = price_data
        except Exception:
            continue
    return prices


# ---------------------------------------------------------------------------
# Pick validation
# ---------------------------------------------------------------------------

def validate_picks(active: list[dict], prices: dict[str, dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Validate all active picks against current prices.
    Returns: (still_active, newly_closed, log_entries)
    """
    still_active = []
    newly_closed = []
    log_entries = []

    for pick in active:
        symbol = pick["symbol"]
        price_data = prices.get(symbol)
        if not price_data:
            still_active.append(pick)
            continue

        current_price = price_data["price"]
        day_high = price_data["high"]
        day_low = price_data["low"]
        # 2026-04-18: changed pick["entry_price"] -> pick.get(...) after a
        # KeyError crashed the entire ALPHA ENGINE scheduled run on a single
        # bad pick. Multiple new emitters (Phase2 strategies, Antigravity
        # research strategies, prediction-market code) can produce picks
        # without entry_price; we now skip them rather than fail the run.
        entry_price = pick.get("entry_price")
        if not entry_price or entry_price == 0:
            still_active.append(pick)
            continue
        tp = pick.get("take_profit")
        sl = pick.get("stop_loss")
        signal_type = pick.get("signal_type", "BUY")
        category = pick.get("category", "crypto")

        # Track MFE/MAE (max favorable/adverse excursion)
        # Guard against None values on the pick (persisted "mfe": null) AND
        # from failed price fetches (day_high / day_low is None). Previous
        # code used `pick.get("mfe", 0)` which returns 0 only when the KEY is
        # absent; if the key exists with value None (valid JSON null), the
        # fallback was skipped and `max(None, float)` raised TypeError —
        # crashing the entire ALPHA ENGINE scheduled run every hour on picks
        # whose mfe/mae was set to null by upstream writers.
        mfe = pick.get("mfe")
        if mfe is None:
            mfe = 0.0
        mae = pick.get("mae")
        if mae is None:
            mae = 0.0
        if signal_type == "BUY":
            if day_high is not None:
                mfe = max(mfe, (day_high - entry_price) / entry_price)
            if day_low is not None:
                mae = min(mae, (day_low - entry_price) / entry_price)
        else:
            if day_low is not None:
                mfe = max(mfe, (entry_price - day_low) / entry_price)
            if day_high is not None:
                mae = min(mae, (entry_price - day_high) / entry_price)
        pick["mfe"] = round(mfe, 6)
        pick["mae"] = round(mae, 6)

        # Track high water mark -- robust None/NaN guard
        _hwm_raw = pick.get("high_water_mark")
        hwm = _hwm_raw if isinstance(_hwm_raw, (int, float)) and _hwm_raw > 0 else entry_price or current_price or 0
        try:
            if signal_type == "BUY":
                if day_high is not None and isinstance(day_high, (int, float)) and hwm is not None:
                    hwm = max(hwm, day_high)
            else:
                if day_low is not None and isinstance(day_low, (int, float)) and hwm is not None:
                    hwm = min(hwm, day_low)
        except (TypeError, ValueError):
            pass  # Keep existing hwm on comparison failure
        pick["high_water_mark"] = hwm

        # Update current price
        pick["current_price"] = current_price
        pick["last_checked"] = _now_iso()

        # Hold duration -- use fractional days so sub-day max_hold (e.g. 0.5 = 12h) works
        entry_date = pick.get("entry_date", _now_date())
        try:
            _hold_delta = (datetime.now(timezone.utc) -
                           datetime.strptime(entry_date, "%Y-%m-%d").replace(tzinfo=timezone.utc))
            days_held = _hold_delta.total_seconds() / 86400.0
        except (ValueError, TypeError):
            days_held = 0
        pick["hold_days"] = round(days_held, 2)

        # SL grace period: compute pick age in hours from created_at timestamp
        # Trades need time to breathe -- skip SL check if pick < 4 hours old
        SL_GRACE_HOURS = 4.0
        _pick_age_hours = None
        try:
            _created_at_str = pick.get("created_at", "")
            if _created_at_str:
                _created_dt = datetime.fromisoformat(_created_at_str.replace("Z", "+00:00"))
                _pick_age_hours = (datetime.now(timezone.utc) - _created_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600.0
        except (ValueError, TypeError):
            _pick_age_hours = None
        _in_sl_grace = (_pick_age_hours is not None and _pick_age_hours < SL_GRACE_HOURS)

        # Hold duration optimizer: adjust SL/trailing based on pick age
        # 0-24h: widen SL 1.5x (breathing room), 24-72h: early trail at 2%,
        # 72h+: tighten SL 0.75x + 5% trail (lock gains)
        _adj_sl = sl
        _adj_trail_pct = TRAILING_STOP.get(category, 0.10)
        _adj_trail_activate = TRAIL_ACTIVATE_PCT
        if _pick_age_hours is not None and _adjust_risk_for_duration is not None:
            try:
                _dur_adj = _adjust_risk_for_duration(pick, _pick_age_hours)
                if _dur_adj:
                    _sl_mult = _dur_adj.get("sl_multiplier", 1.0)
                    if sl and _sl_mult != 1.0:
                        # SL is an absolute price; adjust distance from entry
                        _sl_dist = abs(entry_price - sl)
                        _new_dist = _sl_dist * _sl_mult
                        _adj_sl = (entry_price - _new_dist) if signal_type == "BUY" else (entry_price + _new_dist)
                    _adj_trail_pct = _dur_adj.get("trail_pct", _adj_trail_pct)
                    _adj_trail_activate = _dur_adj.get("trail_activate", _adj_trail_activate)
            except Exception:
                pass

        # Check exit conditions
        # Uses BOTH current price AND daily extremes (hybrid approach)
        # - Current price catches real-time moves
        # - Daily high/low catches intrabar spikes between validator runs
        # - 0.3% buffer prevents false triggers from spread/slippage noise
        exit_reason = None
        exit_price = current_price
        SL_BUFFER = 0.003  # 0.3% tolerance for spread/slippage

        # Realistic slippage: fills never land exactly at TP/SL
        # TP slippage is mild (limit-like), SL slippage is worse (stop-market)
        TP_SLIPPAGE = 0.0005   # 0.05% adverse slippage on take-profit fills
        SL_SLIPPAGE = 0.001    # 0.10% adverse slippage on stop-loss fills

        if signal_type == "BUY":
            # TP hit: current price near TP OR day high exceeded TP
            if tp and (current_price >= tp * (1 - SL_BUFFER) or day_high >= tp):
                exit_reason = "TP_HIT"
                exit_price = tp * (1 - TP_SLIPPAGE)  # LONG TP fills slightly below target
            # SL hit: uses _adj_sl from hold_duration_optimizer (wider early, tighter late)
            elif _adj_sl and (current_price <= _adj_sl * (1 + SL_BUFFER) or day_low <= _adj_sl):
                if _in_sl_grace:
                    print(f"  [SL GRACE] SL grace period: {pick.get('symbol', '?')} only "
                          f"{_pick_age_hours:.1f}h old, skipping SL check "
                          f"(grace={SL_GRACE_HOURS}h)")
                else:
                    exit_reason = "SL_HIT"
                    exit_price = _adj_sl * (1 - SL_SLIPPAGE)
            # Trailing stop: uses _adj_trail_pct and _adj_trail_activate from optimizer
            elif _adj_trail_pct > 0:
                profit_pct = (hwm - entry_price) / entry_price
                if profit_pct > _adj_trail_activate:
                    trail_level = hwm * (1 - _adj_trail_pct)
                    if current_price <= trail_level * (1 + SL_BUFFER) or day_low <= trail_level:
                        exit_reason = "TRAILING_STOP"
                        exit_price = trail_level * (1 - SL_SLIPPAGE)

        elif signal_type == "SELL":
            if tp and (current_price <= tp * (1 + SL_BUFFER) or day_low <= tp):
                exit_reason = "TP_HIT"
                exit_price = tp * (1 + TP_SLIPPAGE)  # SHORT TP fills slightly above target
            # SL hit (SHORT): uses _adj_sl from hold_duration_optimizer
            elif _adj_sl and (current_price >= _adj_sl * (1 - SL_BUFFER) or day_high >= _adj_sl):
                if _in_sl_grace:
                    print(f"  [SL GRACE] SL grace period: {pick.get('symbol', '?')} only "
                          f"{_pick_age_hours:.1f}h old, skipping SL check "
                          f"(grace={SL_GRACE_HOURS}h)")
                else:
                    exit_reason = "SL_HIT"
                    exit_price = _adj_sl * (1 + SL_SLIPPAGE)

        # Max hold time -- score-aware: low-grade picks expire faster
        _, _, max_hold = CATEGORY_RISK.get(category, (-0.08, 0.15, 10))
        pick_score = float(pick.get("elite_score", 50) or 50)

        # Non-crypto minimum hold times: these assets move slowly,
        # score-based reduction must NOT go below the floor.
        # BUG FIX: Previous floors (forex=1d, commodity=1d) were far too short.
        # Forex moves ~0.5%/day; with 1% TP, need 3-5 days minimum.
        # Commodities move ~1-2%/day; with 5% TP, need 3+ days.
        # Old floors caused mass TIME_EXPIRY at 0.65-1.07 days with tiny PnL (±0.03%).
        _NON_CRYPTO_MIN_HOLD = {
            "forex": 2.0,       # min 2 days -- 0.3% TP achievable in 1-2 sessions
            "equity": 5.0,      # min 5 days -- swing trades / earnings catalysts need time
            "commodity": 3.0,   # min 3 days -- commodities are volatile but still need room
            "etf": 5.0,         # min 5 days -- ETFs track equities
            "futures": 3.0,     # min 3 days
            "bond": 5.0,        # min 5 days -- bonds move very slowly
        }
        _min_hold = _NON_CRYPTO_MIN_HOLD.get(category, 0)

        if pick_score < 30:
            max_hold = min(max_hold, 0.5)   # F grade: 12h max (crypto only)
        elif pick_score < 45:
            max_hold = min(max_hold, 1.0)   # D grade: 1 day max
        elif pick_score < 60:
            max_hold = min(max_hold, 2.0)   # C grade: 2 days max
        # B+ keeps full max_hold

        # Enforce non-crypto minimum hold floor (score reduction can't go below it)
        if _min_hold > 0 and max_hold < _min_hold:
            max_hold = _min_hold

        if days_held >= max_hold and exit_reason is None:
            exit_reason = "TIME_EXPIRY"
            exit_price = current_price

        if exit_reason:
            # Detect stale data: if exit_price == entry_price, the price feed
            # returned the same value (data failure).  Don't count as a real trade.
            _price_diff_pct = abs(exit_price - entry_price) / entry_price if entry_price > 0 else 0
            if _price_diff_pct < 0.0001 and exit_reason in ("TIME_EXPIRY", "SL_HIT"):
                # Price didn't move at all (< 0.01%) -- stale data, not a real outcome
                exit_reason = "STALE_DATA_NO_PRICE"

            # Data-quality gate: flag exit prices that are >20% beyond the recorded SL.
            # This prevents corrupted price feeds (e.g., DOGE price leaked as TRX) from entering the dashboard.
            _sl = pick.get("stop_loss")
            if _sl and float(_sl) > 0 and exit_reason not in ("STALE_DATA_NO_PRICE", "TIME_EXPIRY"):
                _sl_val = float(_sl)
                if signal_type == "BUY":
                    if exit_price < _sl_val * 0.8:
                        exit_reason = "INVALID_EXIT_BEYOND_SL"
                else:
                    if exit_price > _sl_val * 1.2:
                        exit_reason = "INVALID_EXIT_BEYOND_SL"

            # Calculate PnL
            if signal_type == "BUY":
                pnl_pct = (exit_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - exit_price) / entry_price

            pick["exit_price"] = exit_price
            pick["exit_date"] = _now_date()
            pick["closed_at"] = _now_iso()
            pick["exit_reason"] = exit_reason
            pick["pnl_pct"] = round(pnl_pct, 6)
            # Quick Win 3: Apply strategy weight overrides for position sizing
            _strat_name = pick.get("strategy", "")
            _weight = STRATEGY_WEIGHT_OVERRIDES.get(_strat_name, 1.0)
            _alloc = DEFAULT_ALLOCATION * _weight
            pick["pnl_dollar"] = round(pnl_pct * _alloc, 2)
            pick["allocation"] = _alloc
            if exit_reason == "STALE_DATA_NO_PRICE":
                pick["status"] = "STALE"
            else:
                pick["status"] = "WON" if pnl_pct > 0 else "LOST"

            # Persist enriched features for ML training (fixes train/serve skew)
            # These features were computed at scoring time but previously lost on close
            if "ml_features_at_entry" not in pick:
                pick["ml_features_at_entry"] = {
                    "rsi_at_entry": pick.get("rsi_at_entry"),
                    "volume_ratio": pick.get("volume_ratio"),
                    "atr_at_entry": pick.get("atr_at_entry"),
                    "market_fear_greed": pick.get("market_fear_greed"),
                    "funding_rate": pick.get("funding_rate"),
                    "confidence": pick.get("confidence"),
                    "ml_score": pick.get("ml_score"),
                    "risk_reward": pick.get("risk_reward"),
                    "convergence": pick.get("convergence", 0),
                    "regime_encoded": pick.get("regime_encoded", 0),
                    # Enriched microstructure features (were always-zero before fix)
                    "orderbook_imbalance": pick.get("orderbook_imbalance"),
                    "ema_position": pick.get("ema_position"),
                    "spread_pct": pick.get("spread_pct"),
                    "wick_ratio": pick.get("wick_ratio"),
                    "entry_distance_vwap": pick.get("entry_distance_vwap"),
                    "bb_pct_b": pick.get("bb_pct_b"),
                    "vpin": pick.get("vpin"),
                    "galaxy_score": pick.get("galaxy_score"),
                    "hma_slope": pick.get("hma_slope"),
                    "rsi_1h": pick.get("rsi_1h"),
                    "rsi_4h": pick.get("rsi_4h"),
                    "forward_wr": pick.get("forward_wr"),
                    "forward_trades": pick.get("forward_trades"),
                }

            # Do not append corrupted exits to the closed book
            if exit_reason == "INVALID_EXIT_BEYOND_SL":
                log_entries.append({
                    "timestamp": _now_iso(),
                    "symbol": symbol,
                    "event": "DATA_QUALITY_REJECT",
                    "reason": exit_reason,
                    "exit_price": exit_price,
                    "stop_loss": _sl,
                    "note": "Exit price exceeded 20% beyond recorded SL — rejected as corrupted data"
                })
            else:
                newly_closed.append(pick)

            # --- Online Learning: update after EVERY trade ---
            _won = pnl_pct > 0
            try:
                from thompson_sampler import update_after_trade
                update_after_trade(pick.get("strategy", ""), _won, symbol=pick.get("symbol", ""))
            except Exception as _thompson_err:
                print(f"  [ONLINE] Thompson sampler update failed for {pick.get('strategy', '?')}: {_thompson_err}")
            try:
                from online_learner import online_update
                _ol_result = online_update(pick, _won)
                if _ol_result:
                    print(f"  [ONLINE] Learner step={_ol_result.get('step', '?')} "
                          f"pred={_ol_result.get('prediction', '?')} "
                          f"actual={'WON' if _won else 'LOST'} "
                          f"error={_ol_result.get('error', '?')}")
            except Exception as _ol_err:
                print(f"  [ONLINE] Online learner update FAILED for {pick.get('id', '?')}: {_ol_err}")
                import traceback
                traceback.print_exc()
            try:
                from bandit_tp_sl import update_bandit
                update_bandit(pick, float(pnl_pct))
            except Exception as _bandit_err:
                print(f"  [ONLINE] Bandit TP/SL update failed for {pick.get('strategy', '?')}: {_bandit_err}")
            # Conformal sizing calibration: feed actual outcome to improve intervals
            try:
                if _conformal_sizer is not None:
                    _pred = pick.get("ml_score") or pick.get("meta_label_score") or 0.5
                    if isinstance(_pred, str):
                        try:
                            _pred = float(_pred)
                        except (ValueError, TypeError):
                            _pred = 0.5
                    _actual = 1.0 if _won else 0.0
                    _conformal_sizer.update(float(_pred), _actual)
            except Exception:
                pass  # Conformal update failure must not block pipeline

            log_entries.append({
                "timestamp": _now_iso(),
                "type": "CLOSED",
                "symbol": symbol,
                "strategy": pick.get("strategy", ""),
                "exit_reason": exit_reason,
                "pnl_pct": pick["pnl_pct"],
                "hold_days": days_held,
                "mfe": pick["mfe"],
                "mae": pick["mae"],
            })

            status_icon = "WIN" if pnl_pct > 0 else "LOSS"
            print(f"  [{status_icon}] {symbol:16s} {pick.get('strategy', ''):30s} "
                  f"PnL={pnl_pct*100:+.2f}%  Exit: {exit_reason}  "
                  f"Held {days_held}d  MFE={mfe*100:.1f}%  MAE={mae*100:.1f}%")
        else:
            # Still active -- update unrealized PnL
            if signal_type == "BUY":
                unrealized = (current_price - entry_price) / entry_price
            else:
                unrealized = (entry_price - current_price) / entry_price
            pick["unrealized_pnl_pct"] = round(unrealized, 6)
            still_active.append(pick)

    return still_active, newly_closed, log_entries


# ---------------------------------------------------------------------------
# Strategy performance computation
# ---------------------------------------------------------------------------

def _compute_stats_from_picks(strat: str, picks: list[dict]) -> dict | None:
    """Compute the stats dict for a single picks list (all share a strategy tag).

    Factored out of ``compute_all_strategy_stats`` so the same metrics can be
    produced both for the by-name aggregate (legacy) and for each
    per-``(source_system, strategy)`` group (collision-safe, see issue #173).
    Returns ``None`` if there are no scoreable trades after filtering
    STALE_DATA_NO_PRICE entries.
    """
    # Exclude STALE_DATA_NO_PRICE picks from WR/PnL stats (data failure, not real trades)
    real_picks = [p for p in picks if p.get("exit_reason") != "STALE_DATA_NO_PRICE"]
    stale_count = len(picks) - len(real_picks)
    pnls = [float(p["pnl_pct"]) for p in real_picks if "pnl_pct" in p and p["pnl_pct"] is not None]
    if not pnls:
        return None

    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p <= 0)
    n = len(pnls)
    win_rate = wins / n

    arr = np.array(pnls)
    avg_pnl = float(arr.mean())
    total_pnl = float(arr.sum())
    sharpe = float(arr.mean() / arr.std() * np.sqrt(252)) if arr.std() > 0 else 0
    downside = arr[arr < 0]
    sortino = (float(arr.mean() / downside.std() * np.sqrt(252))
               if len(downside) > 0 and downside.std() > 0 else sharpe)

    cum = np.cumsum(arr)
    peak = np.maximum.accumulate(cum)
    max_dd = float((cum - peak).min()) if len(cum) > 0 else 0

    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # MFE/MAE analysis (for TP/SL tweaking)
    mfes = [float(p.get("mfe") or 0) for p in picks if p.get("mfe") is not None]
    maes = [float(p.get("mae") or 0) for p in picks if p.get("mae") is not None]
    avg_mfe = float(np.mean(mfes)) if mfes else 0
    avg_mae = float(np.mean(maes)) if maes else 0

    # Exit reason breakdown
    exit_reasons: dict[str, int] = {}
    for p in picks:
        reason = p.get("exit_reason", "UNKNOWN")
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    # Hold time analysis
    hold_days = [float(p.get("hold_days") or 0) for p in picks if p.get("hold_days") is not None]
    avg_hold = float(np.mean(hold_days)) if hold_days else 0

    # By-symbol breakdown
    by_symbol: dict[str, dict] = {}
    for p in picks:
        sym = p.get("symbol", "")
        by_symbol.setdefault(sym, {"wins": 0, "losses": 0, "total_pnl": 0})
        _pnl_val = float(p.get("pnl_pct", 0) or 0)
        if _pnl_val > 0:
            by_symbol[sym]["wins"] += 1
        else:
            by_symbol[sym]["losses"] += 1
        by_symbol[sym]["total_pnl"] += _pnl_val

    # Kelly fraction and avg win/loss for position sizing
    if wins > 0 and losses > 0:
        avg_win = np.mean([p for p in pnls if p > 0])
        avg_loss_val = abs(np.mean([p for p in pnls if p < 0]))
        kelly = win_rate - (1 - win_rate) / (avg_win / avg_loss_val) if avg_loss_val > 0 else 0
    elif wins > 0:
        avg_win = np.mean([p for p in pnls if p > 0])
        avg_loss_val = 0.0
        kelly = 0
    else:
        avg_win = 0.0
        avg_loss_val = 0.0
        kelly = 0

    p_value = binomial_p_value(wins, n)

    return {
        "closed_picks": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 4),
        "avg_pnl_pct": round(avg_pnl, 6),
        "total_pnl_pct": round(total_pnl, 6),
        "total_pnl_dollar": round(total_pnl * DEFAULT_ALLOCATION * STRATEGY_WEIGHT_OVERRIDES.get(strat, 1.0), 2),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "max_drawdown": round(max_dd, 6),
        "profit_factor": round(min(profit_factor, 99.99), 3),
        "kelly_fraction": round(kelly, 4),
        "avg_win_pct": round(float(avg_win), 6),
        "avg_loss_pct": round(float(avg_loss_val), 6),
        "p_value": round(p_value, 6),
        "statistically_significant": p_value < 0.05 and n >= 20,
        "avg_hold_days": round(avg_hold, 1),
        "avg_mfe": round(avg_mfe, 6),
        "avg_mae": round(avg_mae, 6),
        "exit_reasons": exit_reasons,
        "by_symbol": {s: {k: round(v, 6) if isinstance(v, float) else v
                          for k, v in info.items()} for s, info in by_symbol.items()},
        "stale_data_excluded": stale_count,
        "last_updated": _now_iso(),
    }


def compute_all_strategy_stats(closed_picks: list[dict]) -> dict:
    """Compute comprehensive stats per strategy from all closed picks.

    Collision-safe aggregation (issue #173, follow-up to PR #171 dashboard fix).

    The top-level dict is still keyed on bare strategy name so every legacy
    caller (auto_tuner, ml_strategy_reviver, print_performance_report, the
    existing ``perf.items()`` iterators in this file) keeps working with no
    schema change. Each by-name entry is the MERGED aggregate across every
    feeder that emitted picks under that tag — identical to the pre-fix
    behavior — so the legacy shape is preserved.

    What's new: each by-name entry now carries two extra fields so the
    collision can be audited and so downstream enrichment can pick the
    uncontaminated row when it knows the feeder:

      * ``source_systems`` — sorted list of every ``source_system`` that
        emitted picks under this strategy tag. Length > 1 means the row
        is a merged aggregate of multiple feeders (the exact pattern that
        produced the "fear_greed_contrarian 80.9% WR / 584 wins" artifact
        documented in ``docs/forensics/fear_greed_contrarian_collapse_2026-04-13.md``).
      * ``by_source_system`` — dict keyed on ``source_system`` whose values
        are independent per-feeder stats dicts (same schema as the by-name
        entry, minus this drill-down key). A caller that knows a pick's
        ``source_system`` can now do::

            row = perf.get(strat, {}).get("by_source_system", {}).get(src, {})

        to get a collision-free metric set. ``annotate_picks_with_forward_gate``
        below does exactly that.

    This preserves the shim for legacy consumers ("don't break ml_strategy_reviver")
    while exposing the collision-safe data the ML scorer path needs. See issue #173
    and PR #171 for the matching dashboard-side fix.
    """
    # Stage 1: group all picks by bare strategy name for the legacy aggregate.
    by_strategy: dict[str, list[dict]] = {}
    for pick in closed_picks:
        strat = pick.get("strategy", "unknown")
        by_strategy.setdefault(strat, []).append(pick)

    # Stage 2: parallel group by (source_system, strategy) for the
    # collision-safe per-feeder breakdown.
    by_sys_strat: dict[tuple[str, str], list[dict]] = {}
    for pick in closed_picks:
        strat = pick.get("strategy", "unknown")
        src = pick.get("source_system", "") or ""
        by_sys_strat.setdefault((src, strat), []).append(pick)

    perf: dict[str, dict] = {}
    for strat, picks in by_strategy.items():
        stats = _compute_stats_from_picks(strat, picks)
        if stats is None:
            continue

        # Attach collision-safe per-(source_system) breakdown.
        per_source: dict[str, dict] = {}
        source_systems: set[str] = set()
        for (src, s_strat), s_picks in by_sys_strat.items():
            if s_strat != strat:
                continue
            source_systems.add(src)
            sub_stats = _compute_stats_from_picks(strat, s_picks)
            if sub_stats is not None:
                per_source[src] = sub_stats

        stats["source_systems"] = sorted(source_systems)
        stats["by_source_system"] = per_source
        perf[strat] = stats

    return perf


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_performance_report(perf: dict, active_count: int):
    """Print formatted performance report."""
    print()
    print("=" * 75)
    print("  ALPHA ENGINE -- Forward Validation Report")
    print(f"  {_now_iso()}")
    print("=" * 75)

    total_closed = sum(s["closed_picks"] for s in perf.values())
    total_won = sum(s["wins"] for s in perf.values())
    total_lost = sum(s["losses"] for s in perf.values())
    total_pnl = sum(s["total_pnl_dollar"] for s in perf.values())
    overall_wr = total_won / total_closed if total_closed > 0 else 0

    print(f"\n  Active picks:  {active_count}")
    print(f"  Closed picks:  {total_closed}")
    print(f"  Win/Loss:      {total_won}/{total_lost} ({overall_wr*100:.1f}%)")
    print(f"  Total P&L:     ${total_pnl:+,.2f}")

    if not perf:
        print("\n  No closed picks yet. Waiting for data to accumulate.")
        print("=" * 75)
        return

    # Sort by total P&L
    sorted_strats = sorted(perf.items(), key=lambda x: x[1]["total_pnl_pct"], reverse=True)

    # Crypto strategies
    crypto_strats = [(s, d) for s, d in sorted_strats
                     if any(s in CRYPTO_SYMBOLS for s in
                            [sym for sym in d.get("by_symbol", {}).keys()])]
    if not crypto_strats:
        crypto_strats = [(s, d) for s, d in sorted_strats
                         if "crypto" in s or "btc" in s or "funding" in s or "fear" in s
                         or "wyckoff" in s or "smart" in s or "hurst" in s
                         or "entropy" in s or "coingecko" in s or "stochrsi" in s
                         or "breakout" in s and "forex" not in s]

    forex_strats = [(s, d) for s, d in sorted_strats
                    if "forex" in s or "carry" in s or "jpy" in s
                    or "dxy" in s or "session" in s]

    equity_strats = [(s, d) for s, d in sorted_strats
                     if "momentum_factor" in s or "penny" in s or "meme_social" in s
                     or "quality" in s or "intermarket" in s or "support" in s]

    def print_section(title: str, strats: list):
        if not strats:
            return
        print(f"\n  {title}:")
        print(f"  {'Strategy':35s} {'WR':>6s} {'Sharpe':>7s} {'PF':>6s} "
              f"{'P&L':>10s} {'Picks':>5s} {'TP%':>5s} {'SL%':>5s}")
        print(f"  {'-'*35} {'-'*6} {'-'*7} {'-'*6} {'-'*10} {'-'*5} {'-'*5} {'-'*5}")
        for s, d in strats:
            exits = d.get("exit_reasons", {})
            total_exits = sum(exits.values())
            tp_pct = exits.get("TP_HIT", 0) / total_exits * 100 if total_exits > 0 else 0
            sl_pct = exits.get("SL_HIT", 0) / total_exits * 100 if total_exits > 0 else 0
            print(f"  {s:35s} {d['win_rate']*100:5.1f}% {d['sharpe']:6.2f} "
                  f"{d['profit_factor']:5.2f} ${d['total_pnl_dollar']:+8.2f} "
                  f"{d['closed_picks']:4d} {tp_pct:4.0f}% {sl_pct:4.0f}%")

    print_section("CRYPTO STRATEGIES", crypto_strats)
    print_section("FOREX STRATEGIES", forex_strats)
    print_section("EQUITY STRATEGIES", equity_strats)

    # MFE/MAE analysis (for TP/SL optimization)
    print(f"\n  MFE/MAE ANALYSIS (TP/SL optimization data):")
    print(f"  {'Strategy':35s} {'AvgMFE':>8s} {'AvgMAE':>8s} {'OptTP':>8s} {'OptSL':>8s}")
    print(f"  {'-'*35} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for s, d in sorted_strats[:15]:
        if d["closed_picks"] < 3:
            continue
        avg_mfe = d.get("avg_mfe", 0)
        avg_mae = d.get("avg_mae", 0)
        opt_tp = avg_mfe * 0.8  # Capture 80% of typical favorable move
        opt_sl = avg_mae * 1.2  # Allow 120% of typical adverse move
        print(f"  {s:35s} {avg_mfe*100:+6.2f}% {avg_mae*100:+6.2f}% "
              f"{opt_tp*100:+6.2f}% {opt_sl*100:+6.2f}%")

    print()
    print("=" * 75)


# ---------------------------------------------------------------------------
# Main operations
# ---------------------------------------------------------------------------

def run_validation():
    """Run the validation cycle on all active picks."""
    print("\n[VALIDATE] Loading active picks...")
    active = load_active_picks()
    if not active:
        print("  No active picks to validate.")
        return [], {}

    # Get unique symbols
    symbols = list({p["symbol"] for p in active})
    print(f"  {len(active)} active picks across {len(symbols)} symbols")

    # Fetch current prices
    print("[VALIDATE] Fetching live prices...")
    prices = fetch_current_prices(symbols)
    print(f"  Got prices for {len(prices)}/{len(symbols)} symbols")

    # Validate
    print("[VALIDATE] Checking TP/SL/trailing/expiry...")
    still_active, newly_closed, log_entries = validate_picks(active, prices)

    # Save updated active picks
    save_active_picks(still_active)

    # Append newly closed to closed picks file
    all_closed = load_closed_picks()
    all_closed.extend(newly_closed)
    save_closed_picks(all_closed)

    # Log events
    if log_entries:
        append_validation_log(log_entries)

    print(f"\n  Results: {len(still_active)} still active, "
          f"{len(newly_closed)} closed this cycle")

    # Compute performance
    perf = compute_all_strategy_stats(all_closed)
    save_strategy_performance(perf)

    # Annotate active picks with forward-test gate metadata
    if still_active and perf:
        n_val = annotate_picks_with_forward_gate(still_active, perf)
        # Recompute elite_score for all active picks (MC data may have improved)
        try:
            enrich_picks_with_elite_score(still_active, DATA_DIR)
        except Exception as e:
            print(f"  [ELITE] Scoring failed (non-fatal): {e}")

        save_active_picks(still_active)  # re-save with gate metadata + elite_score
        print(f"  [FORWARD GATE] {n_val}/{len(still_active)} active picks from validated strategies")

    # --- Rolling Expectancy Tracker ---
    try:
        _rolling_exp = compute_rolling_expectancy(all_closed, window=50)
        print(f"  [EXPECTANCY] Rolling expectancy (last 50 closed): {_rolling_exp:+.4f}% per trade")
        if _rolling_exp < 0.15:
            print(f"  [EXPECTANCY] WARNING: Below target 0.15% (current: {_rolling_exp:.4f}%)")
    except Exception as _exp_err:
        print(f"  [EXPECTANCY] Tracker failed (non-fatal): {_exp_err}")

    return newly_closed, perf


def compute_rolling_expectancy(closed_picks: list, window: int = 50) -> float:
    """Track rolling expectancy from recent closed picks.

    Returns average pnl_pct over the last `window` closed picks.
    Target: >= 0.15% per trade.
    """
    recent = closed_picks[-window:]
    pnls = [float(p.get('pnl_pct', 0) or 0) for p in recent if isinstance(p, dict)]
    if not pnls:
        return 0
    return sum(pnls) / len(pnls)


def apply_regime_adaptive_tp_sl(pick: dict, signal: dict) -> None:
    """Regime-adaptive TP/SL scaling (ported from ml_crypto_predictor).

    PnL audit showed TPs are 40% too ambitious (MFE/TP ratio = 0.60).
    This tightens TP/SL based on ATR and market regime, but ONLY when the
    current TP is more ambitious than the regime-adaptive target (i.e. it
    tightens, never widens).

    Regime mapping:
      BULL / MARKUP / trending   -> TP = 3.0 * ATR, SL = 1.5 * ATR
      SIDEWAYS / ranging         -> TP = 2.0 * ATR, SL = 1.0 * ATR
      HIGH_VOL / transitional    -> TP = 2.5 * ATR, SL = 1.25 * ATR
      BEAR / MARKDOWN            -> TP = 1.5 * ATR, SL = 0.75 * ATR
    """
    atr = pick.get("atr_at_entry") or 0
    entry = pick.get("entry_price") or 0
    if entry <= 0:
        return

    # If ATR not populated, estimate from SL distance or default to 2% of entry
    if atr <= 0:
        sl = pick.get("stop_loss") or 0
        if sl > 0 and entry > 0:
            atr = abs(entry - sl) / 1.5  # reverse-engineer ATR from SL (SL ~ 1.5 * ATR)
        else:
            atr = entry * 0.02  # fallback: 2% of entry price
        pick["atr_at_entry"] = atr  # persist for downstream use

    # Determine regime from multiple sources (sentinel > scanner > fallback)
    regime_raw = (
        signal.get("sentinel_regime")
        or signal.get("regime")
        or signal.get("hmm_regime")
        or "SIDEWAYS"
    )
    regime = regime_raw.upper()

    direction = pick.get("direction", "LONG").upper()

    # Map regime labels to (tp_multiplier, sl_multiplier) in ATR units
    regime_multipliers = {
        "BULL": (3.0, 1.5),
        "MARKUP": (3.0, 1.5),
        "ACCUMULATION": (2.5, 1.25),
        "TRENDING": (3.0, 1.5),
        "SIDEWAYS": (2.0, 1.0),
        "RANGING": (2.0, 1.0),
        "BEAR": (1.5, 0.75),
        "MARKDOWN": (1.5, 0.75),
        "DISTRIBUTION": (1.5, 0.75),
        "HIGH_VOL": (2.5, 1.25),
        "TRANSITIONAL": (2.5, 1.25),
    }
    tp_mult, sl_mult = regime_multipliers.get(regime, (2.0, 1.0))

    if direction in ("LONG", "BUY"):
        adaptive_tp = entry + tp_mult * atr
        adaptive_sl = entry - sl_mult * atr
    else:
        adaptive_tp = entry - tp_mult * atr
        adaptive_sl = entry + sl_mult * atr

    current_tp = pick.get("take_profit") or 0
    current_sl = pick.get("stop_loss") or 0

    adjusted = False

    # Only tighten TP (reduce distance from entry), never widen
    if current_tp and abs(current_tp - entry) > abs(adaptive_tp - entry):
        pick["take_profit_original"] = current_tp
        pick["take_profit"] = round(adaptive_tp, 8)
        adjusted = True

    # Only tighten SL (reduce distance from entry), never widen
    if current_sl and abs(current_sl - entry) > abs(adaptive_sl - entry):
        pick["stop_loss_original"] = current_sl
        pick["stop_loss"] = round(adaptive_sl, 8)
        adjusted = True

    if adjusted:
        pick["tp_sl_regime_adjusted"] = True
        pick["tp_sl_regime"] = regime
        pick["tp_sl_atr_mult"] = (tp_mult, sl_mult)
        # Recalculate risk_reward after adjustment
        new_tp = pick.get("take_profit") or 0
        new_sl = pick.get("stop_loss") or 0
        if new_tp and new_sl:
            tp_dist = abs(new_tp - entry)
            sl_dist = abs(new_sl - entry)
            if sl_dist > 0:
                pick["risk_reward"] = round(tp_dist / sl_dist, 2)
        print(f"  [REGIME TP/SL] {pick['symbol']} {pick['strategy']}: "
              f"regime={regime} ATR={atr:.4f} "
              f"TP {current_tp:.4f}->{pick['take_profit']:.4f} "
              f"SL {current_sl:.4f}->{pick['stop_loss']:.4f}")


def run_generation():
    """Generate new picks by running the scanner."""
    _reset_winner_filter_stats()  # Reset winner filter stats for this cycle
    print("\n[GENERATE] Running scanner...")
    from scanner import (
        fetch_market_data, fetch_context_data, run_strategies,
        rank_and_filter_signals,
    )
    from ml_ranker import MLSignalRanker
    from database import SQLiteStore
    from config import MAX_OPEN_PICKS, MAX_PICKS_PER_STRATEGY

    from kill_switch import check_kill_conditions
    _kill_status = check_kill_conditions()
    _kill_severity = _kill_status.get("severity", "ok")
    _kill_reason = _kill_status.get("kill_reason")

    if _kill_severity == "emergency":
        print(f"  [KILL SWITCH] EMERGENCY: {_kill_reason}")
        print(f"  [KILL SWITCH] Halting all new pick generation. Returning empty.")
        return
    elif _kill_severity == "critical":
        print(f"  [KILL SWITCH] CRITICAL: {_kill_reason}")
        print(f"  [KILL SWITCH] Only high-conviction picks (score >= 80) will pass through.")
    elif _kill_severity == "warning":
        print(f"  [KILL SWITCH] WARNING: {_kill_reason}")
        print(f"  [KILL SWITCH] Subtracting 5 from all elite_scores.")
    else:
        print(f"  [KILL SWITCH] OK -- no anomalous conditions detected")

    # --- Shadow Tracker: resolve old blocked signals against current prices ---
    try:
        if resolve_shadow_outcomes is not None:
            _shadow_result = resolve_shadow_outcomes()
            _sh_resolved = _shadow_result.get("resolved", 0)
            _sh_saved = _shadow_result.get("saved", 0)
            _sh_killed = _shadow_result.get("killed_alpha", 0)
            if _sh_resolved > 0:
                print(f"  [SHADOW] Resolved {_sh_resolved} blocked signals: "
                      f"{_sh_saved} saved us, {_sh_killed} killed alpha")
            # Log per-gate stats
            if get_gate_shadow_stats is not None:
                _gate_stats = get_gate_shadow_stats()
                for _gname, _gstat in _gate_stats.items():
                    _sr = _gstat.get("save_rate")
                    if _sr is not None and _gstat.get("resolved", 0) >= 5:
                        print(f"    Shadow: {_gname} saved {_gstat['saved']}/{_gstat['resolved']} "
                              f"(save_rate={_sr:.0%})")
    except Exception as _shadow_err:
        print(f"  [SHADOW] Resolution failed (non-fatal): {_shadow_err}")

    # --- Recalibrate SL/TP from closed picks (MAE/MFE analysis) ---
    if recalibrate_sl is not None:
        try:
            recalibrate_sl()
        except Exception as _recal_err:
            print(f"  [SL_CAL] Recalibration failed (non-fatal): {_recal_err}")

    # Load existing active picks
    active = load_active_picks()
    active_symbols_by_strategy: dict[str, set] = {}
    for p in active:
        s = p.get("strategy", "")
        active_symbols_by_strategy.setdefault(s, set()).add(p["symbol"])

    # BUGFIX: Also track recently closed picks from TODAY to prevent
    # re-opening the same trade within hours when TP hits quickly.
    # Without this, a pick that closes at 09:30 gets re-opened at 10:00.
    today_str = _now_date()
    closed = load_closed_picks()
    closed_today_by_strategy: dict[str, set] = {}
    for p in closed:
        close_date = (p.get("closed_at") or p.get("created_at") or "")[:10]
        entry_date = (p.get("entry_date") or "")[:10]
        if close_date == today_str or entry_date == today_str:
            s = p.get("strategy", "")
            closed_today_by_strategy.setdefault(s, set()).add(p["symbol"])

    # Fetch data (match scanner.py: yfinance tickers + yf_to_key remap for crypto)
    all_syms = list(ALL_SYMBOLS.keys())
    yf_tickers, yf_to_key, binance_only = resolve_yf_symbols(all_syms)
    raw_data = fetch_market_data(yf_tickers + binance_only)
    if not raw_data:
        print("  No market data. Aborting generation.")
        return
    data = {}
    for _sym, _df in raw_data.items():
        _canonical = yf_to_key.get(_sym, _sym)
        data[_canonical] = _df

    context = fetch_context_data()
    # 2026-04-18: pass strategy_filter="all" so scanner.run_strategies loads
    # BOND_STRATEGIES, ETF_STRATEGIES, FUTURES_STRATEGIES, FOREX_STRATEGIES
    # alongside crypto. Previously default ("crypto") meant non-crypto strategy
    # modules were dead code in the production emit path — bonds/futures had
    # 0 active picks because no source ever generated signals for them.
    # Antigravity P0 + cross-agent diagnosis convergence; downstream gates
    # (winner_filter expanded 85c6a67a83, hc_filter 8e97a8500d, etc.) handle
    # quality. See updates/2026-04-18-non-crypto-synthesis-and-action-plan.md.
    _strategy_filter = os.environ.get("STRATEGY_FILTER", "all")
    signals = run_strategies(data, context, strategy_filter=_strategy_filter)
    repaired_streams = _repair_standard_streams()
    if repaired_streams:
        print(f"  [STDIO] Repaired closed stream(s): {', '.join(repaired_streams)}")
    print(f"  Raw signals: {len(signals)}")

    # Rank with ML
    db = SQLiteStore()
    ranker = MLSignalRanker()
    ranked = rank_and_filter_signals(signals, ranker, db, market_data=data)
    db.close()
    repaired_streams = _repair_standard_streams()
    if repaired_streams:
        print(f"  [STDIO] Repaired closed stream(s): {', '.join(repaired_streams)}")
    print(f"  After ML filter: {len(ranked)}")

    # --- Pre-compute VPIN cache for gate (Task 1) ---
    _vpin_cache: dict[str, float] = {}
    if calculate_vpin is not None:
        for _sym, _df in data.items():
            try:
                _c = _df.get("Close", _df.get("close"))
                _o = _df.get("Open", _df.get("open"))
                _h = _df.get("High", _df.get("high"))
                _l = _df.get("Low", _df.get("low"))
                _v = _df.get("Volume", _df.get("volume"))
                if _c is None or _o is None or _h is None or _l is None or _v is None:
                    continue
                _vpin_series = calculate_vpin(_c, _o, _h, _l, _v)
                _last_vpin = _vpin_series.dropna()
                if len(_last_vpin) > 0:
                    _vpin_cache[_sym] = float(_last_vpin.iloc[-1])
            except Exception:
                continue
        if _vpin_cache:
            print(f"  [VPIN] Computed VPIN for {len(_vpin_cache)} symbols")

    # --- Pre-load closed picks for cooldown gate (Task 2) ---
    # `closed` is already loaded above (line ~974); reuse it for cooldown checks.

    # --- Pre-compute DSR cache for deflated Sharpe gate (Task 3) ---
    _dsr_cache: dict[str, float] = {}  # strategy_name -> DSR probability
    if returns_stats is not None and sharpe_variance is not None and deflated_sharpe_ratio is not None:
        _all_strat_names = set(s.get("strategy", "") for s in ranked)
        _nb_trials = max(len(_all_strat_names), 1)
        for _strat_name in _all_strat_names:
            try:
                # Gather per-trade returns for this strategy from closed picks
                _strat_returns = []
                for _cp in closed:
                    if _cp.get("strategy") == _strat_name and isinstance(_cp.get("pnl_pct"), (int, float)):
                        _strat_returns.append(float(_cp["pnl_pct"]) / 100.0)
                if len(_strat_returns) < 20:
                    continue  # Not enough trades for DSR
                _stats = returns_stats(_strat_returns)
                _sr = _stats["mean"] / max(math.sqrt(_stats["variance"]), 1e-12)
                _sr_var = sharpe_variance(_sr, len(_strat_returns),
                                          _stats["skewness"], _stats["kurtosis"])
                _dsr = deflated_sharpe_ratio(
                    estimated_sharpe=_sr,
                    sr_variance=_sr_var,
                    nb_trials=_nb_trials,
                    backtest_horizon=len(_strat_returns),
                    skew=_stats["skewness"],
                    kurtosis=_stats["kurtosis"],
                )
                _dsr_cache[_strat_name] = _dsr
            except Exception:
                continue
        if _dsr_cache:
            print(f"  [DSR] Computed Deflated Sharpe for {len(_dsr_cache)} strategies")

    # --- Pre-compute White's Reality Check cache (Task 8) ---
    _wrc_cache: dict[str, float] = {}  # strategy_name -> adjusted p-value
    try:
        _wrc_cache = run_white_reality_check(CLOSED_PICKS_PATH)
        if _wrc_cache:
            _n_sig = sum(1 for p in _wrc_cache.values() if p < 0.05)
            print(f"  [WRC] White's Reality Check: {len(_wrc_cache)} strategies tested, "
                  f"{_n_sig} significant (p<0.05)")
    except Exception:
        pass  # WRC failure must not block pipeline

    # Open new picks (respecting limits)
    # Exclude informational-only picks (e.g. insider_filing_scanner with $0 entry)
    # from the cap -- they consume slots but aren't real trades.
    _INFORMATIONAL_STRATEGIES = {"insider_filing_scanner"}
    _tradeable_active = [p for p in active if p.get("strategy") not in _INFORMATIONAL_STRATEGIES]
    # --- Structural vs Directional tracking counters ---
    _structural_accepted = 0
    _structural_blocked = 0
    _directional_accepted = 0
    _directional_blocked = 0
    _kill_list_cache = _load_core_whitelist_kill_list()  # Pre-load once for structural bypass

    # Structural strategies bypass directional gates entirely.
    # They collect spread/premium, not directional price prediction.
    STRUCTURAL_STRATEGIES = {
        'funding_rate_carry', 'funding_rate_carry_pro',
        'funding_rate_arbitrage', 'perpetual_basis',
        'perpetual_basis_ms', 'spot_perp_basis_arb',
        'cross_exchange_basis_carry', 'cross_exchange_price_arb',
        'cross_exchange_funding_arb', 'super_funding_rate_carry',
        'ag_rsi_pairs_arbitrage',
    }

    # M-083: Pre-compute elite_score for signals missing it before the adjustment pipeline.
    # Strategies that don't call compute_elite_score() at emission time arrive with
    # elite_score=None. The downstream adjustment gates (Volume L2812, MTF L2833,
    # GRU L2740) use signal.get('elite_score', 0|50) as the base, which anchors the
    # final score at a junk value (e.g., fractal_sr_bounce: 0+adj→-8.2 instead of 33).
    # Batch-enriching before the loop ensures adjustments modify the REAL score.
    _m083_unscored = [s for s in ranked if s.get("elite_score") is None]
    if _m083_unscored:
        try:
            enrich_picks_with_elite_score(_m083_unscored, DATA_DIR)
            print(f"  [M-083] Pre-scored {len(_m083_unscored)} unscored signal(s) with elite_scorer")
        except Exception as _m083_err:
            print(f"  [M-083] Pre-score failed (non-fatal): {_m083_err}")

    new_picks = []
    for signal in ranked:
        if len(_tradeable_active) + len(new_picks) >= MAX_OPEN_PICKS:
            break

        strategy = signal.get("strategy", "")
        existing = active_symbols_by_strategy.get(strategy, set())
        if len(existing) >= MAX_PICKS_PER_STRATEGY:
            continue
        if signal["symbol"] in existing:
            continue
        # BUGFIX: Don't re-open a pick that already closed today
        if signal["symbol"] in closed_today_by_strategy.get(strategy, set()):
            continue

        # Derive direction from signal_type
        _sig_type = signal.get("signal_type", "BUY").upper()
        _direction = "SHORT" if _sig_type in ("SELL", "SHORT") else "LONG"

        # --- Entry Price Sanity Gate ---
        # Reject signals where yfinance returned a BTC-denominated price
        # for a USD-quoted symbol. Known micro-price tokens are exempt.
        _MICRO_TOKENS = {"BONK-USD", "FLOKI-USD", "SHIB-USD", "PEPE-USD",
                         "BOME-USD", "GALA-USD", "LUNC-USD", "SPELL-USD",
                         "JASMY-USD", "HOT-USD", "WIN-USD", "DOGS-USD",
                         "NOT-USD", "1000SATS-USD"}
        _MIN_FLOORS = {
            "BTC-USD": 1000, "ETH-USD": 100, "BNB-USD": 50, "SOL-USD": 5,
            "APT-USD": 1, "AVAX-USD": 3, "LINK-USD": 2, "DOT-USD": 1,
            "NEAR-USD": 0.5, "SUI-USD": 0.3, "ADA-USD": 0.05, "XRP-USD": 0.1,
            "UNI-USD": 1, "AAVE-USD": 10, "FIL-USD": 1, "ARB-USD": 0.1,
            "OP-USD": 0.3, "TIA-USD": 1,
        }
        _gen_ep = signal.get("entry_price", 0)
        _gen_sym = signal.get("symbol", "")
        _floor = _MIN_FLOORS.get(_gen_sym)
        if _floor and _gen_ep > 0 and _gen_ep < _floor * 0.01:
            print(f"  [PRICE SANITY] SKIP {_gen_sym} {strategy}: "
                  f"entry=${_gen_ep:.8f} far below floor ${_floor} "
                  f"(likely BTC-denominated yfinance bug)")
            continue
        if (_gen_ep > 0 and _gen_ep < 0.001
                and _gen_sym.endswith("-USD")
                and _gen_sym not in _MICRO_TOKENS
                and not _gen_sym.startswith("DEX:")):
            print(f"  [PRICE SANITY] SKIP {_gen_sym} {strategy}: "
                  f"entry=${_gen_ep:.8f} suspiciously low for USD pair")
            continue

        if _emitter_registry_blocks_signal(signal):
            print(f"  [EMITTER REGISTRY] SKIP {signal.get('symbol')} {strategy}: toxic or not whitelisted")
            try:
                if record_blocked_signal is not None:
                    record_blocked_signal(signal, "EMITTER_REGISTRY", "emitter_registry_gate")
            except Exception:
                pass
            continue

        # --- STRUCTURAL TRADE BYPASS ---
        # Structural strategies bypass all directional gates (see set defined
        # above the loop).  They need ONLY: positive net edge after costs,
        # minimum volume, not on the kill list, and max 2 per symbol.
        if strategy in STRUCTURAL_STRATEGIES:
            # --- Structural acceptance criteria (NOT directional) ---
            _struct_blocked = False
            _struct_block_reason = ""

            # Check 1: Kill list (universal)
            if is_strategy_killed(
                strategy,
                _kill_list_cache,
                source_system=signal.get("source_system") or signal.get("source"),
                source_subsystem=signal.get("source_subsystem"),
            ):
                _struct_blocked = True
                _struct_block_reason = "on kill list"

            # Check 2: Max 2 structural positions per symbol (correlation limit)
            if not _struct_blocked:
                _struct_sym_count = sum(
                    1 for p in (active + new_picks)
                    if p.get("symbol") == signal["symbol"]
                    and p.get("trade_type") == "structural"
                )
                if _struct_sym_count >= 2:
                    _struct_blocked = True
                    _struct_block_reason = f"already {_struct_sym_count} structural positions on {signal['symbol']}"

            # Check 3: Net edge after costs > 5 bps
            _struct_net_edge = {}
            if not _struct_blocked and compute_net_edge is not None:
                try:
                    _struct_atr_pct = None
                    _struct_atr_val = signal.get("atr_at_entry", 0)
                    _struct_entry = signal.get("entry_price", 0)
                    if _struct_atr_val and _struct_entry and _struct_entry > 0:
                        _struct_atr_pct = _struct_atr_val / _struct_entry
                    _struct_net_edge = compute_net_edge(signal, atr_pct=_struct_atr_pct)
                    _struct_net_bps = _struct_net_edge.get("net_edge_bps", 0)
                    if _struct_net_bps < 5:
                        _struct_blocked = True
                        _struct_block_reason = f"net edge {_struct_net_bps:.1f} bps < 5 bps cost floor"
                except Exception as _struct_cost_err:
                    pass  # Cost check failure does NOT block structural trades

            # Check 4: Minimum volume (volume_ratio > 0.3 -- very lenient for structural)
            if not _struct_blocked:
                _struct_vol = signal.get("volume_ratio")
                if isinstance(_struct_vol, (int, float)) and _struct_vol < 0.3:
                    _struct_blocked = True
                    _struct_block_reason = f"volume_ratio={_struct_vol:.2f} < 0.3 minimum"

            if _struct_blocked:
                print(f"  [STRUCTURAL] BLOCK {signal['symbol']} {strategy}: {_struct_block_reason}")
                try:
                    if record_blocked_signal is not None:
                        record_blocked_signal(signal, "STRUCTURAL_GATE", _struct_block_reason)
                except Exception:
                    pass
                _structural_blocked += 1
                continue

            # Passed structural acceptance -- bypass ALL directional gates
            _struct_edge_bps = _struct_net_edge.get("net_edge_bps", 0) if _struct_net_edge else 0
            signal['elite_score'] = 70   # B grade default (structural = reliable)
            signal['elite_grade'] = 'B'

            pick = {
                "id": f"{strategy}::{signal['symbol']}::{_now_date()}",
                "strategy": strategy,
                "symbol": signal["symbol"],
                "category": signal.get("category", ""),
                "signal_type": signal.get("signal_type", "BUY"),
                "direction": _direction,
                "entry_price": signal["entry_price"],
                "entry_date": _now_date(),
                "timestamp": _now_iso(),
                "take_profit": signal.get("take_profit"),
                "stop_loss": signal.get("stop_loss"),
                "confidence": signal.get("confidence"),
                "ml_score": signal.get("ml_score"),
                "risk_reward": signal.get("risk_reward"),
                "reason": signal.get("reason", ""),
                "rsi_at_entry": signal.get("rsi_at_entry"),
                "volume_ratio": signal.get("volume_ratio"),
                "atr_at_entry": signal.get("atr_at_entry"),
                "market_fear_greed": signal.get("market_fear_greed"),
                "funding_rate": signal.get("funding_rate"),
                "convergence": signal.get("convergence", 0),
                "regime_encoded": signal.get("regime_encoded", 0),
                "status": "OPEN",
                "mfe": 0,
                "mae": 0,
                "high_water_mark": signal["entry_price"],
                "current_price": signal["entry_price"],
                "unrealized_pnl_pct": 0,
                "hold_days": 0,
                "created_at": _now_iso(),
                "trade_type": "structural",
                "elite_score": 70,
                "elite_grade": "B",
                "structural_edge_bps": _struct_edge_bps,
                "net_edge_bps": _struct_edge_bps,
                "cost_breakdown": _struct_net_edge.get("cost_breakdown", {}),
                "gross_edge_bps": _struct_net_edge.get("gross_edge_bps", 0),
                "total_cost_bps": _struct_net_edge.get("total_cost_bps", 0),
                "confluence_score": signal.get("confluence_score", 1.0),
                "confluence_reason": signal.get("confluence_reason", ""),
                "confluence_strategies": signal.get("confluence_strategies", []),
                "ensemble_only": signal.get("ensemble_only", False),
                # --- ML training features (match directional picks path) ---
                # Forward-test gate metadata
                "forward_wr": signal.get("forward_wr"),
                "forward_trades": signal.get("forward_trades"),
                "forward_validated": signal.get("forward_validated"),
                # Enriched market microstructure features
                "orderbook_imbalance": signal.get("orderbook_imbalance"),
                "ema_position": signal.get("ema_position"),
                "spread_pct": signal.get("spread_pct"),
                "wick_ratio": signal.get("wick_ratio"),
                "entry_distance_vwap": signal.get("entry_distance_vwap"),
                "bb_pct_b": signal.get("bb_pct_b"),
                "vpin": signal.get("vpin"),
                "galaxy_score": signal.get("galaxy_score"),
                # Technical indicator features
                "hma_slope": signal.get("hma_slope"),
                "rsi_1h": signal.get("rsi_1h"),
                "rsi_4h": signal.get("rsi_4h"),
                # OBI velocity features
                "obi_delta_5": signal.get("obi_delta_5"),
                "obi_acceleration": signal.get("obi_acceleration"),
            }
            # Tag with fast regime at entry time (feeds ML regime feature)
            if _HAS_FAST_REGIME:
                try:
                    _sym = signal.get("symbol", "BTCUSDT")
                    _fr = get_regime_for_symbol(_sym)
                    pick["entry_fast_regime"] = _fr
                    pick["entry_fast_regime_numeric"] = regime_to_numeric(_fr)
                except Exception:
                    pass
            new_picks.append(pick)
            existing.add(signal["symbol"])
            active_symbols_by_strategy[strategy] = existing
            _structural_accepted += 1

            print(f"  [STRUCTURAL] {signal['symbol']} {strategy} "
                  f"edge={_struct_edge_bps:.0f}bps -- bypassed directional gates")
            continue  # Skip ALL directional gates below

        # --- Quick Win 1: RR Gate (Mercury: RR>=1.5 lifts WR 39%->68%) ---
        # Relaxed for mean-reversion strategies (naturally lower R:R, higher WR)
        _ep = signal.get("entry_price", 0)
        _tp = signal.get("take_profit")
        _sl = signal.get("stop_loss")
        if _ep and _tp and _sl:
            _tp_dist = abs(_tp - _ep)
            _sl_dist = abs(_ep - _sl)
            _rr = _tp_dist / _sl_dist if _sl_dist > 0 else 0
            _is_mr = any(kw in strategy.lower() for kw in ['reversion', 'rsi', 'bollinger', 'mean_rev', 'connors', 'oversold'])
            _min_rr = 1.0 if _is_mr else 1.5  # mean-reversion: 1.0 min, others: 1.5
            if _rr < _min_rr:
                print(f"  [RR GATE] REJECTED {signal['symbol']} {strategy}: R:R={_rr:.2f} < {_min_rr} (risk exceeds reward)")
                try:
                    if record_blocked_signal is not None:
                        record_blocked_signal(signal, "RR_GATE", f"R:R={_rr:.2f} < {_min_rr}")
                except Exception:
                    pass
                continue

        # --- Quick Win 2: Alpha Engine Direction Gate (dynamic) ---
        # NOTE (2026-04-19 code review, Finding 3): gate iterates ALL
        # strategy_performance entries regardless of direction, so it is a
        # SYSTEM-WIDE win-rate check, not LONG-only (block only runs when
        # _direction=="LONG", so SHORTs bypass it and hit the SHORT gate below).
        # TODO: add per-direction breakdown in strategy_performance.json and
        # reinstate a true LONG-only gate on top of this system-wide floor.
        ALPHA_SYSTEM_WR_THRESHOLD = 0.30  # Lowered from 0.40: per-strategy quality gates + confidence >= 0.70 gate handles filtering
        ALPHA_SYSTEM_MIN_TRADES = 10
        if _direction == "LONG":
            _perf_data = load_strategy_performance()
            _sys_wins = 0
            _sys_total = 0
            for _s, _sd in _perf_data.items():
                _sys_wins += _sd.get("wins", 0)
                _sys_total += _sd.get("closed_picks", 0)
            _sys_wr = _sys_wins / _sys_total if _sys_total > 0 else 0.5
            if _sys_total >= ALPHA_SYSTEM_MIN_TRADES and _sys_wr < ALPHA_SYSTEM_WR_THRESHOLD:
                print(f"  [DIRECTION GATE] SKIP LONG {signal['symbol']} {strategy} "
                      f"(system WR={_sys_wr:.1%} < {ALPHA_SYSTEM_WR_THRESHOLD:.0%} across {_sys_total} trades)")
                try:
                    if record_blocked_signal is not None:
                        record_blocked_signal(signal, "DIRECTION_GATE", f"system WR={_sys_wr:.1%} < {ALPHA_SYSTEM_WR_THRESHOLD:.0%}")
                except Exception:
                    pass
                continue
            else:
                print(f"  [DIRECTION GATE] ALLOW LONG {signal['symbol']} {strategy} "
                      f"(system WR={_sys_wr:.1%}, {_sys_total} trades)")

        # --- Enhanced SHORT Gate (Mar 17 2026 root cause fix) ---
        # SHORT WR = 20.5% (27/132). Multi-layer gate:
        #   1. System-wide SHORT WR must be >= 40% (unchanged)
        #   2. Confidence >= 0.80 required for any SHORT signal
        #   3. ML score >= 0.80 required for SHORT
        #   4. Price must be below 50-period SMA (confirmed downtrend)
        # EXEMPTIONS (Mar 26 2026): Strategies with proven profitable SHORT WR
        #   Per analyze_short_strategies.py on 666 closed SHORT picks:
        _SHORT_EXEMPT_STRATEGIES = {
            "funding_momentum",                            # 60.4% WR n=106 (highest vol)
            "crypto_bayesian_regime_transition_momentum_v1",  # 100% WR n=10
            "crypto_kalman_trend_residual_reversion_v1",  # 80.0% WR n=5
            "crypto_keltner_compression_expansion_v1",    # 75.0% WR n=8
            "vwap_deviation_reversion_xrp_v1",            # 66.7% WR n=6
            "crypto_soc_orderflow_absorption_a01_v1",     # 60.0% WR n=10
            "crypto_soc_delta_divergence_a01_v1",         # 66.7% WR n=6
            "crypto_soc_delta_divergence_a04_v1",         # 57.1% WR n=7
            "crypto_soc_proxy_decoupling_a04_v1",         # 60.0% WR n=5
            "crypto_soc_delta_divergence_a07_v1",         # 60.0% WR n=5
        }
        if _direction == "SHORT":
            # Exempt proven-profitable SHORT strategies from the gate entirely
            if strategy in _SHORT_EXEMPT_STRATEGIES:
                print(f"  [SHORT EXEMPTION] ALLOW {signal['symbol']} {strategy} "
                      f"(proven profitable SHORT — exempt from gate)")
            else:
                _short_block_reason = None

                # Layer 1: System-wide SHORT WR check
                _actual_short_wr = 0.205  # Known baseline: 20.5%
                try:
                    import json as _json
                    _cp_path = os.path.join(os.path.dirname(__file__), "data", "closed_picks.json")
                    if os.path.exists(_cp_path):
                        with open(_cp_path, "r") as _cpf:
                            _closed = _json.load(_cpf)
                        _s_wins = sum(1 for p in _closed if isinstance(p, dict)
                                      and str(p.get("direction", p.get("signal_type", ""))).upper()
                                      in ("SHORT", "SELL") and p.get("status", "").upper() == "WON")
                        _s_total = sum(1 for p in _closed if isinstance(p, dict)
                                       and str(p.get("direction", p.get("signal_type", ""))).upper()
                                       in ("SHORT", "SELL"))
                        if _s_total >= 10:
                            _actual_short_wr = _s_wins / _s_total
                except Exception:
                    pass

                if _actual_short_wr < 0.40:
                    _short_block_reason = f"system-wide SHORT WR={_actual_short_wr:.1%} < 40%"

                # Layer 2: Confidence gate (>= 0.80 for shorts)
                if not _short_block_reason:
                    _short_conf = signal.get("confidence", 0) or 0
                    if isinstance(_short_conf, str):
                        try:
                            _short_conf = float(_short_conf)
                        except (ValueError, TypeError):
                            _short_conf = 0
                    if _short_conf < 0.80:
                        _short_block_reason = f"confidence={_short_conf:.2f} < 0.80"

                # Layer 3: ML score gate (>= 0.80 for shorts)
                if not _short_block_reason:
                    _short_ml = signal.get("ml_score", 0) or 0
                    if _short_ml < 0.80:
                        _short_block_reason = f"ml_score={_short_ml:.2f} < 0.80"

                # Layer 4: Downtrend confirmation (price must be below 50-period SMA)
                if not _short_block_reason:
                    try:
                        _short_sym = signal.get("symbol", "")
                        _short_ep = signal.get("entry_price", 0)
                        _sma50 = signal.get("extra", {}).get("sma_50")
                        # Try to get from market data if not in signal
                        if _sma50 is None and hasattr(signal, "get"):
                            _md = signal.get("market_regime", {})
                            _sma50 = _md.get("sma_50") if isinstance(_md, dict) else None
                        if _sma50 is not None and _short_ep > 0 and _short_ep >= _sma50:
                            _short_block_reason = (
                                f"price ${_short_ep:.4f} >= 50-SMA ${_sma50:.4f} "
                                f"(no confirmed downtrend)")
                    except Exception:
                        pass  # If SMA unavailable, skip this layer

                if _short_block_reason:
                    print(f"  [ENHANCED SHORT GATE] BLOCK {signal['symbol']} {strategy} "
                          f"({_short_block_reason})")
                    try:
                        if record_blocked_signal is not None:
                            record_blocked_signal(signal, "SHORT_GATE", _short_block_reason)
                    except Exception:
                        pass
                    continue
                else:
                    print(f"  [ENHANCED SHORT GATE] ALLOW {signal['symbol']} {strategy} "
                          f"(all 4 layers passed: WR={_actual_short_wr:.1%}, "
                          f"conf={signal.get('confidence', 0):.2f}, "
                          f"ml={signal.get('ml_score', 0):.2f})")

        # --- Quick Win 4: CATEGORY GATES ---
        # Forex: 0% WR (0/9), all SHORTs hit SL. Block all forex until WR > 30%.
        # Meme SHORTs: 25% WR -- block meme SHORTs specifically.
        _cat = str(signal.get("category", "")).lower()
        if _cat == "forex":
            # Compute forex WR from closed picks
            _forex_wr = 0.0
            try:
                import json as _json
                _cp_path = os.path.join(os.path.dirname(__file__), "data", "closed_picks.json")
                if os.path.exists(_cp_path):
                    with open(_cp_path, "r") as _cpf:
                        _closed = _json.load(_cpf)
                    _fx_wins = sum(1 for p in _closed if isinstance(p, dict)
                                   and str(p.get("category", "")).lower() == "forex"
                                   and p.get("status", "").upper() == "WON")
                    _fx_total = sum(1 for p in _closed if isinstance(p, dict)
                                    and str(p.get("category", "")).lower() == "forex")
                    if _fx_total >= 5:
                        _forex_wr = _fx_wins / _fx_total
            except Exception:
                pass
            if _forex_wr < 0.30:
                print(f"  [FOREX GATE] BLOCK {signal['symbol']} {strategy} "
                      f"(forex WR={_forex_wr:.0%} -- below 30% threshold)")
                try:
                    if record_blocked_signal is not None:
                        record_blocked_signal(signal, "FOREX_GATE", f"forex WR={_forex_wr:.0%} < 30%")
                except Exception:
                    pass
                continue

        if _cat in ("meme",) and _direction == "SHORT":
            print(f"  [MEME SHORT GATE] BLOCK {signal['symbol']} {strategy} "
                  f"(meme SHORT WR=25% -- blocking meme shorts)")
            try:
                if record_blocked_signal is not None:
                    record_blocked_signal(signal, "MEME_SHORT_GATE", "meme SHORT WR=25%")
            except Exception:
                pass
            continue

        # --- Gate 5: VPIN Toxicity Gate + Regime Routing ---
        try:
            if calculate_vpin is not None:
                _sym_vpin = _vpin_cache.get(signal["symbol"])
                if _sym_vpin is not None:
                    if _sym_vpin > 0.55:
                        # High toxicity -- suppress entirely
                        print(f"  [VPIN GATE] VPIN toxicity gate: {signal['symbol']} "
                              f"VPIN={_sym_vpin:.2f} > 0.55, suppressing")
                        try:
                            if record_blocked_signal is not None:
                                record_blocked_signal(signal, "VPIN_GATE", f"VPIN={_sym_vpin:.2f} > 0.55")
                        except Exception:
                            pass
                        continue
                    elif _sym_vpin >= 0.3:
                        # Informed trading regime -- only allow elite picks (score >= 60)
                        _vpin_elite = signal.get("elite_score")
                        if isinstance(_vpin_elite, (int, float)) and _vpin_elite < 60:
                            print(f"  [VPIN REGIME] Informed trading regime: {signal['symbol']} "
                                  f"VPIN={_sym_vpin:.2f}, elite_score={_vpin_elite} < 60, suppressing")
                            try:
                                if record_blocked_signal is not None:
                                    record_blocked_signal(signal, "VPIN_REGIME_GATE", f"VPIN={_sym_vpin:.2f}, elite={_vpin_elite} < 60")
                            except Exception:
                                pass
                            continue
                        print(f"  [VPIN REGIME] Informed trading regime: {signal['symbol']} "
                              f"VPIN={_sym_vpin:.2f}, elite_score={_vpin_elite} -- allowed (elite)")
                    else:
                        # Noise trading regime (VPIN < 0.3) -- favor mean-reversion strategies
                        _strat_lower = strategy.lower()
                        if any(kw in _strat_lower for kw in ('mean_reversion', 'rsi', 'bollinger')):
                            _prev_elite = signal.get("elite_score")
                            if isinstance(_prev_elite, (int, float)):
                                signal["elite_score"] = _prev_elite + 5
                                print(f"  [VPIN REGIME] Noise trading regime: {signal['symbol']} "
                                      f"VPIN={_sym_vpin:.2f}, +5 score to mean-reversion strategy "
                                      f"'{strategy}' ({_prev_elite} -> {signal['elite_score']})")
                            else:
                                print(f"  [VPIN REGIME] Noise trading regime: {signal['symbol']} "
                                      f"VPIN={_sym_vpin:.2f}, mean-reversion boost skipped (no elite_score)")
                        else:
                            print(f"  [VPIN REGIME] Noise trading regime: {signal['symbol']} "
                                  f"VPIN={_sym_vpin:.2f}, no mean-reversion boost for '{strategy}'")
        except Exception as _vpin_err:
            pass  # VPIN failure must not block picks

        # --- Gate 5b: Liquidation Density Score (LDS) Risk Filter ---
        try:
            if _cat in ("crypto",) and _direction == "LONG":
                _lds_entry = signal.get("entry_price", 0)
                _lds_atr = signal.get("atr_at_entry", 0)
                _lds_funding = signal.get("funding_rate", 0) or 0
                # Compute 7d price change from OHLCV data if available
                _lds_price_change_7d = 0.0
                _lds_sym_data = data.get(signal["symbol"])
                if _lds_sym_data is not None:
                    try:
                        _lds_close = _lds_sym_data.get("Close", _lds_sym_data.get("close"))
                        if _lds_close is not None and len(_lds_close) >= 7:
                            _lds_price_now = float(_lds_close.iloc[-1])
                            _lds_price_7d = float(_lds_close.iloc[-7])
                            if _lds_price_7d > 0:
                                _lds_price_change_7d = (_lds_price_now - _lds_price_7d) / _lds_price_7d
                    except Exception:
                        pass
                # Compute ATR percentage
                _lds_atr_pct = (_lds_atr / _lds_entry) if (_lds_entry > 0 and _lds_atr > 0) else 0
                if _lds_atr_pct > 0:
                    _lds_atr_ratio = _lds_price_change_7d / _lds_atr_pct
                    _lds = abs(_lds_atr_ratio) * max(abs(_lds_funding) / 0.01, 1.0)
                    if _lds > 5:
                        print(f"  [LDS BLOCK] {signal['symbol']} LDS={_lds:.1f}, cascade imminent")
                        try:
                            if record_blocked_signal is not None:
                                record_blocked_signal(signal, "LDS_GATE", f"LDS={_lds:.1f} > 5, cascade imminent")
                        except Exception:
                            pass
                        continue
                    elif _lds > 3:
                        _lds_prev_score = signal.get("elite_score")
                        if isinstance(_lds_prev_score, (int, float)):
                            signal["elite_score"] = _lds_prev_score - 15
                        print(f"  [LDS WARNING] {signal['symbol']} LDS={_lds:.1f}, high cascade risk, -15 score")
        except Exception as _lds_err:
            pass  # LDS failure must not block picks

        # --- Gate 6: Consecutive-Loss Cooldown (Task 2) ---
        try:
            if should_skip_due_to_losses is not None:
                if should_skip_due_to_losses(signal["symbol"], strategy, closed, max_consecutive=2):
                    # Count consecutive losses for log message
                    _matching = [p for p in closed
                                 if p.get("symbol") == signal["symbol"]
                                 and p.get("strategy") == strategy]
                    _n_consec = 0
                    for _mp in _matching:
                        if _mp.get("result") == "loss":
                            _n_consec += 1
                        else:
                            break
                    print(f"  [COOLDOWN GATE] Cooldown gate: {signal['symbol']} {strategy} "
                          f"has {_n_consec} consecutive losses, cooling down")
                    try:
                        if record_blocked_signal is not None:
                            record_blocked_signal(signal, "COOLDOWN_GATE", f"{_n_consec} consecutive losses")
                    except Exception:
                        pass
                    continue
        except Exception as _cool_err:
            pass  # Cooldown failure must not block picks

        # --- Gate 7: Deflated Sharpe Penalty (Task 3) ---
        # Does NOT block -- penalizes elite_score by 15 if Sharpe not significant
        try:
            if deflated_sharpe_ratio is not None and strategy in _dsr_cache:
                _dsr_val = _dsr_cache[strategy]
                if _dsr_val < 0.95:
                    # Strategy has >= 20 trades but DSR says Sharpe not significant
                    _prev_score = signal.get("elite_score")
                    if isinstance(_prev_score, (int, float)):
                        signal["elite_score"] = _prev_score - 15
                    print(f"  [DSR GATE] DSR penalty: {strategy} Sharpe not significant "
                          f"after multiple testing correction (DSR={_dsr_val:.3f}), -15 score")
        except Exception as _dsr_err:
            pass  # DSR failure must not block picks

        # --- Gate 8: White's Reality Check Penalty ---
        # Does NOT block -- penalizes elite_score by 10 if strategy alpha is not
        # significant after multiple hypothesis testing correction.
        try:
            if _wrc_cache and strategy in _wrc_cache:
                _wrc_pval = _wrc_cache[strategy]
                if _wrc_pval > 0.05:
                    _prev_score = signal.get("elite_score")
                    if isinstance(_prev_score, (int, float)):
                        signal["elite_score"] = _prev_score - 10
                    print(f"  [WRC GATE] White's Reality Check: {strategy} not significant "
                          f"(p={_wrc_pval:.3f}), -10 score")
        except Exception:
            pass  # WRC failure must not block picks

        # --- HMM Regime Score Adjustment ---
        try:
            from hmm_regime import get_regime_score_adjustment
            _hmm_adj = get_regime_score_adjustment(signal)
            if abs(_hmm_adj) >= 2.0:
                _s = signal.get("elite_score", 0)
                if isinstance(_s, (int, float)):
                    signal["elite_score"] = _s + _hmm_adj
                signal["hmm_regime_adj"] = _hmm_adj
        except Exception:
            pass

        # --- BOCPD Changepoint Warning ---
        try:
            from bocpd import check_changepoint, fetch_btc_daily_stats
            _ret, _ = fetch_btc_daily_stats() if not hasattr(check_changepoint, '_cached') else (None, None)
            if _ret is not None:
                _cp = check_changepoint(_ret)
                if _cp.get("is_changepoint"):
                    _s = signal.get("elite_score", 0)
                    if isinstance(_s, (int, float)):
                        signal["elite_score"] = _s - 8
                    signal["bocpd_changepoint"] = True
                    logging.info(f"[BOCPD] Changepoint detected! P={_cp['changepoint_prob']:.2f}, -8 score")
        except Exception:
            pass

        # --- Bandit TP/SL Selection ---
        try:
            from bandit_tp_sl import select_tp_sl
            _atr = signal.get("atr_at_entry", 0)
            if _atr and float(_atr) > 0:
                _btp = select_tp_sl(signal, float(_atr))
                if _btp.get("take_profit") and _btp.get("stop_loss"):
                    signal["bandit_tp"] = _btp["take_profit"]
                    signal["bandit_sl"] = _btp["stop_loss"]
                    signal["bandit_arm_index"] = _btp.get("arm_index", 0)
        except Exception:
            pass

        # --- Thompson Sampling Bonus: Bayesian strategy allocation ---
        # Strategies with strong posterior WR get up to +10, weak get up to -10
        try:
            from thompson_sampler import get_strategy_score_bonus
            _ts_bonus = get_strategy_score_bonus(strategy)
            if abs(_ts_bonus) >= 2.0:
                _score = signal.get("elite_score", 0)
                if isinstance(_score, (int, float)):
                    signal["elite_score"] = _score + _ts_bonus
                if _ts_bonus > 0:
                    logging.info(f"[THOMPSON] {signal['symbol']} {strategy} +{_ts_bonus:.0f} (strong posterior)")
        except Exception:
            pass

        # --- GRU Deep Learning Bonus: local GPU-trained direction model ---
        try:
            from local_gpu_trainer.inference import predict_direction
            _gru_pred = predict_direction(signal['symbol'])
            if _gru_pred and _gru_pred.get('confidence', 0) > 0.6:
                _gru_adj = 5 if _gru_pred['direction'] == signal.get('direction', 'LONG') else -5
                signal['elite_score'] = signal.get('elite_score', 0) + _gru_adj
                signal['gru_prediction'] = _gru_pred
        except Exception:
            pass

        # --- Hot Streak Bonus: proven strategies get score boost ---
        try:
            _strat_perf = perf.get(strategy, {}) if perf else {}
            _strat_wr = _strat_perf.get("win_rate", 0)
            _strat_n = _strat_perf.get("total", _strat_perf.get("closed_picks", 0))
            if _strat_n >= 5 and _strat_wr >= 0.75:
                _streak_bonus = 10 if _strat_wr >= 0.90 else 5
                _score = signal.get("elite_score", 0)
                if isinstance(_score, (int, float)):
                    signal["elite_score"] = _score + _streak_bonus
                logging.info(f"[STREAK] {signal['symbol']} {strategy} WR={_strat_wr:.0%} ({_strat_n} trades) +{_streak_bonus} bonus")
        except Exception:
            pass

        # --- Gate 10: Momentum Confirmation ---
        # Root cause data: entries without momentum alignment have 25.7% WR.
        # Require the signal direction to align with short-term momentum.
        try:
            _sym_data = data.get(signal["symbol"], data.get(list(data.keys())[0])) if data else None
            if _sym_data is not None and hasattr(_sym_data, '__len__') and len(_sym_data) >= 20:
                _close = _sym_data['Close'] if 'Close' in _sym_data else _sym_data.get('close')
                if _close is not None and len(_close) >= 20:
                    _sma5 = float(_close.iloc[-5:].mean())
                    _sma20 = float(_close.iloc[-20:].mean())
                    _cur = float(_close.iloc[-1])
                    _mom_aligned = True
                    if _direction == "LONG" and _cur < _sma5 < _sma20:
                        _mom_aligned = False  # price falling below both SMAs -- no long
                    elif _direction == "SHORT" and _cur > _sma5 > _sma20:
                        _mom_aligned = False  # price rising above both SMAs -- no short
                    if not _mom_aligned:
                        _score = signal.get("elite_score", 50)
                        if isinstance(_score, (int, float)):
                            signal["elite_score"] = _score - 8
                        logging.info(f"[MOM GATE] {signal['symbol']} {_direction} against momentum (SMA5/20), -8 score")

                    # Multi-timeframe: daily trend bonus/penalty (SMA50 vs SMA200)
                    if len(_close) >= 200:
                        _sma50 = float(_close.iloc[-50:].mean())
                        _sma200 = float(_close.iloc[-200:].mean())
                        if _direction == "LONG" and _sma50 > _sma200 and _cur > _sma50:
                            # Uptrend on daily -- strong confirmation
                            _score = signal.get("elite_score", 50)
                            if isinstance(_score, (int, float)):
                                signal["elite_score"] = _score + 5
                            signal["daily_trend"] = "UPTREND"
                        elif _direction == "LONG" and _sma50 < _sma200:
                            # Downtrend on daily -- penalty for going long
                            _score = signal.get("elite_score", 50)
                            if isinstance(_score, (int, float)):
                                signal["elite_score"] = _score - 5
                            signal["daily_trend"] = "DOWNTREND"
        except Exception:
            pass

        # --- Volume Confirmation Bonus ---
        # Data: volume > 1.5x average = 62-68% WR. Low volume = noise.
        try:
            _sym_data2 = data.get(signal["symbol"]) if data else None
            if _sym_data2 is not None and hasattr(_sym_data2, '__len__') and len(_sym_data2) >= 20:
                _vol = _sym_data2.get('Volume', _sym_data2.get('volume'))
                if _vol is not None and len(_vol) >= 20:
                    _cur_vol = float(_vol.iloc[-1])
                    _avg_vol = float(_vol.iloc[-20:].mean())
                    if _avg_vol > 0:
                        _vol_ratio = _cur_vol / _avg_vol
                        if _vol_ratio >= 2.0:
                            signal["elite_score"] = signal.get("elite_score", 50) + 5
                            signal["volume_confirmation"] = "STRONG"
                        elif _vol_ratio >= 1.5:
                            signal["elite_score"] = signal.get("elite_score", 50) + 3
                            signal["volume_confirmation"] = "CONFIRMED"
                        elif _vol_ratio < 0.5:
                            signal["elite_score"] = signal.get("elite_score", 50) - 3
                            signal["volume_confirmation"] = "WEAK"
        except Exception:
            pass

        # --- Gate: MTF Confirmation (SOFT) ---
        # Multi-timeframe alignment check for crypto picks.
        # Adjusts elite_score based on higher-TF agreement. Does NOT hard-block.
        try:
            from alpha_engine.mtf_gate import check_mtf_alignment
            asset_class = signal.get("asset_class", "").lower()
            if asset_class == "crypto" and signal.get("symbol"):
                direction = "BULL" if signal.get("direction", "").upper() in ("LONG", "BUY") else "BEAR"
                mtf = check_mtf_alignment(signal["symbol"], direction)
                if mtf and mtf.get("score_adjustment"):
                    signal["elite_score"] = max(0, signal.get("elite_score", 50) + mtf["score_adjustment"])
                    signal["mtf_aligned"] = mtf.get("aligned", True)
                    signal["mtf_agreement"] = mtf.get("agreement_ratio", "?")
        except Exception:
            pass

        # --- Gate: Ensemble Confirmation (SOFT) ---
        # 2-of-3 ensemble check for crypto picks.
        # Boosts confidence if multiple sub-models agree; penalizes score if they disagree.
        try:
            from alpha_engine.ensemble_gate import check_ensemble
            asset_class = signal.get("asset_class", "").lower()
            if asset_class == "crypto" and signal.get("symbol"):
                direction = signal.get("direction", "LONG").upper()
                ens = check_ensemble(signal["symbol"], direction)
                if ens:
                    signal["ensemble_passes"] = ens.get("passes", True)
                    signal["ensemble_signals"] = ens.get("signals_aligned", 0)
                    if ens.get("confidence_boost"):
                        conf = signal.get("confidence", 0.5)
                        signal["confidence"] = min(0.95, conf + ens["confidence_boost"])
                    if not ens.get("passes") and signal.get("elite_score", 50) < 60:
                        signal["elite_score"] = max(0, signal.get("elite_score", 50) - 10)
        except Exception:
            pass

        # --- Gate: Heikin Ashi Trend Filter (SOFT) ---
        # HA ensemble filter for crypto picks.
        # Adjusts elite_score based on HA candle trend alignment. Does NOT hard-block.
        try:
            from alpha_engine.ha_ensemble_filter import check_ha_ensemble
            asset_class = signal.get("asset_class", "").lower()
            if asset_class == "crypto" and signal.get("symbol"):
                direction = signal.get("direction", "LONG").upper()
                ha = check_ha_ensemble(signal["symbol"], direction)
                if ha and ha.get("score_adjustment"):
                    signal["elite_score"] = max(0, signal.get("elite_score", 50) + ha["score_adjustment"])
                    signal["ha_trend"] = ha.get("ha_trend", "UNKNOWN")
        except Exception:
            pass

        # --- OBI Velocity Score Adjustment (Priority 1) ---
        # If order book imbalance velocity strongly favors the pick direction: +3
        # If OBI velocity opposes the pick direction: -3
        try:
            if compute_obi_velocity_batch is not None:
                _obi_raw = signal.get("orderbook_imbalance")
                if isinstance(_obi_raw, (int, float)) and _obi_raw != 0:
                    # Compute velocity for this symbol inline using batch with single entry
                    _obi_vel_result = compute_obi_velocity_batch({signal["symbol"]: float(_obi_raw)})
                    _obi_vel = _obi_vel_result.get(signal["symbol"], {})
                    _obi_d5 = _obi_vel.get("obi_delta_5", 0)
                    _obi_accel = _obi_vel.get("obi_acceleration", 0)
                    # Combined velocity signal: delta_5 + acceleration
                    _obi_combined = _obi_d5 + _obi_accel
                    signal["obi_velocity_score"] = round(_obi_combined, 4)
                    signal["obi_delta_5"] = _obi_d5
                    signal["obi_acceleration"] = _obi_accel

                    _obi_es = signal.get("elite_score", 50)
                    if isinstance(_obi_es, (int, float)):
                        if _direction == "LONG" and _obi_combined > 0.15:
                            # Buy pressure accelerating -- favors LONG
                            signal["elite_score"] = _obi_es + 3
                            signal["obi_note"] = f"OBI velocity favors LONG (vel={_obi_combined:.3f}), +3"
                        elif _direction == "LONG" and _obi_combined < -0.15:
                            # Sell pressure accelerating -- opposes LONG
                            signal["elite_score"] = _obi_es - 3
                            signal["obi_note"] = f"OBI velocity opposes LONG (vel={_obi_combined:.3f}), -3"
                        elif _direction == "SHORT" and _obi_combined < -0.15:
                            # Sell pressure accelerating -- favors SHORT
                            signal["elite_score"] = _obi_es + 3
                            signal["obi_note"] = f"OBI velocity favors SHORT (vel={_obi_combined:.3f}), +3"
                        elif _direction == "SHORT" and _obi_combined > 0.15:
                            # Buy pressure accelerating -- opposes SHORT
                            signal["elite_score"] = _obi_es - 3
                            signal["obi_note"] = f"OBI velocity opposes SHORT (vel={_obi_combined:.3f}), -3"
        except Exception:
            pass  # OBI velocity failure must not block picks

        # --- Gate 9: Minimum elite_score Quality Gate (score < 30 = suppress) ---
        # Bottom ~20% of picks are net-negative expectancy. Suppress entirely.
        _qg_score = signal.get("elite_score")
        if isinstance(_qg_score, (int, float)) and _qg_score < 30:
            print(f"  Quality gate: {signal['symbol']} score={_qg_score} < 30, suppressed")
            try:
                if record_blocked_signal is not None:
                    record_blocked_signal(signal, "QUALITY_GATE", f"elite_score={_qg_score} < 30")
            except Exception:
                pass
            continue

        # --- Gate 11: Winner Filter (research-backed quality gate) ---
        # Applied AFTER elite scoring, BEFORE final emission.
        # Based on 8,457 closed pick analysis. Configurable and lenient.
        _wf_pass, _wf_reason = apply_winner_filter(signal)
        if not _wf_pass:
            print(f"  [WINNER FILTER] BLOCK {signal['symbol']} {strategy}: {_wf_reason}")
            try:
                if record_blocked_signal is not None:
                    record_blocked_signal(signal, "WINNER_FILTER", _wf_reason)
            except Exception:
                pass
            _directional_blocked += 1
            continue

        pick = {
            "id": f"{signal.get('strategy', '')}::{signal.get('symbol', '')}::{_now_date()}",
            "strategy": signal.get("strategy", ""),
            "symbol": signal.get("symbol", ""),
            "category": signal.get("category", ""),
            "signal_type": signal.get("signal_type", "BUY"),
            "direction": _direction,
            "entry_price": signal.get("entry_price", 0),
            "entry_date": _now_date(),
            "timestamp": _now_iso(),
            "take_profit": signal.get("take_profit"),
            "stop_loss": signal.get("stop_loss"),
            "confidence": signal.get("confidence"),
            "ml_score": signal.get("ml_score"),
            "risk_reward": signal.get("risk_reward"),
            "reason": signal.get("reason", ""),
            "rsi_at_entry": signal.get("rsi_at_entry"),
            "volume_ratio": signal.get("volume_ratio"),
            "atr_at_entry": signal.get("atr_at_entry"),
            "market_fear_greed": signal.get("market_fear_greed"),
            "funding_rate": signal.get("funding_rate"),
            "convergence": signal.get("convergence", 0),
            "regime_encoded": signal.get("regime_encoded", 0),
            "status": "OPEN",
            "mfe": 0,
            "mae": 0,
            "high_water_mark": signal["entry_price"],
            "current_price": signal["entry_price"],
            "unrealized_pnl_pct": 0,
            "hold_days": 0,
            "created_at": _now_iso(),
            # Confluence engine metadata
            "confluence_score": signal.get("confluence_score", 1.0),
            "confluence_reason": signal.get("confluence_reason", ""),
            "confluence_strategies": signal.get("confluence_strategies", []),
            "ensemble_only": signal.get("ensemble_only", False),
            # --- ML training features (persisted so ML model sees non-zero values) ---
            # Forward-test gate metadata from rank_and_filter_signals
            "forward_wr": signal.get("forward_wr"),
            "forward_trades": signal.get("forward_trades"),
            "forward_validated": signal.get("forward_validated"),
            # Enriched market microstructure features
            "orderbook_imbalance": signal.get("orderbook_imbalance"),
            "ema_position": signal.get("ema_position"),
            "spread_pct": signal.get("spread_pct"),
            "wick_ratio": signal.get("wick_ratio"),
            "entry_distance_vwap": signal.get("entry_distance_vwap"),
            "bb_pct_b": signal.get("bb_pct_b"),
            "vpin": signal.get("vpin"),
            "galaxy_score": signal.get("galaxy_score"),
            # Technical indicator features from enrich_signals_with_ml_features
            "hma_slope": signal.get("hma_slope"),
            "rsi_1h": signal.get("rsi_1h"),
            "rsi_4h": signal.get("rsi_4h"),
            # OBI velocity features (Priority 1)
            "obi_velocity_score": signal.get("obi_velocity_score"),
            "obi_delta_5": signal.get("obi_delta_5"),
            "obi_delta_15": signal.get("obi_delta_15"),
            "obi_acceleration": signal.get("obi_acceleration"),
            "obi_note": signal.get("obi_note"),
            # Winner filter time penalty (if applied during death zone)
            "winner_filter_time_penalty": signal.get("winner_filter_time_penalty", 0),
        }

        # Tag with fast regime at entry time (feeds ML regime feature)
        if _HAS_FAST_REGIME:
            try:
                _sym = signal.get("symbol", "BTCUSDT")
                _fr = get_regime_for_symbol(_sym)
                pick["entry_fast_regime"] = _fr
                pick["entry_fast_regime_numeric"] = regime_to_numeric(_fr)
            except Exception:
                pass

        # --- Trade-worthy and Leverage-worthy tags (Task 2) ---
        # These tags are read by the dashboard for portfolio allocation.
        _pick_score = signal.get("elite_score", 0)
        if isinstance(_pick_score, str):
            try:
                _pick_score = float(_pick_score)
            except (ValueError, TypeError):
                _pick_score = 0
        _pick_conf = signal.get("confidence", 0) or 0
        if isinstance(_pick_conf, str):
            try:
                _pick_conf = float(_pick_conf)
            except (ValueError, TypeError):
                _pick_conf = 0
        _pick_rr = signal.get("risk_reward", 0) or 0
        if isinstance(_pick_rr, str):
            try:
                _pick_rr = float(_pick_rr)
            except (ValueError, TypeError):
                _pick_rr = 0
        _pick_cat = str(signal.get("category", "")).lower()

        # trade_worthy: score >= 45 AND passed winner filter
        # Threshold lowered from 50 to 45 -- too strict in bearish market conditions
        pick["trade_worthy"] = (isinstance(_pick_score, (int, float))
                                and _pick_score >= 45)
        if pick["trade_worthy"]:
            WINNER_FILTER_STATS["trade_worthy_count"] += 1

        # leverage_worthy: score >= 60, confidence >= 0.70, crypto, R:R >= 2.0
        # Threshold lowered from 68 to 60 -- too strict in bearish market conditions
        pick["leverage_worthy"] = (
            isinstance(_pick_score, (int, float)) and _pick_score >= 60
            and _pick_conf >= 0.70
            and _pick_cat in ("crypto", "meme")
            and _pick_rr >= 2.0
        )
        if pick["leverage_worthy"]:
            WINNER_FILTER_STATS["leverage_worthy_count"] += 1

        # Apply tweaks if any exist
        tweaks = load_tweaks()
        strat_tweaks = tweaks.get(strategy, {})
        if strat_tweaks.get("tp_multiplier_adj"):
            adj = strat_tweaks["tp_multiplier_adj"]
            if pick["take_profit"] and pick["entry_price"]:
                tp_dist = pick["take_profit"] - pick["entry_price"]
                pick["take_profit"] = pick["entry_price"] + tp_dist * adj
        if strat_tweaks.get("sl_multiplier_adj"):
            adj = strat_tweaks["sl_multiplier_adj"]
            if pick["stop_loss"] and pick["entry_price"]:
                sl_dist = pick["entry_price"] - pick["stop_loss"]
                pick["stop_loss"] = pick["entry_price"] - sl_dist * adj

        # --- Regime-adaptive TP/SL (ported from ml_crypto_predictor) ---
        # PnL audit: TPs 40% too ambitious (MFE/TP=0.60). Tighten using ATR * regime mult.
        apply_regime_adaptive_tp_sl(pick, signal)

        # --- Dynamic SL/TP Calibrator (MAE/MFE analysis on closed picks) ---
        # Only tightens (more conservative), never widens. Safe to fail.
        if apply_calibrated_sl_tp is not None:
            try:
                _entry_quality = pick.get("entry_timing_score")
                apply_calibrated_sl_tp(pick, entry_quality=_entry_quality)
            except Exception as _cal_err:
                print(f"  [SL_CAL] Calibration failed for {pick.get('symbol')} (non-fatal): {_cal_err}")

        # --- Kill Switch filtering on individual picks ---
        try:
            if _kill_status is not None:
                _ks_sev = _kill_status.get("severity", "ok")
                if _ks_sev == "critical":
                    # Only allow high-conviction picks (elite_score >= 80)
                    _ks_score = pick.get("elite_score") or signal.get("elite_score") or signal.get("ml_score", 0)
                    if isinstance(_ks_score, (int, float)) and _ks_score < 80:
                        print(f"  [KILL SWITCH] CRITICAL filter: SKIP {pick['symbol']} {strategy} "
                              f"(score={_ks_score} < 80)")
                        continue
                elif _ks_sev == "warning":
                    # Subtract 5 from elite_score
                    _ks_prev = pick.get("elite_score") or signal.get("elite_score")
                    if isinstance(_ks_prev, (int, float)):
                        pick["elite_score"] = _ks_prev - 5
                        signal["elite_score"] = _ks_prev - 5
        except Exception:
            pass  # Kill switch filtering must never block the pipeline

        new_picks.append(pick)
        existing.add(signal["symbol"])
        active_symbols_by_strategy[strategy] = existing
        _directional_accepted += 1

        print(f"  NEW: {signal.get('signal_type', signal.get('side', 'BUY'))} {signal['symbol']} @ {signal['entry_price']} "
              f"[{signal['strategy']}] ML={signal.get('ml_score', '?')}")

    # --- Structural vs Directional stats ---
    # Directional blocked = total signals processed minus all accepted and structural
    _total_structural = _structural_accepted + _structural_blocked
    _directional_candidates = len(ranked) - _total_structural
    _directional_blocked = max(0, _directional_candidates - _directional_accepted)
    print(f"  [STATS] Structural: {_structural_accepted} picks generated (bypassed gates), "
          f"{_structural_blocked} blocked by cost/liquidity gate")
    print(f"  [STATS] Directional: {_directional_accepted} picks generated, "
          f"~{_directional_blocked} blocked by gates")

    # Annotate new picks with forward-test gate metadata
    perf = load_strategy_performance()
    if new_picks:
        n_validated = annotate_picks_with_forward_gate(new_picks, perf)
        n_total = len(new_picks)
        n_unvalidated = n_total - n_validated
        print(f"  [FORWARD GATE] {n_validated}/{n_total} picks from validated strategies "
              f"({n_unvalidated} unvalidated -- still tracked, not blocked)")

    # Also annotate existing active picks so all active_picks.json entries
    # carry forward-gate metadata
    if active and perf:
        annotate_picks_with_forward_gate(active, perf)

    # --- Kelly Criterion position sizing ---
    # Annotate each new pick with kelly_fraction, position_size_usd, etc.
    if new_picks:
        # Compute current crypto allocation from existing active picks
        _crypto_alloc = sum(
            float(p.get("position_size_usd", 0) or 0)
            for p in active
            if p.get("category") in ("crypto", "meme")
        )
        _account_equity = STARTING_CAPITAL
        _kelly_tier = "half"  # Half-Kelly justified: picks pass MIN_SCORE=65 and PF>=1.5 quality gates (quant audit 2026-04-07)

        for pick in new_picks:
            strat_name = pick.get("strategy", "")
            strat_perf = perf.get(strat_name, {})
            # Map strategy_performance fields to what position_sizing expects
            _stats = {
                "win_rate": strat_perf.get("win_rate", 0.5),
                "avg_win_pct": strat_perf.get("avg_win_pct", 2.0),
                "avg_loss_pct": strat_perf.get("avg_loss_pct", 2.0),
                "closed_picks": strat_perf.get("closed_picks", 0),
            }
            annotate_signal_with_kelly(
                pick,
                strategy_stats=_stats,
                account_equity=_account_equity,
                kelly_tier=_kelly_tier,
                open_positions=active,
                current_crypto_allocation=_crypto_alloc,
            )
            # Track running crypto allocation for subsequent picks
            if pick.get("category") in ("crypto", "meme"):
                _crypto_alloc += pick.get("position_size_usd", 0)

        _sized = [p for p in new_picks if p.get("position_size_usd", 0) > 0]
        print(f"  [KELLY] Sized {len(_sized)}/{len(new_picks)} picks "
              f"(tier={_kelly_tier}, equity=${_account_equity:,.0f})")

    # --- Conformal Sizing: uncertainty-adjusted position multiplier (Priority 2) ---
    # High model uncertainty -> reduce position size, low uncertainty -> allow full size.
    # Applies AFTER Kelly to scale the position_size_usd by conformal multiplier.
    if _conformal_sizer is not None and new_picks:
        _conf_adjusted = 0
        for pick in new_picks:
            try:
                # Use ml_score or meta_label_score as the predicted probability
                _pred_prob = pick.get("ml_score") or pick.get("meta_label_score") or 0.5
                if isinstance(_pred_prob, str):
                    try:
                        _pred_prob = float(_pred_prob)
                    except (ValueError, TypeError):
                        _pred_prob = 0.5
                _pred_prob = max(0.0, min(1.0, float(_pred_prob)))

                _conf_mult = _conformal_sizer.size_multiplier(_pred_prob)
                _conf_diag = _conformal_sizer.get_diagnostics(_pred_prob)
                pick["conformal_size_mult"] = _conf_mult
                pick["conformal_width"] = _conf_diag.get("conformal_width")
                pick["conformal_calibrated"] = _conf_diag.get("conformal_calibrated", False)

                # Scale position size by conformal multiplier
                _pos_usd = pick.get("position_size_usd", 0) or 0
                if _pos_usd > 0 and _conf_mult != 1.0:
                    _new_pos = round(_pos_usd * _conf_mult, 2)
                    pick["position_size_usd_pre_conformal"] = _pos_usd
                    pick["position_size_usd"] = _new_pos
                    _conf_adjusted += 1
            except Exception:
                pass  # Conformal sizing failure must not block picks

        if _conf_adjusted > 0:
            print(f"  [CONFORMAL] Adjusted {_conf_adjusted}/{len(new_picks)} pick sizes "
                  f"(calibrated={_conformal_sizer.calibrated}, "
                  f"residuals={len(_conformal_sizer.residuals)})")
        else:
            print(f"  [CONFORMAL] No size adjustments (calibrated={_conformal_sizer.calibrated})")
    elif _conformal_sizer is None:
        print("  [CONFORMAL] conformal_sizing module not available, skipping")

    # Save all active picks
    active.extend(new_picks)

    # Compute elite_score for ALL active picks (not just new ones)
    # This ensures scores update as Monte Carlo data improves over time
    try:
        enrich_picks_with_elite_score(active, DATA_DIR)
    except Exception as e:
        print(f"  [ELITE] Scoring failed (non-fatal): {e}")

    # --- Entry Timing Optimization ---
    # Adjust elite_score based on real-time entry timing quality.
    # Bad timing (score < 0.3) = -5, excellent timing (score > 0.7) = +5.
    if compute_entry_timing_score is not None:
        _timing_adjusted = 0
        for pick in active:
            try:
                symbol = pick.get("symbol", "")
                if not symbol:
                    continue
                timing_score = compute_entry_timing_score(symbol, signal=pick)
                pick["entry_timing_score"] = timing_score

                current_score = pick.get("elite_score")
                if isinstance(current_score, (int, float)):
                    if timing_score < 0.3:
                        pick["elite_score"] = current_score - 5
                        pick["entry_timing_note"] = f"Bad entry timing ({timing_score:.2f}), -5"
                        _timing_adjusted += 1
                    elif timing_score > 0.7:
                        pick["elite_score"] = current_score + 5
                        pick["entry_timing_note"] = f"Excellent entry timing ({timing_score:.2f}), +5"
                        _timing_adjusted += 1
            except Exception:
                pass  # Entry timing failure must never block a pick
        if _timing_adjusted > 0:
            print(f"  [ENTRY TIMING] Adjusted {_timing_adjusted} picks by entry timing score")
    else:
        print("  [ENTRY TIMING] entry_optimizer module not available, skipping")

    # --- Smart Entry Zone Scoring ---
    # Multi-factor confluence analysis: support proximity, momentum, volume,
    # trend alignment, volatility compression. Score 0-100.
    # Weak zone (< 30) = -5 elite_score + note; Strong zone (> 70) = +5 + note.
    if _smart_entry_detector is not None:
        _sez_adjusted = 0
        for pick in active:
            try:
                symbol = pick.get("symbol", "")
                if not symbol:
                    continue
                _direction = (pick.get("direction") or pick.get("signal_type") or "LONG").upper()
                if _direction in ("BUY",):
                    _direction = "LONG"
                elif _direction in ("SELL",):
                    _direction = "SHORT"

                # Use market data if available, otherwise skip
                _sym_df = data.get(symbol) if data else None
                if _sym_df is None or not hasattr(_sym_df, "iloc") or len(_sym_df) < 10:
                    continue

                _ez_result = _smart_entry_detector.score_entry_zone(symbol, _sym_df, direction=_direction)
                _ez_score = _ez_result.get("score", 0)
                pick["entry_zone_score"] = _ez_score
                pick["entry_zone_factors"] = _ez_result.get("factors", {})
                pick["entry_zone_recommendation"] = _ez_result.get("recommendation", "WAIT")

                current_score = pick.get("elite_score")
                if isinstance(current_score, (int, float)):
                    if _ez_score < 30:
                        pick["elite_score"] = current_score - 5
                        pick["entry_zone_note"] = f"WEAK ENTRY ZONE (score={_ez_score}), -5"
                        _sez_adjusted += 1
                    elif _ez_score > 70:
                        pick["elite_score"] = current_score + 5
                        pick["entry_zone_note"] = f"STRONG ENTRY ZONE (score={_ez_score}), +5"
                        _sez_adjusted += 1
            except Exception:
                pass  # Smart entry zone failure must never block a pick
        if _sez_adjusted > 0:
            print(f"  [SMART ENTRY] Adjusted {_sez_adjusted} picks by entry zone score")
        else:
            print(f"  [SMART ENTRY] No entry zone adjustments this cycle")
    else:
        print("  [SMART ENTRY] smart_entry module not available, skipping")

    # --- GARCH Volatility Regime Gate ---
    # Adjust elite_score and TP/SL based on GARCH(1,1) volatility forecast.
    # Only applies to crypto symbols (where vol clustering is strongest).
    if get_garch_forecast is not None:
        _garch_adjusted = 0
        _garch_symbols_cache = {}  # cache per yahoo symbol to avoid redundant downloads
        for pick in active:
            try:
                cat = pick.get("category", "")
                if cat not in ("crypto", "meme"):
                    continue
                symbol = pick.get("symbol", "")
                if not symbol:
                    continue

                # Convert to Yahoo symbol for yfinance
                yahoo_sym = _normalize_to_yahoo(symbol)

                # Fetch close prices (cached per symbol within this cycle)
                # Try Binance first (works on CI), then yfinance fallback
                if yahoo_sym not in _garch_symbols_cache:
                    _garch_symbols_cache[yahoo_sym] = None
                    # Try Binance klines (reliable on CI)
                    try:
                        _binance_sym = symbol.upper().replace('-USD', 'USDT').replace('-', '')
                        if not _binance_sym.endswith('USDT'):
                            _binance_sym += 'USDT' if 'USD' not in _binance_sym else ''
                        # Failover: shared.binance_api (multi-mirror) -> inline mirrors -> yfinance
                        _kdata = None
                        try:
                            from shared.binance_api import binance_get
                            _kdata = binance_get(
                                "/api/v3/klines",
                                params={"symbol": _binance_sym, "interval": "1d", "limit": "120"},
                            )
                        except ImportError:
                            import urllib.request as _ur
                            for _m in ["https://data-api.binance.vision", "https://api1.binance.com",
                                       "https://api2.binance.com", "https://api3.binance.com",
                                       "https://api.binance.com"]:
                                try:
                                    _kurl = f"{_m}/api/v3/klines?symbol={_binance_sym}&interval=1d&limit=120"
                                    _kreq = _ur.Request(_kurl, headers={"User-Agent": "AlphaEngine/2.0"})
                                    _kdata = json.loads(_ur.urlopen(_kreq, timeout=10).read())
                                    if _kdata:
                                        break
                                except Exception:
                                    continue
                        if _kdata and isinstance(_kdata, list) and len(_kdata) >= 50:
                            _garch_symbols_cache[yahoo_sym] = np.array([float(k[4]) for k in _kdata])
                    except Exception:
                        pass
                    # Fallback to yfinance
                    if _garch_symbols_cache[yahoo_sym] is None:
                        try:
                            _gdf = yf.download(yahoo_sym, period="120d", interval="1d",
                                               auto_adjust=True, progress=False)
                            if _gdf is not None and len(_gdf) >= 50:
                                _garch_symbols_cache[yahoo_sym] = _gdf["Close"].dropna().values.astype(float)
                        except Exception:
                            pass

                close_prices = _garch_symbols_cache.get(yahoo_sym)
                if close_prices is None or len(close_prices) < 50:
                    continue

                forecast = get_garch_forecast(close_prices, horizon=1)
                pos_mult = forecast.get("position_size_multiplier", 1.0)
                tp_sl_mult = forecast.get("tp_sl_multiplier", 1.0)
                vol_regime = forecast.get("vol_regime", "unknown")

                # --- Adjust elite_score by volatility regime ---
                current_score = pick.get("elite_score")
                if isinstance(current_score, (int, float)):
                    if pos_mult < 0.5:
                        pick["elite_score"] = current_score - 10
                        pick["garch_note"] = "GARCH: high-vol regime, reduced sizing"
                    elif pos_mult > 1.2:
                        pick["elite_score"] = current_score + 5
                        pick["garch_note"] = "GARCH: low-vol regime, favorable"
                    else:
                        pick["garch_note"] = f"GARCH: {vol_regime}, neutral"

                # --- Adjust TP/SL by tp_sl_multiplier ---
                entry = pick.get("entry_price")
                tp = pick.get("take_profit")
                sl = pick.get("stop_loss")
                direction = pick.get("direction", "long")

                if entry and tp and sl and tp_sl_mult != 1.0:
                    if direction == "long":
                        tp_dist = tp - entry
                        sl_dist = entry - sl
                        pick["take_profit"] = round(entry + tp_dist * tp_sl_mult, 8)
                        pick["stop_loss"] = round(entry - sl_dist * tp_sl_mult, 8)
                    else:  # short
                        tp_dist = entry - tp
                        sl_dist = sl - entry
                        pick["take_profit"] = round(entry - tp_dist * tp_sl_mult, 8)
                        pick["stop_loss"] = round(entry + sl_dist * tp_sl_mult, 8)

                # Annotate pick with GARCH metadata
                pick["garch_vol_regime"] = vol_regime
                pick["garch_position_mult"] = pos_mult
                pick["garch_tp_sl_mult"] = tp_sl_mult
                pick["garch_vol_ratio"] = forecast.get("vol_ratio", 1.0)

                _garch_adjusted += 1
            except Exception as _garch_err:
                pass  # GARCH failure must never block a pick

        if _garch_adjusted > 0:
            print(f"  [GARCH] Adjusted {_garch_adjusted} crypto picks by volatility regime")
    else:
        print("  [GARCH] garch_volatility module not available, skipping vol regime gate")

    # --- Execution Cost Gate ---
    # Compute net edge after all friction costs. Penalize or suppress
    # picks with insufficient edge to cover execution costs.
    if compute_net_edge is not None:
        _cost_adjusted = 0
        _cost_suppressed = 0
        _to_remove = []
        for pick in active:
            try:
                _atr_pct = None
                _atr_val = pick.get("atr_at_entry", 0)
                _entry = pick.get("entry_price", 0)
                if _atr_val and _entry and _entry > 0:
                    _atr_pct = _atr_val / _entry

                cost_result = compute_net_edge(pick, atr_pct=_atr_pct)
                net_bps = cost_result.get("net_edge_bps", 0)

                # Store cost metadata on the pick
                pick["net_edge_bps"] = net_bps
                pick["cost_breakdown"] = cost_result.get("cost_breakdown", {})
                pick["gross_edge_bps"] = cost_result.get("gross_edge_bps", 0)
                pick["total_cost_bps"] = cost_result.get("total_cost_bps", 0)

                current_score = pick.get("elite_score")

                if net_bps < 0:
                    # Negative expectancy after costs -- suppress entirely
                    _to_remove.append(pick)
                    _cost_suppressed += 1
                elif net_bps < 5:
                    # Below safety buffer -- penalize elite_score by 10
                    if isinstance(current_score, (int, float)):
                        pick["elite_score"] = current_score - 10
                        pick["cost_note"] = f"Low net edge ({net_bps:.1f} bps < 5 bps buffer), -10"
                    _cost_adjusted += 1
            except Exception:
                pass  # Execution cost failure must never block a pick

        # Remove negative-expectancy picks
        for p in _to_remove:
            if p in active:
                active.remove(p)

        if _cost_adjusted > 0 or _cost_suppressed > 0:
            print(f"  [EXEC COST] Penalized {_cost_adjusted} picks (low edge), "
                  f"suppressed {_cost_suppressed} picks (negative expectancy)")
    else:
        print("  [EXEC COST] execution_cost module not available, skipping")

    # --- Pattern Predictor: adjust elite_score based on historical pattern WR ---
    if _pattern_predictor is not None:
        # Re-train on latest closed picks if available
        try:
            _pp_closed = load_closed_picks()
            if len(_pp_closed) >= 20:
                _pattern_predictor.train(_pp_closed)
                _pattern_predictor.save()
        except Exception as _pp_train_err:
            print(f"  [PATTERN] Re-train failed (non-fatal): {_pp_train_err}")

        _pp_golden = 0
        _pp_danger = 0
        for pick in active:
            try:
                result = _pattern_predictor.predict_wr(pick)
                predicted_wr = result.get("predicted_wr")
                samples = result.get("pattern_samples", 0)

                # Store pattern metadata on pick
                pick["pattern_predicted_wr"] = predicted_wr
                pick["matching_pattern"] = result.get("matching_pattern")
                pick["pattern_samples"] = samples

                current_score = pick.get("elite_score")
                if isinstance(current_score, (int, float)) and predicted_wr is not None:
                    if predicted_wr > 0.65 and samples >= 5:
                        pick["elite_score"] = current_score + 10
                        pick["pattern_note"] = f"Golden pattern match (WR={predicted_wr:.0%}, n={samples}), +10"
                        _pp_golden += 1
                    elif predicted_wr < 0.30 and samples >= 10:
                        pick["elite_score"] = current_score - 15
                        pick["pattern_note"] = f"Danger pattern (WR={predicted_wr:.0%}, n={samples}), -15"
                        _pp_danger += 1
            except Exception:
                pass  # Pattern prediction failure must never block a pick

        if _pp_golden or _pp_danger:
            print(f"  [PATTERN] Adjusted {_pp_golden} golden (+10) and {_pp_danger} danger (-15) picks")
    else:
        print("  [PATTERN] pattern_predictor module not available, skipping")

    # --- META-LABELER: Score all active picks with P(profitable) ---
    # Uses ML model (XGBoost/RF) trained on 313+ closed picks.
    # Adds meta_label_score to each pick for elite_scorer integration.
    try:
        from meta_labeler import MetaLabeler
        _ml_labeler = MetaLabeler()
        # Try loading saved model first; retrain if not available
        if not _ml_labeler.load():
            from meta_labeler import load_all_closed_picks as _ml_load_closed
            _ml_closed = _ml_load_closed()
            _ml_metrics = _ml_labeler.train(_ml_closed)
            _ml_labeler.save()
            print(f"  [META-LABELER] Trained on {len(_ml_closed)} closed picks: "
                  f"model={_ml_labeler.model_type}, AUC={_ml_labeler.validation_auc:.4f}")
        else:
            print(f"  [META-LABELER] Loaded {_ml_labeler.model_type} model "
                  f"(AUC={_ml_labeler.validation_auc:.4f})")

        _ml_scored = 0
        _ml_high = 0
        _ml_low = 0
        for pick in active:
            _meta_prob = _ml_labeler.score_pick(pick)
            pick["meta_label_score"] = round(_meta_prob, 4)
            pick["meta_label_model"] = _ml_labeler.model_type
            _ml_scored += 1
            if _meta_prob >= 0.7:
                _ml_high += 1
            elif _meta_prob < 0.3:
                _ml_low += 1

        print(f"  [META-LABELER] Scored {_ml_scored} picks: "
              f"{_ml_high} high-conviction (>0.7), {_ml_low} low-conviction (<0.3)")
    except Exception as _meta_err:
        print(f"  [META-LABELER] Skipped (non-fatal): {_meta_err}")

    # --- QUALITY GATE: Log low-grade picks but do NOT remove ---
    # v99.0 gate at score<50 was too aggressive -- killed 52/60 picks,
    # leaving dashboard empty. Scoring is handled client-side by the
    # dashboard's Gate=Score≥24 filter. Let the user decide.
    _low_grade = [p for p in active if isinstance(p.get("elite_score"), (int, float))
                  and 0 < p["elite_score"] < 24]
    if _low_grade:
        print(f"  [GRADE INFO] {len(_low_grade)}/{len(active)} picks below score 24 "
              f"(dashboard filter will hide these)")

    # --- Feature Health Report (once per generation cycle) ---
    try:
        from feature_health import generate_health_report
        _fh_report = generate_health_report()
        _fh_score = _fh_report.get("health_score", 0)
        _fh_alive = _fh_report.get("alive_features", 0)
        _fh_total = _fh_report.get("total_features", 0)
        _fh_recs = _fh_report.get("recommendations", [])
        print(f"  [FEATURE HEALTH] Score={_fh_score:.2%} ({_fh_alive}/{_fh_total} alive)")
        if _fh_recs:
            for _rec in _fh_recs[:3]:
                print(f"    -> {_rec}")
    except Exception as _fh_err:
        print(f"  [FEATURE HEALTH] Report failed (non-fatal): {_fh_err}")

    # --- Winner Filter Summary (Task 3) ---
    print_winner_filter_summary()

    save_active_picks(active)
    print(f"  Opened {len(new_picks)} new picks. Total active: {len(active)}")


def run_tweaker(perf: dict):
    """Auto-tweak strategy parameters based on performance data."""
    print("\n[TWEAK] Analyzing strategy performance for parameter adjustments...")

    tweaks = load_tweaks()
    changes = []

    for strat, stats in perf.items():
        if stats["closed_picks"] < 5:
            continue  # Not enough data to tweak

        # Current tweaks for this strategy
        current = tweaks.get(strat, {
            "tp_multiplier_adj": 1.0,
            "sl_multiplier_adj": 1.0,
            "confidence_adj": 0.0,
            "blacklisted_symbols": [],
            "tweak_count": 0,
        })

        exits = stats.get("exit_reasons", {})
        total_exits = sum(exits.values())
        tp_hits = exits.get("TP_HIT", 0)
        sl_hits = exits.get("SL_HIT", 0)
        time_exits = exits.get("TIME_EXPIRY", 0)
        tp_rate = tp_hits / total_exits if total_exits > 0 else 0
        sl_rate = sl_hits / total_exits if total_exits > 0 else 0
        time_rate = time_exits / total_exits if total_exits > 0 else 0

        # --- TP ADJUSTMENT ---
        # If too many time expiries (TP never hit), TP is too aggressive -> tighten
        if time_rate > 0.50 and stats["closed_picks"] >= 8:
            old = current["tp_multiplier_adj"]
            current["tp_multiplier_adj"] = round(max(0.5, old * 0.85), 3)
            changes.append(f"  {strat}: TP tightened {old:.2f} -> {current['tp_multiplier_adj']:.2f} "
                           f"(time_expiry={time_rate*100:.0f}%)")

        # If TP hit rate is very high (>60%), TP may be too conservative -> widen
        elif tp_rate > 0.60 and stats.get("avg_mfe", 0) > 0:
            mfe = stats["avg_mfe"]
            old = current["tp_multiplier_adj"]
            current["tp_multiplier_adj"] = round(min(2.0, old * 1.10), 3)
            changes.append(f"  {strat}: TP widened {old:.2f} -> {current['tp_multiplier_adj']:.2f} "
                           f"(tp_rate={tp_rate*100:.0f}%, avg_mfe={mfe*100:.1f}%)")

        # --- SL ADJUSTMENT ---
        # If SL hit rate > 50%, stops are too tight -> widen
        if sl_rate > 0.50 and stats["closed_picks"] >= 8:
            old = current["sl_multiplier_adj"]
            current["sl_multiplier_adj"] = round(min(2.0, old * 1.15), 3)
            changes.append(f"  {strat}: SL widened {old:.2f} -> {current['sl_multiplier_adj']:.2f} "
                           f"(sl_rate={sl_rate*100:.0f}%)")

        # If SL hit rate is very low (<15%) and win rate is good, tighten SL for better R:R
        elif sl_rate < 0.15 and stats["win_rate"] > 0.55:
            old = current["sl_multiplier_adj"]
            current["sl_multiplier_adj"] = round(max(0.5, old * 0.90), 3)
            changes.append(f"  {strat}: SL tightened {old:.2f} -> {current['sl_multiplier_adj']:.2f} "
                           f"(sl_rate={sl_rate*100:.0f}%, wr={stats['win_rate']*100:.0f}%)")

        # --- CONFIDENCE ADJUSTMENT ---
        if stats["win_rate"] > 0.60 and stats["sharpe"] > 0.8:
            current["confidence_adj"] = round(min(0.15, current.get("confidence_adj", 0) + 0.02), 3)
        elif stats["win_rate"] < 0.35:
            current["confidence_adj"] = round(max(-0.20, current.get("confidence_adj", 0) - 0.03), 3)

        # --- SYMBOL BLACKLISTING ---
        by_symbol = stats.get("by_symbol", {})
        for sym, sym_stats in by_symbol.items():
            total_sym = sym_stats.get("wins", 0) + sym_stats.get("losses", 0)
            if total_sym >= 3 and sym_stats.get("wins", 0) == 0:
                if sym not in current.get("blacklisted_symbols", []):
                    current.setdefault("blacklisted_symbols", []).append(sym)
                    changes.append(f"  {strat}: Blacklisted {sym} "
                                   f"(0/{total_sym} wins)")

        current["tweak_count"] = current.get("tweak_count", 0) + 1
        current["last_tweaked"] = _now_iso()
        tweaks[strat] = current

    # Save tweaks
    tweaks["_meta"] = {
        "last_run": _now_iso(),
        "total_changes": len(changes),
    }
    with open(TWEAKS_PATH, "w") as f:
        json.dump(tweaks, f, indent=2)

    if changes:
        for c in changes:
            print(c)
    else:
        print("  No parameter adjustments needed this cycle.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ALPHA ENGINE Forward Validator")
    parser.add_argument("--generate", action="store_true", help="Generate new picks")
    parser.add_argument("--report", action="store_true", help="Performance report only")
    parser.add_argument("--full-cycle", action="store_true", help="Generate + validate + tweak")
    args = parser.parse_args()

    start = time.time()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.report:
        perf = load_strategy_performance()
        active = load_active_picks()
        print_performance_report(perf, len(active))
        return

    if args.full_cycle or not args.generate:
        # Validate existing picks
        newly_closed, perf = run_validation()

        # Tweak parameters based on outcomes
        if perf:
            run_tweaker(perf)

    if args.full_cycle or args.generate:
        # Generate new picks
        run_generation()

    # Final report
    perf = load_strategy_performance()
    active = load_active_picks()
    print_performance_report(perf, len(active))

    elapsed = time.time() - start
    print(f"\nForward validator completed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
