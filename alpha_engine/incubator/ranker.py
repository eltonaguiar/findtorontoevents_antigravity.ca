"""
Incubator — Multi-Objective Ranker
=====================================
Combines backtest metrics into a single composite score and produces
ranked lists for:
  1. Combined BTC-USD & ETH-USD
  2. Individual market rankings
  3. Per-archetype best performers

Scoring: 0.4×Sharpe − 0.3×MaxDD + 0.2×ProfitFactor + 0.1×WinRate

Also applies paper-trading readiness filters:
  - Sharpe > 1.2
  - MaxDrawdown < 15%
  - MinTrades >= 10
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .fast_backtester import BacktestResult

# Deflated Sharpe Ratio — graceful degradation if validation module unavailable
try:
    from ..validation.metrics import PerformanceMetrics as _PM
    _compute_dsr = _PM.compute_deflated_sharpe
except Exception:                       # pragma: no cover
    _compute_dsr = None                 # DSR gate disabled


# Weights for composite score
W_SHARPE = 0.40
W_DRAWDOWN = 0.30
W_PROFIT_FACTOR = 0.20
W_WIN_RATE = 0.10

# Paper-trading readiness thresholds
MIN_SHARPE = 1.2
MAX_DRAWDOWN_PCT = 0.15  # 15%
MIN_TRADES = 20          # raised from 10 (2026-05-18 MASTER_ENHANCEMENT_PLAN hardening)
MIN_WIN_RATE = 0.50      # raised from 0.45 — aligns with money_ready_verdict() threshold
MIN_DSR_PROB = 0.75  # Deflated Sharpe Ratio probability threshold (Bailey & Lopez de Prado)

# Walk-forward / cross-symbol consistency gate (MASTER_ENHANCEMENT_PLAN P1 hardening)
# Proxy for walk-forward min_window_consistency: require Sharpe > 0 in ≥60% of tested symbols.
MIN_SYMBOL_SIGN_CONSISTENCY = 0.60  # fraction of symbols with positive Sharpe
MIN_SYMBOLS_FOR_CONSISTENCY = 4     # only apply consistency gate when ≥4 symbols are tested


@dataclass
class RankedCandidate:
    """A ranked incubator candidate."""
    perm_id: str
    archetype: str
    params: dict
    seed_strategy: str

    # Combined metrics (avg across symbols)
    combined_sharpe: float = 0.0
    combined_sortino: float = 0.0
    combined_max_dd: float = 0.0
    combined_pf: float = 0.0
    combined_wr: float = 0.0
    combined_trades: int = 0
    combined_return: float = 0.0

    # Per-symbol results
    per_symbol: dict[str, dict] = field(default_factory=dict)

    # Composite score
    composite_score: float = 0.0

    # Status
    ready_for_paper: bool = False
    rejection_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "perm_id": self.perm_id,
            "archetype": self.archetype,
            "params": self.params,
            "seed_strategy": self.seed_strategy,
            "combined_sharpe": round(self.combined_sharpe, 3),
            "combined_sortino": round(self.combined_sortino, 3),
            "combined_max_dd": round(self.combined_max_dd, 6),
            "combined_pf": round(self.combined_pf, 3),
            "combined_wr": round(self.combined_wr, 4),
            "combined_trades": self.combined_trades,
            "combined_return": round(self.combined_return, 6),
            "composite_score": round(self.composite_score, 4),
            "ready_for_paper": self.ready_for_paper,
            "rejection_reasons": self.rejection_reasons,
            "per_symbol": self.per_symbol,
        }


def rank_results(
    results: list[BacktestResult],
    top_n: int = 15,
) -> dict:
    """Rank backtest results and produce incubator candidates.

    Returns:
        {
            "combined_ranking": [RankedCandidate, ...],
            "per_symbol_ranking": {"BTC-USD": [...], "ETH-USD": [...]},
            "per_archetype_best": {"rsi_mean_reversion": [...], ...},
            "paper_ready": [RankedCandidate, ...],
            "summary": {...}
        }
    """
    if not results:
        return {"combined_ranking": [], "per_symbol_ranking": {},
                "per_archetype_best": {}, "paper_ready": [], "summary": {}}

    # Group results by perm_id
    by_perm: dict[str, list[BacktestResult]] = {}
    for r in results:
        by_perm.setdefault(r.perm_id, []).append(r)

    # Build combined candidates
    candidates: list[RankedCandidate] = []
    for perm_id, perm_results in by_perm.items():
        if not perm_results:
            continue

        first = perm_results[0]
        candidate = RankedCandidate(
            perm_id=perm_id,
            archetype=first.archetype,
            params=first.params,
            seed_strategy=first.seed_strategy,
        )

        # Average metrics across symbols
        sharpes = [r.sharpe for r in perm_results if r.total_trades > 0]
        sortinos = [r.sortino for r in perm_results if r.total_trades > 0]
        dds = [r.max_drawdown for r in perm_results if r.total_trades > 0]
        pfs = [r.profit_factor for r in perm_results if r.total_trades > 0]
        wrs = [r.win_rate for r in perm_results if r.total_trades > 0]
        trades = sum(r.total_trades for r in perm_results)
        returns = [r.total_return for r in perm_results if r.total_trades > 0]

        if not sharpes:
            continue

        candidate.combined_sharpe = float(np.mean(sharpes))
        candidate.combined_sortino = float(np.mean(sortinos))
        candidate.combined_max_dd = float(np.min(dds))  # worst DD across markets
        candidate.combined_pf = float(np.mean(pfs))
        candidate.combined_wr = float(np.mean(wrs))
        candidate.combined_trades = trades
        candidate.combined_return = float(np.mean(returns))

        # Per-symbol detail
        for r in perm_results:
            candidate.per_symbol[r.symbol] = r.to_dict()

        # Composite score
        candidate.composite_score = _compute_composite(candidate)

        # Paper-trading readiness (n_trials = total permutations tested, for DSR)
        _check_paper_ready(candidate, n_trials=len(by_perm))

        candidates.append(candidate)

    # Sort by composite score
    candidates.sort(key=lambda c: c.composite_score, reverse=True)

    # Build rankings
    combined_ranking = candidates[:top_n]

    # Per-symbol rankings
    per_symbol_ranking: dict[str, list[dict]] = {}
    symbols = set()
    for r in results:
        symbols.add(r.symbol)
    for sym in symbols:
        sym_results = [r for r in results if r.symbol == sym and r.total_trades > 0]
        sym_results.sort(key=lambda r: _single_composite(r), reverse=True)
        per_symbol_ranking[sym] = [r.to_dict() for r in sym_results[:top_n]]

    # Per-archetype best
    per_archetype: dict[str, list[dict]] = {}
    for c in candidates:
        per_archetype.setdefault(c.archetype, []).append(c.to_dict())
    # Keep top 5 per archetype
    for k in per_archetype:
        per_archetype[k] = per_archetype[k][:5]

    # Paper-ready candidates
    paper_ready = [c for c in candidates if c.ready_for_paper]

    summary = {
        "total_permutations_tested": len(by_perm),
        "total_backtests": len(results),
        "candidates_ranked": len(candidates),
        "paper_ready_count": len(paper_ready),
        "avg_composite_score": round(float(np.mean([c.composite_score for c in candidates])), 4) if candidates else 0,
        "best_composite_score": round(candidates[0].composite_score, 4) if candidates else 0,
        "best_sharpe": round(max(c.combined_sharpe for c in candidates), 3) if candidates else 0,
        "best_archetype": candidates[0].archetype if candidates else "none",
        "archetypes_tested": len(per_archetype),
    }

    return {
        "combined_ranking": [c.to_dict() for c in combined_ranking],
        "per_symbol_ranking": per_symbol_ranking,
        "per_archetype_best": per_archetype,
        "paper_ready": [c.to_dict() for c in paper_ready],
        "summary": summary,
    }


def _compute_composite(c: RankedCandidate) -> float:
    """Compute composite score: 0.4*Sharpe - 0.3*|MaxDD| + 0.2*PF + 0.1*WR."""
    # Normalize to reasonable scales
    sharpe_n = np.clip(c.combined_sharpe / 5.0, -1, 1)  # scale to [-1, 1] at Sharpe=5
    dd_n = np.clip(abs(c.combined_max_dd) / 0.30, 0, 1)  # 30% DD = max penalty
    pf_n = np.clip(c.combined_pf / 3.0, 0, 1)            # PF=3 is excellent
    wr_n = c.combined_wr                                   # already 0-1

    return float(
        W_SHARPE * sharpe_n
        - W_DRAWDOWN * dd_n
        + W_PROFIT_FACTOR * pf_n
        + W_WIN_RATE * wr_n
    )


def _single_composite(r: BacktestResult) -> float:
    """Composite score for a single backtest result."""
    sharpe_n = np.clip(r.sharpe / 5.0, -1, 1)
    dd_n = np.clip(abs(r.max_drawdown) / 0.30, 0, 1)
    pf_n = np.clip(r.profit_factor / 3.0, 0, 1)
    wr_n = r.win_rate

    return float(
        W_SHARPE * sharpe_n
        - W_DRAWDOWN * dd_n
        + W_PROFIT_FACTOR * pf_n
        + W_WIN_RATE * wr_n
    )


def _check_paper_ready(c: RankedCandidate, n_trials: int = 1000) -> None:
    """Check if candidate meets paper-trading thresholds.

    Gates (ALL must pass):
      1. Sharpe >= MIN_SHARPE
      2. MaxDrawdown <= MAX_DRAWDOWN_PCT
      3. Trades >= MIN_TRADES
      4. WinRate >= MIN_WIN_RATE
      5. DSR probability >= MIN_DSR_PROB (deflated Sharpe ratio — guards against
         data-snooping bias when many permutations are tested; Bailey & Lopez de
         Prado, 2014)
    """
    reasons = []

    if c.combined_sharpe < MIN_SHARPE:
        reasons.append(f"Sharpe {c.combined_sharpe:.2f} < {MIN_SHARPE}")
    if abs(c.combined_max_dd) > MAX_DRAWDOWN_PCT:
        reasons.append(f"MaxDD {abs(c.combined_max_dd):.1%} > {MAX_DRAWDOWN_PCT:.0%}")
    if c.combined_trades < MIN_TRADES:
        reasons.append(f"Trades {c.combined_trades} < {MIN_TRADES}")
    if c.combined_wr < MIN_WIN_RATE:
        reasons.append(f"WinRate {c.combined_wr:.1%} < {MIN_WIN_RATE:.0%}")

    # Deflated Sharpe Ratio gate — rejects strategies whose Sharpe is likely
    # explained by multiple-testing luck rather than a genuine edge.
    if _compute_dsr is not None and c.combined_trades >= MIN_TRADES:
        try:
            dsr_prob = _compute_dsr(
                sharpe=c.combined_sharpe,
                n_trials=max(n_trials, 1),
                n_observations=c.combined_trades,
            )
            if dsr_prob < MIN_DSR_PROB:
                reasons.append(f"DSR {dsr_prob:.3f} < {MIN_DSR_PROB}")
        except Exception:
            pass  # graceful degradation — skip DSR if scipy missing, etc.

    # Cross-symbol sign-consistency gate — proxy for walk-forward consistency.
    # Requires that at least MIN_SYMBOL_SIGN_CONSISTENCY fraction of tested symbols
    # show positive Sharpe. Catches strategies that are marginal on average but
    # only profitable on one dominant symbol (curve-fit or regime-specific).
    if c.per_symbol and len(c.per_symbol) >= MIN_SYMBOLS_FOR_CONSISTENCY:
        positive_sharpe = sum(
            1 for sym_res in c.per_symbol.values()
            if isinstance(sym_res, dict) and sym_res.get("sharpe", 0.0) > 0
        )
        consistency = positive_sharpe / len(c.per_symbol)
        if consistency < MIN_SYMBOL_SIGN_CONSISTENCY:
            reasons.append(
                f"SymbolConsistency {consistency:.0%} < {MIN_SYMBOL_SIGN_CONSISTENCY:.0%} "
                f"({positive_sharpe}/{len(c.per_symbol)} symbols Sharpe>0)"
            )

    c.rejection_reasons = reasons
    c.ready_for_paper = len(reasons) == 0
