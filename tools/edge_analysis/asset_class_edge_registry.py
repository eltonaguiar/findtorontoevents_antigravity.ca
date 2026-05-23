"""
Asset-Class Edge Registry — institutional-grade proven filters
==============================================================
Continues from Kilocode's asset_class_edge_analysis.py (which identified
proven strategies per class from 13,140 picks). This module structures
those findings as a registry usable at runtime for pick filtering.

Data source: audit_dashboard/data/dashboard_data.json::systems
             (post-resolver-v2 noise filter, resolved_n verdict-grade)
Last verified: 2026-05-16

Usage:
    from tools.edge_analysis.asset_class_edge_registry import get_edge_criteria, apply_edge_filter
    criteria = get_edge_criteria("CRYPTO")
    approved_picks = apply_edge_filter(picks, "CRYPTO")
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ProvenSystem:
    """A system with verified institutional-grade edge (n>=30, WR>=50%, PF>=1.5)."""
    name: str
    n: int
    win_rate: float           # percent, e.g. 75.0
    profit_factor: float
    source_system: str        # name as it appears in pick source_system field
    evidence: str             # citation for the quant reviewer


@dataclass
class EdgeCriteria:
    """Institutional-grade edge filter for one asset class.

    A pick passes the filter when ALL of:
      - source_system is in approved_systems (if non-empty)
      - confidence >= min_confidence
      - direction in approved_directions (if non-empty)
      - signal is not in blocked_strategies

    Kelly sizing: quarter-Kelly at win_rate and avg_win/loss estimates.
    """
    asset_class: str
    tradeable: bool
    tier: str                          # "T1", "T2", "Near-T2", "Below-floor", "Thin"
    resolved_n: int                    # verdict-grade resolved picks
    win_rate: float                    # class-wide WR%
    profit_factor: float               # class-wide PF
    oos_win_rate: Optional[float]      # OOS WR% from walk-forward (None if missing)
    oos_folds: int                     # number of WF folds
    oos_consistency: float             # % folds with positive WR (0-100)
    min_confidence: float              # min confidence for approved picks
    approved_systems: list[str]        # source_system values that pass filter
    approved_directions: list[str]     # ["LONG"] or ["LONG","SHORT"] or []
    blocked_strategies: list[str]      # strategies always blocked in this class
    kelly_quarter: float               # quarter-Kelly fraction (0.0–0.10 cap)
    kelly_usd_10k: float               # USD size at $10k account (capped at $1000)
    proven_systems: list[ProvenSystem] = field(default_factory=list)
    edge_secrets: list[str]            = field(default_factory=list)
    verdict: str                       = ""
    caveat: str                        = ""

    def passes(self, pick: dict) -> bool:
        """Return True if pick passes this class's edge filter."""
        if not self.tradeable:
            return False
        if pick.get("asset_class") != self.asset_class:
            return False
        conf = float(pick.get("confidence") or pick.get("score") or 0.0)
        if conf < self.min_confidence:
            return False
        if self.approved_systems:
            ss = pick.get("source_system", "") or pick.get("strategy", "")
            if ss not in self.approved_systems:
                return False
        if self.approved_directions:
            d = pick.get("direction", "LONG")
            if d not in self.approved_directions:
                return False
        strategy = pick.get("strategy", "")
        if strategy in self.blocked_strategies:
            return False
        return True

    def position_size_usd(self, account_balance: float = 10_000.0) -> float:
        """Return Kelly-sized USD position for this account balance."""
        return round(self.kelly_quarter * account_balance, 2)

    def stat_sig(self, n: Optional[int] = None) -> dict:
        """One-proportion z-test: H0=WR=50%. Returns z, p_value, significant."""
        sample_n = n or self.resolved_n
        if sample_n < 10:
            return {"z": 0.0, "p_value": 1.0, "significant": False}
        p = self.win_rate / 100.0
        p0 = 0.50
        se = math.sqrt(p0 * (1 - p0) / sample_n)
        z = (p - p0) / se if se > 0 else 0.0
        # two-tailed p approximation (normal CDF)
        import math as _m
        p_val = 2 * (1 - 0.5 * (1 + _m.erf(abs(z) / _m.sqrt(2))))
        return {"z": round(z, 3), "p_value": round(p_val, 4), "significant": p_val < 0.05}


