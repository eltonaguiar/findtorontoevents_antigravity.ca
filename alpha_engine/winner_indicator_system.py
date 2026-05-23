#!/usr/bin/env python3
"""
WINNER INDICATOR SYSTEM v1.1
============================
Technical indicator system reverse-engineered from 368 closed picks (169W/199L).

FEATURE AVAILABILITY (critical for calibration):
    confidence:     100% (368/368) -- PRIMARY PREDICTOR
    ml_score:        75% (276/368) -- SECONDARY PREDICTOR
    risk_reward:     62% (230/368) -- AVAILABLE
    elite_score:     52% (190/368) -- AVAILABLE
    volume_ratio:    26% (94/368)  -- SPARSE
    rsi_at_entry:    23% (83/368)  -- SPARSE
    ml_features:      4% (15/368)  -- VERY SPARSE (SMA, momentum, bb_position, etc.)

Key findings from analysis:
    1. CONFIDENCE >= 0.80 = 69.6% WR (vs 42.4% for conf < 0.60).
       Strongest single predictor. Monotonically increasing across quartiles.

    2. ML_SCORE: Above-median = 61.6% WR vs below-median 42.8%.
       Correlation with PnL = +0.33 (strongest positive corr).

    3. ELITE_SCORE: Q1=27.7% -> Q4=44.9% WR. Monotonic.

    4. RISK_REWARD: LOWER is better. Winners 1.81 vs losers 1.99.
       R:R > 2.5 = likely unreachable TP. Negative correlation with PnL.

    5. VOLUME: Winners enter at LOWER volume (1.20 vs 1.32).
       CONFIRMED but modest effect. Low volume = calm, not FOMO.

    6. gross_edge_bps: STRONG negative corr (-0.30). Bloated edge = overfitted.

    7. HOLD DURATION: 4-7d sweet spot = 68.2% WR, +15.5% avg PnL.

    8. REGIME: BEAR = 60% WR. ACCUMULATION = 13.6% WR (avoid).

    9. MAE: Winners = -0.87% vs Losers = -6.37%. Tight drawdown = good.

Usage:
    from winner_indicator_system import (
        MomentumSafetyIndex, EntryQualityScore, RiskFilter,
        score_pick, backtest_indicators
    )

    result = score_pick(pick_dict)
    stats = backtest_indicators(closed_picks_list)
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Constants derived from empirical analysis of 368 closed picks
# ---------------------------------------------------------------------------

CONFIDENCE_HIGH = 0.80    # Q4 = 69.6% WR
CONFIDENCE_MED = 0.67     # Q3 boundary
CONFIDENCE_LOW = 0.60     # Q2 boundary

ML_SCORE_HIGH = 0.75      # Above-median threshold
ML_SCORE_MED = 0.65       # Median value
ML_SCORE_LOW = 0.50       # Below which = weak

ELITE_HIGH = 36           # Q4 start (44.9% WR)
ELITE_MED = 26            # Q3 start (42.6% WR)
ELITE_LOW = 15            # Below = Q1 (27.7% WR)

RR_OPTIMAL_HIGH = 2.0     # Winners avg 1.81
RR_WARN = 2.5             # Beyond = unreachable TP

VOLUME_CALM = 1.0         # Below = calm entry (winners)
VOLUME_FOMO = 3.0         # Above = FOMO chasing

RSI_OVERSOLD = 30
RSI_SWEET_LOW = 35
RSI_SWEET_HIGH = 65
RSI_OVERBOUGHT = 70

EDGE_BLOAT = 500          # bps -- above = overfitted signal


def _safe_float(v: Any) -> Optional[float]:
    """Safely convert to float, returning None for invalid values."""
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _get_ml_feature(pick: Dict, key: str) -> Optional[float]:
    """Extract a feature from ml_features_at_entry."""
    ml = pick.get('ml_features_at_entry') or {}
    return _safe_float(ml.get(key))


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


# =========================================================================
# INDICATOR 1: MomentumSafetyIndex (MSI)
# =========================================================================

class MomentumSafetyIndex:
    """
    Composite indicator for entry momentum quality.
    Score 0-100.  Entry threshold: >= 60.

    Uses AVAILABLE features (weighted by availability and predictive power):
        - Confidence level      : 30 pts (100% avail, strongest predictor)
        - ML score              : 25 pts (75% avail, corr +0.33)
        - Elite score           : 20 pts (52% avail, monotonic WR)
        - Volume calm           : 10 pts (26% avail, confirmed effect)
        - RSI sweet spot        : 10 pts (23% avail)
        - Technical features    :  5 pts (4% avail, bonus when present)

    When a feature is missing, its points are redistributed proportionally
    to available features (no penalty for missing data).
    """

    ENTRY_THRESHOLD = 60

    def compute(self, pick: Dict) -> int:
        """Compute MSI score (0-100) for a pick."""
        components = []  # (score_fraction 0-1, max_weight)

        direction = pick.get('signal_type', 'BUY')
        is_long = direction in ('BUY', 'LONG')

        # --- Confidence (30 pts) ---
        confidence = _safe_float(pick.get('confidence'))
        if confidence is not None:
            if confidence >= CONFIDENCE_HIGH:
                frac = 1.0
            elif confidence >= CONFIDENCE_MED:
                frac = 0.65
            elif confidence >= CONFIDENCE_LOW:
                frac = 0.40
            elif confidence >= 0.50:
                frac = 0.25
            else:
                frac = 0.10
            components.append((frac, 30))

        # --- ML Score (25 pts) ---
        ml_score = _safe_float(pick.get('ml_score'))
        if ml_score is not None:
            if ml_score >= ML_SCORE_HIGH:
                frac = 1.0
            elif ml_score >= ML_SCORE_MED:
                frac = 0.70
            elif ml_score >= ML_SCORE_LOW:
                frac = 0.40
            else:
                frac = 0.10
            components.append((frac, 25))

        # --- Elite Score (20 pts) ---
        elite = _safe_float(pick.get('elite_score'))
        if elite is not None:
            if elite >= ELITE_HIGH:
                frac = 1.0
            elif elite >= ELITE_MED:
                frac = 0.70
            elif elite >= ELITE_LOW:
                frac = 0.40
            else:
                frac = 0.10
            components.append((frac, 20))

        # --- Volume Calm (10 pts) ---
        vol_ratio = _get_ml_feature(pick, 'volume_ratio') or _safe_float(pick.get('volume_ratio'))
        if vol_ratio is not None:
            if vol_ratio < 0.5:
                frac = 0.80
            elif vol_ratio < VOLUME_CALM:
                frac = 1.0
            elif vol_ratio < 1.5:
                frac = 0.55
            elif vol_ratio < VOLUME_FOMO:
                frac = 0.20
            else:
                frac = 0.0
            components.append((frac, 10))

        # --- RSI Sweet Spot (10 pts) ---
        rsi = _get_ml_feature(pick, 'rsi_14') or _safe_float(pick.get('rsi_at_entry'))
        if rsi is not None:
            if is_long:
                if RSI_SWEET_LOW <= rsi <= RSI_SWEET_HIGH:
                    frac = 1.0
                elif RSI_OVERSOLD <= rsi < RSI_SWEET_LOW:
                    frac = 0.70
                elif RSI_SWEET_HIGH < rsi <= RSI_OVERBOUGHT:
                    frac = 0.30
                else:
                    frac = 0.0
            else:
                if 55 <= rsi <= 80:
                    frac = 1.0
                elif rsi > 80:
                    frac = 0.70
                elif 45 <= rsi < 55:
                    frac = 0.30
                else:
                    frac = 0.0
            components.append((frac, 10))

        # --- Technical Features Bonus (5 pts) ---
        sma20 = _get_ml_feature(pick, 'price_vs_sma20')
        sma50 = _get_ml_feature(pick, 'price_vs_sma50')
        mom_7 = _get_ml_feature(pick, 'momentum_7d')
        tech_vals = [v for v in [sma20, sma50, mom_7] if v is not None]
        if tech_vals:
            tech_good = 0
            for v in tech_vals:
                if is_long and v > 0:
                    tech_good += 1
                elif not is_long and v < 0:
                    tech_good += 1
            frac = tech_good / len(tech_vals)
            components.append((frac, 5))

        # --- Normalize: redistribute missing weight proportionally ---
        if not components:
            return 50

        total_weight = sum(w for _, w in components)
        score = 0.0
        for frac, w in components:
            score += frac * w * (100.0 / total_weight)

        return int(_clamp(round(score), 0, 100))

    def passes(self, pick: Dict) -> bool:
        return self.compute(pick) >= self.ENTRY_THRESHOLD


# =========================================================================
# INDICATOR 2: EntryQualityScore (EQS)
# =========================================================================

class EntryQualityScore:
    """
    Rates entry quality based on:
      - Confidence alignment       (30 pts -- most predictive, always available)
      - Risk:Reward realism        (25 pts -- 62% available, lower = better)
      - Edge estimate quality      (20 pts -- 52% available, bloated = bad)
      - Volume divergence          (15 pts -- 26% available)
      - RSI / Bollinger position   (10 pts -- sparse, bonus)

    Score 0-100. Entry threshold: >= 50.
    Same normalization: missing features redistribute weight.
    """

    ENTRY_THRESHOLD = 50

    def compute(self, pick: Dict) -> int:
        components = []
        is_long = pick.get('signal_type', 'BUY') in ('BUY', 'LONG')

        # --- Confidence Alignment (30 pts) ---
        confidence = _safe_float(pick.get('confidence'))
        ml_score = _safe_float(pick.get('ml_score'))

        if confidence is not None:
            if confidence >= CONFIDENCE_HIGH:
                conf_frac = 1.0
            elif confidence >= CONFIDENCE_MED:
                conf_frac = 0.60
            elif confidence >= CONFIDENCE_LOW:
                conf_frac = 0.35
            else:
                conf_frac = 0.10

            # Bonus: both high = strong alignment
            if ml_score is not None and ml_score >= ML_SCORE_MED and confidence >= CONFIDENCE_MED:
                conf_frac = min(1.0, conf_frac + 0.15)

            components.append((conf_frac, 30))

        # --- Risk:Reward Realism (25 pts) ---
        rr = _safe_float(pick.get('risk_reward'))
        if rr is not None:
            if 1.0 <= rr <= 1.8:
                frac = 1.0
            elif 1.8 < rr <= RR_OPTIMAL_HIGH:
                frac = 0.75
            elif RR_OPTIMAL_HIGH < rr <= RR_WARN:
                frac = 0.40
            elif rr > RR_WARN:
                frac = 0.10
            else:
                frac = 0.30
            components.append((frac, 25))

        # --- Edge Estimate Quality (20 pts) ---
        gross_edge = _safe_float(pick.get('gross_edge_bps'))
        net_edge = _safe_float(pick.get('net_edge_bps'))
        edge = net_edge or gross_edge
        if edge is not None:
            if edge < 200:
                frac = 1.0
            elif edge < 350:
                frac = 0.70
            elif edge < EDGE_BLOAT:
                frac = 0.40
            else:
                frac = 0.10
            components.append((frac, 20))

        # --- Volume Divergence (15 pts) ---
        vol_ratio = _get_ml_feature(pick, 'volume_ratio') or _safe_float(pick.get('volume_ratio'))
        if vol_ratio is not None:
            if vol_ratio < 0.7:
                frac = 0.90
            elif vol_ratio < VOLUME_CALM:
                frac = 1.0
            elif vol_ratio < 1.5:
                frac = 0.50
            elif vol_ratio < VOLUME_FOMO:
                frac = 0.20
            else:
                frac = 0.0
            components.append((frac, 15))

        # --- RSI / Bollinger Position (10 pts) ---
        rsi = _get_ml_feature(pick, 'rsi_14') or _safe_float(pick.get('rsi_at_entry'))
        bb_pos = _get_ml_feature(pick, 'bb_position') or _safe_float(pick.get('bb_pct_b'))

        tech_fracs = []
        if rsi is not None:
            if is_long:
                if RSI_SWEET_LOW <= rsi <= RSI_SWEET_HIGH:
                    tech_fracs.append(1.0)
                elif rsi < RSI_SWEET_LOW:
                    tech_fracs.append(0.60)
                else:
                    tech_fracs.append(0.15)
            else:
                if 55 <= rsi <= 80:
                    tech_fracs.append(1.0)
                elif rsi > 80:
                    tech_fracs.append(0.60)
                else:
                    tech_fracs.append(0.15)

        if bb_pos is not None:
            if is_long:
                if bb_pos < 0.3:
                    tech_fracs.append(1.0)
                elif bb_pos < 0.5:
                    tech_fracs.append(0.65)
                else:
                    tech_fracs.append(0.20)
            else:
                if bb_pos > 0.7:
                    tech_fracs.append(1.0)
                elif bb_pos > 0.5:
                    tech_fracs.append(0.65)
                else:
                    tech_fracs.append(0.20)

        if tech_fracs:
            components.append((sum(tech_fracs) / len(tech_fracs), 10))

        # --- Normalize ---
        if not components:
            return 50

        total_weight = sum(w for _, w in components)
        score = 0.0
        for frac, w in components:
            score += frac * w * (100.0 / total_weight)

        return int(_clamp(round(score), 0, 100))

    def passes(self, pick: Dict) -> bool:
        return self.compute(pick) >= self.ENTRY_THRESHOLD


# =========================================================================
# INDICATOR 3: RiskFilter
# =========================================================================

class RiskFilter:
    """
    Blocks or warns on entries matching empirically bad patterns.

    Returns list of (severity, message) tuples.
    'BLOCK' = do not enter, 'WARN' = proceed with caution.
    """

    def evaluate(self, pick: Dict) -> List[Tuple[str, str]]:
        """Return list of (severity, message) flags."""
        flags: List[Tuple[str, str]] = []
        is_long = pick.get('signal_type', 'BUY') in ('BUY', 'LONG')

        # RSI extremes
        rsi = _get_ml_feature(pick, 'rsi_14') or _safe_float(pick.get('rsi_at_entry'))
        if rsi is not None:
            if is_long and rsi > RSI_OVERBOUGHT:
                flags.append(('BLOCK', f'RSI {rsi:.1f} > 70 for LONG: overbought'))
            elif not is_long and rsi < RSI_OVERSOLD:
                flags.append(('BLOCK', f'RSI {rsi:.1f} < 30 for SHORT: oversold'))

        # Volume FOMO
        vol_ratio = _get_ml_feature(pick, 'volume_ratio') or _safe_float(pick.get('volume_ratio'))
        if vol_ratio is not None and vol_ratio > VOLUME_FOMO:
            flags.append(('BLOCK', f'Volume ratio {vol_ratio:.2f} > 3x: FOMO chasing'))

        # Bloated edge
        gross_edge = _safe_float(pick.get('gross_edge_bps'))
        if gross_edge is not None and gross_edge > 800:
            flags.append(('BLOCK', f'Gross edge {gross_edge:.0f} bps > 800: severely overfitted'))
        elif gross_edge is not None and gross_edge > EDGE_BLOAT:
            flags.append(('WARN', f'Gross edge {gross_edge:.0f} bps > 500: possibly overfitted'))

        # R:R too high
        rr = _safe_float(pick.get('risk_reward'))
        if rr is not None and rr > RR_WARN:
            flags.append(('WARN', f'R:R {rr:.2f} > 2.5: TP likely unreachable'))

        # Very low confidence
        confidence = _safe_float(pick.get('confidence'))
        if confidence is not None and confidence < 0.45:
            flags.append(('WARN', f'Confidence {confidence:.2f} < 0.45: very weak signal'))

        # Very low elite score
        elite = _safe_float(pick.get('elite_score'))
        if elite is not None and elite < 10:
            flags.append(('WARN', f'Elite score {elite:.0f} < 10: bottom tier'))

        # ACCUMULATION regime trap
        regime = pick.get('sentinel_regime') or pick.get('regime_at_entry')
        if regime == 'ACCUMULATION':
            flags.append(('WARN', f'ACCUMULATION regime: 13.6% WR historically'))

        # Funding divergence
        funding = _safe_float(pick.get('funding_rate'))
        if funding is not None:
            if is_long and funding < -0.001:
                flags.append(('WARN', f'Funding {funding:.6f} deeply negative for LONG'))
            elif not is_long and funding > 0.001:
                flags.append(('WARN', f'Funding {funding:.6f} deeply positive for SHORT'))

        return flags

    def is_blocked(self, pick: Dict) -> bool:
        return any(sev == 'BLOCK' for sev, _ in self.evaluate(pick))

    def has_warnings(self, pick: Dict) -> bool:
        return any(sev == 'WARN' for sev, _ in self.evaluate(pick))


# =========================================================================
# UNIFIED SCORING
# =========================================================================

def score_pick(pick: Dict) -> Dict[str, Any]:
    """
    Score a pick with all three indicators and assign portfolio.

    Returns:
        msi (int): MomentumSafetyIndex 0-100
        eqs (int): EntryQualityScore 0-100
        risk_flags (list): [(severity, message), ...]
        blocked (bool): True if any BLOCK flag
        portfolio (str|None): ALPHA, BETA, GAMMA, or None
        combined_score (float): weighted MSI + EQS
    """
    msi_engine = MomentumSafetyIndex()
    eqs_engine = EntryQualityScore()
    risk_engine = RiskFilter()

    msi = msi_engine.compute(pick)
    eqs = eqs_engine.compute(pick)
    flags = risk_engine.evaluate(pick)
    blocked = any(sev == 'BLOCK' for sev, _ in flags)

    combined = 0.55 * msi + 0.45 * eqs

    portfolio = None
    if not blocked:
        passes_msi = msi >= MomentumSafetyIndex.ENTRY_THRESHOLD
        passes_eqs = eqs >= EntryQualityScore.ENTRY_THRESHOLD
        if passes_msi and passes_eqs:
            portfolio = 'GAMMA'
        elif passes_msi:
            portfolio = 'ALPHA'
        elif passes_eqs:
            portfolio = 'BETA'

    return {
        'msi': msi,
        'eqs': eqs,
        'combined_score': round(combined, 1),
        'risk_flags': [(sev, msg) for sev, msg in flags],
        'blocked': blocked,
        'portfolio': portfolio,
    }


# =========================================================================
# BACKTEST ENGINE
# =========================================================================

def backtest_indicators(picks: List[Dict]) -> Dict[str, Any]:
    """Apply indicators retroactively and compute statistics."""
    valid = [p for p in picks if p.get('status') in ('WON', 'LOST')]

    scored = []
    for p in valid:
        result = score_pick(p)
        result['status'] = p['status']
        result['pnl_pct'] = _safe_float(p.get('pnl_pct')) or 0.0
        result['strategy'] = p.get('strategy', 'unknown')
        result['symbol'] = p.get('symbol', 'unknown')
        result['id'] = p.get('id', 'unknown')
        scored.append(result)

    total = len(scored)
    if total == 0:
        return {'error': 'No valid picks to backtest'}

    # Quartile analyses
    msi_quartiles = _quartile_analysis(sorted(scored, key=lambda x: x['msi']), 'msi')
    eqs_quartiles = _quartile_analysis(sorted(scored, key=lambda x: x['eqs']), 'eqs')
    combined_quartiles = _quartile_analysis(sorted(scored, key=lambda x: x['combined_score']), 'combined_score')

    # Portfolio performance
    portfolios = {
        'ALPHA': {'picks': [], 'desc': 'MSI >= 60 only (momentum-safe)'},
        'BETA': {'picks': [], 'desc': 'EQS >= 50 only (quality entry)'},
        'GAMMA': {'picks': [], 'desc': 'MSI >= 60 AND EQS >= 50 (combined)'},
        'UNFILTERED': {'picks': [], 'desc': 'All picks (baseline)'},
        'REJECTED': {'picks': [], 'desc': 'Blocked by RiskFilter'},
    }

    for s in scored:
        portfolios['UNFILTERED']['picks'].append(s)
        if s['blocked']:
            portfolios['REJECTED']['picks'].append(s)
            continue
        if s['portfolio'] == 'GAMMA':
            portfolios['GAMMA']['picks'].append(s)
            portfolios['ALPHA']['picks'].append(s)
            portfolios['BETA']['picks'].append(s)
        elif s['portfolio'] == 'ALPHA':
            portfolios['ALPHA']['picks'].append(s)
        elif s['portfolio'] == 'BETA':
            portfolios['BETA']['picks'].append(s)

    portfolio_stats = {}
    for name, pdata in portfolios.items():
        picks_list = pdata['picks']
        n = len(picks_list)
        if n == 0:
            portfolio_stats[name] = {'description': pdata['desc'], 'n': 0}
            continue
        wins = sum(1 for p in picks_list if p['status'] == 'WON')
        pnls = [p['pnl_pct'] for p in picks_list]
        std = float(np.std(pnls)) if len(pnls) > 1 else 0.0
        portfolio_stats[name] = {
            'description': pdata['desc'],
            'n': n, 'wins': wins, 'losses': n - wins,
            'win_rate': round(wins / n, 4),
            'avg_pnl': round(float(np.mean(pnls)), 6),
            'median_pnl': round(float(np.median(pnls)), 6),
            'total_pnl': round(float(np.sum(pnls)), 6),
            'std_pnl': round(std, 6),
            'sharpe_approx': round(float(np.mean(pnls) / std) if std > 0 else 0, 4),
            'best_pnl': round(float(np.max(pnls)), 6),
            'worst_pnl': round(float(np.min(pnls)), 6),
            'avg_msi': round(float(np.mean([p['msi'] for p in picks_list])), 1),
            'avg_eqs': round(float(np.mean([p['eqs'] for p in picks_list])), 1),
        }

    # Threshold sweep
    threshold_sweep = []
    for msi_thresh in range(40, 85, 5):
        for eqs_thresh in range(30, 75, 5):
            passing = [s for s in scored if s['msi'] >= msi_thresh and s['eqs'] >= eqs_thresh and not s['blocked']]
            n = len(passing)
            if n >= 5:
                wins = sum(1 for p in passing if p['status'] == 'WON')
                avg_pnl = float(np.mean([p['pnl_pct'] for p in passing]))
                threshold_sweep.append({
                    'msi_threshold': msi_thresh, 'eqs_threshold': eqs_thresh,
                    'n': n, 'win_rate': round(wins / n, 4),
                    'avg_pnl': round(avg_pnl, 6),
                })
    threshold_sweep.sort(key=lambda x: (x['win_rate'], x['avg_pnl']), reverse=True)

    msi_scores = [s['msi'] for s in scored]
    eqs_scores = [s['eqs'] for s in scored]

    return {
        'total_picks': total,
        'baseline_wr': round(sum(1 for s in scored if s['status'] == 'WON') / total, 4),
        'msi_quartiles': msi_quartiles,
        'eqs_quartiles': eqs_quartiles,
        'combined_quartiles': combined_quartiles,
        'portfolio_stats': portfolio_stats,
        'threshold_sweep_top10': threshold_sweep[:10],
        'score_distribution': {
            'msi_mean': round(float(np.mean(msi_scores)), 1),
            'msi_median': round(float(np.median(msi_scores)), 1),
            'msi_std': round(float(np.std(msi_scores)), 1),
            'msi_p25': round(float(np.percentile(msi_scores, 25)), 1),
            'msi_p75': round(float(np.percentile(msi_scores, 75)), 1),
            'eqs_mean': round(float(np.mean(eqs_scores)), 1),
            'eqs_median': round(float(np.median(eqs_scores)), 1),
            'eqs_std': round(float(np.std(eqs_scores)), 1),
            'eqs_p25': round(float(np.percentile(eqs_scores, 25)), 1),
            'eqs_p75': round(float(np.percentile(eqs_scores, 75)), 1),
        },
        'blocked_count': sum(1 for s in scored if s['blocked']),
    }


def _quartile_analysis(sorted_items: list, key: str) -> List[Dict]:
    """Split sorted items into quartiles and compute WR/PnL."""
    n = len(sorted_items)
    q_size = n // 4
    quartiles = []
    for i in range(4):
        start = i * q_size
        end = (i + 1) * q_size if i < 3 else n
        q = sorted_items[start:end]
        if not q:
            continue
        wins = sum(1 for p in q if p['status'] == 'WON')
        pnls = [p['pnl_pct'] for p in q]
        scores = [p[key] for p in q]
        quartiles.append({
            'quartile': f'Q{i+1}',
            'score_range': f'{min(scores):.0f}-{max(scores):.0f}',
            'n': len(q),
            'wins': wins,
            'win_rate': round(wins / len(q), 4),
            'avg_pnl': round(float(np.mean(pnls)), 6),
            'median_pnl': round(float(np.median(pnls)), 6),
        })
    return quartiles


# =========================================================================
# CLI
# =========================================================================

def main():
    """Run backtest and save results."""
    data_dir = Path(__file__).resolve().parent / 'data'
    closed_path = data_dir / 'closed_picks.json'

    if not closed_path.exists():
        print(f'ERROR: {closed_path} not found')
        return

    with open(closed_path) as f:
        picks = json.load(f)

    print(f'Loaded {len(picks)} closed picks')

    results = backtest_indicators(picks)

    print(f"\n{'='*70}")
    print('BACKTEST RESULTS -- Winner Indicator System v1.1')
    print(f"{'='*70}")
    print(f"Total picks analyzed: {results['total_picks']}")
    print(f"Baseline WR: {results['baseline_wr']:.1%}")
    print(f"Blocked by RiskFilter: {results['blocked_count']}")

    print(f"\n--- MSI Quartile Analysis ---")
    for q in results['msi_quartiles']:
        print(f"  {q['quartile']} ({q['score_range']:>6}): WR={q['win_rate']:.1%}, "
              f"avg_pnl={q['avg_pnl']:+.4f}, n={q['n']}")

    print(f"\n--- EQS Quartile Analysis ---")
    for q in results['eqs_quartiles']:
        print(f"  {q['quartile']} ({q['score_range']:>6}): WR={q['win_rate']:.1%}, "
              f"avg_pnl={q['avg_pnl']:+.4f}, n={q['n']}")

    print(f"\n--- Combined Score Quartile ---")
    for q in results['combined_quartiles']:
        print(f"  {q['quartile']} ({q['score_range']:>6}): WR={q['win_rate']:.1%}, "
              f"avg_pnl={q['avg_pnl']:+.4f}, n={q['n']}")

    print(f"\n--- Portfolio Performance ---")
    for name in ['UNFILTERED', 'ALPHA', 'BETA', 'GAMMA', 'REJECTED']:
        ps = results['portfolio_stats'].get(name, {})
        if ps.get('n', 0) > 0:
            print(f"  {name:<12}: WR={ps['win_rate']:.1%}, avg_pnl={ps['avg_pnl']:+.4f}, "
                  f"sharpe={ps.get('sharpe_approx', 0):.3f}, n={ps['n']}")

    print(f"\n--- Top Threshold Combinations ---")
    for t in results.get('threshold_sweep_top10', [])[:7]:
        print(f"  MSI>={t['msi_threshold']}, EQS>={t['eqs_threshold']}: "
              f"WR={t['win_rate']:.1%}, avg_pnl={t['avg_pnl']:+.4f}, n={t['n']}")

    print(f"\n--- Score Distribution ---")
    sd = results['score_distribution']
    print(f"  MSI: mean={sd['msi_mean']}, median={sd['msi_median']}, "
          f"std={sd['msi_std']}, p25={sd['msi_p25']}, p75={sd['msi_p75']}")
    print(f"  EQS: mean={sd['eqs_mean']}, median={sd['eqs_median']}, "
          f"std={sd['eqs_std']}, p25={sd['eqs_p25']}, p75={sd['eqs_p75']}")

    # Build comprehensive output with feature findings
    feature_findings = {
        'volume_ratio_verdict': {
            'claim': 'Winners enter at LOWER volume (1.12 vs 1.33)',
            'verdict': 'PARTIALLY CONFIRMED',
            'evidence': {
                'top_level_winners_mean': 1.1967,
                'top_level_losers_mean': 1.3168,
                'top_level_winners_median': 0.665,
                'top_level_losers_median': 0.748,
                'ml_winners_mean': 1.3077,
                'ml_losers_mean': 1.3053,
                'note': ('Top-level volume_ratio confirms: winners 1.20 vs losers 1.32 mean, '
                         'winners 0.67 vs losers 0.75 median. ML features mixed. '
                         'Quintile analysis: no clean monotonic pattern but Q1 (lowest) has '
                         'smallest losses. Effect real but modest, driven by outlier '
                         'high-volume FOMO losers. Bottom line: prefer calm entries.'),
            }
        },
        'top_predictors': [
            {'rank': 1, 'feature': 'confidence',
             'finding': 'Q4 (>=0.80)=69.6% WR vs Q1 (<0.60)=42.4%'},
            {'rank': 2, 'feature': 'ml_score',
             'finding': 'Corr +0.33. Above-median=61.6% WR vs below=42.8%'},
            {'rank': 3, 'feature': 'mae',
             'finding': 'Winners -0.87% vs Losers -6.37%. Tight drawdown = strong signal'},
            {'rank': 4, 'feature': 'elite_score',
             'finding': 'Monotonic Q1=27.7% -> Q4=44.9% WR'},
            {'rank': 5, 'feature': 'hold_days',
             'finding': '4-7d sweet spot=68.2% WR +15.5% avg PnL'},
            {'rank': 6, 'feature': 'risk_reward',
             'finding': 'LOWER is better: winners 1.81 vs losers 1.99'},
            {'rank': 7, 'feature': 'gross_edge_bps',
             'finding': 'Corr -0.30: winners 466 bps vs losers 673 bps. Bloated = bad'},
            {'rank': 8, 'feature': 'volume_ratio',
             'finding': 'Winners 1.20 vs losers 1.32. Calm > FOMO'},
        ],
        'regime_findings': {
            'BEAR': '60% WR (n=10) -- counter-trend',
            'unknown': '47.8% WR (n=335) -- baseline',
            'ACCUMULATION': '13.6% WR (n=22) -- AVOID',
        },
        'time_findings': {
            'best_hold': '4-7 days (68.2% WR, +15.5% avg PnL)',
            'worst_hold': '0-1 days (42.5% WR) -- noise',
        },
        'strategy_findings': {
            'top': [
                'ml_enhanced_FETUSDT_1d_B_lightgbm (100% WR, n=15)',
                'ml_enhanced_BNBUSDT_15m_B_lightgbm (93.8% WR, n=16)',
                'ml_enhanced_RENDERUSDT_1h_D_ensemble_stack (93.3% WR, n=15)',
                'copy_hl_NMTD_25M (81.2% WR, n=16)',
            ],
            'worst': [
                'winner_pattern_precursor (20% WR, n=75)',
                'yahoo_analyst_consensus (0% WR, n=5)',
            ],
        },
    }

    output = {
        'analysis_date': '2026-03-24',
        'system_version': '1.1',
        'dataset': {
            'total_closed_picks': len(picks),
            'analyzable_won_lost': results['total_picks'],
            'baseline_win_rate': results['baseline_wr'],
        },
        'feature_findings': feature_findings,
        'backtest_results': results,
    }

    output_path = data_dir / 'winner_pattern_analysis.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f'\nFull results saved to {output_path}')


if __name__ == '__main__':
    main()
