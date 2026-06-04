"""
M-061: Unified money_ready_verdict() — wires DSR + PBO/CSCV + SPA into one per-class verdict.

Returns a per-asset-class readiness dict:
    {
        "COMMODITY": {
            "dsr_ok": True,
            "pbo_ok": True,
            "spa_ok": True,
            "n_ok": True,
            "n_resolved": 750,
            "verdict": "MONEY_READY",   # MONEY_READY | WATCH | NOT_READY | INSUFFICIENT_DATA
            "details": {...}
        },
        ...
    }

Verdicts:
    MONEY_READY     — all applicable gates pass (n_ok + at least dsr_ok or spa_ok)
    WATCH           — enough data, mixed signals (e.g. n_ok but pbo failed)
    NOT_READY       — enough data, edge not confirmed
    INSUFFICIENT_DATA — too few resolved picks for statistical testing

Usage:
    python alpha_engine/money_ready_verdict.py               # print report
    python alpha_engine/money_ready_verdict.py --json        # JSON output
    python alpha_engine/money_ready_verdict.py --class COMMODITY
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

# P1/#7 — Net-of-cost slippage / expectancy promotion gate.
# ENFORCED by default (2026-05-19, swarm-settled Q1 verdict): the net-of-slippage
# expectancy gate is now the real money-ready promotion gate — a negative
# expectancy hard-downgrades MONEY_READY -> NOT_READY. Set
# SLIPPAGE_PROMOTION_GATE_ENABLED=0 to disable. Monotone-conservative: only ever
# downgrades, never promotes.
_SLIPPAGE_GATE_ENABLED: bool = (
    os.environ.get("SLIPPAGE_PROMOTION_GATE_ENABLED", "1").strip().lower()
    in ("1", "true", "yes", "on")
)

# M-105 — ml_enhanced family quarantine for CRYPTO.
# Default shadow (OFF): stamps `_ml_enhanced_quarantine_recommend` on CRYPTO verdict.
# The ml_enhanced family has 112+ variants; only 4 have n>=20 for per-variant SPA.
# Aggregate PF=2.83 on surviving 281 picks is selection-biased (blocked bad actors).
# Set ML_ENHANCED_CRYPTO_QUARANTINE=1 to exclude the entire ml_enhanced family from
# CRYPTO money_ready_verdict until each variant passes per-variant SPA (n>=20).
# Downgrade effect: CRYPTO → NOT_READY (only 10 non-ml picks remaining).
# Needs operator go/no-go before enforcing — see MASTER_ACTION_PLAN M-105.
_ML_ENHANCED_CRYPTO_QUARANTINE: bool = (
    os.environ.get("ML_ENHANCED_CRYPTO_QUARANTINE", "0").strip().lower()
    in ("1", "true", "yes", "on")
)
# Prefix used to identify the ml_enhanced family
_ML_ENHANCED_PREFIX = "ml_enhanced_"

# I-3 — MDD ≤ 20% + CVaR tail-risk gate.
# Default shadow (OFF): stamps `_mdd_cvar_recommend` on verdicts that fail this gate.
# Hard lesson: 1 bad trade at rapid_fire → 69% MDD — positive Kelly does NOT protect
# against catastrophic runs. This gate downgrades MONEY_READY → NOT_READY when the
# class's resolved-pick equity curve has a rolling MDD > MDD_GATE_THRESHOLD or
# CVaR-95% tail loss > CVAR_GATE_THRESHOLD_PCT.
# Set MDD_GATE_ENFORCE=0 to disable.  Enforced by default since 2026-05-19.
# 3-engine swarm (DeepSeek/Mercury-2/Ring-2.6-1T) unanimous: enforce with per-class caps.
_MDD_GATE_ENFORCE: bool = (
    os.environ.get("MDD_GATE_ENFORCE", "1").strip().lower()
    in ("1", "true", "yes", "on")
)
MDD_GATE_THRESHOLD: float = 0.20   # 20% max drawdown per charter (default)
# Per-class MDD overrides: CTA-style trend-following funds have structurally higher
# drawdown profiles (SocGen CTA Index historical MDD: 30-50%).  COMMODITY=55% is the
# institutional CTA band ceiling; still acts as a meaningful guardrail vs 100% free-run.
MDD_GATE_THRESHOLD_BY_CLASS: dict[str, float] = {
    "COMMODITY": 0.55,   # CTA institutional norm; confirmed by 3-engine swarm 2026-05-19
}
CVAR_GATE_THRESHOLD_PCT: float = 10.0  # CVaR-95% must be < 10% absolute loss

REPO_ROOT = Path(__file__).parent.parent
# Ensure repo root and alpha_engine dir are importable regardless of how this file is invoked
import sys as _sys
for _p in [str(REPO_ROOT), str(Path(__file__).parent)]:
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
CLOSED_PATH = REPO_ROOT / "alpha_engine/data/closed_picks.json"
DASHBOARD_PATH = REPO_ROOT / "audit_dashboard/data/dashboard_data.json"
GATES_PATH = REPO_ROOT / "audit_trail/quality_gates.py"

# ---------------------------------------------------------------------------
# Canonical row pipeline (2026-05-19, swarm-debated — deepseek/xai 3-round).
#
# The Money-Ready verdict MUST read the same deduped, policy-clean per-pick
# rows that feed audit_dashboard/data/pf_registry.json. Previously this file
# read closed_picks.json directly with its own strategy filter, producing a
# small non-representative subset (CRYPTO n=292, PF 2.61) that contradicted
# the canonical registry (CRYPTO n=1673, PF 1.21) — a live falsehood on the
# /audit Money-Ready surface (caught by tools/ci_gate_money_ready_vs_registry).
#
# build_pf_registry exposes the exact pipeline:
#   load_rows()        -> all SOURCE_FILES raw rows (wider than closed_picks)
#   classify_rows()    -> dedup re-emissions + drop flicker + closed-only
#   _is_policy_excluded-> Layer 1/2/3 exclusion (PERMANENTLY_KILLED,
#                         BLOCKED_SOURCE_SYSTEMS, PF_REGISTRY_POLICY_EXCLUDED,
#                         BLOCKED_DIRECTION_TRIPLES, BLOCKED_ASSET_STRATEGY_PAIRS).
# Layer 3 already applies the 119 BLOCKED_ASSET_STRATEGY_PAIRS, so this file's
# old per-class strategy filter was redundant and has been removed.
# build_pf_registry is imported lazily inside _load_picks() — a module-level
# import here triggers a circular import (build_pf_registry -> audit_trail
# -> ... chain). Lazy import runs after every module is fully initialized.
sys.path.insert(0, str(REPO_ROOT / "tools"))


def _canonical_pipeline():
    """Lazily import the build_pf_registry pipeline. Returns the 4-tuple of
    callables, or None if unavailable (caller falls back to the legacy loader)."""
    try:
        from build_pf_registry import (  # type: ignore
            load_rows, classify_rows, _is_policy_excluded, _asset_class,
        )
        return load_rows, classify_rows, _is_policy_excluded, _asset_class
    except Exception as exc:  # noqa: BLE001 — fail-open to the legacy loader
        print(f"WARN: build_pf_registry pipeline unavailable ({exc}); "
              f"money_ready_verdict falling back to closed_picks.json",
              file=sys.stderr)
        return None

# Tier-2 floors per PERFORMANCE_CHARTER.md
MIN_N_CLASS = 50          # minimum resolved picks for a class verdict
MIN_WR = 0.55             # win-rate floor (default fallback only — all real asset
                          # classes now have an explicit lower per-class sanity
                          # floor in CLASS_WR_FLOORS below)
MIN_PF = 1.5              # profit-factor floor
DSR_THRESHOLD = 0.95      # DSR probability threshold
PBO_THRESHOLD = 0.55      # PBO ≤ threshold means edge likely real (low overfit prob)
# PBO/CSCV requires ≥5 strategies to have meaningful overfit detection power
# (Bailey et al., 2016 — with <5 strategies the stat is essentially random)
MIN_STRATEGIES_FOR_PBO = 5
SPA_ALPHA = 0.10          # family-wise alpha for SPA (looser than per-strategy 0.05)
MIN_N_STRATEGY = 20       # minimum per-strategy picks for SPA inclusion

# ENHANCEMENT_OVERALL #64 (2026-06-02): multiple-testing pre-gate.
# The repo tests ~dozens of strategy x class cells with no per-strategy
# multiplicity control before promotion — finding 1-2 "PF>1" sleeves at
# alpha=0.05 across that many cells is chance-level (EAGLE2 synthesis
# 2026-06-02). This gate runs a per-strategy one-sided test of mean pnl > 0
# and applies Benjamini-Hochberg FDR (+ reports Bonferroni) across the
# strategy family. If ZERO strategies survive FDR, the class edge is not
# multiplicity-robust and cannot be MONEY_READY.
# Shadow-first (default OFF, mirrors the MDD/ML gates): when off it only
# stamps `_fdr_recommend`; set MONEY_READY_FDR_GATE=1 to hard-enforce.
FDR_Q = 0.10              # Benjamini-Hochberg false-discovery-rate level
_FDR_GATE_ENFORCE: bool = (
    os.environ.get("MONEY_READY_FDR_GATE", "0").strip().lower()
    in ("1", "true", "yes", "on")
)

# ENHANCEMENT_OVERALL #65 (2026-06-02): hard-reject single-source-artifact edge.
# The only 2 CRYPTO sleeves with PF>1 (crypto_liquidity_wick_reversal,
# atr_percentile_gate) are 100% single-source (pf_registry
# is_single_source_artifact). A class whose ENTIRE profitable edge rests on
# single-source strategies is a feed idiosyncrasy, not a class-level edge.
# This gate checks whether any *profitable* strategy (mean pnl>0, n>=
# MIN_N_STRATEGY) draws from >=2 source_systems. Shadow-first (default OFF):
# stamps `_single_source_recommend`; set MONEY_READY_SINGLE_SOURCE_GATE=1 to
# hard-downgrade MONEY_READY -> NOT_READY when every profitable sleeve is
# single-source.
_SINGLE_SOURCE_GATE_ENFORCE: bool = (
    os.environ.get("MONEY_READY_SINGLE_SOURCE_GATE", "0").strip().lower()
    in ("1", "true", "yes", "on")
)
# M-070: a class whose resolved picks are dominated by ONE symbol is not a
# class-level edge — it is a single-name bet. When the top symbol exceeds this
# share of resolved picks, the verdict is capped at WATCH (cannot be
# MONEY_READY). The dashboard's own concentration disclosure WARNs at 0.70.
MAX_SYMBOL_CONCENTRATION = 0.60

# Per-class overrides for MAX_SYMBOL_CONCENTRATION.
# COMMODITY=0.85: CT=F promoted PROBATION→FULL (2026-05-18, n=77, WR=78%, PF=4.73).
# Genuine concentrated edge in a single elite futures contract is NOT a data problem.
# Threshold 0.85 retains protection against >85% single-name dominance while
# allowing a proven T1 symbol to represent the COMMODITY class at its current n.
# Review: lower back to 0.60 if CT=F WR drops below 60% on n>=20.
MAX_SYMBOL_CONCENTRATION_BY_CLASS: dict[str, float] = {
    "COMMODITY": 0.85,
}

# 2026-05-28 Tier-0 fix: also cap source_system concentration. The CRYPTO
# Smart-Picks 78.9% WR cell was driven by a single source (claude_gainer_st
# 91.7% of cohort) which then EXPIRED→WON mislabeled. CT=F COT pilot DSR=1.0
# was driven by `multi_asset_cot_positioning` over-emitting one CFTC release
# ~6× (falsified 2026-05-13). When a single source dominates the resolved
# sample, the DSR/SPA result reflects that source's idiosyncrasies, not a
# class-level edge — cap at WATCH to require source diversification before
# any MONEY_READY verdict.
# Ref: reports/ASSET_CLASS_EDGE_FIX_PLAN_2026-05-27.md action #3.
# 2026-05-28 Tier-1: the full set of asset classes /audit tracks. Every one
# must appear in money_ready_verdict.json even at n=0 (as INSUFFICIENT_DATA)
# so downstream consumers never assume a class is absent. Ref: action #9.
CANONICAL_ASSET_CLASSES = ("CRYPTO", "EQUITY", "COMMODITY", "ETF", "FOREX", "BOND", "FUTURES")


def _is_class_policy_frozen(asset_class: str) -> bool:
    """Return True if asset_class is in BLOCKED_ASSET_CLASSES from quality_gates.

    Used to stamp `policy_frozen=true` on the verdict so the dashboard can
    distinguish operator-imposed class freezes (lift via operator decision)
    from genuinely data-thin classes (lift via more picks). Both classes
    surface as INSUFFICIENT_DATA today which is misleading.
    """
    try:
        from audit_trail.quality_gates import BLOCKED_ASSET_CLASSES
        return (asset_class or "").upper() in BLOCKED_ASSET_CLASSES
    except Exception:
        return False


MAX_SOURCE_CONCENTRATION = 0.40
MAX_SOURCE_CONCENTRATION_BY_CLASS: dict[str, float] = {
    # COMMODITY 0.60: CT=F edge is genuinely concentrated in one
    # source-system (cftc_socrata) by design; raise the ceiling here to
    # match the symbol-level COMMODITY exception. Still strict vs 1.0.
    "COMMODITY": 0.60,
}

# Per-class post-cost slippage estimates (bps, basis points)
SLIPPAGE_BPS: dict[str, float] = {
    "CRYPTO": 15.0,   # ~10-20bps taker
    "EQUITY": 10.0,   # market impact + spread
    "COMMODITY": 12.0,
    "ETF": 8.0,
    "FOREX": 5.0,     # tight spreads
    "BOND": 8.0,
    "FUTURES": 10.0,
}
DEFAULT_SLIPPAGE_BPS: float = 10.0

# Per-class WR SANITY floor for _verdict() (2026-05-19, swarm-settled Q1 verdict).
# These are low gross statistical-validity SANITY floors — NOT the promotion gate.
# A hard 55% WR AND-term structurally under-ranked valid trend/carry sleeves that
# legitimately win <50% of the time (e.g. COMMODITY trend books). The real
# money-ready promotion gate is now the net-of-slippage EXPECTANCY gate
# (_SLIPPAGE_GATE_ENABLED, ENFORCED by default) — WR is demoted to a per-class
# sanity floor so a pathological low-WR book still cannot sneak through.
# COMMODITY/FOREX/FUTURES: 40% — trend/carry signature; WR<50% with PF>=1.5 is the
#   NORMAL payoff profile for CTAs / commodity trend-following (9/9 engine
#   consensus, reports/multi_engine_institutional_strategies_2026_05_19.md).
# ETF/BOND: 45%
# EQUITY: 52% (hedge-fund T2 floor per PERFORMANCE_CHARTER.md)
# CRYPTO: 50% (high-volume, lower margin strategies — compensated by PF threshold)
CLASS_WR_FLOORS: dict[str, float] = {
    "COMMODITY": 0.40,
    "FOREX": 0.40,
    "FUTURES": 0.40,
    "ETF": 0.45,
    "BOND": 0.45,
    "EQUITY": 0.52,
    "CRYPTO": 0.50,
}
# Alias for backwards compat with older callers that referenced MIN_WR_BY_CLASS
MIN_WR_BY_CLASS = CLASS_WR_FLOORS
DEFAULT_WR_FLOOR: float = MIN_WR

# M-061a: DSR multiple-testing correction per asset class.
# nb_trials must reflect the actual number of independent strategies/systems
# tested per class.  nb_trials=1 applies zero correction and is statistically
# meaningless for real-money readiness.
# Values derived from live closed-picks source-system counts (2026-05-17).
NB_TRIALS_BY_CLASS: dict[str, int] = {
    "COMMODITY": 3,   # 3 eligible source systems with >=20 picks
    "CRYPTO": 14,     # per verdict JSON n_strategies_tested: 14
    "FOREX": 6,       # 6 eligible source systems with >=20 picks
}


# ---------------------------------------------------------------------------
# Data loading (shared with whites_reality_check.py, deflated_sharpe.py)
# ---------------------------------------------------------------------------

def _load_blocked(asset_class: str = "") -> set[str]:
    """Return set of blocked strategy names.

    Reads from:
    - BLOCKED_SOURCE_SYSTEMS / BLOCKED_STRATEGIES (global strategy blocks)
    - BLOCKED_ASSET_STRATEGY_PAIRS (per-class blocks, filtered by asset_class when given)
    - PF_REGISTRY_POLICY_EXCLUDED (data-accuracy exclusions: strategies already
      gate-blocked whose historical picks would distort PF/WR verdicts)

    Including BLOCKED_ASSET_STRATEGY_PAIRS prevents closed historical picks from
    killed strategies inflating gross_loss in per-class PF/WR calculations.
    """
    blocked: set[str] = set()
    if not GATES_PATH.exists():
        return blocked
    text = GATES_PATH.read_text(encoding="utf-8", errors="replace")

    # Pass 1: global blocks (BLOCKED_SOURCE_SYSTEMS, BLOCKED_STRATEGIES)
    in_block = False
    for line in text.splitlines():
        s = line.strip()
        if ("BLOCKED_SOURCE_SYSTEMS" in s or "BLOCKED_STRATEGIES" in s) and "=" in s:
            in_block = True
        elif in_block:
            if s.startswith("}"):
                in_block = False
                continue
            if s.startswith('"') or s.startswith("'"):
                name = s.split('"')[1] if '"' in s else s.split("'")[1]
                if name:
                    blocked.add(name)

    # Pass 2: BLOCKED_ASSET_STRATEGY_PAIRS — tuples of (asset_class, strategy)
    # Include strategies blocked for this specific asset class.
    in_pairs = False
    ac_upper = asset_class.upper() if asset_class else ""
    for line in text.splitlines():
        s = line.strip()
        if "BLOCKED_ASSET_STRATEGY_PAIRS" in s and "=" in s:
            in_pairs = True
        elif in_pairs:
            if s.startswith("}") or (s.startswith("]") and "BLOCKED" not in s):
                in_pairs = False
                continue
            # Match lines like: ("CRYPTO", "ml_enhanced_APEUSDT_1d_D_ensemble_stack"),
            if s.startswith("(") and ',' in s:
                parts = [p.strip().strip("\"'(),") for p in s.split(",")]
                if len(parts) >= 2:
                    pair_ac = parts[0].strip("(\"'")
                    pair_strat = parts[1].strip("\"')")
                    if pair_strat and (not ac_upper or pair_ac.upper() == ac_upper):
                        blocked.add(pair_strat)

    # Pass 3: PF_REGISTRY_POLICY_EXCLUDED — strategies whose historical picks are
    # data-accuracy exclusions (gate-blocked via BLOCKED_DIRECTION_TRIPLES for ALL
    # directions, but not in BLOCKED_ASSET_STRATEGY_PAIRS). Importing directly avoids
    # text parsing of the set literal.
    try:
        from audit_trail.quality_gates import PF_REGISTRY_POLICY_EXCLUDED
        for name in PF_REGISTRY_POLICY_EXCLUDED:
            blocked.add(str(name))
    except Exception:
        pass  # fail-open: never break verdict on import error

    return blocked


def _load_blocked_symbols() -> set[str]:
    """Return the set of blocked symbols from BLOCKED_SYMBOLS in quality_gates.py.

    Picks for these symbols are excluded from per-class PF/WR calculations
    even when the pick's strategy name is not in the strategy-level blocklists.
    """
    syms: set[str] = set()
    if not GATES_PATH.exists():
        return syms
    text = GATES_PATH.read_text(encoding="utf-8", errors="replace")
    in_block = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("BLOCKED_SYMBOLS") and "=" in s and "BY_CLASS" not in s and "PAIRS" not in s:
            if "{" in s:
                in_block = True
        elif in_block:
            if s.startswith("}"):
                in_block = False
                continue
            if s.startswith('"') or s.startswith("'"):
                sym = s.split('"')[1] if '"' in s else s.split("'")[1]
                if sym:
                    syms.add(sym)
    return syms


def _load_picks_legacy() -> list[dict]:
    """Legacy loader — closed_picks.json only. Kept as the fail-open fallback."""
    if not CLOSED_PATH.exists():
        return []
    return json.loads(CLOSED_PATH.read_text())


def _load_picks() -> list[dict]:
    """Canonical pick loader — the deduped, policy-clean per-pick rows that
    feed pf_registry.json (by_asset_class_policy_clean_net).

    Falls back to the legacy closed_picks.json loader if the build_pf_registry
    pipeline is unavailable.
    """
    pipeline = _canonical_pipeline()
    if pipeline is None:
        return _load_picks_legacy()
    _bpr_load_rows, _bpr_classify_rows, _bpr_is_policy_excluded, _bpr_asset_class = pipeline
    try:
        rows, _meta = _bpr_load_rows()
        res = _bpr_classify_rows(rows)
        kept_policy = [r for r in res["kept"] if not _bpr_is_policy_excluded(r)]
        # Normalize each row so the existing _class_stats / gate code consumes
        # it unchanged: `asset_class` to the registry-normalized class,
        # `pnl_pct` to the sanitized `_pnl_pct`, `status` so _resolved() keeps
        # every closed row (win/loss is recomputed NET downstream anyway).
        for r in kept_policy:
            r["asset_class"] = _bpr_asset_class(r)
            r["pnl_pct"] = r.get("_pnl_pct", r.get("pnl_pct"))
            r["status"] = "WON" if (r.get("pnl_pct") or 0) > 0 else "LOST"
        return kept_policy
    except Exception as exc:  # noqa: BLE001 — fail-open to legacy
        print(f"WARN: canonical pick pipeline failed ({exc}); "
              f"falling back to closed_picks.json", file=sys.stderr)
        return _load_picks_legacy()


PF_REGISTRY_PATH = REPO_ROOT / "audit_dashboard/data/pf_registry.json"


def _load_dashboard_health() -> dict[str, dict]:
    """Per-class n/wr/pf used as a display fallback when a class has fewer
    than MIN_N_CLASS resolved picks.

    Reads the CANONICAL pf_registry (by_asset_class_policy_clean_net) so the
    fallback is consistent with the verdict-grade ledger — NOT the /audit
    dashboard tiles, which can be inflated (2026-05-19, swarm-debated: the
    Money-Ready surface must read one source of truth). Falls back to
    dashboard_data.json::asset_class_health only if pf_registry is missing.
    """
    if PF_REGISTRY_PATH.exists():
        try:
            reg = json.loads(PF_REGISTRY_PATH.read_text())
            canon_key = reg.get("canonical_view", "by_asset_class_policy_clean_net")
            rows = reg.get(canon_key) or []
            out: dict[str, dict] = {}
            for r in rows:
                if not isinstance(r, dict) or "asset_class" not in r:
                    continue
                out[str(r["asset_class"]).upper()] = {
                    "n": r.get("n", 0),
                    "win_rate": r.get("win_rate_pct") or 0,
                    "pf": r.get("profit_factor") or 0,
                    # Q2 (2026-05-19): class-level max drawdown persisted in
                    # pf_registry.json (fraction). None on older registries.
                    "max_drawdown_pct": r.get("max_drawdown_pct"),
                    "_health_source": "pf_registry",
                }
            if out:
                return out
        except Exception:
            pass
    # Legacy fallback — only if pf_registry is unavailable.
    if not DASHBOARD_PATH.exists():
        return {}
    try:
        dd = json.loads(DASHBOARD_PATH.read_text())
        return dd.get("performance", {}).get("asset_class_health", {})
    except Exception:
        return {}


def _resolved(picks: list[dict]) -> list[dict]:
    return [p for p in picks if str(p.get("status", "")).upper() in ("WON", "LOST")]


# ---------------------------------------------------------------------------
# Per-class aggregation
# ---------------------------------------------------------------------------

def _net_pnl(pick: dict) -> float:
    """Per-pick NET return = gross pnl_pct minus per-class round-trip slippage.

    M-069 (2026-05-17): a function named `money_ready_verdict` MUST judge
    edge net of execution cost — the charter_slippage rationale is exactly
    that the "REAL gross" verdict can survive while the "real money" verdict
    does not (a 7bp gross COMMODITY win is a net loss after the 12bp
    round-trip). `deduct_slippage` is the M-069-corrected fraction-unit
    deduction. Fail-open: if the import is unavailable, fall back to gross.
    """
    gross = float(pick.get("pnl_pct") or 0)
    try:
        from alpha_engine.charter_slippage import deduct_slippage
        return deduct_slippage(gross, pick.get("asset_class"))
    except Exception:
        return gross


def _class_stats(picks: list[dict]) -> dict[str, dict]:
    # Picks arrive deduped + policy-clean from _load_picks() (the canonical
    # build_pf_registry pipeline). The strategy filtering below is therefore a
    # redundant no-op on the canonical path — kept only as defense-in-depth for
    # the legacy fail-open path (closed_picks.json). NOTE: blocked-symbol
    # filtering was REMOVED here (2026-05-19) — pf_registry's policy-clean view
    # excludes by strategy/source, never by symbol, so a symbol filter here put
    # money_ready's CRYPTO n below the canonical registry n (1365 vs 1673).
    global_blocked = _load_blocked()
    by_class: dict[str, list[dict]] = defaultdict(list)
    for p in _resolved(picks):
        strat = p.get("strategy") or p.get("source_system") or ""
        ac = str(p.get("asset_class") or "UNKNOWN").upper()
        if strat in global_blocked:
            continue
        by_class[ac].append(p)

    # Second pass: filter per-class blocks from BLOCKED_ASSET_STRATEGY_PAIRS
    class_blocked: dict[str, set[str]] = {}
    filtered_by_class: dict[str, list[dict]] = defaultdict(list)
    for ac, ps in by_class.items():
        if ac not in class_blocked:
            class_blocked[ac] = _load_blocked(asset_class=ac)
        for p in ps:
            strat = p.get("strategy") or p.get("source_system") or ""
            if strat not in class_blocked[ac]:
                filtered_by_class[ac].append(p)
    by_class = filtered_by_class

    # M-105: ml_enhanced family quarantine for CRYPTO.
    # When ML_ENHANCED_CRYPTO_QUARANTINE=1, exclude all ml_enhanced_* picks from
    # CRYPTO verdict (shadow mode: count excluded picks and stamp on verdict).
    _ml_enhanced_quarantine_n_by_class: dict[str, int] = {}
    if "CRYPTO" in by_class:
        ml_count = sum(
            1 for p in by_class["CRYPTO"]
            if (p.get("strategy") or p.get("source_system") or "").startswith(_ML_ENHANCED_PREFIX)
        )
        _ml_enhanced_quarantine_n_by_class["CRYPTO"] = ml_count
        if _ML_ENHANCED_CRYPTO_QUARANTINE:
            by_class["CRYPTO"] = [
                p for p in by_class["CRYPTO"]
                if not (p.get("strategy") or p.get("source_system") or "").startswith(_ML_ENHANCED_PREFIX)
            ]

    stats: dict[str, dict] = {}
    for ac, ps in by_class.items():
        n = len(ps)
        # M-069: judge win/loss by NET return (after slippage), not the stored
        # status field. A status=WON pick whose gross edge is below the
        # round-trip cost is a real-money LOSS — counting it as a win is how
        # the gross verdict overstates the edge (e.g. the CT=F COMMODITY leak:
        # ~7bp gross wins that are net-negative after the 12bp round-trip).
        nets = [_net_pnl(p) for p in ps]
        wins = sum(1 for v in nets if v > 0)
        wr = wins / n if n else 0.0
        gross_win = sum(v for v in nets if v > 0)
        gross_loss = abs(sum(v for v in nets if v < 0))
        pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
        returns = nets
        # M-070: single-symbol concentration of the resolved sample.
        sym_counts: dict[str, int] = defaultdict(int)
        for p in ps:
            sym_counts[str(p.get("symbol") or "UNKNOWN")] += 1
        top_symbol, top_count = ("", 0)
        if sym_counts:
            top_symbol, top_count = max(sym_counts.items(), key=lambda kv: kv[1])
        top_symbol_share = (top_count / n) if n else 0.0
        # 2026-05-28 Tier-0: single-source concentration of the resolved sample.
        src_counts: dict[str, int] = defaultdict(int)
        for p in ps:
            src_counts[str(p.get("source_system") or "UNKNOWN")] += 1
        top_source, top_src_count = ("", 0)
        if src_counts:
            top_source, top_src_count = max(src_counts.items(), key=lambda kv: kv[1])
        top_source_share = (top_src_count / n) if n else 0.0
        win_vals = [v for v in nets if v > 0]
        loss_vals = [abs(v) for v in nets if v < 0]
        avg_win = sum(win_vals) / len(win_vals) if win_vals else 0.0
        avg_loss = sum(loss_vals) / len(loss_vals) if loss_vals else 0.0
        stats[ac] = {
            "n": n,
            "wr": round(wr, 4),
            "pf": round(pf, 4),
            "returns": returns,
            "picks": ps,
            "top_symbol": top_symbol,
            "top_symbol_share": round(top_symbol_share, 4),
            "top_source": top_source,
            "top_source_share": round(top_source_share, 4),
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "_ml_enhanced_quarantine_n": _ml_enhanced_quarantine_n_by_class.get(ac, 0),
        }
    return stats


# ---------------------------------------------------------------------------
# DSR gate (per-class aggregate — treat all class picks as one strategy)
# ---------------------------------------------------------------------------

def _dsr_gate(returns: list[float]) -> dict[str, Any]:
    try:
        try:
            from alpha_engine.deflated_sharpe import returns_stats, sharpe_variance, deflated_sharpe_ratio
        except ImportError:
            from deflated_sharpe import returns_stats, sharpe_variance, deflated_sharpe_ratio
    except ImportError:
        return {"ok": None, "note": "deflated_sharpe not importable", "dsr_score": None}

    arr = np.array(returns, dtype=float)
    if len(arr) < 10:
        return {"ok": None, "note": f"n={len(arr)} too small for DSR", "dsr_score": None}

    mu, sd = arr.mean(), arr.std()
    if sd == 0:
        return {"ok": False, "note": "zero variance returns", "dsr_score": 0.0}

    sr = mu / sd * np.sqrt(252)  # annualised daily SR approximation
    stats = returns_stats(list(returns))
    horizon = len(arr)
    sr_var = sharpe_variance(sr, horizon, stats["skewness"], stats["kurtosis"])
    # nb_trials=1 — we're testing the class aggregate, not a selected-best strategy
    dsr = deflated_sharpe_ratio(
        estimated_sharpe=sr,
        sr_variance=sr_var,
        nb_trials=1,
        backtest_horizon=horizon,
        skew=stats["skewness"],
        kurtosis=stats["kurtosis"],
    )
    return {"ok": dsr >= DSR_THRESHOLD, "dsr_score": round(dsr, 4), "note": ""}


# ---------------------------------------------------------------------------
# PBO gate (per-class aggregate: build strategy columns from top strategies)
# ---------------------------------------------------------------------------

def _pbo_gate(picks: list[dict]) -> dict[str, Any]:
    try:
        from tools.pbo_cscv import compute_pbo
    except ImportError:
        try:
            sys.path.insert(0, str(REPO_ROOT / "tools"))
            from pbo_cscv import compute_pbo
        except ImportError:
            return {"ok": None, "note": "pbo_cscv not importable", "pbo": None}

    blocked = _load_blocked()
    by_strat: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        strat = p.get("strategy") or p.get("source_system") or ""
        if not strat or strat in blocked:
            continue
        try:
            by_strat[strat].append(float(p.get("pnl_pct") or 0))
        except (TypeError, ValueError):
            pass

    eligible = {k: v for k, v in by_strat.items() if len(v) >= MIN_N_STRATEGY}
    if len(eligible) < 2:
        return {"ok": None, "note": f"need ≥2 strategies with n≥{MIN_N_STRATEGY}, got {len(eligible)}", "pbo": None}
    # PBO/CSCV has near-zero power with <MIN_STRATEGIES_FOR_PBO strategies
    if len(eligible) < MIN_STRATEGIES_FOR_PBO:
        return {
            "ok": None,
            "note": f"n_strategies={len(eligible)} < {MIN_STRATEGIES_FOR_PBO} — PBO statistically unreliable (N/A)",
            "pbo": None,
            "n_strategies": len(eligible),
        }

    T_max = max(len(v) for v in eligible.values())
    rng = np.random.default_rng(42)
    mat = np.zeros((T_max, len(eligible)))
    for j, (_, rets) in enumerate(eligible.items()):
        r = np.array(rets, dtype=float)
        if len(r) < T_max:
            idx = rng.integers(0, len(r), size=T_max)
            r = r[idx]
        mat[:, j] = r

    result = compute_pbo(mat)
    pbo = result.get("pbo")
    ok = (pbo is not None) and (pbo <= PBO_THRESHOLD)
    return {"ok": ok, "pbo": round(pbo, 4) if pbo is not None else None, "n_strategies": len(eligible), "note": result.get("note", "")}


# ---------------------------------------------------------------------------
# SPA gate (family-wise — delegates to whites_spa_test)
# ---------------------------------------------------------------------------

def _spa_gate(picks: list[dict]) -> dict[str, Any]:
    try:
        tools_dir = str(REPO_ROOT / "tools")
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        from whites_reality_check import whites_spa_test
    except ImportError:
        return {"ok": None, "note": "whites_reality_check not importable", "spa_p": None}

    blocked = _load_blocked()
    by_strat: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        strat = p.get("strategy") or p.get("source_system") or ""
        if not strat or strat in blocked:
            continue
        try:
            by_strat[strat].append(float(p.get("pnl_pct") or 0))
        except (TypeError, ValueError):
            pass

    eligible = {k: v for k, v in by_strat.items() if len(v) >= MIN_N_STRATEGY}
    if not eligible:
        return {"ok": None, "note": f"no strategies with n≥{MIN_N_STRATEGY}", "spa_p": None, "n_spa_pass": 0}

    result = whites_spa_test(eligible, n_boot=500, alpha=SPA_ALPHA)
    spa_p = result.get("family_p_spa")
    ok = (spa_p is not None) and (spa_p <= SPA_ALPHA)
    return {
        "ok": ok,
        "spa_p": round(spa_p, 4) if spa_p is not None else None,
        "n_spa_pass": result.get("n_spa_pass", 0),
        "n_strategies_tested": result.get("n_strategies", 0),
        "note": "",
    }


def _one_sided_t_pvalue(pnls: list[float]) -> float | None:
    """One-sided p-value for H1: mean(pnl) > 0, normal approx of the t-stat.

    Returns None when the sample is too small or has zero variance.
    n>=MIN_N_STRATEGY (20) makes the normal approximation of Student-t adequate
    and keeps the gate dependency-free (no scipy)."""
    arr = [float(p) for p in pnls if p is not None]
    n = len(arr)
    if n < MIN_N_STRATEGY:
        return None
    mean = sum(arr) / n
    var = sum((x - mean) ** 2 for x in arr) / (n - 1)
    if var <= 0:
        # zero variance: all-positive mean is a (degenerate) certain win, all
        # non-positive is a certain non-win.
        return 0.0 if mean > 0 else 1.0
    t = mean / math.sqrt(var / n)
    # one-sided upper-tail p of standard normal = 0.5 * erfc(t / sqrt(2))
    return 0.5 * math.erfc(t / math.sqrt(2.0))


def _fdr_gate(picks: list[dict]) -> dict[str, Any]:
    """Per-strategy multiple-testing pre-gate (ENHANCEMENT_OVERALL #64).

    Tests each eligible strategy (n>=MIN_N_STRATEGY) for mean pnl > 0, then
    applies Benjamini-Hochberg FDR at FDR_Q across the strategy family. Also
    reports the Bonferroni survivor count. ok semantics match the other gates:
      True  — >=1 strategy survives FDR (class edge is multiplicity-robust)
      False — >=2 strategies tested but 0 survive (chance-level edge)
      None  — <2 testable strategies (fail-open; never blocks on its own)"""
    blocked = _load_blocked()
    by_strat: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        strat = p.get("strategy") or p.get("source_system") or ""
        if not strat or strat in blocked:
            continue
        try:
            by_strat[strat].append(float(p.get("pnl_pct") or 0))
        except (TypeError, ValueError):
            pass

    pvals: list[tuple[str, float]] = []
    for strat, pnls in by_strat.items():
        pv = _one_sided_t_pvalue(pnls)
        if pv is not None:
            pvals.append((strat, pv))

    m = len(pvals)
    if m < 2:
        return {"ok": None, "n_tested": m, "n_fdr_pass": 0,
                "n_bonferroni_pass": 0, "min_p": None, "fdr_q": FDR_Q,
                "note": f"need >=2 testable strategies (n>={MIN_N_STRATEGY}), got {m}"}

    pvals.sort(key=lambda kv: kv[1])
    # Benjamini-Hochberg: largest k with p_(k) <= (k/m) * q  (k is 1-indexed)
    n_fdr_pass = 0
    for k, (_, pv) in enumerate(pvals, start=1):
        if pv <= (k / m) * FDR_Q:
            n_fdr_pass = k
    bonf_thresh = FDR_Q / m
    n_bonf_pass = sum(1 for _, pv in pvals if pv <= bonf_thresh)
    return {
        "ok": n_fdr_pass >= 1,
        "n_tested": m,
        "n_fdr_pass": n_fdr_pass,
        "n_bonferroni_pass": n_bonf_pass,
        "min_p": round(pvals[0][1], 5),
        "fdr_q": FDR_Q,
        "bonferroni_threshold": round(bonf_thresh, 6),
        "note": "",
    }


def _single_source_gate(picks: list[dict]) -> dict[str, Any]:
    """Reject class edge that rests entirely on single-source sleeves (#65).

    For each strategy with n>=MIN_N_STRATEGY, count distinct source_systems and
    its mean pnl. A *profitable* strategy (mean>0) is an 'artifact' when it
    draws from exactly one source_system. ok semantics:
      True  — >=1 profitable strategy is multi-source (real class-level edge)
      False — >=1 profitable strategy exists and ALL are single-source
      None  — no profitable strategy / insufficient data (fail-open)"""
    blocked = _load_blocked()
    by_strat_pnl: dict[str, list[float]] = defaultdict(list)
    by_strat_src: dict[str, set] = defaultdict(set)
    for p in picks:
        strat = p.get("strategy") or p.get("source_system") or ""
        if not strat or strat in blocked:
            continue
        try:
            by_strat_pnl[strat].append(float(p.get("pnl_pct") or 0))
        except (TypeError, ValueError):
            continue
        by_strat_src[strat].add(str(p.get("source_system") or "UNKNOWN"))

    profitable_single, profitable_multi = [], []
    for strat, pnls in by_strat_pnl.items():
        if len(pnls) < MIN_N_STRATEGY:
            continue
        if (sum(pnls) / len(pnls)) <= 0:
            continue
        if len(by_strat_src[strat]) <= 1:
            profitable_single.append(strat)
        else:
            profitable_multi.append(strat)

    n_prof = len(profitable_single) + len(profitable_multi)
    if n_prof == 0:
        return {"ok": None, "n_profitable": 0, "n_profitable_single_source": 0,
                "n_profitable_multi_source": 0,
                "note": f"no profitable strategy with n>={MIN_N_STRATEGY}"}
    ok = len(profitable_multi) >= 1
    return {
        "ok": ok,
        "n_profitable": n_prof,
        "n_profitable_single_source": len(profitable_single),
        "n_profitable_multi_source": len(profitable_multi),
        "single_source_strategies": sorted(profitable_single)[:10],
        "note": "" if ok else "all profitable sleeves are single-source (artifact edge)",
    }


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

def _verdict(n: int, wr: float, pf: float, dsr: dict, pbo: dict, spa: dict,
             asset_class: str = "", top_symbol_share: float = 0.0,
             top_source_share: float = 0.0,
             avg_win: float = 0.0, avg_loss: float = 0.0,
             mdd_cvar_gate_ok: bool | None = None,
             fdr_gate_ok: bool | None = None,
             single_source_gate_ok: bool | None = None) -> str:
    n_ok = n >= MIN_N_CLASS
    if not n_ok:
        return "INSUFFICIENT_DATA"

    wr_floor = MIN_WR_BY_CLASS.get(asset_class.upper(), MIN_WR)
    wr_ok = wr >= wr_floor
    pf_ok = pf >= MIN_PF

    dsr_ok = dsr.get("ok") is True
    pbo_ok = pbo.get("ok") is True
    spa_ok = spa.get("ok") is True

    if wr_ok and pf_ok and (dsr_ok or spa_ok) and (pbo_ok or spa_ok):
        # M-070: a class edge concentrated in one symbol is a single-name bet,
        # not a class-level edge — cannot be MONEY_READY. Downgrade to WATCH.
        _conc_cap = MAX_SYMBOL_CONCENTRATION_BY_CLASS.get(
            asset_class.upper(), MAX_SYMBOL_CONCENTRATION
        )
        if top_symbol_share > _conc_cap:
            return "WATCH"
        # 2026-05-28 Tier-0: source-concentration cap (mirrors symbol cap).
        _src_conc_cap = MAX_SOURCE_CONCENTRATION_BY_CLASS.get(
            asset_class.upper(), MAX_SOURCE_CONCENTRATION
        )
        if top_source_share > _src_conc_cap:
            return "WATCH"
        # P1/#7: Net-of-cost slippage promotion gate.
        # When enabled, block MONEY_READY if post-slippage expectancy is negative.
        if _SLIPPAGE_GATE_ENABLED and avg_win > 0 and avg_loss > 0:
            slippage = SLIPPAGE_BPS.get(asset_class.upper(), DEFAULT_SLIPPAGE_BPS) / 10000.0
            expectancy = wr * (avg_win - slippage) - (1 - wr) * (avg_loss + slippage)
            if expectancy <= 0:
                return "NOT_READY"
        # I-3: MDD ≤ 20% + CVaR-95% < 10% tail-risk gate.
        # When MDD_GATE_ENFORCE is set, a failed tail-risk gate hard-downgrades
        # MONEY_READY → NOT_READY. Monotone-conservative: only ever downgrades,
        # and only when gate_ok is explicitly False (None = insufficient data,
        # leaves the verdict untouched). Default OFF (shadow) — no-op when unset.
        if _MDD_GATE_ENFORCE and mdd_cvar_gate_ok is False:
            return "NOT_READY"
        # ENHANCEMENT #64: multiple-testing pre-gate. When enforced, a class
        # whose strategy family has ZERO FDR survivors is not multiplicity-
        # robust -> NOT_READY. Monotone-conservative: only downgrades, and only
        # when fdr_gate_ok is explicitly False (None = insufficient strategies,
        # leaves the verdict untouched). Default OFF (shadow) — no-op when unset.
        if _FDR_GATE_ENFORCE and fdr_gate_ok is False:
            return "NOT_READY"
        # ENHANCEMENT #65: single-source-artifact pre-gate. When enforced, a
        # class whose entire profitable edge is single-source -> NOT_READY.
        # Monotone-conservative + fail-open (None never blocks). Default OFF.
        if _SINGLE_SOURCE_GATE_ENFORCE and single_source_gate_ok is False:
            return "NOT_READY"
        return "MONEY_READY"
    # A profit factor below 1.0 means the book loses money gross — never WATCH.
    # (2026-05-19 Q1 follow-up: lowering the per-class WR sanity floor lets a
    # money-losing class such as FOREX PF 0.27 satisfy wr_ok and fall into the
    # `wr_ok or pf_ok` WATCH branch alongside a profitable near-miss like
    # EQUITY PF 1.41. PF<1.0 must hard-route to NOT_READY regardless of WR.)
    if pf < 1.0:
        return "NOT_READY"
    if wr_ok or pf_ok:
        return "WATCH"
    return "NOT_READY"


def _expectancy_gate(wr: float, avg_win: float, avg_loss: float,
                     asset_class: str) -> dict[str, Any]:
    """Compute post-cost expectancy: E = WR*adj_win - (1-WR)*adj_loss.

    Warning-only; promote to hard gate after 30d shadow (2026-06-17).
    Returns a dict with keys: expectancy (float), expectancy_ok (bool|None).
    expectancy_ok is None when avg_win or avg_loss data is unavailable.
    """
    slippage = SLIPPAGE_BPS.get(asset_class.upper(), DEFAULT_SLIPPAGE_BPS) / 10000.0
    if avg_win <= 0 or avg_loss <= 0:
        return {"expectancy": None, "expectancy_ok": None,
                "note": "avg_win or avg_loss unavailable (no pick data)"}
    adj_win = avg_win - slippage
    adj_loss = avg_loss + slippage
    expectancy = wr * adj_win - (1 - wr) * adj_loss
    expectancy_ok = expectancy > 0
    return {
        "expectancy": round(expectancy, 6),
        "expectancy_ok": expectancy_ok,
        "adj_win": round(adj_win, 6),
        "adj_loss": round(adj_loss, 6),
        "slippage_bps": SLIPPAGE_BPS.get(asset_class.upper(), DEFAULT_SLIPPAGE_BPS),
        "note": "",
    }


# ---------------------------------------------------------------------------
# I-3 — MDD + CVaR tail-risk gate
# ---------------------------------------------------------------------------

def _rolling_mdd(returns: list[float]) -> float:
    """Compute max drawdown of the cumulative equity curve from a return series.

    Uses absolute (not percentage-of-peak) drawdown on the cumulative curve.
    Returns a non-negative float: 0.0 = no drawdown, 0.20 = 20% peak-to-trough.
    """
    if not returns:
        return 0.0
    # Build cumulative equity curve starting at 1.0
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        equity *= (1.0 + r)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _mdd_cvar_gate(returns: list[float], asset_class: str,
                   registry_mdd: float | None = None) -> dict[str, Any]:
    """I-3 tail-risk gate: MDD ≤ 20% + CVaR-95% < 10%.

    Q2 (2026-05-19): when `registry_mdd` is supplied (the persisted
    `max_drawdown_pct` from pf_registry.json::by_asset_class_policy_clean_net,
    a fraction), it is PREFERRED for the MDD leg over the ephemeral
    `_rolling_mdd(returns)` recompute — the registry value is computed from the
    canonical deduped policy-clean net series and is the single source of
    truth. The recompute remains the fallback for old registry files that
    predate the key (registry_mdd is None).

    Returns a dict with keys:
        mdd (float): max drawdown fraction (0.20 = 20%)
        mdd_ok (bool|None): True if mdd ≤ effective cap (MDD_GATE_THRESHOLD_BY_CLASS or default); None if n < 10
        cvar_95 (float): CVaR at 95% as a percentage (negative = loss)
        cvar_ok (bool|None): True if |cvar_95| < CVAR_GATE_THRESHOLD_PCT; None if n < 10
        gate_ok (bool|None): True if both mdd_ok and cvar_ok are True
        mdd_source (str): "registry" or "recompute" — which MDD was used
    """
    MIN_N_RISK = 10  # below this, skip the gate (insufficient data)
    if len(returns) < MIN_N_RISK:
        return {"mdd": None, "mdd_ok": None, "cvar_95": None, "cvar_ok": None,
                "gate_ok": None, "mdd_source": None}

    if registry_mdd is not None:
        mdd = float(registry_mdd)
        mdd_source = "registry"
    else:
        mdd = _rolling_mdd(returns)
        mdd_source = "recompute"
    effective_mdd_cap = MDD_GATE_THRESHOLD_BY_CLASS.get(
        (asset_class or "").upper(), MDD_GATE_THRESHOLD
    )
    mdd_ok = mdd <= effective_mdd_cap

    # CVaR-95%: expected loss in the worst 5% of outcomes
    sorted_r = sorted(returns)
    n_tail = max(1, int(len(sorted_r) * 0.05))
    tail = sorted_r[:n_tail]
    cvar_95_pct = (sum(tail) / len(tail)) * 100  # negative = loss
    cvar_ok = abs(cvar_95_pct) < CVAR_GATE_THRESHOLD_PCT

    return {
        "mdd": round(mdd, 4),
        "mdd_ok": mdd_ok,
        "cvar_95": round(cvar_95_pct, 4),
        "cvar_ok": cvar_ok,
        "gate_ok": mdd_ok and cvar_ok,
        "mdd_source": mdd_source,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def money_ready_verdict(asset_class: str | None = None, n_boot: int = 500) -> dict[str, dict]:
    """Return per-class readiness verdict dict.

    When closed_picks.json has <MIN_N_CLASS picks for an asset class, the n/wr/pf
    from dashboard_data.json::asset_class_health is used as a fallback for display.
    Statistical tests (DSR/PBO/SPA) still require actual pick-level data and will
    show N/A when the closed_picks sample is too small.
    """
    picks = _load_picks()
    class_stats = _class_stats(picks)
    dash_health = _load_dashboard_health()

    # Include any classes in dashboard health that have no closed_picks data at all
    for ac_dash, health in dash_health.items():
        ac_up = ac_dash.upper()
        if ac_up not in class_stats:
            # M-080: dashboard stores WR as win_rate/wr_pct (percentage) not "wr" fraction.
            # "wr" key does not exist in asset_class_health — must use win_rate or wr_pct.
            _raw_wr = health.get("win_rate") or health.get("wr_pct") or health.get("wr") or 0
            _wr = float(_raw_wr) / 100 if float(_raw_wr or 0) > 1 else float(_raw_wr or 0)
            _pf = float(health.get("pf") or health.get("profit_factor") or 0)
            class_stats[ac_up] = {
                "n": health.get("n", 0),
                "wr": _wr,
                "pf": _pf,
                "returns": [],
                "picks": [],
                "_source": "dashboard_fallback",
            }

    # 2026-05-28 Tier-1 fix: force every canonical asset class to emit a row.
    # ETF + BOND were silently DROPPED from money_ready_verdict.json whenever
    # they had zero resolved picks AND no dashboard_health entry — downstream
    # consumers then assumed those classes don't exist. Backfill an empty
    # stats entry so they surface as INSUFFICIENT_DATA instead of vanishing.
    # Ref: reports/ASSET_CLASS_EDGE_FIX_PLAN_2026-05-27.md action #9.
    for _canon in CANONICAL_ASSET_CLASSES:
        if _canon not in class_stats:
            class_stats[_canon] = {
                "n": 0, "wr": 0.0, "pf": 0.0,
                "returns": [], "picks": [], "_source": "backfill_no_data",
            }

    results: dict[str, dict] = {}
    for ac, stats in class_stats.items():
        if asset_class and ac != asset_class.upper():
            continue

        n = stats["n"]
        wr = stats["wr"]
        pf = stats["pf"]
        returns = stats["returns"]
        ac_picks = stats["picks"]
        data_source = stats.get("_source", "closed_picks")

        # Dashboard fallback: if closed_picks n < MIN_N_CLASS but dashboard has more data,
        # use ALL dashboard n/wr/pf for verdict display (statistical tests still need pick data)
        if n < MIN_N_CLASS and ac in dash_health:
            h = dash_health[ac]
            dash_n = h.get("n", 0)
            if dash_n > n:
                n = dash_n
                # dashboard stores wr as percentage (53.3) in win_rate/wr_pct, or fraction in wr
                raw_wr = h.get("win_rate") or h.get("wr_pct") or h.get("wr") or 0
                wr = float(raw_wr) / 100 if float(raw_wr or 0) > 1 else float(raw_wr or 0)
                pf = float(h.get("pf") or h.get("profit_factor") or 0)
                data_source = "dashboard_fallback"

        dsr = _dsr_gate(returns)
        pbo = _pbo_gate(ac_picks)
        spa = _spa_gate(ac_picks)
        fdr = _fdr_gate(ac_picks)
        single_src = _single_source_gate(ac_picks)
        top_symbol = stats.get("top_symbol", "")
        top_symbol_share = stats.get("top_symbol_share", 0.0)
        top_source = stats.get("top_source", "")
        top_source_share = stats.get("top_source_share", 0.0)
        avg_win = stats.get("avg_win", 0.0)
        avg_loss = stats.get("avg_loss", 0.0)
        # Q2 (2026-05-19): prefer the persisted class-level MDD from
        # pf_registry.json over the ephemeral _rolling_mdd recompute.
        _registry_mdd = (dash_health.get(ac) or {}).get("max_drawdown_pct")
        mdd_cvar = _mdd_cvar_gate(returns, asset_class=ac,
                                  registry_mdd=_registry_mdd)
        verdict = _verdict(n, wr, pf, dsr, pbo, spa, asset_class=ac,
                           top_symbol_share=top_symbol_share,
                           top_source_share=top_source_share,
                           avg_win=avg_win, avg_loss=avg_loss,
                           mdd_cvar_gate_ok=mdd_cvar.get("gate_ok"),
                           fdr_gate_ok=fdr.get("ok"),
                           single_source_gate_ok=single_src.get("ok"))
        wr_floor = MIN_WR_BY_CLASS.get(ac.upper(), MIN_WR)
        exp_gate = _expectancy_gate(wr, avg_win, avg_loss, asset_class=ac)

        results[ac] = {
            "n_resolved": n,
            "wr": round(wr, 4),
            "pf": round(pf, 4) if pf != float("inf") else None,
            "n_ok": n >= MIN_N_CLASS,
            "wr_ok": wr >= wr_floor,
            "pf_ok": pf >= MIN_PF,
            "dsr_ok": dsr.get("ok"),
            "dsr_score": dsr.get("dsr_score"),
            "pbo_ok": pbo.get("ok"),
            "pbo": pbo.get("pbo"),
            "spa_ok": spa.get("ok"),
            "spa_p": spa.get("spa_p"),
            "n_spa_pass": spa.get("n_spa_pass", 0),
            "expectancy": exp_gate.get("expectancy"),
            "expectancy_ok": exp_gate.get("expectancy_ok"),
            # P1/#7 shadow: when gate is OFF, stamp what the gate would have done
            "_slippage_gate_enabled": _SLIPPAGE_GATE_ENABLED,
            "_slippage_recommend": (
                "NOT_READY"
                if (not _SLIPPAGE_GATE_ENABLED
                    and exp_gate.get("expectancy_ok") is False
                    and verdict == "MONEY_READY")
                else None
            ),
            # M-105 shadow: stamp ml_enhanced quarantine impact on CRYPTO verdict
            "_ml_enhanced_quarantine_enabled": _ML_ENHANCED_CRYPTO_QUARANTINE,
            "_ml_enhanced_quarantine_n": stats.get("_ml_enhanced_quarantine_n", 0),
            "_ml_enhanced_quarantine_recommend": (
                "NOT_READY"
                if (ac == "CRYPTO"
                    and not _ML_ENHANCED_CRYPTO_QUARANTINE
                    and stats.get("_ml_enhanced_quarantine_n", 0) > 0
                    and verdict == "MONEY_READY")
                else None
            ),
            # I-3 shadow: MDD ≤ 20% + CVaR-95% < 10% tail-risk gate
            "_mdd_gate_enforce": _MDD_GATE_ENFORCE,
            "mdd": mdd_cvar.get("mdd"),
            "mdd_ok": mdd_cvar.get("mdd_ok"),
            "cvar_95": mdd_cvar.get("cvar_95"),
            "cvar_ok": mdd_cvar.get("cvar_ok"),
            "_mdd_cvar_gate_ok": mdd_cvar.get("gate_ok"),
            "_mdd_cvar_recommend": (
                "NOT_READY"
                if (not _MDD_GATE_ENFORCE
                    and mdd_cvar.get("gate_ok") is False
                    and verdict == "MONEY_READY")
                else None
            ),
            # ENHANCEMENT #64: multiple-testing (Bonferroni/BH-FDR) pre-gate
            "_fdr_gate_enforce": _FDR_GATE_ENFORCE,
            "fdr_ok": fdr.get("ok"),
            "n_fdr_pass": fdr.get("n_fdr_pass", 0),
            "n_bonferroni_pass": fdr.get("n_bonferroni_pass", 0),
            "n_fdr_tested": fdr.get("n_tested", 0),
            "_fdr_recommend": (
                "NOT_READY"
                if (not _FDR_GATE_ENFORCE
                    and fdr.get("ok") is False
                    and verdict == "MONEY_READY")
                else None
            ),
            # ENHANCEMENT #65: single-source-artifact pre-gate
            "_single_source_gate_enforce": _SINGLE_SOURCE_GATE_ENFORCE,
            "single_source_ok": single_src.get("ok"),
            "n_profitable_multi_source": single_src.get("n_profitable_multi_source", 0),
            "n_profitable_single_source": single_src.get("n_profitable_single_source", 0),
            "_single_source_recommend": (
                "NOT_READY"
                if (not _SINGLE_SOURCE_GATE_ENFORCE
                    and single_src.get("ok") is False
                    and verdict == "MONEY_READY")
                else None
            ),
            "verdict": verdict,
            # 2026-06-04: surface BLOCKED_ASSET_CLASSES freeze status so the
            # dashboard can distinguish "policy-blocked" classes (FOREX,
            # COMMODITY, BOND, FUTURES — frozen by design until external
            # replication / source rehab) from "data-thin" classes (genuinely
            # n<MIN_N_CLASS). Both currently surface as INSUFFICIENT_DATA which
            # is technically correct but misleads operators into thinking
            # the fix is "collect more picks" when it's actually "operator
            # decision to lift freeze". Add the flag without changing verdict.
            "policy_frozen": _is_class_policy_frozen(ac),
            "data_source": data_source,
            "top_symbol": top_symbol,
            "top_symbol_share": round(top_symbol_share, 4),
            "concentration_capped": (
                top_symbol_share > MAX_SYMBOL_CONCENTRATION_BY_CLASS.get(
                    ac.upper(), MAX_SYMBOL_CONCENTRATION
                )
            ),
            "top_source": top_source,
            "top_source_share": round(top_source_share, 4),
            "source_concentration_capped": (
                top_source_share > MAX_SOURCE_CONCENTRATION_BY_CLASS.get(
                    ac.upper(), MAX_SOURCE_CONCENTRATION
                )
            ),
            "details": {"dsr": dsr, "pbo": pbo, "spa": spa, "expectancy": exp_gate,
                        "mdd_cvar": mdd_cvar, "fdr": fdr, "single_source": single_src},
        }

    return results


def print_report(results: dict[str, dict]) -> None:
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"# Money-Ready Verdict — {today}\n")
    print(f"{'Class':<12} {'n':>6} {'WR':>7} {'PF':>7} {'DSR':>6} {'PBO':>6} {'SPA':>6} {'Verdict':<18}")
    print("-" * 76)

    order = ["EQUITY", "COMMODITY", "CRYPTO", "ETF", "FOREX", "BOND", "FUTURES"]
    for ac in order + [k for k in results if k not in order]:
        if ac not in results:
            continue
        r = results[ac]
        dsr_str = "PASS" if r["dsr_ok"] is True else ("FAIL" if r["dsr_ok"] is False else "N/A")
        pbo_str = "PASS" if r["pbo_ok"] is True else ("FAIL" if r["pbo_ok"] is False else "N/A")
        spa_str = "PASS" if r["spa_ok"] is True else ("FAIL" if r["spa_ok"] is False else "N/A")
        pf_val = r["pf"]
        pf_str = f"{pf_val:7.2f}" if pf_val is not None else "    inf"
        src_tag = " [DASH]" if r.get("data_source") == "dashboard_fallback" else ""
        print(f"{ac:<12} {r['n_resolved']:>6} {r['wr']:>7.1%} {pf_str} {dsr_str:>6} {pbo_str:>6} {spa_str:>6} {r['verdict']:<18}{src_tag}")

    print("\n## Gate Thresholds")
    print(f"- n_ok: ≥{MIN_N_CLASS} resolved picks")
    _wr_floors = ", ".join(
        f"{k} {v:.0%}" for k, v in sorted(CLASS_WR_FLOORS.items())
    )
    print(f"- wr_ok: per-class SANITY floor (gross statistical-validity check, "
          f"not the promotion gate): {_wr_floors}; default {MIN_WR:.0%}")
    print(f"- expectancy_ok: net-of-slippage expectancy E > 0 — the real "
          f"money-ready promotion gate ({'ENFORCED' if _SLIPPAGE_GATE_ENABLED else 'shadow/OFF'})")
    print(f"- pf_ok: ≥{MIN_PF}")
    print(f"- DSR: probability ≥{DSR_THRESHOLD}")
    print(f"- PBO: overfit probability ≤{PBO_THRESHOLD}")
    print(f"- SPA: family-wise p ≤{SPA_ALPHA} (α={SPA_ALPHA})")

    money_ready = [ac for ac, r in results.items() if r["verdict"] == "MONEY_READY"]
    watch = [ac for ac, r in results.items() if r["verdict"] == "WATCH"]
    print(f"\n**MONEY_READY:** {', '.join(money_ready) or 'none'}")
    print(f"**WATCH:** {', '.join(watch) or 'none'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="M-061: Unified money_ready_verdict()")
    parser.add_argument("--class", dest="asset_class", help="Filter to one asset class")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    results = money_ready_verdict(asset_class=args.asset_class)
    if args.as_json:
        print(json.dumps(results, indent=2))
    else:
        print_report(results)


if __name__ == "__main__":
    main()
