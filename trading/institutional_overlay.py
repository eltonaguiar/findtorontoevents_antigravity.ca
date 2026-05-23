#!/usr/bin/env python3
"""
Institutional Overlay — 7-Layer Safety Stack
=============================================

Transforms the ATM Challenge from a retail signal system into
an institutional-grade alpha engine.

Layers:
    1. Bayesian Edge Scoring     — Replace raw WR with posterior confidence
    2. Regime-Weighted Routing   — Probabilistic position sizing by regime
    3. Meta-Model Consensus      — Stacked ensemble over all engines
    4. Fractional Kelly Sizing   — Drawdown-constrained position sizing
    5. Correlation-Aware Alloc   — Risk parity across strategy sleeves
    6. Walk-Forward Validation   — Mandatory OOS validation for promotion
    7. Feature Drift Monitoring  — PSI-based edge decay detection

Usage:
    from trading.institutional_overlay import InstitutionalOverlay

    overlay = InstitutionalOverlay()
    # Bayesian scoring
    score = overlay.bayesian_edge_score(wins=15, losses=5)
    # Regime routing
    weight = overlay.regime_weight(strategy_type="funding_carry", regime_probs={...})
    # Full pipeline
    decision = overlay.evaluate_signal(variant, regime_state, market_features)
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ── Layer 1: Bayesian Edge Scoring ───────────────────────────────────

@dataclass
class BayesianEdgeScore:
    """Result of Bayesian win-rate estimation."""
    posterior_mean: float
    prob_above_50: float
    prob_above_55: float
    credible_interval_90: Tuple[float, float]
    sample_size: int
    confidence_grade: str  # A/B/C/D/F


class BayesianEdgeScorer:
    """
    Replace raw win-rate with Bayesian posterior confidence.

    Uses Beta-Binomial conjugate model:
        Prior: Beta(alpha=1, beta=1) — uniform (no prior bias)
        Posterior: Beta(alpha + wins, beta + losses)

    Key metric: P(true_WR > threshold | data)
    This prevents small-sample illusions and lucky-streak promotions.
    """

    PROMOTION_THRESHOLD = 0.50
    PROMOTION_CONFIDENCE = 0.90
    KILL_CONFIDENCE = 0.40
    MIN_TRADES_BAYESIAN = 5

    def __init__(self, prior_alpha: float = 1.0, prior_beta: float = 1.0):
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta

    def score(self, wins: int, losses: int) -> BayesianEdgeScore:
        """Compute Bayesian edge score from win/loss record."""
        total = wins + losses
        alpha = self.prior_alpha + wins
        beta = self.prior_beta + losses

        posterior_mean = alpha / (alpha + beta)
        prob_above_50 = self._beta_sf(0.50, alpha, beta)
        prob_above_55 = self._beta_sf(0.55, alpha, beta)

        ci_low = self._beta_ppf(0.05, alpha, beta)
        ci_high = self._beta_ppf(0.95, alpha, beta)

        grade = self._grade(prob_above_50, total)

        return BayesianEdgeScore(
            posterior_mean=round(posterior_mean, 4),
            prob_above_50=round(prob_above_50, 4),
            prob_above_55=round(prob_above_55, 4),
            credible_interval_90=(round(ci_low, 4), round(ci_high, 4)),
            sample_size=total,
            confidence_grade=grade,
        )

    def should_promote(self, wins: int, losses: int,
                       min_trades: int = 30) -> bool:
        """Promote only if P(true WR > 50%) > 90% AND trades >= min."""
        total = wins + losses
        if total < min_trades:
            return False
        score = self.score(wins, losses)
        return score.prob_above_50 >= self.PROMOTION_CONFIDENCE

    def should_kill(self, wins: int, losses: int,
                    min_trades: int = 10) -> bool:
        """Kill if P(true WR > 50%) < 40%."""
        total = wins + losses
        if total < min_trades:
            return False
        score = self.score(wins, losses)
        return score.prob_above_50 < self.KILL_CONFIDENCE

    def _grade(self, prob_above_50: float, sample_size: int) -> str:
        if sample_size < 10:
            return "F"
        if prob_above_50 >= 0.95 and sample_size >= 50:
            return "A"
        if prob_above_50 >= 0.90 and sample_size >= 30:
            return "B"
        if prob_above_50 >= 0.75 and sample_size >= 20:
            return "C"
        if prob_above_50 >= 0.50:
            return "D"
        return "F"

    @staticmethod
    def _beta_sf(x: float, alpha: float, beta: float) -> float:
        """P(X > x) for Beta distribution using regularized incomplete beta."""
        return 1.0 - BayesianEdgeScorer._beta_cdf(x, alpha, beta)

    @staticmethod
    def _beta_cdf(x: float, alpha: float, beta: float) -> float:
        """CDF of Beta distribution via continued fraction approximation."""
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0
        return BayesianEdgeScorer._regularized_beta(x, alpha, beta)

    @staticmethod
    def _beta_ppf(p: float, alpha: float, beta: float,
                  tol: float = 1e-6, max_iter: int = 100) -> float:
        """Inverse CDF (quantile) via bisection."""
        lo, hi = 0.0, 1.0
        for _ in range(max_iter):
            mid = (lo + hi) / 2.0
            cdf_mid = BayesianEdgeScorer._beta_cdf(mid, alpha, beta)
            if abs(cdf_mid - p) < tol:
                return mid
            if cdf_mid < p:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    @staticmethod
    def _regularized_beta(x: float, a: float, b: float) -> float:
        """Regularized incomplete beta function I_x(a, b)."""
        if x < (a + 1) / (a + b + 2):
            return (BayesianEdgeScorer._beta_cf(x, a, b) *
                    math.exp(a * math.log(x) + b * math.log(1 - x) -
                             BayesianEdgeScorer._log_beta(a, b)) / a)
        else:
            return 1.0 - (BayesianEdgeScorer._beta_cf(1 - x, b, a) *
                          math.exp(b * math.log(1 - x) + a * math.log(x) -
                                   BayesianEdgeScorer._log_beta(a, b)) / b)

    @staticmethod
    def _beta_cf(x: float, a: float, b: float,
                 max_iter: int = 200, tol: float = 1e-10) -> float:
        """Continued fraction for incomplete beta (Lentz's method)."""
        tiny = 1e-30
        f = tiny
        c = f
        d = 0.0
        for m in range(max_iter):
            if m == 0:
                numerator = 1.0
            elif m % 2 == 0:
                k = m // 2
                numerator = (k * (b - k) * x) / ((a + 2 * k - 1) * (a + 2 * k))
            else:
                k = (m + 1) // 2
                numerator = -((a + k) * (a + b + k) * x) / ((a + 2 * k) * (a + 2 * k + 1))

            d = 1.0 + numerator * d
            if abs(d) < tiny:
                d = tiny
            d = 1.0 / d
            c = 1.0 + numerator / c
            if abs(c) < tiny:
                c = tiny
            delta = c * d
            f *= delta
            if abs(delta - 1.0) < tol:
                break
        return f

    @staticmethod
    def _log_beta(a: float, b: float) -> float:
        """Log of Beta function: log(B(a,b)) = lgamma(a) + lgamma(b) - lgamma(a+b)."""
        return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


# ── Layer 2: Regime-Weighted Routing ─────────────────────────────────

STRATEGY_REGIME_AFFINITY = {
    "funding_carry": {
        "TRENDING_UP": 0.9,
        "TRENDING_DOWN": 0.9,
        "MEAN_REVERTING": 0.5,
        "HIGH_VOLATILITY": 0.7,
        "LOW_VOLATILITY": 0.3,
        "CRISIS": 0.8,
        "NEUTRAL": 0.6,
    },
    "ema_crossover": {
        "TRENDING_UP": 1.0,
        "TRENDING_DOWN": 1.0,
        "MEAN_REVERTING": 0.2,
        "HIGH_VOLATILITY": 0.5,
        "LOW_VOLATILITY": 0.4,
        "CRISIS": 0.3,
        "NEUTRAL": 0.5,
    },
    "bollinger_squeeze": {
        "TRENDING_UP": 0.4,
        "TRENDING_DOWN": 0.4,
        "MEAN_REVERTING": 0.9,
        "HIGH_VOLATILITY": 0.7,
        "LOW_VOLATILITY": 1.0,
        "CRISIS": 0.3,
        "NEUTRAL": 0.6,
    },
    "atr_regime_rsi": {
        "TRENDING_UP": 0.3,
        "TRENDING_DOWN": 0.3,
        "MEAN_REVERTING": 0.9,
        "HIGH_VOLATILITY": 0.5,
        "LOW_VOLATILITY": 0.7,
        "CRISIS": 0.6,
        "NEUTRAL": 0.5,
    },
    "whale_rsi": {
        "TRENDING_UP": 0.5,
        "TRENDING_DOWN": 0.5,
        "MEAN_REVERTING": 0.8,
        "HIGH_VOLATILITY": 0.9,
        "LOW_VOLATILITY": 0.3,
        "CRISIS": 0.7,
        "NEUTRAL": 0.5,
    },
    "connors_rsi2": {
        "TRENDING_UP": 0.7,
        "TRENDING_DOWN": 0.3,
        "MEAN_REVERTING": 1.0,
        "HIGH_VOLATILITY": 0.6,
        "LOW_VOLATILITY": 0.5,
        "CRISIS": 0.4,
        "NEUTRAL": 0.6,
    },
    "multi_rsi": {
        "TRENDING_UP": 0.4,
        "TRENDING_DOWN": 0.4,
        "MEAN_REVERTING": 0.9,
        "HIGH_VOLATILITY": 0.6,
        "LOW_VOLATILITY": 0.5,
        "CRISIS": 0.5,
        "NEUTRAL": 0.5,
    },
}


class RegimeRouter:
    """
    Regime-weighted routing: instead of binary on/off gating,
    scale position size by P(strategy_regime_match).

    Position size = base_size × regime_affinity × regime_confidence
    """

    def __init__(self, affinity_map: Optional[Dict] = None):
        self.affinity_map = affinity_map or STRATEGY_REGIME_AFFINITY

    def get_regime_weight(
        self,
        strategy_type: str,
        regime: str,
        regime_confidence: float = 0.5,
    ) -> float:
        """
        Get position weight multiplier based on regime alignment.

        Returns value in [0.1, 1.0] — never fully zero (avoids missing
        regime transitions), but heavily penalizes mismatched strategies.
        """
        affinities = self.affinity_map.get(strategy_type, {})
        base_affinity = affinities.get(regime, 0.5)

        weight = base_affinity * regime_confidence + (1 - regime_confidence) * 0.5
        return max(0.1, min(1.0, round(weight, 4)))

    def get_regime_weights_probabilistic(
        self,
        strategy_type: str,
        regime_probs: Dict[str, float],
    ) -> float:
        """
        Compute expected regime weight given probabilistic regime state.

        regime_probs: e.g. {"TRENDING_UP": 0.6, "MEAN_REVERTING": 0.3, "NEUTRAL": 0.1}
        Returns weighted average of affinities.
        """
        affinities = self.affinity_map.get(strategy_type, {})
        weight = 0.0
        for regime, prob in regime_probs.items():
            affinity = affinities.get(regime, 0.5)
            weight += affinity * prob
        return max(0.1, min(1.0, round(weight, 4)))


# ── Layer 3: Meta-Model Consensus ────────────────────────────────────

@dataclass
class MetaModelInput:
    """Feature vector for the meta-model."""
    strategy_confidence: float
    win_rate: float
    sharpe: float
    risk_reward: float
    regime: str
    regime_confidence: float
    vol_ratio: float
    momentum_24h: float
    bayesian_prob_above_50: float
    regime_affinity: float
    drawdown_pct: float
    trades_count: int


class MetaModelScorer:
    """
    Meta-model: logistic scoring over all engine features.

    Until we have enough data to train an XGBoost classifier,
    this uses a weighted scoring formula that approximates
    a trained meta-learner. The weights can be replaced with
    learned coefficients once training data accumulates.

    Output: P(trade > 0 R) in [0, 1]
    """

    FEATURE_WEIGHTS = {
        "bayesian_prob_above_50": 0.25,
        "regime_affinity": 0.15,
        "sharpe_normalized": 0.15,
        "risk_reward_normalized": 0.12,
        "strategy_confidence": 0.10,
        "win_rate": 0.08,
        "vol_ratio_penalty": 0.05,
        "drawdown_penalty": 0.05,
        "sample_size_bonus": 0.05,
    }

    MIN_META_SCORE = 0.65
    MIN_RR = 1.5
    MAX_FRESHNESS_MIN = 15

    def score(self, inp: MetaModelInput) -> float:
        """Compute meta-model probability of positive R."""
        features = {}

        features["bayesian_prob_above_50"] = inp.bayesian_prob_above_50
        features["regime_affinity"] = inp.regime_affinity
        features["sharpe_normalized"] = min(inp.sharpe / 3.0, 1.0) if inp.sharpe > 0 else 0.0
        features["risk_reward_normalized"] = min(inp.risk_reward / 4.0, 1.0) if inp.risk_reward > 0 else 0.0
        features["strategy_confidence"] = inp.strategy_confidence
        features["win_rate"] = inp.win_rate

        if inp.vol_ratio > 2.0:
            features["vol_ratio_penalty"] = max(0, 1.0 - (inp.vol_ratio - 2.0) / 3.0)
        else:
            features["vol_ratio_penalty"] = 1.0

        if inp.drawdown_pct > 0.05:
            features["drawdown_penalty"] = max(0, 1.0 - (inp.drawdown_pct - 0.05) / 0.10)
        else:
            features["drawdown_penalty"] = 1.0

        if inp.trades_count >= 50:
            features["sample_size_bonus"] = 1.0
        elif inp.trades_count >= 30:
            features["sample_size_bonus"] = 0.8
        elif inp.trades_count >= 15:
            features["sample_size_bonus"] = 0.6
        else:
            features["sample_size_bonus"] = 0.3

        score = sum(
            features.get(k, 0.5) * w
            for k, w in self.FEATURE_WEIGHTS.items()
        )

        return round(max(0.0, min(1.0, score)), 4)

    def should_trade(self, meta_score: float, risk_reward: float) -> bool:
        """Master pick rule: meta score > 0.65 AND RR >= 1.5."""
        return meta_score >= self.MIN_META_SCORE and risk_reward >= self.MIN_RR


# ── Layer 4: Drawdown-Constrained Fractional Kelly ───────────────────

class ConstrainedKellySizer:
    """
    Institutional Kelly sizing with drawdown constraints.

    Base: f* = edge / variance
    Applied: size = kelly_fraction × f*
    Constrained:
        - If rolling DD > 5%: reduce size by 50%
        - If DD > 8%: pause component entirely
        - Cap at max_position_pct
    """

    def __init__(
        self,
        kelly_fraction: float = 0.5,
        max_position_pct: float = 0.02,
        dd_reduce_threshold: float = 0.05,
        dd_pause_threshold: float = 0.08,
        dd_reduce_factor: float = 0.5,
    ):
        self.kelly_fraction = kelly_fraction
        self.max_position_pct = max_position_pct
        self.dd_reduce_threshold = dd_reduce_threshold
        self.dd_pause_threshold = dd_pause_threshold
        self.dd_reduce_factor = dd_reduce_factor

    def calculate_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        current_dd: float = 0.0,
        regime_weight: float = 1.0,
        meta_score: float = 0.7,
    ) -> Dict[str, float]:
        """
        Compute constrained Kelly position size.

        Returns dict with:
            - kelly_full: unconstrained Kelly fraction
            - kelly_fractional: after fraction applied
            - final_size: after all constraints
            - dd_multiplier: drawdown adjustment
            - regime_multiplier: regime weight
            - paused: whether component is paused
        """
        if current_dd >= self.dd_pause_threshold:
            return {
                "kelly_full": 0.0,
                "kelly_fractional": 0.0,
                "final_size": 0.0,
                "dd_multiplier": 0.0,
                "regime_multiplier": regime_weight,
                "meta_multiplier": meta_score,
                "paused": True,
            }

        if avg_loss <= 0 or avg_win <= 0:
            return {
                "kelly_full": 0.0,
                "kelly_fractional": 0.0,
                "final_size": 0.001,
                "dd_multiplier": 1.0,
                "regime_multiplier": regime_weight,
                "meta_multiplier": meta_score,
                "paused": False,
            }

        edge = win_rate * avg_win - (1 - win_rate) * avg_loss
        second_moment = (win_rate * avg_win ** 2 + (1 - win_rate) * avg_loss ** 2)

        if second_moment <= 0 or edge <= 0:
            kelly_full = 0.0
        else:
            kelly_full = edge / second_moment

        kelly_frac = kelly_full * self.kelly_fraction

        dd_mult = 1.0
        if current_dd >= self.dd_reduce_threshold:
            dd_mult = self.dd_reduce_factor

        final_size = kelly_frac * dd_mult * regime_weight * meta_score
        final_size = max(0.001, min(final_size, self.max_position_pct))

        return {
            "kelly_full": round(kelly_full, 6),
            "kelly_fractional": round(kelly_frac, 6),
            "final_size": round(final_size, 6),
            "dd_multiplier": dd_mult,
            "regime_multiplier": regime_weight,
            "meta_multiplier": round(meta_score, 4),
            "paused": False,
        }