# ---------------------------------------------------------------------------
# Registry — built from verified dashboard_data.json evidence
# ---------------------------------------------------------------------------

# Strategies confirmed as 4-6σ WR decay; quarantined 2026-05-16
_CRYPTO_SOC_QUARANTINE = [
    "crypto_soc_proxy_decoupling_a03_v1",
    "crypto_soc_proxy_decoupling_a07_v1",
    "crypto_soc_orderflow_absorption_a02_v1",
    "crypto_soc_orderflow_absorption_a03_v1",
    "crypto_soc_orderflow_absorption_a04_v1",
    "crypto_soc_orderflow_absorption_a07_v1",
    "crypto_soc_orderflow_absorption_a08_v1",
    "crypto_soc_orderflow_absorption_a09_v1",
    "crypto_soc_delta_divergence_a02_v1",
    "crypto_soc_delta_divergence_a07_v1",
    "crypto_adx_pullback_trendresume_v1",
    "crypto_choppiness_regime_switch_v1",
]

# Additional low-WR CRYPTO strategies blocked (verified n>=30, WR<45%)
_CRYPTO_BLOCKED_LOW_WR = [
    "bollinger_squeeze",
    "gainer_compression_relaxed_mut",
    "rapid_momentum_filter_mut",
    "multi_period_rsi_confluence_doge",
    "crypto_shortterm_nr_er_cci_ignition_v1",
    "crypto_shortterm_nr_er_adx_ignition_v1",
]


