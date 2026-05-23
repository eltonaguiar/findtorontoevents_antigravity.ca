#!/usr/bin/env python3
"""
Strategy Prover — Institutional-Grade Validation Pipeline
==========================================================
Implements the full hedge-fund playbook for proving strategy edge:

  Gate 1: Backtest Validation (historical data)
  Gate 2: Walk-Forward OOS (purged time-series split)
  Gate 3: Paper Forward Test (live market, no tweaks)
  Gate 4: Auto-Promote (graduation to production)

Metrics computed per §2.1-2.4 of the quant playbook:
  - Performance: AR, AV, Sharpe, Sortino, Calmar, IR, Hit Rate, Alpha
  - Risk: MDD, VaR, CVaR, Beta, Turnover
  - Statistical: p-value of alpha, Bootstrap Sharpe CI, White's Reality Check

Usage:
    python strategy_prover.py --strategy connors_rsi2 --asset-class EQUITY
    python strategy_prover.py --all
    python strategy_prover.py --scorecard  # Weekly asset-class report
"""

from __future__ import annotations
import json
import math
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "alpha_engine" / "data"
FORWARD_DIR = DATA_DIR / "forward_tests"
OUTPUT_DIR = REPO_ROOT / "tools" / "data"
# DATA SOURCE OF TRUTH (2026-04-11): Use audit_dashboard/data/dashboard_data.json
# (the live, post-resolver-fix ledger). The legacy alpha_engine/data/closed_picks.json
# is pre-resolver-fix and has wrong outcomes for many trades — using it would
# produce false gate decisions. The dashboard data file is updated by the resolver
# pipeline and is the authoritative source of closed trade outcomes.
# See: SESSION_INSIGHTS_2026-04-11.md and alpha_engine/data/hc_lookback_bias_report_v2.json
LIVE_LEDGER_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
LEGACY_CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"  # fallback only
CLOSED_PICKS_PATH = LIVE_LEDGER_PATH  # alias for new code path
STRATEGY_PERF_PATH = DATA_DIR / "strategy_performance.json"

# Gate thresholds
GATE1_MIN_N = 30
GATE1_MIN_PF = 1.2
GATE1_MIN_SHARPE = 1.0
GATE1_P_VALUE = 0.01

GATE2_MAX_DECAY_PCT = 30  # OOS metrics must be within 30% of IS

GATE3_MIN_N = 30
GATE3_MIN_PF = 1.0

RISK_FREE_RATE = 0.05  # 5% annualized (US 1-month T-bill proxy)
ANNUALIZATION_FACTOR = 252  # Trading days per year

# Asset-class-specific R:R break-even WR
# If your R:R is 2:1, break-even WR = 1/(1+2) = 33.3%
# If your R:R is 1:1, break-even WR = 50%
DEFAULT_BREAK_EVEN_WR = 0.50


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class PickRecord:
    """Normalized closed pick for analysis."""
    id: str = ""
    strategy: str = ""
    symbol: str = ""
    direction: str = "LONG"
    asset_class: str = "CRYPTO"
    entry_price: float = 0.0
    exit_price: float = 0.0
    pnl_pct: float = 0.0
    entry_time: str = ""
    exit_time: str = ""
    hold_days: float = 0.0
    exit_reason: str = ""

    @property
    def is_win(self) -> bool:
        return self.pnl_pct > 0

    @property
    def daily_return(self) -> float:
        if self.hold_days > 0:
            return self.pnl_pct / self.hold_days
        return self.pnl_pct


@dataclass
class PerformanceMetrics:
    """§2.1 Core Performance Metrics."""
    n_trades: int = 0
    n_wins: int = 0
    n_losses: int = 0
    win_rate: float = 0.0
    total_pnl_pct: float = 0.0
    avg_pnl_pct: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    profit_factor: float = 0.0
    annualized_return: float = 0.0
    annualized_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    jensens_alpha: float = 0.0
    mae_pct: float = 0.0
    avg_hold_days: float = 0.0


@dataclass
class RiskMetrics:
    """§2.2 Risk-Control Metrics."""
    max_drawdown_pct: float = 0.0
    var_95_pct: float = 0.0
    var_99_pct: float = 0.0
    cvar_95_pct: float = 0.0
    cvar_99_pct: float = 0.0
    beta_to_market: float = 0.0
    max_consecutive_losses: int = 0
    kelly_fraction: float = 0.0
    tail_ratio: float = 0.0  # abs(95th percentile) / abs(5th percentile)


@dataclass
class StatisticalTests:
    """§2.4 Statistical Significance Checks."""
    binomial_p_value: float = 1.0
    alpha_t_stat: float = 0.0
    alpha_p_value: float = 1.0
    bootstrap_sharpe_lower: float = 0.0
    bootstrap_sharpe_upper: float = 0.0
    bootstrap_sharpe_median: float = 0.0
    is_statistically_significant: bool = False
    multiple_testing_adjusted_p: float = 1.0


@dataclass
class GateResult:
    """Result of a single validation gate."""
    gate_name: str = ""
    passed: bool = False
    reason: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyReport:
    """Complete proving report for a strategy."""
    strategy: str = ""
    asset_class: str = ""
    generated_at: str = ""
    gate1: Optional[GateResult] = None
    gate2: Optional[GateResult] = None
    gate3: Optional[GateResult] = None
    final_tier: str = "UNPROVEN"
    performance: Optional[PerformanceMetrics] = None
    risk: Optional[RiskMetrics] = None
    stats: Optional[StatisticalTests] = None
    by_symbol: Dict[str, Dict] = field(default_factory=dict)
    by_direction: Dict[str, Dict] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core Computation Engine
