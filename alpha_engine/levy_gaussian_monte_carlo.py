"""
Levy-Gaussian Hybrid Monte Carlo Simulation

Standard Gaussian Monte Carlo assumes independent, normally-distributed returns.
But crypto (and our portfolio) has FAT TAILS: excess kurtosis = 6.85+ (typical
hedge fund = 3-5). A pure Gaussian simulation UNDERESTIMATES rare events like
the -69% DEGOUSDT crash.

This module combines Gaussian noise (normal market behavior) with Levy stable
distribution (rare extreme events / black swans) using the Chambers-Mallows-Stuck
algorithm for pure-Python Levy sampling (no scipy required).

Insight source: r/algotrading fat-tail analysis.

Usage:
    python -m alpha_engine.levy_gaussian_monte_carlo
"""

import json
import math
import os
import time
from datetime import datetime, timezone

import numpy as np


# ======================================================================
# 1. LEVY STABLE DISTRIBUTION (Chambers-Mallows-Stuck algorithm)
# ======================================================================

def levy_stable_sample(alpha=1.7, beta=0.0, gamma=1.0, delta=0.0, size=1, rng=None):
    """
    Generate samples from a Levy stable distribution using the
    Chambers-Mallows-Stuck (CMS) method.

    Parameters:
        alpha (float): Stability parameter in (0, 2]. Lower = fatter tails.
                       alpha=2 recovers Gaussian. Crypto typically 1.5-1.8.
        beta  (float): Skewness parameter in [-1, 1]. 0 = symmetric.
        gamma (float): Scale parameter (>0). Analogous to std deviation.
        delta (float): Location parameter. Analogous to mean.
        size  (int):   Number of samples to generate.
        rng:           numpy random Generator instance.

    Returns:
        np.ndarray of shape (size,) with Levy stable samples.

    Reference:
        Chambers, Mallows & Stuck (1976), "A Method for Simulating Stable
        Random Variables", Journal of the American Statistical Association.
    """
    if rng is None:
        rng = np.random.default_rng()

    # Edge case: alpha=2 is Gaussian (std = gamma * sqrt(2))
    if abs(alpha - 2.0) < 1e-10:
        return delta + gamma * math.sqrt(2) * rng.standard_normal(size)

    # Step 1: Uniform on (-pi/2, pi/2)
    V = rng.uniform(-math.pi / 2, math.pi / 2, size=size)

    # Step 2: Exponential with mean 1
    W = rng.exponential(1.0, size=size)

    # Clamp V away from boundaries to avoid division by zero
    eps = 1e-10
    V = np.clip(V, -math.pi / 2 + eps, math.pi / 2 - eps)

    if abs(alpha - 1.0) < 1e-10:
        # Special case: alpha = 1 (Cauchy-like)
        # X = (2/pi) * ((pi/2 + beta*V) * tan(V) - beta * ln(W*cos(V)/(pi/2+beta*V)))
        bV = beta * V
        half_pi = math.pi / 2
        term1 = (half_pi + bV) * np.tan(V)
        # Protect against log of non-positive
        inner = np.maximum(W * np.cos(V) / (half_pi + bV), eps)
        term2 = beta * np.log(inner)
        X = (2.0 / math.pi) * (term1 - term2)
        return delta + gamma * X + (2.0 / math.pi) * beta * gamma * np.log(gamma)

    # General case: alpha != 1
    # B = arctan(beta * tan(pi*alpha/2)) / alpha
    B = np.arctan(beta * math.tan(math.pi * alpha / 2.0)) / alpha

    # S = (1 + beta^2 * tan^2(pi*alpha/2))^(1/(2*alpha))
    S = (1.0 + (beta * math.tan(math.pi * alpha / 2.0)) ** 2) ** (1.0 / (2.0 * alpha))

    # X = S * sin(alpha*(V+B)) / cos(V)^(1/alpha)
    #     * (cos(V - alpha*(V+B)) / W)^((1-alpha)/alpha)
    alpha_VB = alpha * (V + B)
    cos_V = np.cos(V)

    # Protect against cos_V = 0
    cos_V = np.where(np.abs(cos_V) < eps, eps, cos_V)

    numerator = np.sin(alpha_VB)
    denominator = np.power(np.maximum(np.abs(cos_V), eps), 1.0 / alpha)
    denominator = np.copysign(denominator, cos_V)

    cos_diff = np.cos(V - alpha_VB)
    # Protect ratio for power operation
    ratio = np.maximum(np.abs(cos_diff), eps) / np.maximum(W, eps)
    ratio = np.copysign(ratio, cos_diff)

    # For the power, handle potential negative base
    exponent = (1.0 - alpha) / alpha
    power_term = np.sign(ratio) * np.power(np.abs(ratio), exponent)

    X = S * (numerator / denominator) * power_term

    return delta + gamma * X


# ======================================================================
# 2. DATA CALIBRATION
# ======================================================================