def _build_registry() -> dict[str, EdgeCriteria]:
    return {

        "CRYPTO": EdgeCriteria(
            asset_class="CRYPTO",
            tradeable=True,
            tier="Below-T2",
            resolved_n=7885,
            win_rate=46.5,
            profit_factor=1.31,
            oos_win_rate=45.7,
            oos_folds=54,
            oos_consistency=74.1,
            min_confidence=0.65,
            approved_systems=[
                "kimi_signal_tracking",   # n=1199, WR=75.0%, PF=5.43
                "signal_validation",      # n=567,  WR=59.5%, PF=4.70
                "ml_crypto_pred_v12",     # n=123,  WR=55.6%, PF=2.53
                "mega_mutation",          # n=291,  WR=58.8%, PF=2.43
                "claude_gainer",          # n=965,  WR=56.2%, PF=2.23
                "copy_trader_intel",      # n=688,  WR=50.0%, PF=1.84
            ],
            approved_directions=["LONG", "SHORT"],
            blocked_strategies=_CRYPTO_SOC_QUARANTINE + _CRYPTO_BLOCKED_LOW_WR,
            kelly_quarter=0.075,   # claude_gainer basis: WR=56.2%, avg_win=2%, avg_loss=1.2%
            kelly_usd_10k=748.0,
            proven_systems=[
                ProvenSystem("kimi_signal_tracking", 1199, 75.0, 5.43,
                             "kimi_signal_tracking",
                             "dashboard_data.json::systems[kimi_signal_tracking]"),
                ProvenSystem("signal_validation", 567, 59.5, 4.70,
                             "signal_validation",
                             "dashboard_data.json::systems[signal_validation]"),
                ProvenSystem("claude_gainer", 965, 56.2, 2.23,
                             "claude_gainer",
                             "dashboard_data.json::systems[claude_gainer]"),
            ],
            edge_secrets=[
                "Class-wide WR=46.5% is dragged by alpha_engine (WR=44.8%, n=12528). "
                "Filter to approved_systems above to get WR=56-75% on n>=100 samples.",
                "Confidence deadzone 0.65-0.75: picks in this band have lower WR than "
                "picks at conf>=0.75 (Kilocode analysis 2026-05-16 on 13,140 picks).",
                "12 crypto_soc baby_strats quarantined (4-6σ WR decay: BT WR 49-66% → "
                "OOS WR 33-41%). All blocked in quality_gates.py.",
                "Concept drift alert ACTIVE — reduce sizing 20% until drift resolves.",
            ],
            verdict="SYSTEM-FILTERED INVEST: approved_systems only, conf>=0.65",
            caveat="Class-wide OOS WR=45.7% is below coin-flip. Only trade approved systems.",
        ),

        "EQUITY": EdgeCriteria(
            asset_class="EQUITY",
            tradeable=True,
            tier="T2",
            resolved_n=425,
            win_rate=51.5,
            profit_factor=1.56,
            oos_win_rate=62.2,
            oos_folds=8,
            oos_consistency=100.0,
            min_confidence=0.60,
            approved_systems=[
                "aggregated_picks",         # n=427, WR=76.3%, PF=5.35
                "multi_asset_copytrader",   # n=1833, WR=66.0%, PF=3.14
                "multi_asset_institutional",# n=58,  WR=66.7%, PF=2.01
            ],
            approved_directions=["LONG"],
            blocked_strategies=[],
            kelly_quarter=0.051,   # class-wide: WR=51.5%, avg_win=4.68%, avg_loss=3.0%
            kelly_usd_10k=510.0,
            proven_systems=[
                ProvenSystem("aggregated_picks", 427, 76.3, 5.35,
                             "aggregated_picks",
                             "dashboard_data.json::systems[aggregated_picks]"),
                ProvenSystem("multi_asset_institutional", 58, 66.7, 2.01,
                             "multi_asset_institutional",
                             "dashboard_data.json::systems[multi_asset_institutional] — n<100, corroborative only"),
            ],
            edge_secrets=[
                "OOS WR=62.2% across 8 folds with 100% fold consistency — "
                "strongest OOS consistency in the system.",
                "aggregated_picks WR=76.3% (n=427): highest-conviction EQUITY filter. "
                "Kilocode identified MomentumEMA at 72.7% WR, PF=4.94 within this system.",
                "elite_score>=55 gate active: picks with score<55 have WR=33.3% (n=44 verified).",
                "Recent hf_stats: WR=52.4%, PF=1.82 — improving trend vs resolved_n baseline.",
            ],
            verdict="INVEST: T2 met (PF=1.56, WR=51.5%, OOS=62.2%, n=425)",
            caveat="aggregated_picks MDD=88% on raw PnL. Use $510/pick cap to bound drawdown.",
        ),

        "COMMODITY": EdgeCriteria(
            asset_class="COMMODITY",
            tradeable=True,
            tier="T1-candidate",
            resolved_n=337,
            win_rate=62.6,
            profit_factor=2.57,
            oos_win_rate=None,
            oos_folds=0,
            oos_consistency=0.0,
            min_confidence=0.60,
            approved_systems=[
                "multi_asset_cot",        # n=131, WR=79.4%, PF=4.72
                "multi_asset_copytrader", # n=1833, WR=66.0%, PF=3.14
            ],
            approved_directions=["LONG"],
            blocked_strategies=["CT=F"],  # blacklisted non-tradeable future
            kelly_quarter=0.10,   # multi_asset_cot: WR=79.4% → full cap applied
            kelly_usd_10k=500.0,  # conservative: no walkforward OOS verification
            proven_systems=[
                ProvenSystem("multi_asset_cot", 131, 79.4, 4.72,
                             "multi_asset_cot",
                             "dashboard_data.json::systems[multi_asset_cot]; "
                             "cot_positioning_CT_locked LONG: WR=89.8% PF=13.1 n=49"),
            ],
            edge_secrets=[
                "multi_asset_cot is the statistically strongest single edge on the system. "
                "Kilocode confirmed COT-based strategies at 78.2% WR, PF=4.64.",
                "CRITICAL CAVEAT: CT=F cotton over-emission (14 signals/day from same CFTC "
                "release). CT=F blacklisted. COT-dedup guard (72h) active since 2026-05-14. "
                "Post-dedup clean picks still accumulating — use $500/pick until n>=100 post-dedup.",
                "Walkforward OOS MISSING for COMMODITY — treat PF=2.57 with caution.",
                "Avoid picks older than 72h from same COMMODITY symbol (COT dedup window).",
            ],
            verdict="INVEST WITH CAVEAT: COT-dedup guard active, await 100 clean post-dedup picks",
            caveat="No walkforward OOS. COT dedup artifact inflated PF. Size conservatively.",
        ),

        "ETF": EdgeCriteria(
            asset_class="ETF",
            tradeable=True,
            tier="Near-T2",
            resolved_n=107,
            win_rate=57.0,
            profit_factor=1.32,
            oos_win_rate=75.0,
            oos_folds=5,
            oos_consistency=100.0,
            min_confidence=0.65,
            approved_systems=[
                "multi_asset_institutional",  # n=58, WR=66.7%, PF=2.01
            ],
            approved_directions=["LONG", "SHORT"],
            blocked_strategies=["SLV"],  # n=2, WR=0%, sum PnL=-15.74%
            kelly_quarter=0.062,   # class-wide: WR=57%, avg_win=2.0%, avg_loss=1.5%
            kelly_usd_10k=619.0,
            proven_systems=[
                ProvenSystem("multi_asset_institutional", 58, 66.7, 2.01,
                             "multi_asset_institutional",
                             "dashboard_data.json::systems[multi_asset_institutional] — n<100"),
            ],
            edge_secrets=[
                "OOS WR=75% across 5 folds with 100% fold consistency — "
                "best OOS WR in the system, but only 5 folds (limited confidence).",
                "Charter floor n>=100 NOW MET (n=107). Target: n>=150 for OOS_READY promotion.",
                "Recent hf_stats: WR=58.7%, PF=1.49 — approaching T2 PF floor.",
                "SLV blacklisted (n=2, WR=0%, sum PnL=-15.74%). Exclude from all filters.",
                "ETF sector emitter was default-ON but emitting 0 picks (silent failure) — "
                "investigate if ETF n growth stalls.",
            ],
            verdict="INVEST (limited size): Near-T2, strong OOS but PF=1.32 below T2 floor",
            caveat="PF=1.32 below T2 floor of 1.5. Size at $619/pick until PF lifted.",
        ),

        "FOREX": EdgeCriteria(
            asset_class="FOREX",
            tradeable=False,
            tier="Below-floor",
            resolved_n=311,
            win_rate=54.7,
            profit_factor=0.86,
            oos_win_rate=None,
            oos_folds=0,
            oos_consistency=0.0,
            min_confidence=0.99,  # effectively blocks all picks
            approved_systems=[],
            approved_directions=[],
            blocked_strategies=[],
            kelly_quarter=0.0,
            kelly_usd_10k=0.0,
            proven_systems=[],
            edge_secrets=[
                "Historical WR=54.7% is misleading. Recent hf_stats WR=30.4% (n=148) — "
                "severe recent WR collapse. Do NOT trade FOREX.",
                "Kilocode found overall 25.8% WR on raw picks. Historical resolved_n WR "
                "overstates real edge due to LONG-direction bias.",
                "Mutation protocol active. LONG-direction blocks pending 2026-05-22 re-eval.",
                "Walkforward OOS MISSING. No verified OOS edge.",
            ],
            verdict="DO NOT TRADE: PF=0.86 (below 1.0), recent WR=30.4%",
            caveat="sizing_allowed=False in system. Await mutation protocol + n>=50 clean picks.",
        ),

        "BOND": EdgeCriteria(
            asset_class="BOND",
            tradeable=False,
            tier="Thin",
            resolved_n=11,
            win_rate=54.5,
            profit_factor=0.66,
            oos_win_rate=56.2,
            oos_folds=8,
            oos_consistency=50.0,
            min_confidence=0.99,
            approved_systems=[],
            approved_directions=[],
            blocked_strategies=[],
            kelly_quarter=0.0,
            kelly_usd_10k=0.0,
            proven_systems=[],
            edge_secrets=[
                "OOS Sharpe=16.224 is N_INSUFFICIENT artifact — 2-pick test folds at n=11 total. "
                "Do NOT interpret as real edge.",
                "BOND_ELITE_FLOOR lowered to 15 (was 35). Scanner now active; accumulating picks.",
                "OOS consistency=50% (4/8 folds positive). Inconclusive at n=11.",
                "Projected n=100 arrival: ~20 weeks at current emission rate (~5/week).",
            ],
            verdict="ACCUMULATING: n=11, await n>=100 charter floor",
            caveat="No tradeable edge at n=11. Revisit when n>=100.",
        ),
    }