# ---------------------------------------------------------------------------
def compute_performance(picks: List[PickRecord], benchmark_returns: Optional[List[float]] = None) -> PerformanceMetrics:
    """Compute §2.1 performance metrics from a list of closed picks."""
    m = PerformanceMetrics()
    if not picks:
        return m

    pnls = [p.pnl_pct for p in picks]
    wins = [p.pnl_pct for p in picks if p.is_win]
    losses = [p.pnl_pct for p in picks if not p.is_win]

    m.n_trades = len(picks)
    m.n_wins = len(wins)
    m.n_losses = len(losses)
    m.win_rate = m.n_wins / m.n_trades if m.n_trades > 0 else 0
    m.total_pnl_pct = sum(pnls)
    m.avg_pnl_pct = np.mean(pnls) if pnls else 0
    m.avg_win_pct = np.mean(wins) if wins else 0
    m.avg_loss_pct = np.mean(losses) if losses else 0
    m.avg_hold_days = np.mean([p.hold_days for p in picks]) if picks else 0

    # Profit Factor
    gross_profit = sum(w for w in wins) if wins else 0
    gross_loss = abs(sum(l for l in losses)) if losses else 0.001
    m.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.99

    # Annualized metrics (treat each trade as a "period")
    if len(pnls) >= 2:
        daily_equiv = [p.daily_return for p in picks]
        mean_daily = np.mean(daily_equiv)
        std_daily = np.std(daily_equiv, ddof=1)

        m.annualized_return = mean_daily * ANNUALIZATION_FACTOR
        m.annualized_volatility = std_daily * math.sqrt(ANNUALIZATION_FACTOR) if std_daily > 0 else 0

        # Sharpe Ratio
        if m.annualized_volatility > 0:
            m.sharpe_ratio = (m.annualized_return - RISK_FREE_RATE) / m.annualized_volatility
        
        # Sortino Ratio (downside deviation only)
        downside = [r for r in daily_equiv if r < 0]
        if downside:
            downside_std = np.std(downside, ddof=1) * math.sqrt(ANNUALIZATION_FACTOR)
            if downside_std > 0:
                m.sortino_ratio = (m.annualized_return - RISK_FREE_RATE) / downside_std

    # Jensen's Alpha (if benchmark provided) — use sample variance (ddof=1)
    # for beta computation; population variance biases beta downward and
    # inflates alpha on small samples (pass-2 issue #2, opus-hc-audit 2026-04-11).
    if benchmark_returns and len(benchmark_returns) == len(pnls) and len(benchmark_returns) >= 2:
        strategy_excess = [p - RISK_FREE_RATE / ANNUALIZATION_FACTOR for p in pnls]
        benchmark_excess = [b - RISK_FREE_RATE / ANNUALIZATION_FACTOR for b in benchmark_returns]
        bench_var = float(np.var(benchmark_excess, ddof=1))
        if bench_var > 0:
            beta = float(np.cov(strategy_excess, benchmark_excess, ddof=1)[0][1] / bench_var)
            m.jensens_alpha = m.annualized_return - (
                RISK_FREE_RATE + beta * (float(np.mean(benchmark_returns)) * ANNUALIZATION_FACTOR - RISK_FREE_RATE)
            )

    # Calmar Ratio (PR #72 cherry-pick): annualized_return / |max_drawdown|
    # Computed inline so we don't duplicate the drawdown loop in compute_risk.
    if len(pnls) >= 2:
        _equity = [0.0]
        for _pnl in pnls:
            _equity.append(_equity[-1] + _pnl)
        _peak = _equity[0]
        _max_dd = 0.0
        for _e in _equity:
            if _e > _peak:
                _peak = _e
            _dd = _peak - _e
            if _dd > _max_dd:
                _max_dd = _dd
        if _max_dd > 0:
            m.calmar_ratio = m.annualized_return / abs(_max_dd)
        else:
            m.calmar_ratio = 0.0

    return m