def calibrate_from_data(closed_picks):
    """
    Calibrate both Gaussian and Levy parameters from actual trade data.

    Returns:
        dict with all calibration parameters and data diagnostics.
    """
    pnl_values = np.array(
        [float(p.get("pnl_pct", 0.0)) for p in closed_picks],
        dtype=np.float64,
    )

    n = len(pnl_values)
    mean_ret = float(np.mean(pnl_values))
    std_ret = float(np.std(pnl_values))

    # Excess kurtosis
    if std_ret > 1e-12:
        kurtosis = float(np.mean(((pnl_values - mean_ret) / std_ret) ** 4) - 3.0)
    else:
        kurtosis = 0.0

    # Skewness
    if std_ret > 1e-12:
        skewness = float(np.mean(((pnl_values - mean_ret) / std_ret) ** 3))
    else:
        skewness = 0.0

    # --- Levy parameters ---

    # Alpha estimation: inverse relationship with kurtosis.
    # For Gaussian: kurtosis=0, alpha=2. Higher kurtosis -> lower alpha.
    #
    # We use a softer mapping than the naive 2/(1+k/3) which collapses
    # too quickly. Instead: alpha = 2 - c*kurtosis/(kurtosis + k0)
    # where c controls max reduction and k0 controls sensitivity.
    # This maps kurtosis=0 -> alpha=2, kurtosis->inf -> alpha=2-c.
    # With c=0.5, k0=6: kurtosis=6.85 -> alpha~1.47 (reasonable for crypto).
    if kurtosis > 0:
        c_reduction = 0.5   # max alpha reduction from 2.0
        k_half = 6.0        # kurtosis at which reduction is half of max
        alpha_est = 2.0 - c_reduction * kurtosis / (kurtosis + k_half)
    else:
        alpha_est = 2.0  # No excess kurtosis -> Gaussian
    alpha_est = max(1.3, min(2.0, alpha_est))

    # Beta from skewness direction (simplified)
    beta_est = max(-1.0, min(1.0, skewness / 3.0))

    # p_tail: fraction of trades beyond 3 standard deviations
    if std_ret > 1e-12:
        tail_mask = np.abs(pnl_values - mean_ret) > 3.0 * std_ret
        p_tail = float(np.mean(tail_mask))
        n_tail_events = int(np.sum(tail_mask))
    else:
        p_tail = 0.0
        n_tail_events = 0
        tail_mask = np.zeros(n, dtype=bool)

    # Ensure minimum tail probability (at least 1% for simulation realism)
    p_tail = max(p_tail, 0.01)

    # Tail scale (gamma for the Levy distribution).
    # Note: Levy stable with alpha < 2 already produces heavy tails, so
    # gamma should be comparable to std_ret, not the raw tail event std
    # (which would double-count the tail heaviness).
    # We use the MAD (median absolute deviation) of tail events as a
    # robust scale estimate, dampened toward std_ret.
    if n_tail_events >= 2:
        tail_events = pnl_values[tail_mask]
        raw_tail_std = float(np.std(tail_events))
        # Use the tail event std, but cap at 2x overall std to prevent
        # unrealistic explosion. The Levy alpha already amplifies tails.
        tail_scale = min(raw_tail_std, 2.0 * std_ret)
        # Floor at overall std (Levy component should be at least as volatile)
        tail_scale = max(tail_scale, std_ret)
    elif n_tail_events == 1:
        tail_events = pnl_values[tail_mask]
        tail_scale = max(
            float(np.abs(tail_events[0] - mean_ret)),
            std_ret,
        )
        tail_scale = min(tail_scale, 2.0 * std_ret)
    else:
        # No extreme events observed yet - slight uplift from kurtosis
        tail_scale = std_ret * (1.0 + min(kurtosis, 10.0) / 12.0)

    # Worst observed events
    sorted_pnl = np.sort(pnl_values)
    worst_5 = sorted_pnl[:5].tolist()
    best_5 = sorted_pnl[-5:].tolist()

    # Category breakdown for tail events
    tail_by_category = {}
    if n_tail_events > 0:
        for i, p in enumerate(closed_picks):
            if tail_mask[i]:
                cat = p.get("category", "unknown")
                tail_by_category[cat] = tail_by_category.get(cat, 0) + 1

    return {
        # Gaussian parameters
        "n_trades": n,
        "mean_return": mean_ret,
        "std_return": std_ret,
        "skewness": skewness,
        "excess_kurtosis": kurtosis,

        # Levy parameters
        "levy_alpha": alpha_est,
        "levy_beta": beta_est,
        "p_tail": p_tail,
        "tail_scale": tail_scale,
        "n_tail_events": n_tail_events,

        # Diagnostics
        "needs_levy": kurtosis > 3.0,
        "fat_tail_severity": (
            "EXTREME" if kurtosis > 10 else
            "HIGH" if kurtosis > 5 else
            "MODERATE" if kurtosis > 3 else
            "NORMAL"
        ),
        "worst_5_pnl": worst_5,
        "best_5_pnl": best_5,
        "tail_by_category": tail_by_category,
    }


# ======================================================================
# 3. HYBRID SIMULATION ENGINE
# ======================================================================

