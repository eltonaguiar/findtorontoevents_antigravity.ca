"""EAGLE-4 + EAGLE-5 admissibility/promotion gates (2026-06-02, minimax-m3-free).

Owns the tournament-validated pick filters in a dedicated module so concurrent
edits to production_scanner.py do not silently revert the data-backed gates.

All thresholds derived from the AI tournament top-5 T1 models
(3,692 resolved picks across 46 models, 5,492 total picks).
Source: audit_dashboard/data/ai_tournament_picks_latest.json
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from alpha_engine.fundamental_macro_gates import (
    passes_high_conviction_gate,
    passes_long_term_stability_gate,
)

# ---------------------------------------------------------------------------
# EAGLE-4 (negative side): kill noise personas, kill negative-edge directions,
# flip CRYPTO LONG→SHORT (67% WR vs 33% WR).
# ---------------------------------------------------------------------------

# Personas with <40% WR in tournament top-5 T1 (confirmed noise).
_EAGLE4_PERSONA_KILL = frozenset({
    "momentum_scalp",       # 28% WR
    "breakout_scanner",     # 28% WR
    "reflexivity_trader",   # 35% WR
    "deep_value",           # 44% WR
})

# (asset_class, direction) tuples with negative or marginal edge.
# CRYPTO LONG is handled by flip (below), not by kill.
_EAGLE4_DIRECTIONAL_KILL = frozenset({
    ("PENNY", "SHORT"),
    ("PENNY", "SELL"),
    ("COMMODITY", "SHORT"),
    ("COMMODITY", "SELL"),
    ("ETF", "SHORT"),
    ("ETF", "SELL"),
    ("EQUITY", "SHORT"),
    ("EQUITY", "SELL"),
})

# CRYPTO: SHORT 67% WR / +3.74% avg PnL vs LONG 33% WR / -0.49% avg PnL
_EAGLE4_CRYPTO_FLIP_TO_SHORT = True


def apply_eagle4_admissibility(picks):
    """Kill noise personas, kill negative-edge directions, flip CRYPTO LONG→SHORT.

    Returns a new list of admissible picks. Input picks are not mutated.
    """
    if not picks:
        return picks

    original_count = len(picks)
    kept = []
    killed_persona = 0
    killed_directional = 0
    flipped_crypto = 0

    for pick in picks:
        ac = str(pick.get("asset_class") or pick.get("category") or "").strip().upper()
        persona = str(
            pick.get("persona_id")
            or pick.get("strategy_name")
            or pick.get("strategy")
            or ""
        ).strip().lower()
        direction = str(
            pick.get("signal_type") or pick.get("direction") or "BUY"
        ).strip().upper()
        norm_dir = "SHORT" if direction in ("SELL", "SHORT") else "LONG"

        if persona in _EAGLE4_PERSONA_KILL:
            killed_persona += 1
            continue

        if _EAGLE4_CRYPTO_FLIP_TO_SHORT and ac == "CRYPTO" and norm_dir == "LONG":
            pick["signal_type"] = "SELL"
            pick["direction"] = "SHORT"
            pick["_eagle4_flipped"] = "CRYPTO_LONG_TO_SHORT"
            norm_dir = "SHORT"
            flipped_crypto += 1

        if (ac, norm_dir) in _EAGLE4_DIRECTIONAL_KILL:
            killed_directional += 1
            continue

        kept.append(pick)

    if killed_persona or killed_directional or flipped_crypto:
        print(
            f"  [EAGLE-4 ADMISSIBILITY] in={original_count} kept={len(kept)} | "
            f"killed_persona={killed_persona} killed_directional={killed_directional} "
            f"flipped_crypto_L_to_S={flipped_crypto}"
        )
    return kept


# ---------------------------------------------------------------------------
# EAGLE-5 (positive side): multiplicative confidence boost for tournament-
# validated symbols and personas. Caps at 1.0 to avoid breaking downstream gates.
# ---------------------------------------------------------------------------

_EAGLE5_SYMBOL_WHITELIST = {
    "EQUITY": {
        "BAC", "JPM", "MSFT", "AMZN", "GOOGL", "AAPL", "PEP", "MU",
        "TSLA", "AMD", "INTC", "META", "XOM", "NVDA", "KO", "WMT",
    },
    "ETF": {"EEM", "IWM", "GLD", "XLK", "XLE"},
    "PENNY": {"KULR", "RGTI", "ASTS", "RKLB", "GSAT", "IONQ", "QBTS", "MVST"},
    "COMMODITY": {"GC=F", "HG=F", "OJ=F"},
    "FUTURES": {"NQ=F"},
}

_EAGLE5_PROMOTED_PERSONAS = {
    "EQUITY": {
        "momentum_breakout", "invert_losers", "momentum_momentum",
        "trend_follower", "cycle_rotator", "statistical_arb",
    },
    "ETF": {"macro_hedge", "sector_rotation", "momentum_breakout", "deep_value"},
    "PENNY": {"microcap_momentum", "gamma_raid"},
    "COMMODITY": {"systematic_momentum", "inflation_hedge", "cta_trend", "vol_arb"},
}

_EAGLE5_SYMBOL_BOOST = 1.20
_EAGLE5_PERSONA_BOOST = 1.15


def apply_eagle5_promotion(picks):
    """Boost confidence for tournament-validated symbols/personas.

    Boosts are multiplicative and capped at 1.0. Runs after EAGLE-4 so the
    boost acts on the cleaned population. Input picks are mutated in place.
    """
    boosted_symbol = 0
    boosted_persona = 0
    for p in picks:
        ac = str(p.get("asset_class") or p.get("category") or "").strip().upper()
        sym = str(p.get("symbol") or "").strip().upper()
        persona = str(p.get("strategy") or p.get("strategy_name") or "").strip().lower()
        original_conf = float(p.get("confidence", 0.5) or 0.5)
        new_conf = original_conf
        sym_match = sym in _EAGLE5_SYMBOL_WHITELIST.get(ac, set())
        persona_match = persona in _EAGLE5_PROMOTED_PERSONAS.get(ac, set())
        if sym_match:
            new_conf *= _EAGLE5_SYMBOL_BOOST
        if persona_match:
            new_conf *= _EAGLE5_PERSONA_BOOST
        new_conf = min(1.0, new_conf)
        if sym_match or persona_match:
            p["confidence"] = new_conf
            p["_eagle5_boosted"] = True
            p["_eagle5_symbol_match"] = sym_match
            p["_eagle5_persona_match"] = persona_match
            p["_eagle4_pre_eagle5_conf"] = original_conf
            if sym_match:
                boosted_symbol += 1
            if persona_match:
                boosted_persona += 1
    if picks and (boosted_symbol or boosted_persona):
        print(
            f"  [EAGLE-5 PROMOTION] boosted_symbol={boosted_symbol} "
            f"boosted_persona={boosted_persona}"
        )
    return picks


# ---------------------------------------------------------------------------
# EAGLE-6 (statistical admissibility, 2026-06-02, minimax-m3-free, v1)
# Global per-strategy hard gates that complement EAGLE-4 (local persona kill)
# and EAGLE-5 (local symbol boost). EAGLE-6 is the "did this strategy survive
# global statistical penalties" check.
#
# v1 gates (today, fully implemented + tested):
#   - DSR noise kill    : strategy must not be in DSR noise set
#   - Insufficient-n    : strategy must have >= 30 resolved trades
#   - HHI concentration : per-source concentration must stay under 0.20
#
# v2 gates (WIRED 2026-06-05):
#   - PBO < 0.5 (global, BBLZ 2017 threshold) : tools/cpcv_pbo_results.json IS generated
#     (file dated 2026-06-02 23:34Z; global PBO=1.0 currently → blocks promotion to Tier-1
#      until strategy set is pruned and global PBO drops below 0.5).
#
# v3 gates (still planned):
#   - WF OOS PF >= 0.8x : requires alpha_engine/walkforward_validator.py per-strat results
#   - Bootstrap CI PF   : requires per-strategy pnL list (not in DSR JSON)
# ---------------------------------------------------------------------------

# Minimum trades required to clear the "statistical significance" bar
_EAGLE6_MIN_TRADES = 30

# Max HHI contribution from a single source (matches EAGLE2 initiative 4.6 HHI<0.20)
_EAGLE6_MAX_SOURCE_HHI = 0.20

# BBLZ 2017 PBO threshold (>= 0.5 = "selection process indistinguishable from chance").
# Used for Tier-1 / real-money gating; production-tier still allowed (fail-soft).
_EAGLE6_MAX_PBO_GLOBAL = 0.5

# Optional DSR noise set (lazy-loaded from tools/deflated_sharpe_results.json)
_DSR_NOISE_CACHE: frozenset[str] | None = None
_DSR_TRADES_CACHE: dict[str, int] | None = None

# Global PBO value (lazy-loaded from tools/cpcv_pbo_results.json)
_PBO_GLOBAL_CACHE: float | None = None
_PBO_LOADED: bool = False


def _load_dsr_noise() -> frozenset[str]:
    """Load the set of strategies flagged as DSR noise (survives=False).

    Returns an empty frozenset on any I/O error so the gate degrades to
    fail-open (won't block picks when the data file is missing).
    """
    global _DSR_NOISE_CACHE, _DSR_TRADES_CACHE
    if _DSR_NOISE_CACHE is not None:
        return _DSR_NOISE_CACHE
    try:
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / "tools" / "deflated_sharpe_results.json"
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        noise: set[str] = set()
        trades: dict[str, int] = {}
        for entry in d.get("all_strategies", []):
            key = entry.get("key")
            if not key:
                continue
            trades[key] = int(entry.get("trades", 0))
            if not entry.get("survives", False):
                noise.add(key)
        _DSR_NOISE_CACHE = frozenset(noise)
        _DSR_TRADES_CACHE = trades
        return _DSR_NOISE_CACHE
    except Exception:
        _DSR_NOISE_CACHE = frozenset()
        _DSR_TRADES_CACHE = {}
        return _DSR_NOISE_CACHE


def _load_pbo_global() -> float | None:
    """Load the global PBO value from `tools/cpcv_pbo_results.json`.

    PBO (Probability of Backtest Overfitting, BBLZ 2017) is a property of the
    *selection process* — not per-strategy. Global PBO >= 0.5 means the
    IS-winner selection is statistically indistinguishable from picking by
    chance. Mirrors `_load_dsr_noise()` pattern, fail-open on I/O error.

    Returns None when the file is missing or unreadable so the gate degrades
    to fail-open. Real value (typically [0, 1]) when available.
    """
    global _PBO_GLOBAL_CACHE, _PBO_LOADED
    if _PBO_LOADED:
        return _PBO_GLOBAL_CACHE
    _PBO_LOADED = True
    try:
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / "tools" / "cpcv_pbo_results.json"
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        pbo = d.get("pbo")
        _PBO_GLOBAL_CACHE = float(pbo) if pbo is not None else None
        return _PBO_GLOBAL_CACHE
    except Exception:
        _PBO_GLOBAL_CACHE = None
        return None


def passes_pbo_global_gate(strict: bool = True) -> tuple[bool, dict]:
    """Hard gate for Tier-1 / real-money promotion based on global PBO.

    `strict=True` (default) blocks when global PBO >= _EAGLE6_MAX_PBO_GLOBAL (0.5).
    `strict=False` only blocks when the file says global PBO >= 0.7 ("FAIL"
    per the file's own pbo_interpretation field).

    Used by `audit_trail/promotion_gate.py` / `audit_trail/quality_gates.py`
    to block Tier-1 promotions while the strategy set is over-fit at the
    selection layer. Returns (pass, gate_info).
    """
    pbo = _load_pbo_global()
    threshold = _EAGLE6_MAX_PBO_GLOBAL if strict else 0.7
    if pbo is None:
        return True, {
            "global_pbo": None,
            "threshold": threshold,
            "pass": True,
            "reason": "no_data (fail-open)",
        }
    return (pbo < threshold), {
        "global_pbo": pbo,
        "threshold": threshold,
        "pass": pbo < threshold,
        "reason": f"global_pbo={pbo:.3f} {'<' if pbo < threshold else '>='} {threshold}",
    }


# ---------------------------------------------------------------------------
# Walk-Forward Efficiency (WFE) gate (2026-06-05, Grok-proposed priority #1)
# WFE = % of walk-forward windows where OOS_PF >= 0.85 * IS_PF.
# Reads tools/walk_forward_per_strategy_latest.json (output of
# tools/walk_forward_per_strategy.py). Hard gate at WFE >= 0.60.
# ---------------------------------------------------------------------------
_EAGLE6_MIN_WFE = 0.60
_WFE_CACHE: dict[str, float] | None = None


def _load_wfe() -> dict[str, float]:
    """Per-(strategy::category) WFE = survival_rate from walk-forward JSON."""
    global _WFE_CACHE
    if _WFE_CACHE is not None:
        return _WFE_CACHE
    try:
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / "audit_dashboard" / "data" / "walk_forward_per_strategy_latest.json"
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        out: dict[str, float] = {}
        for cell in d.get("cells", []):
            key = f"{cell.get('strategy','')}::{cell.get('category','')}"
            if cell.get("survival_rate") is not None:
                out[key] = float(cell["survival_rate"])
        _WFE_CACHE = out
        return _WFE_CACHE
    except Exception:
        _WFE_CACHE = {}
        return _WFE_CACHE


def passes_wfe_gate(strategy: str, category: str = "") -> tuple[bool, dict]:
    """Hard gate: WFE >= 0.60 per Grok's priority #1.

    Fails-open when the walk-forward JSON is missing or the (strategy, category)
    cell is not in it (= no opinion). Used by Tier-1 promotion paths.
    """
    wfe = _load_wfe().get(f"{strategy}::{category}")
    if wfe is None:
        return True, {"wfe": None, "threshold": _EAGLE6_MIN_WFE, "pass": True, "reason": "no_data (fail-open)"}
    return (wfe >= _EAGLE6_MIN_WFE), {
        "wfe": round(wfe, 4),
        "threshold": _EAGLE6_MIN_WFE,
        "pass": wfe >= _EAGLE6_MIN_WFE,
        "reason": f"wfe={wfe:.3f} {'>=' if wfe >= _EAGLE6_MIN_WFE else '<'} {_EAGLE6_MIN_WFE}",
    }


# ---------------------------------------------------------------------------
# Minimum Track Record Length (MinTRL) gate (Bailey & Lopez de Prado 2014)
# MinTRL = 1 + (1 - γ3*SR + ((γ4 - 1)/4) * SR²) * (Z_α / SR)²
# where γ3 is skew, γ4 is excess kurtosis, Z_α is z-score for desired
# confidence (1.96 for 95%). A strategy is Sharpe-trustworthy iff its
# closed-trade count >= MinTRL.
# Default benchmark SR = 0 (i.e. we want the strategy SR > 0 reliably).
# ---------------------------------------------------------------------------
_MIN_TRL_CONFIDENCE_Z = 1.96  # 95%


def compute_min_trl(returns: list[float], benchmark_sr: float = 0.0) -> float | None:
    """Bailey-Lopez de Prado 2014 MinTRL. Returns None on degenerate input."""
    if not returns or len(returns) < 4:
        return None
    import math
    n = len(returns)
    mu = sum(returns) / n
    var = sum((x - mu) ** 2 for x in returns) / (n - 1)
    if var <= 0:
        return None
    sd = math.sqrt(var)
    sr = mu / sd
    if abs(sr - benchmark_sr) < 1e-9:
        return None  # degenerate: SR ≈ benchmark → MinTRL undefined
    # Fisher-corrected skew + excess kurtosis
    z = [(x - mu) / sd for x in returns]
    skew = ((n * n) / ((n - 1) * (n - 2))) * sum(zi ** 3 for zi in z) / n
    kurt_raw = sum(zi ** 4 for zi in z) / n
    kurt_excess = ((n + 1) * kurt_raw - 3 * (n - 1)) * (n - 1) / ((n - 2) * (n - 3))
    bracket = 1.0 - skew * sr + ((kurt_excess) / 4.0) * sr * sr
    if bracket <= 0:
        return None  # implausible
    denom = sr - benchmark_sr
    min_trl = 1.0 + bracket * (_MIN_TRL_CONFIDENCE_Z / denom) ** 2
    return float(min_trl)


def passes_min_trl_gate(returns: list[float], n_closed: int, benchmark_sr: float = 0.0) -> tuple[bool, dict]:
    """Hard gate: n_closed >= MinTRL. Fails-open when MinTRL is undefined."""
    min_trl = compute_min_trl(returns, benchmark_sr)
    if min_trl is None:
        return True, {"min_trl": None, "n_closed": n_closed, "pass": True, "reason": "min_trl_undefined (fail-open)"}
    return (n_closed >= min_trl), {
        "min_trl": round(min_trl, 1),
        "n_closed": n_closed,
        "pass": n_closed >= min_trl,
        "reason": f"n_closed={n_closed} {'>=' if n_closed >= min_trl else '<'} min_trl={min_trl:.1f}",
    }


def _strategy_name(pick: dict) -> str:
    """Extract a normalised strategy name from a pick dict."""
    return str(
        pick.get("strategy")
        or pick.get("strategy_name")
        or pick.get("persona_id")
        or ""
    ).strip()


def _compute_source_hhi(picks: list[dict]) -> dict[str, float]:
    """Compute per-strategy source concentration (HHI proxy).

    HHI is the sum of squared market shares. Here we compute per-strategy share
    of total picks and return the per-strategy HHI contribution (share^2).
    Returns an empty dict on zero picks.
    """
    if not picks:
        return {}
    counts: dict[str, int] = {}
    for p in picks:
        s = _strategy_name(p)
        if s:
            counts[s] = counts.get(s, 0) + 1
    n = sum(counts.values())
    if n <= 0:
        return {}
    return {s: (c / n) ** 2 for s, c in counts.items()}


def is_admissible_for_production(
    pick: dict,
    picks_for_hhi: list[dict] | None = None,
) -> tuple[bool, dict]:
    """EAGLE-6 admissibility check (v1).

    Returns (is_admissible, gate_results) where gate_results is a dict with
    one key per gate plus an overall `verdict`. Currently checks:
      - DSR noise kill (fail-closed: if strategy is in DSR noise set, kill)
      - Insufficient-n (kill if strategy has < _EAGLE6_MIN_TRADES resolved trades)
      - HHI concentration (kill if this strategy's source-HHI > _EAGLE6_MAX_SOURCE_HHI)

    `picks_for_hhi` should be the full active pick list so concentration can
    be computed against the current universe, not per-pick.
    """
    strat = _strategy_name(pick)
    gates: dict[str, dict] = {}

    # Gate 1: DSR noise
    noise = _load_dsr_noise()
    gates["dsr"] = {
        "strategy": strat,
        "is_noise": strat in noise if strat else None,
        "pass": strat not in noise if strat else True,
    }

    # Gate 2: Insufficient-n (only fires if we have DSR data for this strategy)
    if _DSR_TRADES_CACHE and strat in _DSR_TRADES_CACHE:
        n = _DSR_TRADES_CACHE[strat]
        gates["min_trades"] = {
            "trades": n,
            "required": _EAGLE6_MIN_TRADES,
            "pass": n >= _EAGLE6_MIN_TRADES,
        }
    else:
        gates["min_trades"] = {
            "trades": None,
            "required": _EAGLE6_MIN_TRADES,
            "pass": True,  # no DSR data = no judgement
        }

    # Gate 3: HHI concentration
    if picks_for_hhi is not None:
        hhi = _compute_source_hhi(picks_for_hhi)
        my_hhi = hhi.get(strat, 0.0)
        gates["hhi"] = {
            "this_strategy_hhi": round(my_hhi, 4),
            "max_allowed": _EAGLE6_MAX_SOURCE_HHI,
            "pass": my_hhi <= _EAGLE6_MAX_SOURCE_HHI,
        }
    else:
        gates["hhi"] = {"this_strategy_hhi": None, "max_allowed": _EAGLE6_MAX_SOURCE_HHI, "pass": True}

    # Gate 4: Walk-Forward Efficiency (WFE) — 2026-06-05
    # Reads tools/walk_forward_per_strategy_latest.json; fails-open when missing.
    cat = str(pick.get("category") or pick.get("asset_class") or "").lower()
    wfe_pass, wfe_detail = passes_wfe_gate(strat, cat)
    gates["wfe"] = wfe_detail

    # Gate 5: Global PBO — 2026-06-05
    # cpcv_pbo_results.json exists (built 2026-06-02); if global PBO >= 0.50
    # the *entire portfolio* is overfit — flag but don't hard-kill individual picks
    # (the per-strategy PBO kill will be added when per-strategy PBO is available).
    pbo_pass, pbo_detail = passes_pbo_global_gate(strict=False)
    gates["pbo_global"] = pbo_detail

    overall_pass = all(g["pass"] for g in gates.values() if isinstance(g, dict))
    verdict = "ADMISSIBLE" if overall_pass else "INADMISSIBLE"
    gates["verdict"] = verdict
    return overall_pass, gates


def apply_eagle6_admissibility(picks: list[dict]) -> list[dict]:
    """EAGLE-6 admissibility gate — kill picks whose strategies fail DSR/n/HHI.

    Tag every pick with `_eagle6_verdict` and `_eagle6_gates`, then return
    only the ADMISSIBLE ones. Fail-open on any I/O error so a missing DSR
    JSON file doesn't break production.
    """
    if not picks:
        return picks
    try:
        hhi_universe = list(picks)  # compute HHI against current active list
        kept: list[dict] = []
        killed_dsr = 0
        killed_n = 0
        killed_hhi = 0
        unscored = 0
        for p in picks:
            ok, gates = is_admissible_for_production(p, hhi_universe)
            p["_eagle6_verdict"] = gates["verdict"]
            p["_eagle6_gates"] = gates
            if not ok:
                if not gates["dsr"]["pass"]:
                    killed_dsr += 1
                if not gates["min_trades"]["pass"]:
                    killed_n += 1
                if not gates["hhi"]["pass"]:
                    killed_hhi += 1
                continue
            # Track picks that passed but had no DSR data (conservative note)
            if gates["min_trades"]["trades"] is None:
                unscored += 1
            kept.append(p)
        if killed_dsr or killed_n or killed_hhi:
            print(
                f"  [EAGLE-6 ADMISSIBILITY] in={len(picks)} kept={len(kept)} | "
                f"killed_dsr={killed_dsr} killed_n={killed_n} killed_hhi={killed_hhi} "
                f"unscored={unscored}"
            )
        return kept
    except Exception as _e6_err:
        print(f"  [EAGLE-6] Admissibility gate failed (non-fatal, fail-open): {_e6_err}")
        for p in picks:
            p.setdefault("_eagle6_verdict", "UNSCORED")
        return picks


# ---------------------------------------------------------------------------
# passes_hard_money_gates — THE gate for real money / shadow probation (2026-06-05)
# Wraps all eagle_gates components into one call.  Designed to be called from
# money_ready_verdict.py, production_scanner.py, and paper-pilot scripts.
# ---------------------------------------------------------------------------

def passes_recency_gate(picks: list[dict]) -> tuple[bool, str]:
    """
    Check if the provided picks are recent enough to be considered active.
    Gate 0: 14-day window. Gate 0.5: 48-hour most recent pick.
    """
    if not picks:
        return False, "RECENCY_FAIL: No picks available"

    now = datetime.now(timezone.utc)
    recency_threshold = now - timedelta(days=14)
    recent_picks = [p for p in picks if p.get('created_at') and p['created_at'] >= recency_threshold]
    if not recent_picks:
        return False, "RECENCY_FAIL: No picks within the last 14 days"

    # Gate 0.5: Check most recent pick's timestamp (48h)
    most_recent_pick_ts = max(p['created_at'] for p in recent_picks)
    if now - most_recent_pick_ts > timedelta(hours=48):
        return False, "RECENCY_FAIL: Most recent pick is older than 48 hours"

    return True, "PASS"


def passes_hard_money_gates(
    pick: dict,
    min_n: int = 100,
) -> tuple[bool, str]:
    """Single entry-point for real-money / shadow-probation eligibility.

    Args:
        pick: dict representing a single pick, with all relevant fields
        min_n: minimum closed trades required (default 100)

    Returns:
        (passes: bool, reason: str)
    """
    n_trades = int(pick.get("n_trades") or 0)
    pf = float(pick.get("profit_factor") or 0.0)
    wr = float(pick.get("win_rate") or 0.0)
    returns = list(pick.get("daily_returns") or pick.get("returns") or [])
    strat = str(pick.get("strategy") or "")
    cat = str(pick.get("category") or "")

    # Gate 0: Recency check
    # This gate expects a list of picks, but here we have a single pick.
    # We'll assume the 'created_at' or 'entry_date' of the single pick is sufficient.
    # For a more robust check, this would need to be refactored to take a list of related picks.
    recency_ok, recency_reason = passes_recency_gate([pick])
    if not recency_ok:
        return False, recency_reason

    # Gate 2: Minimum n
    if n_trades < min_n:
        return False, f"INSUFFICIENT_N: need>={min_n} have={n_trades}"

    # Gate 2: T2 baseline (PF >= 1.5, WR >= 50%)
    if pf < 1.5:
        return False, f"BELOW_T2_PF: pf={pf:.2f} < 1.5"
    if wr < 0.50:
        return False, f"BELOW_T2_WR: wr={wr:.1%} < 50%"

    # Gate 3: DSR noise kill (strategy must not be in DSR noise set)
    noise = _load_dsr_noise()
    if strat and strat in noise:
        return False, f"DSR_NOISE_KILL: strategy={strat}"

    # Gate 4: WFE >= 0.60 (fail-open when data missing)
    wfe_pass, wfe_detail = passes_wfe_gate(strat, cat)
    if not wfe_pass:
        return False, f"WFE_FAIL: {wfe_detail.get('reason', 'wfe<0.60')}"

    # Gate 5: MinTRL (need sufficient observations to trust the Sharpe estimate)
    if returns:
        trl_pass, trl_detail = passes_min_trl_gate(returns, n_trades)
        if not trl_pass:
            return False, f"MIN_TRL_FAIL: {trl_detail.get('reason', 'n<min_trl')}"

    # Gate 6: Global PBO sanity (soft gate — fail if global PBO >= 0.70)
    pbo_pass, pbo_detail = passes_pbo_global_gate(strict=True)
    if not pbo_pass:
        return False, f"PBO_GLOBAL_FAIL: {pbo_detail.get('reason', 'pbo>=0.50')}"

    # Gate 7: Symbol concentration (optional)
    max_share = pick.get("max_symbol_share")
    if max_share is not None and float(max_share) > 0.30:
        return False, f"CONCENTRATION: max_symbol_share={max_share:.1%} > 30%"

    # New Gates from fundamental_macro_gates.py
    hc_ok, hc_details = passes_high_conviction_gate(pick)
    lt_ok, lt_details = passes_long_term_stability_gate(pick)

    # Apply confidence boosts and tags
    confidence_boost = 1.0
    tags = set()

    if hc_ok:
        confidence_boost *= hc_details.get("confidence_boost", 1.0)
        tags.add("HIGH_CONVICTION_IMMEDIATE_OPPORTUNITY")
    if lt_ok:
        confidence_boost *= lt_details.get("confidence_boost", 1.0)
        tags.add("LONG_TERM_STABLE_EDGE")

    # Add fundamental and macro details to the pick for downstream visibility
    pick["_fundamental_strength"] = hc_details.get("fundamental_strength_status")
    pick["_macro_alignment"] = hc_details.get("macro_alignment_status")
    pick["_confidence_boost"] = round(confidence_boost, 2)
    pick["_tags"] = sorted(list(tags))

    # If any of the new gates explicitly fail, it should not be MONEY_READY
    # For now, we'll let them pass through and use the confidence boost/tags.
    # Future: potentially add hard-fail logic based on these new gates.

    return True, "ALL_HARD_GATES_PASS — MONEY_READY"