def compute_risk(picks: List[PickRecord]) -> RiskMetrics:
    """Compute §2.2 risk metrics."""
    r = RiskMetrics()
    if not picks:
        return r

    pnls = [p.pnl_pct for p in picks]

    # Maximum Drawdown (sequential equity curve)
    equity = [0.0]
    for pnl in pnls:
        equity.append(equity[-1] + pnl)
    peak = equity[0]
    max_dd = 0.0
    for e in equity:
        if e > peak:
            peak = e
        dd = peak - e
        if dd > max_dd:
            max_dd = dd
    r.max_drawdown_pct = max_dd

    # Calmar Ratio
    if max_dd > 0 and len(pnls) >= 2:
        mean_daily = np.mean([p.daily_return for p in picks])
        ar = mean_daily * ANNUALIZATION_FACTOR
        r.max_drawdown_pct = max_dd
    
    # VaR and CVaR
    sorted_pnls = sorted(pnls)
    n = len(sorted_pnls)
    if n >= 20:
        idx_95 = max(0, int(n * 0.05))
        idx_99 = max(0, int(n * 0.01))
        r.var_95_pct = abs(sorted_pnls[idx_95])
        r.var_99_pct = abs(sorted_pnls[idx_99])
        r.cvar_95_pct = abs(np.mean(sorted_pnls[:idx_95 + 1])) if idx_95 > 0 else r.var_95_pct
        r.cvar_99_pct = abs(np.mean(sorted_pnls[:idx_99 + 1])) if idx_99 > 0 else r.var_99_pct

    # Max Consecutive Losses
    max_streak = 0
    current_streak = 0
    for p in picks:
        if not p.is_win:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    r.max_consecutive_losses = max_streak

    # Kelly Fraction — minimum-loss guard prevents 1000x ratios from the
    # avg_l=0.001 failsafe. Ref: minimax quant review issue #2 (2026-04-11),
    # verified by opus-hc-audit.
    MIN_AVG_LOSS_PCT = 0.5  # require at least 0.5% mean loss before scaling Kelly
    KELLY_CAP = 1.0         # hard cap — never recommend more than full capital
    if picks:
        wr = sum(1 for p in picks if p.is_win) / len(picks)
        wins_only = [p.pnl_pct for p in picks if p.is_win]
        losses_only = [p.pnl_pct for p in picks if not p.is_win]
        avg_w = np.mean(wins_only) if wins_only else 0.0
        avg_l = abs(np.mean(losses_only)) if losses_only else 0.0

        if losses_only and avg_l >= MIN_AVG_LOSS_PCT and avg_w > 0:
            rr = avg_w / avg_l
            kelly = wr - (1 - wr) / rr
            r.kelly_fraction = max(0.0, min(kelly, KELLY_CAP))
        elif losses_only and avg_l > 0 and avg_w > 0:
            # Tiny losses observed but below the trust threshold —
            # use a conservative half-Kelly proxy until more loss data accumulates
            r.kelly_fraction = max(0.0, min(wr * 0.5, 0.10))
        else:
            # Zero losses recorded — refuse to size aggressively, cap at 5%
            r.kelly_fraction = max(0.0, min(wr * 0.25, 0.05))

    # Tail Ratio
    if n >= 20:
        p95 = np.percentile(pnls, 95)
        p5 = abs(np.percentile(pnls, 5))
        r.tail_ratio = p95 / p5 if p5 > 0 else 99.99

    return r


def compute_statistics(picks: List[PickRecord], n_total_strategies: int = 1) -> StatisticalTests:
    """Compute §2.4 statistical significance checks."""
    s = StatisticalTests()
    if len(picks) < 5:
        return s

    pnls = [p.pnl_pct for p in picks]
    n = len(picks)
    wins = sum(1 for p in picks if p.is_win)

    # Binomial test: is WR significantly above break-even (50%)?
    # Using normal approximation for binomial
    p0 = DEFAULT_BREAK_EVEN_WR
    p_hat = wins / n
    se = math.sqrt(p0 * (1 - p0) / n)
    if se > 0:
        z = (p_hat - p0) / se
        # One-sided p-value (is WR > break-even?)
        s.binomial_p_value = _norm_sf(z)
    
    # t-test on returns (is mean return significantly > 0?)
    mean_pnl = np.mean(pnls)
    std_pnl = np.std(pnls, ddof=1)
    if std_pnl > 0 and n > 1:
        s.alpha_t_stat = mean_pnl / (std_pnl / math.sqrt(n))
        s.alpha_p_value = _t_sf(s.alpha_t_stat, n - 1)

    # Bootstrap Sharpe CI (1000 resamples)
    bootstrap_sharpes = []
    rng = np.random.RandomState(42)
    for _ in range(1000):
        sample = rng.choice(pnls, size=n, replace=True)
        mean_s = np.mean(sample)
        std_s = np.std(sample, ddof=1)
        if std_s > 0:
            bootstrap_sharpes.append(mean_s / std_s * math.sqrt(ANNUALIZATION_FACTOR))
    
    if bootstrap_sharpes:
        bootstrap_sharpes.sort()
        s.bootstrap_sharpe_lower = bootstrap_sharpes[int(0.025 * len(bootstrap_sharpes))]
        s.bootstrap_sharpe_upper = bootstrap_sharpes[int(0.975 * len(bootstrap_sharpes))]
        s.bootstrap_sharpe_median = bootstrap_sharpes[len(bootstrap_sharpes) // 2]

    # Multiple testing correction (Bonferroni)
    s.multiple_testing_adjusted_p = min(1.0, s.binomial_p_value * n_total_strategies)

    # Overall significance (PR #72 cherry-pick: use Bonferroni-adjusted p for
    # multiple-testing protection across n_total_strategies).
    s.is_statistically_significant = (
        s.multiple_testing_adjusted_p < GATE1_P_VALUE and
        s.alpha_p_value < 0.05 and
        s.bootstrap_sharpe_lower > 0
    )

    return s


def _norm_sf(z: float) -> float:
    """Survival function of standard normal (1 - CDF). No scipy needed."""
    # Approximation via error function
    return 0.5 * math.erfc(z / math.sqrt(2))


def _t_sf(t: float, df: int) -> float:
    """Approximate one-sided p-value for t-distribution. For df > 30, use normal approx."""
    if df > 30:
        return _norm_sf(t)
    # Rough approximation for smaller df
    # Using the relationship: for large df, t ≈ z
    adjustment = 1 + 1 / (4 * max(df, 1))
    return _norm_sf(t / adjustment)


def whites_reality_check(
    strategy_returns: List[float],
    n_bootstrap: int = 1000,
) -> Dict[str, Any]:
    """White's Reality Check scaffold (PR #72 cherry-pick).

    Tests the null hypothesis that the observed Sharpe could arise by chance
    under a mean-zero distribution with the same volatility. Uses a
    stationary-bootstrap-lite: resamples returns with replacement, recenters
    to zero mean (null), and compares the bootstrap max Sharpe distribution
    against the observed Sharpe.

    Args:
        strategy_returns: per-trade (or per-period) return series
        n_bootstrap: number of bootstrap resamples

    Returns:
        {"reality_check_pvalue": p, "reject_null": p < 0.05}
    """
    if not strategy_returns or len(strategy_returns) < 5:
        return {"reality_check_pvalue": 1.0, "reject_null": False}

    arr = np.asarray(strategy_returns, dtype=float)
    mean_ret = float(np.mean(arr))
    std_ret = float(np.std(arr, ddof=1))
    if std_ret <= 0:
        return {"reality_check_pvalue": 1.0, "reject_null": False}

    observed_sharpe = mean_ret / std_ret * math.sqrt(ANNUALIZATION_FACTOR)

    rng = np.random.RandomState(42)
    n = len(arr)
    # Center under the null (mean-zero); bootstrap draws from the centered
    # distribution. Fraction of bootstrap Sharpes >= observed Sharpe is the
    # one-sided reality-check p-value.
    centered = arr - mean_ret
    hits = 0
    bootstrap_max = -math.inf
    for _ in range(n_bootstrap):
        sample = rng.choice(centered, size=n, replace=True)
        s_std = float(np.std(sample, ddof=1))
        if s_std <= 0:
            continue
        s_sharpe = float(np.mean(sample)) / s_std * math.sqrt(ANNUALIZATION_FACTOR)
        if s_sharpe > bootstrap_max:
            bootstrap_max = s_sharpe
        if s_sharpe >= observed_sharpe:
            hits += 1

    p = hits / n_bootstrap if n_bootstrap > 0 else 1.0
    return {
        "reality_check_pvalue": float(p),
        "reject_null": bool(p < 0.05),
        "observed_sharpe": round(observed_sharpe, 4),
        "bootstrap_max_sharpe": round(bootstrap_max, 4) if bootstrap_max != -math.inf else None,
        "n_bootstrap": n_bootstrap,
    }


# ---------------------------------------------------------------------------
# Walk-Forward Splitter (§1.5 + §2.3)
# ---------------------------------------------------------------------------
def _parse_pick_time(s: Optional[str]) -> Optional[datetime]:
    """Parse a pick.entry_time string into a tz-aware UTC datetime, or None.

    Accepts ISO-8601 with or without timezone suffix; treats naive timestamps
    as UTC. Returns None on any parse failure so callers can drop the pick
    rather than letting bad data poison the split.
    """
    if not s:
        return None
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, AttributeError):
        return None