# Module-level singleton
_REGISTRY: dict[str, EdgeCriteria] | None = None


def get_registry() -> dict[str, EdgeCriteria]:
    """Return the full edge registry (built once, cached)."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def get_edge_criteria(asset_class: str) -> EdgeCriteria:
    """Return EdgeCriteria for one asset class. Raises KeyError if unknown."""
    return get_registry()[asset_class.upper()]


def apply_edge_filter(picks: list[dict], asset_class: str | None = None) -> list[dict]:
    """Filter picks to those passing the institutional-grade edge criteria.

    Args:
        picks:       list of pick dicts (each must have 'asset_class' key)
        asset_class: if given, only apply filter for this class; else all classes

    Returns:
        Filtered list. Picks from non-tradeable classes are always excluded.
    """
    reg = get_registry()
    approved = []
    for pick in picks:
        cls = pick.get("asset_class", "")
        if asset_class and cls != asset_class.upper():
            continue
        criteria = reg.get(cls)
        if criteria and criteria.passes(pick):
            approved.append(pick)
    return approved


def stat_sig_summary() -> list[dict]:
    """Return one-proportion z-test results for every class in the registry."""
    return [
        {
            "asset_class": cls,
            "n": c.resolved_n,
            "win_rate": c.win_rate,
            **c.stat_sig(),
            "tradeable": c.tradeable,
            "verdict": c.verdict,
        }
        for cls, c in get_registry().items()
    ]


def print_registry_report() -> None:
    """Print an institutional-grade edge summary to stdout."""
    reg = get_registry()
    print("=" * 72)
    print("ASSET-CLASS EDGE REGISTRY — institutional-grade filters")
    print("Data: audit_dashboard/data/dashboard_data.json (post-resolver-v2)")
    print("=" * 72)
    for cls, c in reg.items():
        sig = c.stat_sig()
        print(f"\n{'─'*60}")
        print(f"{cls} | Tier: {c.tier} | Tradeable: {c.tradeable}")
        print(f"  Class: n={c.resolved_n}, WR={c.win_rate}%, PF={c.profit_factor}")
        if c.oos_win_rate is not None:
            print(f"  OOS:   WR={c.oos_win_rate}% ({c.oos_folds} folds, {c.oos_consistency}% consistent)")
        else:
            print("  OOS:   MISSING (walkforward not available)")
        print(f"  Stat-sig (H0=WR=50%): z={sig['z']}, p={sig['p_value']}, "
              f"{'SIGNIFICANT' if sig['significant'] else 'NOT SIGNIFICANT'}")
        if c.tradeable:
            print(f"  Kelly (¼-fraction): {c.kelly_quarter*100:.1f}% = ${c.kelly_usd_10k:.0f}/pick at $10k")
            if c.approved_systems:
                print(f"  Approved systems: {', '.join(c.approved_systems[:3])}"
                      f"{'...' if len(c.approved_systems) > 3 else ''}")
        print(f"  Verdict: {c.verdict}")
        if c.caveat:
            print(f"  Caveat: {c.caveat}")
    print(f"\n{'=' * 72}")


if __name__ == "__main__":
    print_registry_report()
    print("\n--- Statistical Significance Summary ---")
    for row in stat_sig_summary():
        flag = "✓ SIGNIFICANT" if row["significant"] else "✗ not sig"
        trade = "TRADE" if row["tradeable"] else "SKIP"
        print(f"  {row['asset_class']:12s} n={row['n']:5d} WR={row['win_rate']:5.1f}% "
              f"z={row['z']:6.2f} p={row['p_value']:.4f} {flag:15s} [{trade}]")
