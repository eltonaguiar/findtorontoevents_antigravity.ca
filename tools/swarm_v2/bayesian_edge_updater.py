"""
Bayesian Edge Updater — PR-4 Meta-Improvement Swarm.

Implements Bayesian updating of per-asset-class edge estimates using a
Beta-Bernoulli conjugate model.  All Beta distribution calculations are
implemented from first principles (no numpy/scipy).

Typical usage::

    updater = BayesianEdgeUpdater(prior_wr=0.52, prior_confidence=20)
    updater.update_from_outcome("BTC-USD", win=True, pnl_pct=3.5)
    updater.update_from_outcome("BTC-USD", win=False, pnl_pct=-2.1)
    print(updater.generate_edge_forecast())
"""
from __future__ import annotations

import json
import logging
import math
import os
import random
import time
from typing import Any

logger = logging.getLogger("swarm_v2.bayesian")


# ---------------------------------------------------------------------------
# Beta distribution helpers (no external dependencies)
# ---------------------------------------------------------------------------

def _log_gamma(z: float) -> float:
    """Compute log(Gamma(z)) using the Lanczos approximation.

    Valid for z > 0.  This is sufficient for the Beta-Bernoulli use-case
    where alpha, beta > 0.
    """
    # Lanczos coefficients for g = 7
    _p = [
        0.99999999999980993,
        676.5203681218851,
        -1259.1392167224028,
        771.32342877765313,
        -176.61502916214059,
        12.507343278686905,
        -0.13857109526572012,
        9.9843695780195716e-6,
        1.5056327351493116e-7,
    ]
    if z < 0.5:
        # Reflection formula
        return math.log(math.pi) - math.log(math.sin(math.pi * z)) - _log_gamma(1.0 - z)

    z -= 1.0
    x = _p[0]
    for i in range(1, 9):
        x += _p[i] / (z + i)
    t = z + 7.0 + 0.5
    return 0.5 * math.log(2.0 * math.pi) + (z + 0.5) * math.log(t) - t + math.log(x)


def _log_beta(a: float, b: float) -> float:
    """Compute log(Beta(a, b)) = log(Gamma(a)) + log(Gamma(b)) - log(Gamma(a+b))."""
    return _log_gamma(a) + _log_gamma(b) - _log_gamma(a + b)


def _beta_pdf(x: float, a: float, b: float) -> float:
    """Probability density function of Beta(a, b) at x."""
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return math.exp((a - 1.0) * math.log(x) + (b - 1.0) * math.log(1.0 - x) - _log_beta(a, b))


def _beta_cdf(x: float, a: float, b: float, n_steps: int = 2000) -> float:
    """Approximate the CDF of Beta(a, b) at x via numerical integration (trapezoid rule).

    Parameters
    ----------
    x:
        Upper integration bound (0 <= x <= 1).
    a, b:
        Beta distribution shape parameters (must be > 0).
    n_steps:
        Number of trapezoids to use.  Increase for more accuracy.
    """
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    # Use adaptive Simpson's method for better accuracy with fewer steps
    def _simpson(f, lo: float, hi: float, eps: float = 1e-10, max_level: int = 20) -> float:
        c = (lo + hi) / 2.0
        d = (hi - lo) / 2.0
        fa, fb, fc = f(lo), f(hi), f(c)
        s = d * (fa + 4.0 * fc + fb) / 3.0

        def _recurse(a: float, b: float, c: float, fa: float, fb: float, fc: float, eps: float, whole: float, level: int) -> float:
            d = (b - a) / 2.0
            e = (a + c) / 2.0
            g = (c + b) / 2.0
            fe, fg = f(e), f(g)
            left = d * (fa + 4.0 * fe + fc) / 3.0
            right = d * (fc + 4.0 * fg + fb) / 3.0
            if level >= max_level:
                return left + right
            if abs(left + right - whole) <= 15.0 * eps:
                return left + right + (left + right - whole) / 15.0
            return (_recurse(a, c, e, fa, fc, fe, eps / 2.0, left, level + 1) +
                    _recurse(c, b, g, fc, fb, fg, eps / 2.0, right, level + 1))

        return _recurse(lo, hi, c, fa, fb, fc, eps, s, 0)

    def _integrand(t: float) -> float:
        return _beta_pdf(t, a, b)

    return _simpson(_integrand, 0.0, x)


def _beta_quantile(p: float, a: float, b: float, tol: float = 1e-8, max_iter: int = 100) -> float:
    """Approximate the p-th quantile of Beta(a, b) via bisection.

    Parameters
    ----------
    p:
        Target cumulative probability (0 < p < 1).
    a, b:
        Beta shape parameters.
    tol:
        Bisection tolerance.
    max_iter:
        Maximum iterations.
    """
    lo, hi = 0.0, 1.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        cdf_mid = _beta_cdf(mid, a, b)
        if abs(cdf_mid - p) < tol:
            return mid
        if cdf_mid < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# ---------------------------------------------------------------------------