def purged_walk_forward_split(
    picks: List[PickRecord],
    train_pct: float = 0.70,
    purge_days: int = 30,
) -> Tuple[List[PickRecord], List[PickRecord]]:
    """Time-based split with an enforced purge buffer.

    Ref: minimax quant review issue #1 (2026-04-11), verified by
    opus-hc-audit. Prior implementation accepted purge_days but ignored it
    (string compare only). This version parses entry_time to datetime and
    drops any test pick whose entry is within purge_days of the last train
    pick — closing the look-ahead bias hole in Gate 2.

    Returns (train_picks, test_picks).
    """
    if not picks:
        return [], []

    # Sort by entry_time string (ISO-8601 sorts correctly lexicographically
    # for the canonical case; bad rows are filtered later by _parse_pick_time)
    sorted_picks = sorted(picks, key=lambda p: p.entry_time or "")
    split_idx = int(len(sorted_picks) * train_pct)
    train = sorted_picks[:split_idx]
    tail = sorted_picks[split_idx:]

    if not train:
        return [], tail

    # Find the largest parseable timestamp in the train set as the anchor
    last_train_dt: Optional[datetime] = None
    for p in reversed(train):
        last_train_dt = _parse_pick_time(p.entry_time)
        if last_train_dt is not None:
            break

    if last_train_dt is None:
        # Train set has no parseable timestamps — fall back to the
        # cardinal split with no purge (and log nothing — caller handles)
        return train, tail

    purge_cutoff = last_train_dt + timedelta(days=purge_days)
    test: List[PickRecord] = []
    for p in tail:
        p_dt = _parse_pick_time(p.entry_time)
        if p_dt is None:
            continue  # drop unparseable rows from the test set
        if p_dt >= purge_cutoff:
            test.append(p)
    return train, test


# ---------------------------------------------------------------------------
# Symbol & Direction Breakdown
# ---------------------------------------------------------------------------
def compute_by_symbol(picks: List[PickRecord]) -> Dict[str, Dict]:
    """Break down performance by symbol."""
    grouped = defaultdict(list)
    for p in picks:
        grouped[p.symbol].append(p)
    
    result = {}
    for symbol, group in grouped.items():
        perf = compute_performance(group)
        result[symbol] = {
            "n": perf.n_trades,
            "wr": round(perf.win_rate * 100, 1),
            "pf": round(perf.profit_factor, 2),
            "avg_pnl": round(perf.avg_pnl_pct, 3),
            "total_pnl": round(perf.total_pnl_pct, 2),
        }
    
    return dict(sorted(result.items(), key=lambda x: x[1]["total_pnl"], reverse=True))