# ── Layer 5: Correlation-Aware Capital Allocation ────────────────────

class CorrelationAllocator:
    """
    Risk parity allocation across strategy sleeves.

    Sleeves:
        - Funding Carry (ATM funding_carry variants)
        - Momentum (ema_crossover variants)
        - Mean Reversion (bollinger_squeeze, RSI variants)
        - Regime Adaptive (atr_regime_rsi variants)

    Capital ∝ 1/Volatility AND penalize high-correlation sleeves.
    """

    SLEEVES = {
        "funding_carry": ["funding_carry"],
        "momentum": ["ema_crossover"],
        "mean_reversion": ["bollinger_squeeze", "connors_rsi2", "multi_rsi", "whale_rsi"],
        "regime_adaptive": ["atr_regime_rsi"],
    }

    DEFAULT_CORRELATIONS = {
        ("funding_carry", "momentum"): 0.15,
        ("funding_carry", "mean_reversion"): -0.10,
        ("funding_carry", "regime_adaptive"): 0.05,
        ("momentum", "mean_reversion"): -0.25,
        ("momentum", "regime_adaptive"): 0.30,
        ("mean_reversion", "regime_adaptive"): 0.20,
    }

    def __init__(self, max_sleeve_pct: float = 0.40, min_sleeve_pct: float = 0.10):
        self.max_sleeve_pct = max_sleeve_pct
        self.min_sleeve_pct = min_sleeve_pct

    def get_sleeve(self, strategy_type: str) -> str:
        """Map strategy type to its sleeve."""
        for sleeve, strategies in self.SLEEVES.items():
            if strategy_type in strategies:
                return sleeve
        return "regime_adaptive"

    def allocate(
        self,
        sleeve_volatilities: Dict[str, float],
        sleeve_correlations: Optional[Dict[Tuple[str, str], float]] = None,
    ) -> Dict[str, float]:
        """
        Compute risk-parity allocation across sleeves.

        Returns dict of sleeve -> allocation weight (sums to 1.0).
        """
        correlations = sleeve_correlations or self.DEFAULT_CORRELATIONS
        sleeves = list(sleeve_volatilities.keys())

        if not sleeves:
            return {}

        inv_vol = {}
        for sleeve in sleeves:
            vol = sleeve_volatilities.get(sleeve, 0.20)
            inv_vol[sleeve] = 1.0 / max(vol, 0.01)

        total_inv_vol = sum(inv_vol.values())
        raw_weights = {s: inv_vol[s] / total_inv_vol for s in sleeves}

        adjusted = {}
        for sleeve in sleeves:
            avg_corr = 0.0
            corr_count = 0
            for other in sleeves:
                if other == sleeve:
                    continue
                key = tuple(sorted([sleeve, other]))
                corr = correlations.get(key, 0.0)
                avg_corr += abs(corr)
                corr_count += 1
            if corr_count > 0:
                avg_corr /= corr_count
            penalty = 1.0 - avg_corr * 0.5
            adjusted[sleeve] = raw_weights[sleeve] * penalty

        total_adj = sum(adjusted.values())
        if total_adj <= 0:
            return {s: 1.0 / len(sleeves) for s in sleeves}

        normalized = {}
        for sleeve in sleeves:
            w = adjusted[sleeve] / total_adj
            w = max(self.min_sleeve_pct, min(self.max_sleeve_pct, w))
            normalized[sleeve] = round(w, 4)

        final_total = sum(normalized.values())
        return {s: round(w / final_total, 4) for s, w in normalized.items()}