class LevyGaussianMonteCarlo:
    """
    Hybrid Monte Carlo simulator combining Gaussian (normal market noise)
    with Levy stable distribution (fat-tail / black swan events).
    """

    def __init__(self, n_simulations=10000, n_trades_per_sim=100, seed=42):
        self.n_simulations = n_simulations
        self.n_trades_per_sim = n_trades_per_sim
        self.rng = np.random.default_rng(seed=seed)

    def simulate_gaussian(self, mean_ret, std_ret):
        """
        Pure Gaussian Monte Carlo: all returns drawn from N(mean, std).
        """
        returns = self.rng.normal(
            mean_ret, std_ret,
            size=(self.n_simulations, self.n_trades_per_sim),
        )
        return self._compute_simulation_metrics(returns)

    def simulate_levy_gaussian_hybrid(self, calibration):
        """
        Hybrid Monte Carlo: most returns from Gaussian, tail events from Levy.

        For each simulated return:
          - With probability p_tail: draw from Levy stable (fat-tail event)
          - With probability (1-p_tail): draw from Gaussian (normal noise)
        """
        mean_ret = calibration["mean_return"]
        std_ret = calibration["std_return"]
        p_tail = calibration["p_tail"]
        alpha = calibration["levy_alpha"]
        beta = calibration["levy_beta"]
        tail_scale = calibration["tail_scale"]

        n_sims = self.n_simulations
        n_trades = self.n_trades_per_sim

        # Pre-generate all returns
        returns = np.empty((n_sims, n_trades), dtype=np.float64)

        # Determine which returns are tail events
        is_tail = self.rng.random(size=(n_sims, n_trades)) < p_tail
        n_tail_total = int(np.sum(is_tail))
        n_normal_total = n_sims * n_trades - n_tail_total

        # Generate Gaussian returns for normal events
        normal_returns = self.rng.normal(mean_ret, std_ret, size=n_normal_total)

        # Generate Levy returns for tail events
        if n_tail_total > 0:
            levy_returns = levy_stable_sample(
                alpha=alpha,
                beta=beta,
                gamma=tail_scale,
                delta=mean_ret,
                size=n_tail_total,
                rng=self.rng,
            )
        else:
            levy_returns = np.array([])

        # Assign returns
        normal_idx = 0
        tail_idx = 0
        for i in range(n_sims):
            for j in range(n_trades):
                if is_tail[i, j]:
                    returns[i, j] = levy_returns[tail_idx]
                    tail_idx += 1
                else:
                    returns[i, j] = normal_returns[normal_idx]
                    normal_idx += 1

        # Clamp extreme returns to realistic bounds (-95% to +200%)
        returns = np.clip(returns, -0.95, 2.0)

        return self._compute_simulation_metrics(returns)

    def _compute_simulation_metrics(self, returns):
        """
        Compute comprehensive metrics across all simulations.

        Args:
            returns: np.ndarray of shape (n_sims, n_trades_per_sim)

        Returns:
            dict with distributions of key risk metrics.
        """
        n_sims = returns.shape[0]

        # Pre-allocate
        max_drawdowns = np.empty(n_sims, dtype=np.float64)
        final_equities = np.empty(n_sims, dtype=np.float64)
        max_consecutive_losses = np.empty(n_sims, dtype=np.float64)
        worst_single_trade = np.empty(n_sims, dtype=np.float64)
        best_single_trade = np.empty(n_sims, dtype=np.float64)
        sharpe_ratios = np.empty(n_sims, dtype=np.float64)
        ruin_flags = np.zeros(n_sims, dtype=bool)  # equity drops below 20%
        half_flags = np.zeros(n_sims, dtype=bool)   # equity drops below 50%
        severe_dd_flags = np.zeros(n_sims, dtype=bool)  # DD > 50%

        for i in range(n_sims):
            sim_returns = returns[i]

            # Equity curve (compounding)
            equity = np.cumprod(1.0 + sim_returns)
            final_equities[i] = equity[-1]

            # Max drawdown
            running_max = np.maximum.accumulate(equity)
            drawdowns = (running_max - equity) / np.maximum(running_max, 1e-12)
            max_dd = float(np.max(drawdowns))
            max_drawdowns[i] = max_dd

            # Ruin/severity flags
            if np.min(equity) < 0.20:
                ruin_flags[i] = True
            if np.min(equity) < 0.50:
                half_flags[i] = True
            if max_dd > 0.50:
                severe_dd_flags[i] = True

            # Consecutive losses
            is_loss = sim_returns < 0
            max_consec = 0
            current_consec = 0
            for loss in is_loss:
                if loss:
                    current_consec += 1
                    max_consec = max(max_consec, current_consec)
                else:
                    current_consec = 0
            max_consecutive_losses[i] = max_consec

            # Worst/best single trade
            worst_single_trade[i] = float(np.min(sim_returns))
            best_single_trade[i] = float(np.max(sim_returns))

            # Sharpe ratio
            std_sim = float(np.std(sim_returns))
            if std_sim > 1e-12:
                sharpe_ratios[i] = (float(np.mean(sim_returns)) / std_sim) * math.sqrt(252)
            else:
                sharpe_ratios[i] = 0.0

        # Compute percentiles
        def pctiles(arr):
            return {
                "mean": float(np.mean(arr)),
                "median": float(np.median(arr)),
                "std": float(np.std(arr)),
                "p5": float(np.percentile(arr, 5)),
                "p10": float(np.percentile(arr, 10)),
                "p25": float(np.percentile(arr, 25)),
                "p75": float(np.percentile(arr, 75)),
                "p90": float(np.percentile(arr, 90)),
                "p95": float(np.percentile(arr, 95)),
                "p99": float(np.percentile(arr, 99)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
            }

        return {
            "max_drawdown": pctiles(max_drawdowns),
            "final_equity": pctiles(final_equities),
            "consecutive_losses": pctiles(max_consecutive_losses),
            "worst_single_trade": pctiles(worst_single_trade),
            "best_single_trade": pctiles(best_single_trade),
            "sharpe_ratio": pctiles(sharpe_ratios),
            "ruin_probability": float(np.mean(ruin_flags)),
            "half_loss_probability": float(np.mean(half_flags)),
            "severe_dd_probability": float(np.mean(severe_dd_flags)),
            "tail_event_stats": {
                "returns_below_neg10pct": float(np.mean(returns < -0.10)),
                "returns_below_neg20pct": float(np.mean(returns < -0.20)),
                "returns_below_neg50pct": float(np.mean(returns < -0.50)),
                "returns_above_pos10pct": float(np.mean(returns > 0.10)),
                "returns_above_pos20pct": float(np.mean(returns > 0.20)),
            },
        }


# ======================================================================
# 4. COMPARISON AND REPORTING
# ======================================================================

def compare_simulations(gaussian_results, hybrid_results):
    """
    Build a side-by-side comparison table between Gaussian and Levy-Gaussian.
    """
    g = gaussian_results
    h = hybrid_results

    comparison = {
        "max_drawdown_95th": {
            "gaussian": g["max_drawdown"]["p95"],
            "levy_gaussian": h["max_drawdown"]["p95"],
            "difference_pct": _pct_diff(g["max_drawdown"]["p95"], h["max_drawdown"]["p95"]),
            "interpretation": "Higher = more realistic tail risk",
        },
        "max_drawdown_99th": {
            "gaussian": g["max_drawdown"]["p99"],
            "levy_gaussian": h["max_drawdown"]["p99"],
            "difference_pct": _pct_diff(g["max_drawdown"]["p99"], h["max_drawdown"]["p99"]),
            "interpretation": "Extreme scenario drawdown",
        },
        "ruin_probability": {
            "gaussian": g["ruin_probability"],
            "levy_gaussian": h["ruin_probability"],
            "difference_factor": (
                h["ruin_probability"] / max(g["ruin_probability"], 1e-6)
            ),
            "interpretation": "Probability of losing 80%+ of capital",
        },
        "half_loss_probability": {
            "gaussian": g["half_loss_probability"],
            "levy_gaussian": h["half_loss_probability"],
            "difference_factor": (
                h["half_loss_probability"] / max(g["half_loss_probability"], 1e-6)
            ),
            "interpretation": "Probability of losing 50%+ of capital",
        },
        "severe_drawdown_probability": {
            "gaussian": g["severe_dd_probability"],
            "levy_gaussian": h["severe_dd_probability"],
            "difference_factor": (
                h["severe_dd_probability"] / max(g["severe_dd_probability"], 1e-6)
            ),
            "interpretation": "Probability of >50% drawdown",
        },
        "consecutive_losses_95th": {
            "gaussian": g["consecutive_losses"]["p95"],
            "levy_gaussian": h["consecutive_losses"]["p95"],
            "difference": h["consecutive_losses"]["p95"] - g["consecutive_losses"]["p95"],
            "interpretation": "Max losing streak (95th percentile)",
        },
        "worst_single_trade_95th": {
            "gaussian": g["worst_single_trade"]["p5"],  # 5th pctile of worst = most extreme
            "levy_gaussian": h["worst_single_trade"]["p5"],
            "difference_pct": _pct_diff(
                abs(g["worst_single_trade"]["p5"]),
                abs(h["worst_single_trade"]["p5"]),
            ),
            "interpretation": "Worst single trade in 95% of sims",
        },
        "median_final_equity": {
            "gaussian": g["final_equity"]["median"],
            "levy_gaussian": h["final_equity"]["median"],
            "difference_pct": _pct_diff(
                g["final_equity"]["median"], h["final_equity"]["median"]
            ),
            "interpretation": "Median portfolio value after 100 trades",
        },
        "tail_event_frequency": {
            "gaussian_neg10pct": g["tail_event_stats"]["returns_below_neg10pct"],
            "hybrid_neg10pct": h["tail_event_stats"]["returns_below_neg10pct"],
            "gaussian_neg20pct": g["tail_event_stats"]["returns_below_neg20pct"],
            "hybrid_neg20pct": h["tail_event_stats"]["returns_below_neg20pct"],
            "gaussian_neg50pct": g["tail_event_stats"]["returns_below_neg50pct"],
            "hybrid_neg50pct": h["tail_event_stats"]["returns_below_neg50pct"],
            "interpretation": "Frequency of extreme negative returns",
        },
    }

    return comparison


def compute_fat_tail_kelly(calibration, gaussian_results, hybrid_results):
    """
    Compute the 'realistic' Kelly fraction accounting for fat tails.

    Standard Kelly: f* = (p*b - q) / b
    Fat-tail adjusted: reduce by ratio of Gaussian/Levy tail risk.
    """
    mean_ret = calibration["mean_return"]
    std_ret = calibration["std_return"]

    # Standard Kelly from win rate and avg win/loss
    pnl_values = np.array(calibration.get("_pnl_values", []))
    if len(pnl_values) == 0:
        # Fallback: estimate from mean/std
        if std_ret > 1e-12:
            kelly_gaussian = mean_ret / (std_ret ** 2)
        else:
            kelly_gaussian = 0.0
        kelly_fat_tail = kelly_gaussian * 0.5
    else:
        # Exclude zero-PnL trades (expired at breakeven) from win/loss calc
        nonzero = pnl_values[np.abs(pnl_values) > 1e-8]
        if len(nonzero) == 0:
            nonzero = pnl_values  # fallback

        wins = nonzero[nonzero > 0]
        losses = nonzero[nonzero < 0]

        if len(wins) > 0 and len(losses) > 0:
            p_win = len(wins) / len(nonzero)
            avg_win = float(np.mean(wins))
            avg_loss = float(np.mean(np.abs(losses)))

            if avg_loss > 1e-12:
                b = avg_win / avg_loss  # win/loss ratio
                kelly_gaussian = (p_win * b - (1 - p_win)) / b
            else:
                kelly_gaussian = p_win
        else:
            kelly_gaussian = 0.0

        # Fat-tail adjustment factor:
        # Ratio of Gaussian to Levy 95th-percentile DD
        g_dd = max(gaussian_results["max_drawdown"]["p95"], 1e-6)
        h_dd = max(hybrid_results["max_drawdown"]["p95"], 1e-6)
        tail_penalty = g_dd / h_dd  # < 1 when Levy shows worse DD

        kelly_fat_tail = kelly_gaussian * tail_penalty

    # Practical Kelly: use quarter-Kelly as is standard practice
    return {
        "kelly_full_gaussian": max(0.0, kelly_gaussian),
        "kelly_full_fat_tail": max(0.0, kelly_fat_tail),
        "kelly_quarter_gaussian": max(0.0, kelly_gaussian * 0.25),
        "kelly_quarter_fat_tail": max(0.0, kelly_fat_tail * 0.25),
        "tail_risk_penalty": float(kelly_fat_tail / max(kelly_gaussian, 1e-6))
            if kelly_gaussian > 0 else 0.0,
        "recommendation": (
            "Fat tails reduce optimal Kelly fraction. Use quarter-Kelly "
            "with the fat-tail adjustment for position sizing."
        ),
    }


def _pct_diff(a, b):
    """Percentage difference: (b - a) / |a| * 100."""
    if abs(a) < 1e-12:
        return 0.0
    return float((b - a) / abs(a) * 100)


# ======================================================================
# 5. TEXT REPORT GENERATOR
# ======================================================================

def generate_markdown_report(calibration, gaussian, hybrid, comparison, kelly):
    """Generate the docs/LEVY_MONTE_CARLO.md report."""
    lines = []

    lines.append("# Levy-Gaussian Hybrid Monte Carlo Simulation")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("## Why Fat Tails Matter")
    lines.append("")
    lines.append("Standard Gaussian Monte Carlo assumes independent, normally-distributed")
    lines.append("returns. But our portfolio data shows **excess kurtosis = "
                 f"{calibration['excess_kurtosis']:.2f}** (normal = 0, typical hedge fund = 3-5).")
    lines.append("This means extreme events occur FAR more often than a bell curve predicts.")
    lines.append("")
    lines.append("A pure Gaussian simulation **underestimates** rare crashes and moonshots.")
    lines.append("The Levy stable distribution captures these fat tails explicitly.")
    lines.append("")

    # Calibration section
    lines.append("## Data Calibration")
    lines.append("")
    lines.append(f"- **Trades analyzed:** {calibration['n_trades']}")
    lines.append(f"- **Mean return:** {calibration['mean_return']*100:.4f}%")
    lines.append(f"- **Std deviation:** {calibration['std_return']*100:.4f}%")
    lines.append(f"- **Excess kurtosis:** {calibration['excess_kurtosis']:.2f} "
                 f"({calibration['fat_tail_severity']})")
    lines.append(f"- **Skewness:** {calibration['skewness']:.4f}")
    lines.append(f"- **Needs Levy correction:** {'YES' if calibration['needs_levy'] else 'NO'}")
    lines.append("")
    lines.append("### Levy Parameters")
    lines.append("")
    lines.append(f"- **Alpha (stability):** {calibration['levy_alpha']:.3f} "
                 "(2.0 = Gaussian, lower = fatter tails)")
    lines.append(f"- **Beta (skewness):** {calibration['levy_beta']:.3f}")
    lines.append(f"- **p_tail (tail probability):** {calibration['p_tail']*100:.1f}% "
                 f"({calibration['n_tail_events']} events beyond 3-sigma)")
    lines.append(f"- **tail_scale:** {calibration['tail_scale']*100:.4f}%")
    lines.append("")
    lines.append(f"Worst 5 trades: {[f'{x*100:.2f}%' for x in calibration['worst_5_pnl']]}")
    lines.append(f"Best 5 trades: {[f'{x*100:.2f}%' for x in calibration['best_5_pnl']]}")
    if calibration["tail_by_category"]:
        lines.append(f"Tail events by category: {calibration['tail_by_category']}")
    lines.append("")

    # Comparison table
    lines.append("## Simulation Results (10,000 simulations x 100 trades each)")
    lines.append("")
    lines.append("| Metric | Gaussian MC | Levy-Gaussian MC | Difference |")
    lines.append("|--------|------------|-----------------|------------|")

    c = comparison

    # Max DD 95th
    lines.append(
        f"| Max Drawdown (95th pct) | "
        f"{c['max_drawdown_95th']['gaussian']*100:.2f}% | "
        f"{c['max_drawdown_95th']['levy_gaussian']*100:.2f}% | "
        f"{c['max_drawdown_95th']['difference_pct']:+.1f}% |"
    )

    # Max DD 99th
    lines.append(
        f"| Max Drawdown (99th pct) | "
        f"{c['max_drawdown_99th']['gaussian']*100:.2f}% | "
        f"{c['max_drawdown_99th']['levy_gaussian']*100:.2f}% | "
        f"{c['max_drawdown_99th']['difference_pct']:+.1f}% |"
    )

    # Ruin probability
    lines.append(
        f"| Ruin probability (>80% loss) | "
        f"{c['ruin_probability']['gaussian']*100:.2f}% | "
        f"{c['ruin_probability']['levy_gaussian']*100:.2f}% | "
        f"{c['ruin_probability']['difference_factor']:.1f}x |"
    )

    # Half loss
    lines.append(
        f"| 50% loss probability | "
        f"{c['half_loss_probability']['gaussian']*100:.2f}% | "
        f"{c['half_loss_probability']['levy_gaussian']*100:.2f}% | "
        f"{c['half_loss_probability']['difference_factor']:.1f}x |"
    )

    # Severe DD
    lines.append(
        f"| >50% drawdown probability | "
        f"{c['severe_drawdown_probability']['gaussian']*100:.2f}% | "
        f"{c['severe_drawdown_probability']['levy_gaussian']*100:.2f}% | "
        f"{c['severe_drawdown_probability']['difference_factor']:.1f}x |"
    )

    # Consecutive losses
    lines.append(
        f"| Consecutive losses (95th pct) | "
        f"{c['consecutive_losses_95th']['gaussian']:.0f} | "
        f"{c['consecutive_losses_95th']['levy_gaussian']:.0f} | "
        f"{c['consecutive_losses_95th']['difference']:+.0f} |"
    )

    # Worst single trade
    lines.append(
        f"| Worst single trade (5th pct) | "
        f"{c['worst_single_trade_95th']['gaussian']*100:.2f}% | "
        f"{c['worst_single_trade_95th']['levy_gaussian']*100:.2f}% | "
        f"{c['worst_single_trade_95th']['difference_pct']:+.1f}% |"
    )

    # Median final equity
    lines.append(
        f"| Median final equity | "
        f"{c['median_final_equity']['gaussian']:.4f} | "
        f"{c['median_final_equity']['levy_gaussian']:.4f} | "
        f"{c['median_final_equity']['difference_pct']:+.1f}% |"
    )

    lines.append("")

    # Tail event frequency
    lines.append("### Tail Event Frequency (per trade)")
    lines.append("")
    lines.append("| Event | Gaussian | Levy-Gaussian | Ratio |")
    lines.append("|-------|----------|--------------|-------|")
    te = c["tail_event_frequency"]
    for threshold, label in [("neg10pct", ">10% loss"), ("neg20pct", ">20% loss"),
                              ("neg50pct", ">50% loss")]:
        g_val = te[f"gaussian_{threshold}"]
        h_val = te[f"hybrid_{threshold}"]
        ratio = h_val / max(g_val, 1e-8)
        lines.append(f"| {label} | {g_val*100:.4f}% | {h_val*100:.4f}% | {ratio:.1f}x |")
    lines.append("")

    # Kelly section
    lines.append("## Risk-Adjusted Position Sizing (Kelly Criterion)")
    lines.append("")
    lines.append(f"- **Full Kelly (Gaussian):** {kelly['kelly_full_gaussian']*100:.2f}%")
    lines.append(f"- **Full Kelly (Fat-Tail Adjusted):** {kelly['kelly_full_fat_tail']*100:.2f}%")
    lines.append(f"- **Quarter Kelly (Gaussian):** {kelly['kelly_quarter_gaussian']*100:.2f}%")
    lines.append(f"- **Quarter Kelly (Fat-Tail Adjusted):** "
                 f"{kelly['kelly_quarter_fat_tail']*100:.2f}%")
    lines.append(f"- **Tail risk penalty:** {kelly['tail_risk_penalty']:.3f} "
                 "(1.0 = no penalty, lower = more conservative)")
    lines.append("")
    lines.append(f"> {kelly['recommendation']}")
    lines.append("")

    # Detailed distributions
    lines.append("## Detailed Distributions")
    lines.append("")
    for sim_name, sim_data in [("Gaussian", gaussian), ("Levy-Gaussian Hybrid", hybrid)]:
        lines.append(f"### {sim_name}")
        lines.append("")
        for metric_name, metric_key in [
            ("Max Drawdown", "max_drawdown"),
            ("Final Equity", "final_equity"),
            ("Sharpe Ratio", "sharpe_ratio"),
        ]:
            d = sim_data[metric_key]
            lines.append(f"**{metric_name}:**")
            mult = 100 if metric_key == "max_drawdown" else 1
            sfx = "%" if metric_key == "max_drawdown" else ""
            lines.append(
                f"  Mean={d['mean']*mult:.2f}{sfx}, "
                f"Median={d['median']*mult:.2f}{sfx}, "
                f"5th={d['p5']*mult:.2f}{sfx}, "
                f"95th={d['p95']*mult:.2f}{sfx}, "
                f"99th={d['p99']*mult:.2f}{sfx}"
            )
            lines.append("")

    # Implications
    lines.append("## Risk Implications")
    lines.append("")

    g_ruin = comparison["ruin_probability"]["gaussian"]
    h_ruin = comparison["ruin_probability"]["levy_gaussian"]
    g_dd95 = comparison["max_drawdown_95th"]["gaussian"]
    h_dd95 = comparison["max_drawdown_95th"]["levy_gaussian"]

    if h_ruin > g_ruin * 2:
        lines.append("**WARNING: Gaussian MC significantly underestimates tail risk.**")
        lines.append("")
        lines.append(
            f"The Levy-Gaussian simulation shows {h_ruin/max(g_ruin,1e-6):.0f}x higher "
            f"ruin probability than the Gaussian model. The 95th-percentile max drawdown "
            f"is {h_dd95*100:.1f}% vs {g_dd95*100:.1f}% under Gaussian assumptions."
        )
    elif h_dd95 > g_dd95 * 1.2:
        lines.append("**CAUTION: Meaningful fat-tail risk detected.**")
        lines.append("")
        lines.append(
            f"The Levy model shows {(h_dd95-g_dd95)*100:.1f}pp worse drawdowns "
            f"at the 95th percentile. Position sizing should account for this."
        )
    else:
        lines.append("Fat-tail effects are modest for this portfolio. Gaussian MC provides")
        lines.append("a reasonable approximation, but the Levy model remains more conservative.")

    lines.append("")
    lines.append("### Recommendations")
    lines.append("")
    lines.append(
        f"1. Use **quarter-Kelly at {kelly['kelly_quarter_fat_tail']*100:.2f}%** "
        "instead of the Gaussian-derived sizing"
    )
    lines.append("2. Set stop losses assuming the Levy tail distribution, not Gaussian")
    lines.append(
        f"3. Budget for max drawdowns of **{h_dd95*100:.1f}%** "
        f"(not {g_dd95*100:.1f}% as Gaussian suggests)"
    )
    lines.append(
        f"4. Maintain cash reserves for {comparison['consecutive_losses_95th']['levy_gaussian']:.0f}+ "
        "consecutive losses"
    )
    lines.append("")
    lines.append("---")
    lines.append("*Generated by `alpha_engine/levy_gaussian_monte_carlo.py`*")

    return "\n".join(lines)


# ======================================================================
# 6. MAIN RUNNER
# ======================================================================

def run_levy_monte_carlo():
    """
    Full pipeline: load data -> calibrate -> simulate -> compare -> report.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    data_path = os.path.join(data_dir, "closed_picks.json")

    if not os.path.exists(data_path):
        print(f"ERROR: closed_picks.json not found at {data_path}")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        closed_picks = json.load(f)

    n_trades = len(closed_picks)
    if n_trades < 10:
        print(f"Only {n_trades} trades — need at least 10 for meaningful simulation.")
        return

    print(f"Loaded {n_trades} closed picks.")
    print()

    # --- Calibrate ---
    print("=" * 60)
    print("CALIBRATING FROM LIVE TRADE DATA")
    print("=" * 60)
    calibration = calibrate_from_data(closed_picks)

    # Store raw PnL for Kelly calculation
    pnl_values = [float(p.get("pnl_pct", 0.0)) for p in closed_picks]
    calibration["_pnl_values"] = pnl_values

    print(f"  Mean return:       {calibration['mean_return']*100:.4f}%")
    print(f"  Std deviation:     {calibration['std_return']*100:.4f}%")
    print(f"  Excess kurtosis:   {calibration['excess_kurtosis']:.2f} "
          f"({calibration['fat_tail_severity']})")
    print(f"  Skewness:          {calibration['skewness']:.4f}")
    print(f"  Levy alpha:        {calibration['levy_alpha']:.3f}")
    print(f"  p_tail:            {calibration['p_tail']*100:.1f}%")
    print(f"  Tail scale:        {calibration['tail_scale']*100:.4f}%")
    print(f"  Needs Levy:        {'YES' if calibration['needs_levy'] else 'NO'}")
    print()

    # --- Simulate ---
    n_sims = 10000
    n_trades_per = 100

    print("=" * 60)
    print(f"RUNNING SIMULATIONS ({n_sims:,} sims x {n_trades_per} trades)")
    print("=" * 60)

    mc = LevyGaussianMonteCarlo(
        n_simulations=n_sims,
        n_trades_per_sim=n_trades_per,
        seed=42,
    )

    # Gaussian simulation
    print("  Running Gaussian MC...", end=" ", flush=True)
    t0 = time.time()
    gaussian = mc.simulate_gaussian(
        calibration["mean_return"],
        calibration["std_return"],
    )
    print(f"done ({time.time()-t0:.1f}s)")

    # Levy-Gaussian hybrid
    print("  Running Levy-Gaussian hybrid MC...", end=" ", flush=True)
    t0 = time.time()
    hybrid = mc.simulate_levy_gaussian_hybrid(calibration)
    print(f"done ({time.time()-t0:.1f}s)")
    print()

    # --- Compare ---
    print("=" * 60)
    print("COMPARISON: GAUSSIAN vs LEVY-GAUSSIAN")
    print("=" * 60)
    comparison = compare_simulations(gaussian, hybrid)

    print(f"{'Metric':<35} {'Gaussian':>12} {'Levy-Gauss':>12} {'Diff':>10}")
    print("-" * 72)
    print(f"{'Max DD (95th pct)':<35} "
          f"{comparison['max_drawdown_95th']['gaussian']*100:>11.2f}% "
          f"{comparison['max_drawdown_95th']['levy_gaussian']*100:>11.2f}% "
          f"{comparison['max_drawdown_95th']['difference_pct']:>+9.1f}%")
    print(f"{'Max DD (99th pct)':<35} "
          f"{comparison['max_drawdown_99th']['gaussian']*100:>11.2f}% "
          f"{comparison['max_drawdown_99th']['levy_gaussian']*100:>11.2f}% "
          f"{comparison['max_drawdown_99th']['difference_pct']:>+9.1f}%")
    print(f"{'Ruin probability (>80% loss)':<35} "
          f"{comparison['ruin_probability']['gaussian']*100:>11.2f}% "
          f"{comparison['ruin_probability']['levy_gaussian']*100:>11.2f}% "
          f"{comparison['ruin_probability']['difference_factor']:>9.1f}x")
    print(f"{'50% loss probability':<35} "
          f"{comparison['half_loss_probability']['gaussian']*100:>11.2f}% "
          f"{comparison['half_loss_probability']['levy_gaussian']*100:>11.2f}% "
          f"{comparison['half_loss_probability']['difference_factor']:>9.1f}x")
    print(f"{'Consecutive losses (95th)':<35} "
          f"{comparison['consecutive_losses_95th']['gaussian']:>12.0f} "
          f"{comparison['consecutive_losses_95th']['levy_gaussian']:>12.0f} "
          f"{comparison['consecutive_losses_95th']['difference']:>+10.0f}")
    print(f"{'Worst trade (5th pct)':<35} "
          f"{comparison['worst_single_trade_95th']['gaussian']*100:>11.2f}% "
          f"{comparison['worst_single_trade_95th']['levy_gaussian']*100:>11.2f}% "
          f"{comparison['worst_single_trade_95th']['difference_pct']:>+9.1f}%")
    print()

    # --- Kelly ---
    kelly = compute_fat_tail_kelly(calibration, gaussian, hybrid)
    print("POSITION SIZING (Kelly Criterion)")
    print("-" * 40)
    print(f"  Full Kelly (Gaussian):    {kelly['kelly_full_gaussian']*100:.2f}%")
    print(f"  Full Kelly (Fat-Tail):    {kelly['kelly_full_fat_tail']*100:.2f}%")
    print(f"  Quarter Kelly (Gaussian): {kelly['kelly_quarter_gaussian']*100:.2f}%")
    print(f"  Quarter Kelly (Fat-Tail): {kelly['kelly_quarter_fat_tail']*100:.2f}%")
    print(f"  Tail risk penalty:        {kelly['tail_risk_penalty']:.3f}")
    print()

    # --- Save JSON report ---
    # Remove non-serializable _pnl_values before saving
    cal_save = {k: v for k, v in calibration.items() if k != "_pnl_values"}

    report_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calibration": cal_save,
        "simulation_config": {
            "n_simulations": n_sims,
            "n_trades_per_sim": n_trades_per,
            "seed": 42,
        },
        "gaussian_results": gaussian,
        "levy_gaussian_results": hybrid,
        "comparison": comparison,
        "kelly_analysis": kelly,
    }

    json_path = os.path.join(data_dir, "levy_monte_carlo_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2, default=str)
    print(f"JSON report saved: {json_path}")

    # --- Save markdown report ---
    docs_dir = os.path.join(os.path.dirname(base_dir), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    md_path = os.path.join(docs_dir, "LEVY_MONTE_CARLO.md")

    md_content = generate_markdown_report(calibration, gaussian, hybrid, comparison, kelly)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Markdown report saved: {md_path}")

    print()
    print("=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_levy_monte_carlo()