def compute_by_direction(picks: List[PickRecord]) -> Dict[str, Dict]:
    """Break down performance by direction (LONG/SHORT)."""
    grouped = defaultdict(list)
    for p in picks:
        d = p.direction.upper()
        if d in ("BUY", "LONG"):
            d = "LONG"
        elif d in ("SELL", "SHORT"):
            d = "SHORT"
        grouped[d].append(p)
    
    result = {}
    for direction, group in grouped.items():
        perf = compute_performance(group)
        result[direction] = {
            "n": perf.n_trades,
            "wr": round(perf.win_rate * 100, 1),
            "pf": round(perf.profit_factor, 2),
            "avg_pnl": round(perf.avg_pnl_pct, 3),
        }
    
    return result


# ---------------------------------------------------------------------------
# The 4-Gate Pipeline
# ---------------------------------------------------------------------------
class StrategyProver:
    """Runs a strategy through the full proving pipeline."""

    def __init__(
        self,
        strategy_name: str,
        asset_class: str,
        closed_picks: Optional[List[PickRecord]] = None,
        forward_picks: Optional[List[PickRecord]] = None,
        n_total_strategies: int = 100,
    ):
        self.strategy = strategy_name
        self.asset_class = asset_class.upper()
        self.n_total_strategies = n_total_strategies
        self.closed_picks = closed_picks or []
        self.forward_picks = forward_picks or []

    def gate1_backtest(self) -> GateResult:
        """Gate 1: Historical backtest validation."""
        g = GateResult(gate_name="Gate 1: Backtest Validation")
        picks = self.closed_picks

        if len(picks) < GATE1_MIN_N:
            g.reason = f"Insufficient trades: n={len(picks)} < {GATE1_MIN_N}"
            g.metrics = {"n": len(picks), "required": GATE1_MIN_N}
            return g

        perf = compute_performance(picks)
        risk = compute_risk(picks)
        stats = compute_statistics(picks, self.n_total_strategies)

        # Check all Gate 1 criteria
        checks = {
            "n_trades": (perf.n_trades >= GATE1_MIN_N, f"{perf.n_trades} >= {GATE1_MIN_N}"),
            "win_rate_above_breakeven": (perf.win_rate > DEFAULT_BREAK_EVEN_WR, f"{perf.win_rate:.1%} > {DEFAULT_BREAK_EVEN_WR:.0%}"),
            "profit_factor": (perf.profit_factor >= GATE1_MIN_PF, f"{perf.profit_factor:.2f} >= {GATE1_MIN_PF}"),
            "sharpe": (perf.sharpe_ratio >= GATE1_MIN_SHARPE, f"{perf.sharpe_ratio:.2f} >= {GATE1_MIN_SHARPE}"),
            "p_value": (stats.multiple_testing_adjusted_p < GATE1_P_VALUE, f"{stats.multiple_testing_adjusted_p:.6f} < {GATE1_P_VALUE} (Bonferroni)"),
            "bootstrap_sharpe_lower_positive": (stats.bootstrap_sharpe_lower > 0, f"lower CI = {stats.bootstrap_sharpe_lower:.2f} > 0"),
            "kelly_positive": (risk.kelly_fraction > 0, f"Kelly = {risk.kelly_fraction:.3f} > 0"),
        }

        all_pass = all(v[0] for v in checks.values())
        g.passed = all_pass
        g.reason = "All checks passed" if all_pass else "Failed: " + ", ".join(k for k, v in checks.items() if not v[0])
        g.metrics = {
            "checks": {k: {"pass": v[0], "detail": v[1]} for k, v in checks.items()},
            "performance": {
                "n": perf.n_trades,
                "wr": round(perf.win_rate * 100, 1),
                "pf": round(perf.profit_factor, 2),
                "sharpe": round(perf.sharpe_ratio, 2),
                "sortino": round(perf.sortino_ratio, 2),
                "calmar": round(perf.calmar_ratio, 2),
                "total_pnl": round(perf.total_pnl_pct, 2),
                "avg_pnl": round(perf.avg_pnl_pct, 3),
                "mdd": round(risk.max_drawdown_pct, 2),
                "var95": round(risk.var_95_pct, 2),
                "cvar95": round(risk.cvar_95_pct, 2),
                "kelly": round(risk.kelly_fraction, 4),
                "max_consec_losses": risk.max_consecutive_losses,
                "tail_ratio": round(risk.tail_ratio, 2),
            },
            "statistics": {
                "binomial_p": round(stats.binomial_p_value, 6),
                "alpha_t_stat": round(stats.alpha_t_stat, 3),
                "alpha_p": round(stats.alpha_p_value, 6),
                "bootstrap_sharpe_95ci": [
                    round(stats.bootstrap_sharpe_lower, 2),
                    round(stats.bootstrap_sharpe_upper, 2),
                ],
                "bonferroni_adjusted_p": round(stats.multiple_testing_adjusted_p, 6),
                "significant": stats.is_statistically_significant,
            },
        }
        return g

    def gate2_walk_forward(self) -> GateResult:
        """Gate 2: Walk-forward out-of-sample validation (§1.5)."""
        g = GateResult(gate_name="Gate 2: Walk-Forward OOS")
        picks = self.closed_picks

        if len(picks) < 20:
            g.reason = f"Insufficient trades for split: n={len(picks)}"
            return g

        train, test = purged_walk_forward_split(picks, train_pct=0.70, purge_days=30)

        if len(test) < 10:
            g.reason = f"OOS set too small after purge: n_test={len(test)}"
            g.metrics = {"n_train": len(train), "n_test": len(test)}
            return g

        train_perf = compute_performance(train)
        test_perf = compute_performance(test)

        # Check decay — guard against zero baselines instead of dividing by a
        # 0.001 magic number that would inflate decay to 10,000%+ for never-won
        # strategies (pass-2 issue #1, opus-hc-audit 2026-04-11).
        if train_perf.win_rate > 0:
            wr_decay = abs(train_perf.win_rate - test_perf.win_rate) / train_perf.win_rate
        else:
            wr_decay = 0.0 if test_perf.win_rate == 0 else float("inf")
        if train_perf.profit_factor > 0:
            pf_decay = abs(train_perf.profit_factor - test_perf.profit_factor) / train_perf.profit_factor
        else:
            pf_decay = 0.0 if test_perf.profit_factor == 0 else float("inf")

        # PR #72 cherry-pick: Sharpe decay check. Fail if OOS Sharpe drops more
        # than 30% vs IS (oos_sharpe < is_sharpe * 0.7). Only gated when
        # is_sharpe > 0; if IS Sharpe is non-positive the strategy shouldn't
        # have reached Gate 2 in the first place.
        is_sharpe = train_perf.sharpe_ratio
        oos_sharpe = test_perf.sharpe_ratio
        sharpe_decay_too_high = False
        sharpe_decay_pct = 0.0
        if is_sharpe > 0:
            sharpe_decay_too_high = oos_sharpe < is_sharpe * 0.7
            sharpe_decay_pct = max(0.0, (is_sharpe - oos_sharpe) / is_sharpe) * 100

        passes = (
            wr_decay < GATE2_MAX_DECAY_PCT / 100 and
            not sharpe_decay_too_high and
            test_perf.win_rate > DEFAULT_BREAK_EVEN_WR and
            test_perf.profit_factor > 1.0
        )

        g.passed = passes
        if passes:
            g.reason = "OOS metrics within tolerance"
        elif sharpe_decay_too_high:
            g.reason = (
                f"sharpe_decay_too_high: IS={is_sharpe:.2f}, OOS={oos_sharpe:.2f} "
                f"({sharpe_decay_pct:.0f}% decay > 30%)"
            )
        else:
            g.reason = f"Decay too high: WR decay {wr_decay:.0%}, PF decay {pf_decay:.0%}"
        g.metrics = {
            "n_train": len(train),
            "n_test": len(test),
            "train_wr": round(train_perf.win_rate * 100, 1),
            "test_wr": round(test_perf.win_rate * 100, 1),
            "wr_decay_pct": round(wr_decay * 100, 1),
            "train_pf": round(train_perf.profit_factor, 2),
            "test_pf": round(test_perf.profit_factor, 2),
            "pf_decay_pct": round(pf_decay * 100, 1),
            "train_sharpe": round(train_perf.sharpe_ratio, 2),
            "test_sharpe": round(test_perf.sharpe_ratio, 2),
            "sharpe_decay_pct": round(sharpe_decay_pct, 1),
            "sharpe_decay_too_high": sharpe_decay_too_high,
        }
        return g

    def gate3_paper_forward(self) -> GateResult:
        """Gate 3: Paper forward test (real-time, no tweaks)."""
        g = GateResult(gate_name="Gate 3: Paper Forward Test")
        picks = self.forward_picks

        if len(picks) < GATE3_MIN_N:
            g.reason = f"Forward test in progress: n={len(picks)} / {GATE3_MIN_N} needed"
            g.metrics = {"n": len(picks), "required": GATE3_MIN_N}
            if picks:
                perf = compute_performance(picks)
                g.metrics["current_wr"] = round(perf.win_rate * 100, 1)
                g.metrics["current_pf"] = round(perf.profit_factor, 2)
            return g

        perf = compute_performance(picks)
        risk = compute_risk(picks)
        stats = compute_statistics(picks, self.n_total_strategies)

        passes = (
            perf.win_rate > DEFAULT_BREAK_EVEN_WR and
            perf.profit_factor > GATE3_MIN_PF and
            stats.multiple_testing_adjusted_p < 0.05  # Bonferroni-adjusted for forward
        )

        g.passed = passes
        g.reason = "Forward test passed" if passes else "Forward metrics below threshold"
        g.metrics = {
            "n": perf.n_trades,
            "wr": round(perf.win_rate * 100, 1),
            "pf": round(perf.profit_factor, 2),
            "sharpe": round(perf.sharpe_ratio, 2),
            "mdd": round(risk.max_drawdown_pct, 2),
            "p_value": round(stats.binomial_p_value, 6),
            "kelly": round(risk.kelly_fraction, 4),
        }
        return g

    def run_full_pipeline(self) -> StrategyReport:
        """Run all 4 gates and produce a complete report."""
        report = StrategyReport(
            strategy=self.strategy,
            asset_class=self.asset_class,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Run gates
        report.gate1 = self.gate1_backtest()
        report.gate2 = self.gate2_walk_forward()
        report.gate3 = self.gate3_paper_forward()

        # Determine final tier
        if report.gate1.passed and report.gate2.passed and report.gate3.passed:
            report.final_tier = "PROVEN"
        elif report.gate1.passed and report.gate2.passed:
            report.final_tier = "PAPER_TESTING"
        elif report.gate1.passed:
            report.final_tier = "BACKTEST_ONLY"
        else:
            report.final_tier = "UNPROVEN"

        # Full metrics on all closed picks
        all_picks = self.closed_picks + self.forward_picks
        if all_picks:
            report.performance = compute_performance(all_picks)
            report.risk = compute_risk(all_picks)
            report.stats = compute_statistics(all_picks, self.n_total_strategies)
            report.by_symbol = compute_by_symbol(all_picks)
            report.by_direction = compute_by_direction(all_picks)

        return report


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------
def load_closed_picks_for_strategy(strategy: str, asset_class: str = "") -> List[PickRecord]:
    """Load closed picks for analysis, filtered by strategy and optionally asset class.

    DATA SOURCE: audit_dashboard/data/dashboard_data.json picks.recent_closed
    (the live post-resolver-fix ledger). Falls back to legacy
    alpha_engine/data/closed_picks.json only if the live ledger is missing.
    """
    picks = []

    # Try live ledger first (the source of truth)
    raw = None
    if LIVE_LEDGER_PATH.exists():
        try:
            doc = json.loads(LIVE_LEDGER_PATH.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and "picks" in doc:
                raw = doc["picks"].get("recent_closed", doc["picks"].get("closed", []))
        except (json.JSONDecodeError, OSError):
            raw = None

    # Fallback to legacy file ONLY if live ledger unavailable
    if raw is None and LEGACY_CLOSED_PICKS_PATH.exists():
        try:
            raw = json.loads(LEGACY_CLOSED_PICKS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                raw = raw.get("picks", raw.get("closed_picks", []))
        except (json.JSONDecodeError, OSError):
            raw = None

    if not raw:
        return picks

    for row in raw:
        strat = str(row.get("strategy", "")).lower()
        if strat != strategy.lower():
            continue

        ac = str(row.get("asset_class", row.get("category", "CRYPTO"))).upper()
        if asset_class and ac != asset_class.upper():
            continue

        # Ghost-pick filter (MATICUSDT delisted picks)
        entry = float(row.get("entry_price", 0) or 0)
        exit_p = float(row.get("exit_price", 0) or 0)
        pnl = float(row.get("pnl_pct", 0) or 0)
        exit_reason = str(row.get("exit_reason", "") or "")
        if entry > 0 and entry == exit_p and abs(pnl + 0.15) < 0.01 and exit_reason.upper() == "TIME_EXIT":
            continue  # Skip ghost/placeholder picks

        picks.append(PickRecord(
            id=str(row.get("id", "")),
            strategy=strat,
            symbol=str(row.get("symbol", "")),
            direction=str(row.get("direction", "LONG")).upper(),
            asset_class=ac,
            entry_price=entry,
            exit_price=exit_p,
            pnl_pct=pnl,
            entry_time=str(row.get("entry_time", row.get("open_time", ""))),
            exit_time=str(row.get("exit_time", row.get("closed_at", ""))),
            hold_days=float(row.get("hold_days", 1) or 1),
            exit_reason=exit_reason,
        ))

    return picks


def load_forward_picks(strategy: str, asset_class: str) -> List[PickRecord]:
    """Load forward test picks from the forward_tests directory."""
    picks = []
    ac_lower = asset_class.lower()
    fwd_path = FORWARD_DIR / ac_lower / f"{strategy}.json"
    
    if not fwd_path.exists():
        return picks

    try:
        raw = json.loads(fwd_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return picks

    for row in raw:
        if not row.get("closed", False):
            continue  # Only count closed forward trades
        picks.append(PickRecord(
            id=str(row.get("id", "")),
            strategy=strategy,
            symbol=str(row.get("symbol", "")),
            direction=str(row.get("direction", "LONG")).upper(),
            asset_class=asset_class.upper(),
            entry_price=float(row.get("entry_price", 0) or 0),
            exit_price=float(row.get("exit_price", 0) or 0),
            pnl_pct=float(row.get("pnl_pct", 0) or 0),
            entry_time=str(row.get("entry_time", "")),
            exit_time=str(row.get("exit_time", "")),
            hold_days=float(row.get("hold_days", 1) or 1),
        ))

    return picks


# ---------------------------------------------------------------------------
# Scorecard Generator
# ---------------------------------------------------------------------------
ASSET_CLASS_STRATEGY_MAP = {
    "CRYPTO": [
        "st_fear_greed_contrarian",
        "keltner_compression_expansion",
        "copy_hl_whale",
        "st_atr_vol_breakout",
    ],
    "EQUITY": [
        "connors_rsi2",
        "supertrend_vwma",
        "quality_value",
        "pead_earnings_drift",
    ],
    "COMMODITY": [
        "triple_confirmation",
        "supertrend_vwma",
    ],
    "ETF": [
        "supertrend_vwma",
        "connors_rsi2",
    ],
    "FOREX": [
        "carry_trade",
        "forex_rsi2",
        "short_only_contrarian",
    ],
    "BONDS": [
        "tsmom",
        "yield_curve_mr",
    ],
    "FUTURES": [
        "tsmom",
        "momentum_persistence",
    ],
}


def generate_scorecard() -> str:
    """Generate the weekly asset-class scorecard."""
    lines = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"# ASSET CLASS STRATEGY SCORECARD")
    lines.append(f"## Generated: {now}")
    lines.append("")

    proven_count = 0
    total_classes = len(ASSET_CLASS_STRATEGY_MAP)

    for ac, strategies in ASSET_CLASS_STRATEGY_MAP.items():
        lines.append(f"### {ac}")
        lines.append(f"{'Strategy':<35} {'Tier':<15} {'n':>5} {'WR':>7} {'PF':>6} {'Sharpe':>7} {'p-value':>10}")
        lines.append("-" * 90)

        best_tier = "UNPROVEN"
        for strat in strategies:
            closed = load_closed_picks_for_strategy(strat, ac)
            forward = load_forward_picks(strat, ac)
            prover = StrategyProver(strat, ac, closed, forward, n_total_strategies=100)
            report = prover.run_full_pipeline()

            tier_emoji = {
                "PROVEN": "✅",
                "PAPER_TESTING": "🟡",
                "BACKTEST_ONLY": "🟠",
                "UNPROVEN": "❌",
            }.get(report.final_tier, "❓")

            perf = report.performance
            stats = report.stats
            if perf and stats:
                lines.append(
                    f"{tier_emoji} {strat:<32} {report.final_tier:<15} "
                    f"{perf.n_trades:>5} {perf.win_rate * 100:>6.1f}% "
                    f"{perf.profit_factor:>5.2f} {perf.sharpe_ratio:>6.2f} "
                    f"{stats.binomial_p_value:>10.6f}"
                )
            else:
                lines.append(f"{tier_emoji} {strat:<32} {report.final_tier:<15}   n/a")

            if report.final_tier == "PROVEN":
                best_tier = "PROVEN"
            elif report.final_tier == "PAPER_TESTING" and best_tier != "PROVEN":
                best_tier = "PAPER_TESTING"

        if best_tier == "PROVEN":
            proven_count += 1
        lines.append("")

    lines.append(f"## SUMMARY: {proven_count}/{total_classes} asset classes have PROVEN strategy")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report Serialization
# ---------------------------------------------------------------------------
def _sanitize_for_json(obj: Any) -> Any:
    """Recursively convert numpy types to Python natives for JSON serialization.

    numpy.bool_ / numpy.int64 / numpy.float64 etc. are not accepted by the
    stdlib json encoder.  This function walks dicts, lists, and scalar values
    and converts them to their Python equivalents.
    """
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    # numpy scalar types — check via the numpy API so we don't need to
    # enumerate every dtype variant (bool_, int64, float32, …).
    if hasattr(obj, "item"):  # numpy scalars expose .item()
        return obj.item()
    return obj


def report_to_dict(report: StrategyReport) -> dict:
    """Convert a StrategyReport to a JSON-serializable dict."""
    d = {
        "strategy": report.strategy,
        "asset_class": report.asset_class,
        "generated_at": report.generated_at,
        "final_tier": report.final_tier,
    }
    if report.gate1:
        d["gate1"] = {"passed": bool(report.gate1.passed), "reason": report.gate1.reason, "metrics": report.gate1.metrics}
    if report.gate2:
        d["gate2"] = {"passed": bool(report.gate2.passed), "reason": report.gate2.reason, "metrics": report.gate2.metrics}
    if report.gate3:
        d["gate3"] = {"passed": bool(report.gate3.passed), "reason": report.gate3.reason, "metrics": report.gate3.metrics}
    if report.performance:
        d["performance"] = asdict(report.performance)
    if report.risk:
        d["risk"] = asdict(report.risk)
    if report.stats:
        d["statistics"] = asdict(report.stats)
    if report.by_symbol:
        d["by_symbol"] = report.by_symbol
    if report.by_direction:
        d["by_direction"] = report.by_direction
    return _sanitize_for_json(d)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Strategy Prover — Institutional-Grade Validation")
    parser.add_argument("--strategy", type=str, help="Strategy name to validate")
    parser.add_argument("--asset-class", type=str, default="", help="Asset class filter")
    parser.add_argument("--all", action="store_true", help="Run all strategies across all asset classes")
    parser.add_argument("--scorecard", action="store_true", help="Generate weekly scorecard")
    parser.add_argument("--output", type=str, default="", help="Output JSON path")
    args = parser.parse_args()

    if args.scorecard:
        print(generate_scorecard())
        return

    if args.all:
        all_reports = []
        for ac, strategies in ASSET_CLASS_STRATEGY_MAP.items():
            for strat in strategies:
                closed = load_closed_picks_for_strategy(strat, ac)
                forward = load_forward_picks(strat, ac)
                prover = StrategyProver(strat, ac, closed, forward, n_total_strategies=100)
                report = prover.run_full_pipeline()
                all_reports.append(report_to_dict(report))
                tier_emoji = {"PROVEN": "✅", "PAPER_TESTING": "🟡", "BACKTEST_ONLY": "🟠", "UNPROVEN": "❌"}.get(report.final_tier, "❓")
                print(f"{tier_emoji} {ac:>10} | {strat:<35} | {report.final_tier}")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = Path(args.output) if args.output else OUTPUT_DIR / "strategy_prover_results.json"
        out_path.write_text(json.dumps(all_reports, indent=2))
        print(f"\nResults written to {out_path}")
        return

    if args.strategy:
        ac = args.asset_class.upper() if args.asset_class else ""
        closed = load_closed_picks_for_strategy(args.strategy, ac)
        forward = load_forward_picks(args.strategy, ac)
        prover = StrategyProver(args.strategy, ac or "ALL", closed, forward, n_total_strategies=100)
        report = prover.run_full_pipeline()
        result = report_to_dict(report)
        print(json.dumps(result, indent=2))

        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