# ── Layer 6: Walk-Forward Validation Gates ───────────────────────────

@dataclass
class WalkForwardGate:
    """Walk-forward validation thresholds for promotion."""
    min_folds: int = 20
    min_sharpe_pct_positive: float = 0.70
    min_median_sharpe: float = 1.0
    max_worst_dd: float = 0.06
    min_stability: float = 0.60

    def passes(
        self,
        fold_sharpes: List[float],
        fold_max_dds: List[float],
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if walk-forward results meet institutional thresholds."""
        if len(fold_sharpes) < self.min_folds:
            return False, {"reason": f"insufficient_folds ({len(fold_sharpes)}/{self.min_folds})"}

        pct_positive = sum(1 for s in fold_sharpes if s > 0) / len(fold_sharpes)
        median_sharpe = sorted(fold_sharpes)[len(fold_sharpes) // 2]
        worst_dd = max(fold_max_dds) if fold_max_dds else 0.0
        sharpe_std = statistics.stdev(fold_sharpes) if len(fold_sharpes) > 1 else 0.0
        sharpe_mean = statistics.mean(fold_sharpes) if fold_sharpes else 0.0
        stability = 1.0 - (sharpe_std / max(abs(sharpe_mean), 0.01))

        results = {
            "pct_positive_sharpe": round(pct_positive, 4),
            "median_sharpe": round(median_sharpe, 4),
            "worst_dd": round(worst_dd, 4),
            "stability": round(stability, 4),
            "folds": len(fold_sharpes),
        }

        passed = (
            pct_positive >= self.min_sharpe_pct_positive
            and median_sharpe >= self.min_median_sharpe
            and worst_dd <= self.max_worst_dd
            and stability >= self.min_stability
        )

        if not passed:
            failures = []
            if pct_positive < self.min_sharpe_pct_positive:
                failures.append(f"pct_positive={pct_positive:.1%}<{self.min_sharpe_pct_positive:.0%}")
            if median_sharpe < self.min_median_sharpe:
                failures.append(f"median_sharpe={median_sharpe:.2f}<{self.min_median_sharpe}")
            if worst_dd > self.max_worst_dd:
                failures.append(f"worst_dd={worst_dd:.1%}>{self.max_worst_dd:.0%}")
            if stability < self.min_stability:
                failures.append(f"stability={stability:.2f}<{self.min_stability}")
            results["failures"] = failures

        return passed, results


# ── Layer 7: Feature Drift Monitoring (PSI) ──────────────────────────

class FeatureDriftMonitor:
    """
    Population Stability Index (PSI) for edge decay detection.

    Monitors distribution shifts in key features:
        - Volatility
        - Volume profile
        - Spread
        - Funding rate

    If PSI > threshold → auto-reduce size by reduction_factor.
    """

    PSI_THRESHOLD = 0.20
    PSI_WARNING = 0.10
    REDUCTION_FACTOR = 0.30
    N_BINS = 10

    def compute_psi(
        self,
        reference: List[float],
        current: List[float],
    ) -> float:
        """
        Compute PSI between reference and current distributions.

        PSI < 0.1: no significant shift
        PSI 0.1-0.2: moderate shift (warning)
        PSI > 0.2: significant shift (reduce exposure)
        """
        if not reference or not current or len(reference) < 10 or len(current) < 5:
            return 0.0

        all_vals = reference + current
        min_val = min(all_vals)
        max_val = max(all_vals)

        if max_val == min_val:
            return 0.0

        bin_width = (max_val - min_val) / self.N_BINS
        epsilon = 1e-4

        ref_hist = [0] * self.N_BINS
        cur_hist = [0] * self.N_BINS

        for val in reference:
            idx = min(int((val - min_val) / bin_width), self.N_BINS - 1)
            ref_hist[idx] += 1

        for val in current:
            idx = min(int((val - min_val) / bin_width), self.N_BINS - 1)
            cur_hist[idx] += 1

        ref_total = len(reference)
        cur_total = len(current)

        psi = 0.0
        for i in range(self.N_BINS):
            ref_pct = (ref_hist[i] / ref_total) + epsilon
            cur_pct = (cur_hist[i] / cur_total) + epsilon
            psi += (cur_pct - ref_pct) * math.log(cur_pct / ref_pct)

        return round(abs(psi), 6)

    def check_drift(
        self,
        feature_name: str,
        reference: List[float],
        current: List[float],
    ) -> Dict[str, Any]:
        """Check a single feature for distribution drift."""
        psi = self.compute_psi(reference, current)
        status = "stable"
        size_multiplier = 1.0

        if psi >= self.PSI_THRESHOLD:
            status = "drifted"
            size_multiplier = 1.0 - self.REDUCTION_FACTOR
        elif psi >= self.PSI_WARNING:
            status = "warning"
            size_multiplier = 1.0 - self.REDUCTION_FACTOR * 0.5

        return {
            "feature": feature_name,
            "psi": psi,
            "status": status,
            "size_multiplier": round(size_multiplier, 4),
            "threshold": self.PSI_THRESHOLD,
        }

    def check_all_features(
        self,
        reference_features: Dict[str, List[float]],
        current_features: Dict[str, List[float]],
    ) -> Dict[str, Any]:
        """Check all features and return aggregate drift assessment."""
        results = {}
        min_multiplier = 1.0

        for feature_name in reference_features:
            ref = reference_features.get(feature_name, [])
            cur = current_features.get(feature_name, [])
            if ref and cur:
                check = self.check_drift(feature_name, ref, cur)
                results[feature_name] = check
                min_multiplier = min(min_multiplier, check["size_multiplier"])

        drifted_count = sum(1 for r in results.values() if r["status"] == "drifted")
        warning_count = sum(1 for r in results.values() if r["status"] == "warning")

        return {
            "features": results,
            "aggregate_multiplier": round(min_multiplier, 4),
            "drifted_features": drifted_count,
            "warning_features": warning_count,
            "total_features": len(results),
            "overall_status": (
                "critical" if drifted_count >= 2
                else "drifted" if drifted_count >= 1
                else "warning" if warning_count >= 2
                else "stable"
            ),
        }


# ── Master Overlay ───────────────────────────────────────────────────

class InstitutionalOverlay:
    """
    Master orchestrator for all 7 institutional layers.

    Composes all layers into a single evaluation pipeline
    that transforms raw signals into institutional-grade decisions.
    """

    def __init__(self):
        self.bayesian = BayesianEdgeScorer()
        self.regime_router = RegimeRouter()
        self.meta_model = MetaModelScorer()
        self.kelly_sizer = ConstrainedKellySizer()
        self.allocator = CorrelationAllocator()
        self.wf_gate = WalkForwardGate()
        self.drift_monitor = FeatureDriftMonitor()

    def evaluate_variant(
        self,
        wins: int,
        losses: int,
        sharpe: float,
        total_pnl: float,
        pnl_history: List[float],
        strategy_type: str,
        regime: str,
        regime_confidence: float,
        current_dd: float = 0.0,
        vol_ratio: float = 1.0,
        momentum_24h: float = 0.0,
        signal_confidence: float = 0.6,
        risk_reward: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Full institutional evaluation of a strategy variant.

        Returns comprehensive assessment with:
            - bayesian: edge score
            - regime: routing weight
            - meta: model score and trade decision
            - sizing: position size with all constraints
            - tier_recommendation: PROMOTE/DEMOTE/HOLD/KILL
        """
        total_trades = wins + losses
        win_rate = wins / total_trades if total_trades > 0 else 0.0

        bayesian_score = self.bayesian.score(wins, losses)

        regime_weight = self.regime_router.get_regime_weight(
            strategy_type, regime, regime_confidence
        )

        meta_input = MetaModelInput(
            strategy_confidence=signal_confidence,
            win_rate=win_rate,
            sharpe=sharpe,
            risk_reward=risk_reward,
            regime=regime,
            regime_confidence=regime_confidence,
            vol_ratio=vol_ratio,
            momentum_24h=momentum_24h,
            bayesian_prob_above_50=bayesian_score.prob_above_50,
            regime_affinity=regime_weight,
            drawdown_pct=current_dd,
            trades_count=total_trades,
        )
        meta_score = self.meta_model.score(meta_input)
        should_trade = self.meta_model.should_trade(meta_score, risk_reward)

        avg_win = 0.0
        avg_loss = 0.0
        if pnl_history:
            wins_pnl = [p for p in pnl_history if p > 0]
            losses_pnl = [abs(p) for p in pnl_history if p < 0]
            avg_win = statistics.mean(wins_pnl) if wins_pnl else 0.01
            avg_loss = statistics.mean(losses_pnl) if losses_pnl else 0.01

        sizing = self.kelly_sizer.calculate_size(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            current_dd=current_dd,
            regime_weight=regime_weight,
            meta_score=meta_score,
        )

        tier_rec = self._tier_recommendation(
            wins, losses, total_trades, sharpe, total_pnl, current_dd
        )

        return {
            "bayesian": {
                "posterior_mean": bayesian_score.posterior_mean,
                "prob_above_50": bayesian_score.prob_above_50,
                "prob_above_55": bayesian_score.prob_above_55,
                "credible_interval_90": bayesian_score.credible_interval_90,
                "grade": bayesian_score.confidence_grade,
            },
            "regime": {
                "weight": regime_weight,
                "regime": regime,
                "regime_confidence": regime_confidence,
            },
            "meta": {
                "score": meta_score,
                "should_trade": should_trade,
            },
            "sizing": sizing,
            "tier_recommendation": tier_rec,
            "strategy_type": strategy_type,
            "total_trades": total_trades,
            "win_rate": round(win_rate, 4),
        }

    def _tier_recommendation(
        self,
        wins: int,
        losses: int,
        total_trades: int,
        sharpe: float,
        total_pnl: float,
        current_dd: float,
    ) -> str:
        """Determine tier recommendation based on Bayesian + fundamentals."""
        if self.bayesian.should_kill(wins, losses, min_trades=10):
            return "KILL"

        if current_dd > 0.08:
            return "PAUSE"

        b_score = self.bayesian.score(wins, losses)
        has_positive_expectancy = total_pnl > 0

        if (b_score.prob_above_50 >= 0.95
                and total_trades >= 50
                and sharpe >= 2.0
                and has_positive_expectancy):
            return "PROMOTE_ELITE"

        if (b_score.prob_above_50 >= 0.90
                and total_trades >= 30
                and sharpe >= 1.0
                and has_positive_expectancy):
            return "PROMOTE_CHAMPION"

        if (b_score.prob_above_50 >= 0.75
                and total_trades >= 15
                and has_positive_expectancy):
            return "PROMOTE_CONTENDER"

        if b_score.prob_above_50 < 0.50 and total_trades >= 20:
            return "DEMOTE"

        return "HOLD"

    def generate_institutional_report(
        self,
        variants: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate institutional-grade portfolio report."""
        now = datetime.now(timezone.utc).isoformat()

        sleeve_stats: Dict[str, Dict] = {}
        for v in variants:
            sleeve = self.allocator.get_sleeve(v.get("strategy_type", "unknown"))
            if sleeve not in sleeve_stats:
                sleeve_stats[sleeve] = {
                    "variants": 0, "total_trades": 0,
                    "total_pnl": 0.0, "avg_wr": [],
                }
            s = sleeve_stats[sleeve]
            s["variants"] += 1
            s["total_trades"] += v.get("total_trades", 0)
            s["total_pnl"] += v.get("total_pnl", 0.0)
            wr = v.get("win_rate", 0)
            if isinstance(wr, (int, float)):
                s["avg_wr"].append(wr)

        for sleeve, s in sleeve_stats.items():
            s["avg_wr"] = round(
                statistics.mean(s["avg_wr"]) if s["avg_wr"] else 0, 4
            )

        return {
            "generated_at": now,
            "total_variants": len(variants),
            "sleeves": sleeve_stats,
            "institutional_metrics": {
                "description": "Targets for fund-grade performance",
                "target_sharpe": 1.5,
                "target_max_dd": 0.08,
                "target_calmar": 1.5,
                "target_profitable_months_pct": 0.60,
                "target_worst_month": -0.04,
                "target_oos_period_months": 3,
            },
        }
