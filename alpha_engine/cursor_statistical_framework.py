"""
Cursor Statistical Framework — 24-strategy paper-pilot gates

Authoritative reference: docs/PAPER_PILOT_HARNESS.md (sections G through M)
Synthesis: reports/peer_claude-TOPIC_DEEP_DIVE_SYNTHESIS_2026-05-31.md

This module provides the gate stubs invoked by the master paper-pilot
harness during the pre-emit step. The original cursor framework (Wilson LB
/ Bootstrap PF / Bonferroni / n>=500) is the per-strategy graduation suite;
the 6 stubs below close the portfolio / regime / cost / sizing / payoff
methodology gaps identified by the 6-topic deep-dive on 2026-05-31.

Wire-up: paper_pilot_harness.run_once() should call:
    1. apply_execution_costs() per trade BEFORE any other gate
    2. regime_kill() daily; if KILL/PAUSE returned, skip emission
    3. capacity_haircut() x kelly_fraction() at sizing time
    4. correlation_cluster_gate() on the 24-strategy returns matrix
    5. rr_floor_gate() per strategy, per asset class
    6. live_paper_divergence_gate() once live trades start accruing

The numerical constants below are the AI-consult-derived defaults from
the 5 successful deep-dives (DeepSeek, Grok, Qwen, Mimo, Kimi) on
2026-05-31. Gemini failed; live-vs-paper section is a Bailey/Lopez de
Prado 2014 PSR/DSR-anchored placeholder pending re-route.

NO DB WRITES. The framework is read-only over JSON sidecars per M-107.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# -------------------------------------------------------------------------
# Bonferroni — 24-strategy override
# -------------------------------------------------------------------------
FAMILY_ALPHA = 0.05
N_STRATEGIES = 24
PER_TEST_ALPHA = FAMILY_ALPHA / N_STRATEGIES  # 0.00208333 — overrides the 0.05/7 default once the 24-cohort lands

# =========================================================================
# Section H — execution costs (DeepSeek)
# =========================================================================
EXEC_COST_PARAMS: Dict[str, Dict[str, float]] = {
    "CRYPTO_MAJOR":     {"spread": 4.0,  "commission": 10.0, "impact_coeff": 0.10},
    "CRYPTO_ALTCOIN":   {"spread": 15.0, "commission": 10.0, "impact_coeff": 0.50},
    "EQUITY_SP500":     {"spread": 1.5,  "commission": 0.5,  "impact_coeff": 0.01},
    "EQUITY_SMALLCAP":  {"spread": 7.0,  "commission": 0.5,  "impact_coeff": 0.10},
    "FOREX_MAJOR":      {"spread": 0.8,  "commission": 0.2,  "impact_coeff": 0.005},
    "FOREX_CROSS":      {"spread": 3.0,  "commission": 0.2,  "impact_coeff": 0.02},
    "COMMODITY_FUTURES":{"spread": 3.0,  "commission": 1.0,  "impact_coeff": 0.05},
    "ETF_SPY":          {"spread": 1.5,  "commission": 0.5,  "impact_coeff": 0.01},
    "BOND":             {"spread": 10.0, "commission": 2.0,  "impact_coeff": 0.20},
    "FUTURES_ES":       {"spread": 0.8,  "commission": 0.3,  "impact_coeff": 0.005},
    "FUTURES_NQ":       {"spread": 1.0,  "commission": 0.5,  "impact_coeff": 0.008},
    "PREDICTION_MARKET":{"spread": 20.0, "commission": 100.0,"impact_coeff": 1.0},
}
IMPACT_NOTIONAL_FLOOR = 10_000.0


def apply_execution_costs(raw_pnl_bps: float, asset_class: str, notional_usd: float) -> float:
    """Net PnL after one-way cost = spread/2 + commission + impact.

    Refs: Almgren-Chriss (2001), Kissell (2013), Cont & Wagalath (2016), BIS Triennial.
    """
    p = EXEC_COST_PARAMS.get(asset_class)
    if p is None:
        return raw_pnl_bps  # unknown class — defer to caller, do not silently zero
    spread_cost = p["spread"] / 2.0
    commission = p["commission"]
    impact = 0.0
    if notional_usd > IMPACT_NOTIONAL_FLOOR:
        impact = p["impact_coeff"] * math.sqrt(notional_usd / 1_000_000.0)
    return raw_pnl_bps - (spread_cost + commission + impact)


# =========================================================================
# Section I — regime kill switches (Grok)
# =========================================================================
@dataclass
class RegimeSnapshot:
    vix: float
    dvix_1d: float
    rv_20: float
    rv_60: float
    pairwise_corr_20: float
    spread_z_20: float
    strat_5d_z: float


def regime_kill(asset_class: str, snap: RegimeSnapshot) -> str:
    """Return OK / PAUSE_3D / KILL. Daily-at-close call. Refs: Ang-Bekaert (2002), Diebold-Yilmaz (2012), Hamilton (1989), Cont (2001)."""
    kills: List[str] = []
    if snap.vix > 35 or snap.dvix_1d > 8:
        kills.append("VIX")
    rv_ratio = snap.rv_20 / snap.rv_60 if snap.rv_60 else 0.0
    if rv_ratio > 1.8 or rv_ratio < 0.6:
        kills.append("VOL_REGIME")
    if (asset_class in ("EQUITY", "FOREX") and snap.pairwise_corr_20 < 0.15) or snap.pairwise_corr_20 > 0.75:
        kills.append("CORR")
    if snap.spread_z_20 > 3.5:
        kills.append("LIQ")
    if snap.strat_5d_z < -3.5:
        kills.append("DD")
    if snap.strat_5d_z < -4.0:
        return "KILL"
    if len(kills) >= 2 or "DD" in kills:
        return "KILL"
    if len(kills) == 1:
        return "PAUSE_3D"
    return "OK"


# =========================================================================
# Section J — capacity haircut + Kelly (Qwen)
# =========================================================================
CAPACITY_TABLE_M: Dict[str, Dict[str, float]] = {
    "mean_rev":         {"CRYPTO": 50, "EQUITY": 200, "FOREX": 100, "COMMODITY": 100, "ETF": 150, "BOND": 300, "FUTURES": 100, "PREDICTION_MARKETS": 50},
    "momentum":         {"CRYPTO": 100,"EQUITY": 500, "FOREX": 200, "COMMODITY": 200, "ETF": 300, "BOND": 600, "FUTURES": 200, "PREDICTION_MARKETS": 100},
    "stat_arb":         {"CRYPTO": 20, "EQUITY": 100, "FOREX": 50,  "COMMODITY": 50,  "ETF": 100, "BOND": 200, "FUTURES": 50,  "PREDICTION_MARKETS": 20},
    "cross_asset_arb":  {"CRYPTO": 50, "EQUITY": 300, "FOREX": 100, "COMMODITY": 100, "ETF": 200, "BOND": 400, "FUTURES": 100, "PREDICTION_MARKETS": 50},
}
FRACTIONAL_KELLY_DEFAULT = 0.25
CAP_NAV_HIGH_CERT = 0.15
CAP_NAV_LOW_CERT = 0.05


def capacity_haircut(aum_usd_m: float, threshold_usd_m: float) -> float:
    if aum_usd_m <= 0:
        return 1.0
    return min(1.0, threshold_usd_m / aum_usd_m)


def kelly_fraction(mean_excess_return: float, variance: float, rf: float = 0.0) -> float:
    """Thorp 2006 continuous form: f* = (mu - rf) / sigma^2."""
    if variance <= 0:
        return 0.0
    return (mean_excess_return - rf) / variance


def size_strategy(
    asset_class: str,
    edge_type: str,
    mean_excess: float,
    variance: float,
    aum_usd_m: float,
    high_certainty: bool,
    full_kelly: bool = False,
) -> float:
    """Final size as fraction of NAV. Refs: Thorp (2006), MacLean/Thorp/Ziemba (2010)."""
    thr = CAPACITY_TABLE_M.get(edge_type, {}).get(asset_class, 50.0)
    h = capacity_haircut(aum_usd_m, thr)
    f = kelly_fraction(mean_excess, variance)
    if not full_kelly:
        f *= FRACTIONAL_KELLY_DEFAULT
    cap = CAP_NAV_HIGH_CERT if high_certainty else CAP_NAV_LOW_CERT
    return max(0.0, min(cap, f * h))


# =========================================================================
# Section K — cross-strategy correlation gate (Mimo)
# =========================================================================
CORR_KILL = 0.85
CORR_FLAG = 0.70
TAIL_CORR_KILL = 0.75
N_EFF_WARN = 0.50
N_EFF_KILL = 0.30
MDD_OVERLAP_KILL = 0.60
MDD_OVERLAP_DAYS = 10
MAX_CLUSTER_WEIGHT = 0.40
MAX_STRAT_WEIGHT = 0.10


@dataclass
class CorrGateResult:
    kill: bool
    violations: List[Tuple[str, str, float, str]] = field(default_factory=list)
    n_eff_ratio: Optional[float] = None
    notes: List[str] = field(default_factory=list)


def correlation_cluster_gate(
    pairwise_spearman: Dict[Tuple[str, str], float],
    n_eff_ratio: Optional[float] = None,
) -> CorrGateResult:
    """Pairwise + N_eff gate. Use risk-adjusted returns (ret / vol_63d), 252d rolling Spearman.

    Full HRP allocation + tail-cluster detection live in
    alpha_engine/paper_pilot/correlation_gate.py (separate PR per Mimo spec);
    this stub enforces the *kill* path so the harness short-circuits before
    sizing. Refs: Lopez de Prado (2016), Bouchaud & Potters (2009), Adrian &
    Brunnermeier (2016), Embrechts et al. (2002).
    """
    res = CorrGateResult(kill=False, n_eff_ratio=n_eff_ratio)
    for (a, b), rho in pairwise_spearman.items():
        r = abs(rho)
        if r > CORR_KILL:
            res.violations.append((a, b, r, "KILL"))
            res.kill = True
        elif r > CORR_FLAG:
            res.violations.append((a, b, r, "FLAG"))
    if n_eff_ratio is not None:
        if n_eff_ratio < N_EFF_KILL:
            res.kill = True
            res.notes.append(f"N_eff ratio {n_eff_ratio:.2f} < {N_EFF_KILL} KILL")
        elif n_eff_ratio < N_EFF_WARN:
            res.notes.append(f"N_eff ratio {n_eff_ratio:.2f} < {N_EFF_WARN} WARN")
    return res


# =========================================================================
# Section L — live vs paper divergence (PLACEHOLDER — Gemini failed)
# =========================================================================
@dataclass
class DivergenceResult:
    action: str  # OK | DOWN_WEIGHT | PAUSE | KILL
    reason: str


def live_paper_divergence_gate(
    pf_paper_30d: float,
    pf_live_30d: float,
    sharpe_paper_60d: float,
    sharpe_live_60d: float,
    psr_live_90d: float,
    consecutive_losers: int,
) -> DivergenceResult:
    """Bailey/Lopez de Prado (2014) DSR/PSR-anchored placeholder. Re-route to
    /consult-codex or /consult-cloudflare before live cohort begins."""
    if psr_live_90d < 0.80:
        return DivergenceResult("KILL", "psr_live_90d<0.80 — alpha decay")
    if psr_live_90d < 0.90:
        return DivergenceResult("PAUSE", "psr_live_90d<0.90")
    if pf_paper_30d > 0 and abs(pf_live_30d - pf_paper_30d) / pf_paper_30d > 0.30:
        return DivergenceResult("PAUSE", "PF 30d divergence>30%")
    if sharpe_paper_60d > 0:
        ratio = sharpe_live_60d / sharpe_paper_60d
        if ratio < 0.70 or ratio > 1.30:
            return DivergenceResult("DOWN_WEIGHT", f"Sharpe ratio {ratio:.2f} outside [0.70, 1.30]")
    if psr_live_90d < 0.95:
        return DivergenceResult("DOWN_WEIGHT", "psr_live_90d<0.95")
    if consecutive_losers >= 5:
        return DivergenceResult("PAUSE", "5 consecutive losers")
    return DivergenceResult("OK", "within tolerance")


# =========================================================================
# Section M — R:R floor + tail risk (Kimi)
# =========================================================================
RR_FLOOR_TABLE: Dict[str, Dict[str, float]] = {
    "CRYPTO":             {"rr": 1.5, "pf": 1.3, "sharpe": 1.0, "sortino": 1.5, "cvar_x_sigma": -2.5, "max_loss_nav": 0.0100, "convex_max_loss_nav": 0.0150},
    "EQUITY":             {"rr": 1.2, "pf": 1.3, "sharpe": 1.0, "sortino": 1.3, "cvar_x_sigma": -2.5, "max_loss_nav": 0.0050, "convex_max_loss_nav": 0.0075},
    "FOREX":              {"rr": 1.0, "pf": 1.2, "sharpe": 0.8, "sortino": 1.2, "cvar_x_sigma": -2.5, "max_loss_nav": 0.0050, "convex_max_loss_nav": 0.0075},
    "COMMODITY":          {"rr": 1.5, "pf": 1.3, "sharpe": 0.9, "sortino": 1.4, "cvar_x_sigma": -2.5, "max_loss_nav": 0.0075, "convex_max_loss_nav": 0.0100},
    "ETF":                {"rr": 1.0, "pf": 1.2, "sharpe": 0.8, "sortino": 1.2, "cvar_x_sigma": -2.5, "max_loss_nav": 0.0050, "convex_max_loss_nav": 0.0075},
    "BOND":               {"rr": 1.0, "pf": 1.2, "sharpe": 0.7, "sortino": 1.0, "cvar_x_sigma": -2.5, "max_loss_nav": 0.0050, "convex_max_loss_nav": 0.0075},
    "FUTURES":            {"rr": 1.2, "pf": 1.3, "sharpe": 0.9, "sortino": 1.3, "cvar_x_sigma": -2.5, "max_loss_nav": 0.0050, "convex_max_loss_nav": 0.0075},
    "PREDICTION_MARKETS": {"rr": 1.0, "pf": 1.2, "sharpe": 0.8, "sortino": 1.2, "cvar_x_sigma": -2.5, "max_loss_nav": 0.0050, "convex_max_loss_nav": 0.0075},
}


@dataclass
class RRGateResult:
    passed: bool
    tag: str  # STANDARD | CONVEX | REJECT
    reasons: List[str] = field(default_factory=list)


def rr_floor_gate(
    asset_class: str,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    pf: float,
    sortino: float,
    cvar_95: float,
    sigma_tgt_daily: float,
) -> RRGateResult:
    """Per-class R:R + 3-tier tail stack (Sortino + CVaR + modified Sharpe).

    Asymmetric (WR<30 & R:R>=3) strategies are tagged CONVEX and must go
    through the Convexity Protocol (separate gate, harness-level, not here).

    Refs: Harvey & Liu (2015), Lo (2002), MacLean/Thorp/Ziemba (2011),
    Rockafellar & Uryasev (2000), Sortino & van der Meer (1991), Taleb (2020).
    """
    floor = RR_FLOOR_TABLE.get(asset_class)
    if floor is None:
        return RRGateResult(False, "REJECT", [f"unknown asset_class={asset_class}"])
    reasons: List[str] = []
    rr = (avg_win / abs(avg_loss)) if avg_loss else math.inf
    if win_rate < 0.30 and rr >= 3.0:
        # route to convexity protocol
        return RRGateResult(False, "CONVEX", ["asymmetric payoff → Convexity Protocol"])
    if rr < floor["rr"]:
        reasons.append(f"R:R {rr:.2f} < floor {floor['rr']}")
    if pf < floor["pf"]:
        reasons.append(f"PF {pf:.2f} < floor {floor['pf']}")
    if sortino < floor["sortino"]:
        reasons.append(f"Sortino {sortino:.2f} < floor {floor['sortino']}")
    cvar_floor = floor["cvar_x_sigma"] * sigma_tgt_daily
    if cvar_95 < cvar_floor:
        reasons.append(f"CVaR-95 {cvar_95:.6f} < floor {cvar_floor:.6f}")
    if reasons:
        return RRGateResult(False, "REJECT", reasons)
    return RRGateResult(True, "STANDARD", ["all floors cleared"])


# -------------------------------------------------------------------------
# Smoke
# -------------------------------------------------------------------------
if __name__ == "__main__":
    # quick sanity check
    print("PER_TEST_ALPHA =", PER_TEST_ALPHA)
    print("net 50bps CRYPTO_ALTCOIN $50k =",
          apply_execution_costs(50, "CRYPTO_ALTCOIN", 50_000))
    snap = RegimeSnapshot(vix=20, dvix_1d=1, rv_20=0.02, rv_60=0.018,
                          pairwise_corr_20=0.4, spread_z_20=0.5, strat_5d_z=-1.0)
    print("regime CRYPTO calm =", regime_kill("CRYPTO", snap))
    print("size CRYPTO momentum =",
          size_strategy("CRYPTO", "momentum", 0.0005, 0.0001, 1.0, False))
    print("rr CRYPTO ok =",
          rr_floor_gate("CRYPTO", 0.55, 1.0, -0.6, 1.5, 1.6, -0.0050, 0.003).passed)