# Edge classification helper
# ---------------------------------------------------------------------------

def _classify_edge(prob_above_baseline: float) -> str:
    """Classify the strength of an edge given P(edge > baseline).

    Thresholds
    ----------
    P > 0.90  → HIGH_CONFIDENCE_EDGE
    P > 0.75  → MODERATE_CONFIDENCE_EDGE
    P > 0.50  → WEAK_EDGE
    P ≤ 0.50  → NO_EDGE
    """
    if prob_above_baseline > 0.90:
        return "HIGH_CONFIDENCE_EDGE"
    if prob_above_baseline > 0.75:
        return "MODERATE_CONFIDENCE_EDGE"
    if prob_above_baseline > 0.50:
        return "WEAK_EDGE"
    return "NO_EDGE"


# ---------------------------------------------------------------------------
# BayesianEdgeUpdater
# ---------------------------------------------------------------------------

class BayesianEdgeUpdater:
    """Bayesian updater for per-asset-class edge estimates.

    Uses a Beta-Bernoulli conjugate model:

        Prior :  Beta(prior_wr * prior_confidence, (1-prior_wr) * prior_confidence)
        Likelihood : Bernoulli(win/loss)
        Posterior : Beta(alpha + wins, beta + losses)

    All Beta distribution math is implemented from first principles
    (log-Gamma via Lanczos, CDF via adaptive Simpson, quantiles via bisection).

    Parameters
    ----------
    prior_wr:
        Prior win-rate belief (default 0.50 = no edge).
    prior_confidence:
        Equivalent sample size of the prior (default 10).  Higher = stronger prior.
    """

    def __init__(self, prior_wr: float = 0.50, prior_confidence: int = 10) -> None:
        if not (0.0 < prior_wr < 1.0):
            raise ValueError("prior_wr must be in (0, 1)")
        if prior_confidence <= 0:
            raise ValueError("prior_confidence must be positive")

        self.prior_wr: float = prior_wr
        self.prior_confidence: int = prior_confidence
        self._prior_alpha: float = prior_wr * prior_confidence
        self._prior_beta: float = (1.0 - prior_wr) * prior_confidence

        # Per-asset-class state: {asset_class: {"wins": int, "losses": int, "pnl_log": [float]}}
        self._state: dict[str, dict[str, Any]] = {}

        logger.info(
            "BayesianEdgeUpdater initialised (prior_wr=%.3f, confidence=%d, alpha=%.3f, beta=%.3f)",
            prior_wr, prior_confidence, self._prior_alpha, self._prior_beta,
        )

    # -- Internal helpers ----------------------------------------------------

    def _get_or_create_asset(self, asset_class: str) -> dict[str, Any]:
        """Return existing state for *asset_class* or create a fresh entry."""
        if asset_class not in self._state:
            self._state[asset_class] = {
                "wins": 0,
                "losses": 0,
                "pnl_log": [],
                "last_updated": time.time(),
            }
            logger.debug("Created new asset entry for %r", asset_class)
        return self._state[asset_class]

    def _posterior_params(self, asset_class: str) -> tuple[float, float]:
        """Return (alpha_posterior, beta_posterior) for *asset_class*."""
        entry = self._get_or_create_asset(asset_class)
        alpha_post = self._prior_alpha + entry["wins"]
        beta_post = self._prior_beta + entry["losses"]
        return alpha_post, beta_post

    def _posterior_mean(self, asset_class: str) -> float:
        """Posterior expected win-rate."""
        a, b = self._posterior_params(asset_class)
        return a / (a + b)

    # -- Public API ----------------------------------------------------------

    def update_from_outcome(self, asset_class: str, win: bool, pnl_pct: float) -> dict:
        """Incorporate a single trade outcome into the Bayesian model.

        Parameters
        ----------
        asset_class:
            Identifier for the asset class (e.g. ``"BTC-USD"``).
        win:
            ``True`` if the trade was profitable, ``False`` otherwise.
        pnl_pct:
            Profit/loss expressed as a percentage (e.g. ``3.5`` for +3.5%%).

        Returns
        -------
        dict
            Summary of the updated posterior:
            ``{"asset_class": str, "win": bool, "pnl_pct": float,
            "posterior_wr": float, "alpha": float, "beta": float,
            "total_trades": int}``
        """
        entry = self._get_or_create_asset(asset_class)
        if win:
            entry["wins"] += 1
        else:
            entry["losses"] += 1
        entry["pnl_log"].append(pnl_pct)
        entry["last_updated"] = time.time()

        a_post, b_post = self._posterior_params(asset_class)
        posterior_wr = a_post / (a_post + b_post)
        total_trades = entry["wins"] + entry["losses"]

        logger.info(
            "Updated %s | win=%s pnl=%+.3f%% | posterior_wr=%.4f (alpha=%.2f beta=%.2f) | n=%d",
            asset_class, win, pnl_pct, posterior_wr, a_post, b_post, total_trades,
        )

        return {
            "asset_class": asset_class,
            "win": win,
            "pnl_pct": pnl_pct,
            "posterior_wr": round(posterior_wr, 6),
            "alpha": round(a_post, 4),
            "beta": round(b_post, 4),
            "total_trades": total_trades,
        }

    def get_posterior_distribution(self, asset_class: str) -> dict:
        """Return the current Beta distribution parameters for *asset_class*.

        Returns
        -------
        dict
            ``{"asset_class": str, "alpha": float, "beta": float,
            "mean": float, "variance": float}``
        """
        a, b = self._posterior_params(asset_class)
        mean = a / (a + b)
        variance = (a * b) / ((a + b) ** 2 * (a + b + 1.0))
        return {
            "asset_class": asset_class,
            "alpha": round(a, 4),
            "beta": round(b, 4),
            "mean": round(mean, 6),
            "variance": round(variance, 8),
        }

    def compute_credible_interval(
        self, asset_class: str, confidence: float = 0.95
    ) -> tuple[float, float]:
        """Compute the Bayesian credible interval for the win-rate of *asset_class*.

        Parameters
        ----------
        asset_class:
            Asset class identifier.
        confidence:
            Credible-interval level (default 0.95 for 95%% CI).

        Returns
        -------
        tuple[float, float]
            ``(lower_bound, upper_bound)`` of the credible interval.
        """
        if not (0.0 < confidence < 1.0):
            raise ValueError("confidence must be in (0, 1)")
        a, b = self._posterior_params(asset_class)
        tail = (1.0 - confidence) / 2.0
        lower = _beta_quantile(tail, a, b)
        upper = _beta_quantile(1.0 - tail, a, b)
        logger.debug("%s %.0f%% CI = [%.4f, %.4f]", asset_class, confidence * 100, lower, upper)
        return round(lower, 6), round(upper, 6)

    def compare_edge_vs_baseline(self, asset_class: str, baseline_wr: float = 0.50) -> dict:
        """Compare the estimated edge against a baseline win-rate.

        Computes ``P(edge > baseline_wr)`` from the posterior Beta distribution
        and classifies the confidence level.

        Parameters
        ----------
        asset_class:
            Asset class identifier.
        baseline_wr:
            Baseline win-rate to compare against (default 0.50).

        Returns
        -------
        dict
            ``{"asset_class": str, "baseline_wr": float,
            "posterior_mean_wr": float, "prob_edge_above_baseline": float,
            "classification": str}``
        """
        a, b = self._posterior_params(asset_class)
        posterior_mean = a / (a + b)

        # P(edge > baseline) = 1 - CDF(baseline)
        prob_above = 1.0 - _beta_cdf(baseline_wr, a, b)
        classification = _classify_edge(prob_above)

        logger.info(
            "Edge comparison %s vs baseline %.3f | P(edge>baseline)=%.4f | %s",
            asset_class, baseline_wr, prob_above, classification,
        )

        return {
            "asset_class": asset_class,
            "baseline_wr": baseline_wr,
            "posterior_mean_wr": round(posterior_mean, 6),
            "prob_edge_above_baseline": round(prob_above, 6),
            "classification": classification,
        }

    def predict_future_win_rate(
        self, asset_class: str, n_future_trades: int
    ) -> dict:
        """Predict the expected win-rate after *n_future_trades* additional samples.

        The prediction is the posterior predictive mean, which equals the
        posterior mean of the win-rate (Beta-Bernoulli conjugacy).

        Parameters
        ----------
        asset_class:
            Asset class identifier.
        n_future_trades:
            Number of future trades to project.

        Returns
        -------
        dict
            ``{"asset_class": str, "n_future_trades": int,
            "predicted_wr": float, "current_wr": float,
            "uncertainty_reduction": float}`` where
            ``uncertainty_reduction`` is the proportional narrowing of the
            posterior standard deviation if the trades were observed.
        """
        a, b = self._posterior_params(asset_class)
        current_mean = a / (a + b)
        current_var = (a * b) / ((a + b) ** 2 * (a + b + 1.0))
        current_std = math.sqrt(current_var)

        # Posterior predictive mean = posterior mean (Beta-Bernoulli)
        predicted_wr = current_mean

        # If we observed n_future_trades, posterior std would shrink
        # (assuming they match current mean)
        a_future = a + n_future_trades * current_mean
        b_future = b + n_future_trades * (1.0 - current_mean)
        future_var = (a_future * b_future) / ((a_future + b_future) ** 2 * (a_future + b_future + 1.0))
        future_std = math.sqrt(future_var)

        uncertainty_reduction = 0.0
        if current_std > 0:
            uncertainty_reduction = (current_std - future_std) / current_std

        return {
            "asset_class": asset_class,
            "n_future_trades": n_future_trades,
            "predicted_wr": round(predicted_wr, 6),
            "current_wr": round(current_mean, 6),
            "current_std": round(current_std, 6),
            "predicted_std_after_n": round(future_std, 6),
            "uncertainty_reduction": round(uncertainty_reduction, 4),
        }

    def generate_edge_forecast(self) -> str:
        """Generate a full markdown report of all tracked asset classes.

        Returns
        -------
        str
            Markdown-formatted edge forecast report.
        """
        if not self._state:
            return "# Bayesian Edge Forecast\n\n_No asset classes tracked yet._\n"

        lines: list[str] = [
            "# Bayesian Edge Forecast",
            "",
            f"_Prior: Beta({self._prior_alpha:.2f}, {self._prior_beta:.2f}) | "
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}_",
            "",
        ]

        for asset in sorted(self._state.keys()):
            post = self.get_posterior_distribution(asset)
            ci_low, ci_high = self.compute_credible_interval(asset, confidence=0.95)
            ci_low_80, ci_high_80 = self.compute_credible_interval(asset, confidence=0.80)
            comparison = self.compare_edge_vs_baseline(asset, baseline_wr=0.50)

            entry = self._state[asset]
            total = entry["wins"] + entry["losses"]
            pnl_log = entry["pnl_log"]
            avg_pnl = sum(pnl_log) / len(pnl_log) if pnl_log else 0.0

            lines.append(f"## {asset}")
            lines.append("")
            lines.append(f"- **Total trades**: {total} (W:{entry['wins']} L:{entry['losses']})")
            lines.append(f"- **Avg PnL**: {avg_pnl:+.3f}%")
            lines.append(f"- **Posterior WR**: {post['mean']:.4f}")
            lines.append(f"- **95% Credible Interval**: [{ci_low:.4f}, {ci_high:.4f}]")
            lines.append(f"- **80% Credible Interval**: [{ci_low_80:.4f}, {ci_high_80:.4f}]")
            lines.append(f"- **P(edge > 0.50)**: {comparison['prob_edge_above_baseline']:.4f}")
            lines.append(f"- **Classification**: `{comparison['classification']}`")
            lines.append("")

        lines.append("---")
        lines.append(f"_Report covers {len(self._state)} asset class(es)_")
        lines.append("")
        return "\n".join(lines)

    # -- Persistence ---------------------------------------------------------

    def save(self, path: str) -> None:
        """Serialise current state to *path* as JSON.

        Parameters
        ----------
        path:
            Destination file path.
        """
        payload = {
            "prior_wr": self.prior_wr,
            "prior_confidence": self.prior_confidence,
            "prior_alpha": self._prior_alpha,
            "prior_beta": self._prior_beta,
            "state": self._state,
            "saved_at": time.time(),
        }
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)
        logger.info("Saved BayesianEdgeUpdater state to %s", path)

    def load(self, path: str) -> None:
        """Restore state from a JSON file written by :meth:`save`.

        Parameters
        ----------
        path:
            Source file path.
        """
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        self.prior_wr = payload["prior_wr"]
        self.prior_confidence = payload["prior_confidence"]
        self._prior_alpha = payload["prior_alpha"]
        self._prior_beta = payload["prior_beta"]
        self._state = payload["state"]
        logger.info("Loaded BayesianEdgeUpdater state from %s (%d assets)", path, len(self._state))

    def get_state_summary(self) -> dict[str, Any]:
        """Return a JSON-serialisable summary of the full internal state.

        Useful for integration with the meta-swarm orchestrator.
        """
        return {
            "prior": {
                "wr": self.prior_wr,
                "confidence": self.prior_confidence,
                "alpha": self._prior_alpha,
                "beta": self._prior_beta,
            },
            "assets": {
                asset: {
                    "wins": data["wins"],
                    "losses": data["losses"],
                    "total_trades": data["wins"] + data["losses"],
                    "avg_pnl": round(sum(data["pnl_log"]) / len(data["pnl_log"]), 6) if data["pnl_log"] else 0.0,
                    "posterior_mean": self._posterior_mean(asset),
                }
                for asset, data in self._state.items()
            },
        }
