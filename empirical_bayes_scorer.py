#!/usr/bin/env python3
"""
Empirical Bayes Win-Probability Scorer — replaces fake heuristic ML scorer.

Replaces simulate_hindsight_win_prob() (hardcoded base 0.55 + magic numbers)
with real Bayesian shrinkage from closed trade history.

Key insight from LEARNINGS.md: sb_strategy_track_record had +97pp WR spread
(1.8% to 98.8% Q1→Q4) but 98% of picks had it empty. This fills that gap.

Usage:
    from empirical_bayes_scorer import EmpiricalBayesScorer
    scorer = EmpiricalBayesScorer(closed_trades)
    result = scorer.win_prob(symbol='BTCUSDT', strategy='crypto_keltner_v1', direction='LONG')
"""

import math
from typing import List, Dict, Optional
from collections import defaultdict


class EmpiricalBayesScorer:
    """
    Beta-Binomial Empirical Bayes win probability estimator.
    
    Shrinkage hierarchy:
    1. Symbol×Strategy×Direction (most specific, least data)
    2. Symbol×Strategy
    3. Strategy×Direction
    4. Strategy (most general within strategy)
    5. Asset Class×Direction (fallback)
    6. Global prior (last resort)
    """
    
    PRIOR_STRENGTH = 20  # Need ~20 trades to move significantly off prior
    NET_LOSER_SCORE_CAP = 59.9
    
    def __init__(self, closed_trades: List[Dict]):
        self.trades = closed_trades
        self.global_wr = self._calc_wr(closed_trades)
        
        # Build index
        self._by_strategy = defaultdict(list)
        self._by_strat_sym = defaultdict(list)
        self._by_strat_sym_dir = defaultdict(list)
        self._by_strat_dir = defaultdict(list)
        self._by_asset_dir = defaultdict(list)
        
        for t in closed_trades:
            strat = t.get('strategy', 'unknown')
            sym = t.get('symbol', 'unknown')
            direction = t.get('direction', 'LONG')
            asset = t.get('asset_class', 'CRYPTO')
            
            self._by_strategy[strat].append(t)
            self._by_strat_sym[f"{strat}|{sym}"].append(t)
            self._by_strat_sym_dir[f"{strat}|{sym}|{direction}"].append(t)
            self._by_strat_dir[f"{strat}|{direction}"].append(t)
            self._by_asset_dir[f"{asset}|{direction}"].append(t)
    
    def _calc_wr(self, trades: List[Dict]) -> float:
        if not trades:
            return 0.44  # System-wide prior from your data
        wins = sum(1 for t in trades if float(t.get('pnl_pct', t.get('pnl', 0)) or 0) > 0)
        return wins / len(trades)

    def _mean_pnl(self, trades: List[Dict]) -> Optional[float]:
        values = []
        for t in trades:
            pnl = t.get('pnl_pct', t.get('pnl'))
            if pnl is None:
                continue
            try:
                values.append(float(pnl))
            except (TypeError, ValueError):
                continue
        if not values:
            return None
        return sum(values) / len(values)
    
    def _shrink(self, observed_wr: float, n: int, prior_wr: float) -> float:
        """Beta-Binomial shrinkage: blend observed toward prior based on sample size."""
        return (n * observed_wr + self.PRIOR_STRENGTH * prior_wr) / (n + self.PRIOR_STRENGTH)
    
    def win_prob(self, symbol: str, strategy: str, direction: str = 'LONG',
                 asset_class: str = 'CRYPTO') -> Dict:
        """
        Compute shrunk win probability for a pick.
        
        Returns dict with win_prob, n_trades, confidence_band, tier, and shrinkage details.
        """
        # Level 1: Strategy×Symbol×Direction (most specific)
        key_ssd = f"{strategy}|{symbol}|{direction}"
        ssd_trades = self._by_strat_sym_dir.get(key_ssd, [])
        n_ssd = len(ssd_trades)
        ssd_wr = self._calc_wr(ssd_trades) if n_ssd > 0 else None
        
        # Level 2: Strategy×Symbol
        key_ss = f"{strategy}|{symbol}"
        ss_trades = self._by_strat_sym.get(key_ss, [])
        n_ss = len(ss_trades)
        ss_wr = self._calc_wr(ss_trades) if n_ss > 0 else None
        
        # Level 3: Strategy×Direction
        key_sd = f"{strategy}|{direction}"
        sd_trades = self._by_strat_dir.get(key_sd, [])
        n_sd = len(sd_trades)
        sd_wr = self._calc_wr(sd_trades) if n_sd > 0 else None
        
        # Level 4: Strategy
        strat_trades = self._by_strategy.get(strategy, [])
        n_strat = len(strat_trades)
        strat_wr = self._calc_wr(strat_trades) if n_strat > 0 else None
        
        # Level 5: Asset×Direction
        key_ad = f"{asset_class}|{direction}"
        ad_trades = self._by_asset_dir.get(key_ad, [])
        n_ad = len(ad_trades)
        ad_wr = self._calc_wr(ad_trades) if n_ad > 0 else None
        
        # Shrinkage cascade
        # Start from most specific, shrink toward broader pool
        if n_ssd >= 5:
            # Enough specific data
            prob_ssd = self._shrink(ssd_wr, n_ssd, ss_wr if ss_wr else strat_wr if strat_wr else self.global_wr)
            prob_ss = self._shrink(ss_wr, n_ss, strat_wr if strat_wr else self.global_wr) if ss_wr else None
            prob_strat = self._shrink(strat_wr, n_strat, self.global_wr) if strat_wr else self.global_wr
            
            final = 0.5 * prob_ssd + 0.3 * (prob_ss or prob_strat) + 0.2 * prob_strat
            n_used = n_ssd
            tier = 'SYMBOL_STRATEGY_DIRECTION'
            
        elif n_ss >= 5:
            prob_ss = self._shrink(ss_wr, n_ss, strat_wr if strat_wr else self.global_wr)
            prob_strat = self._shrink(strat_wr, n_strat, self.global_wr) if strat_wr else self.global_wr
            
            final = 0.5 * prob_ss + 0.3 * prob_strat + 0.2 * self.global_wr
            n_used = n_ss
            tier = 'SYMBOL_STRATEGY'
            
        elif n_sd >= 5:
            prob_sd = self._shrink(sd_wr, n_sd, strat_wr if strat_wr else self.global_wr)
            prob_strat = self._shrink(strat_wr, n_strat, self.global_wr) if strat_wr else self.global_wr
            
            final = 0.5 * prob_sd + 0.3 * prob_strat + 0.2 * self.global_wr
            n_used = n_sd
            tier = 'STRATEGY_DIRECTION'
            
        elif n_strat >= 5:
            final = self._shrink(strat_wr, n_strat, self.global_wr)
            n_used = n_strat
            tier = 'STRATEGY'
            
        elif n_ad >= 5:
            final = self._shrink(ad_wr, n_ad, self.global_wr)
            n_used = n_ad
            tier = 'ASSET_DIRECTION'
            
        else:
            final = self.global_wr
            n_used = max(n_ssd, n_ss, n_sd, n_strat, n_ad, 0)
            tier = 'GLOBAL_PRIOR'
        
        # Confidence band (95% Wilson interval)
        if n_used > 0:
            z = 1.96
            denom = 1 + z**2 / n_used
            center = (final + z**2 / (2 * n_used)) / denom
            spread = z * math.sqrt((final * (1-final) + z**2 / (4 * n_used)) / n_used) / denom
            ci_low = max(0, center - spread)
            ci_high = min(1, center + spread)
        else:
            ci_low = final - 0.15
            ci_high = final + 0.15
        
        return {
            'win_prob': round(final, 3),
            'n_trades': n_used,
            'tier': tier,
            'ci_95_low': round(ci_low, 3),
            'ci_95_high': round(ci_high, 3),
            'confidence_band': round(ci_high - ci_low, 3),
            'shrinkage_applied': n_used < 20,
            'global_prior': round(self.global_wr, 3),
            'raw': {
                'ssd': {'n': n_ssd, 'wr': round(ssd_wr, 3) if ssd_wr else None},
                'ss': {'n': n_ss, 'wr': round(ss_wr, 3) if ss_wr else None},
                'sd': {'n': n_sd, 'wr': round(sd_wr, 3) if sd_wr else None},
                'strat': {'n': n_strat, 'wr': round(strat_wr, 3) if strat_wr else None},
            }
        }
    
    def score_pick(self, pick: Dict, closed_trades: List[Dict] = None) -> Dict:
        """
        Enrich a pick dict with empirical win probability.
        Drop-in replacement for enhance_pick() in ml_pick_scorer.py
        """
        result = self.win_prob(
            symbol=pick.get('symbol', ''),
            strategy=pick.get('strategy', ''),
            direction=pick.get('direction', 'LONG'),
            asset_class=pick.get('asset_class', 'CRYPTO'),
        )
        
        original_score = pick.get('score', 50)
        baseline = self.global_wr if self.global_wr > 0 else 0.44
        enhanced_score = min(100, original_score * (result['win_prob'] / baseline))
        strategy_trades = self._by_strategy.get(pick.get('strategy', ''), [])
        mean_pnl = self._mean_pnl(strategy_trades)
        is_net_loser = mean_pnl is not None and mean_pnl < 0 and len(strategy_trades) >= 10
        if is_net_loser:
            enhanced_score = min(enhanced_score, self.NET_LOSER_SCORE_CAP)
        
        pick['eb_win_prob'] = result['win_prob']
        pick['eb_tier'] = result['tier']
        pick['eb_n_trades'] = result['n_trades']
        pick['eb_ci_band'] = result['confidence_band']
        pick['eb_shrunk'] = result['shrinkage_applied']
        pick['eb_mean_pnl'] = round(mean_pnl, 4) if mean_pnl is not None else None
        pick['eb_net_loser_cap_applied'] = is_net_loser
        pick['enhanced_score'] = round(enhanced_score, 1)
        
        # Kill flag: if win_prob < 0.35 after shrinkage, flag for removal
        pick['eb_kill_flag'] = result['win_prob'] < 0.35 and result['n_trades'] >= 10
        
        return pick


if __name__ == '__main__':
    # Example with mock closed trades
    mock_trades = [
        {'strategy': 'crypto_keltner_v1', 'symbol': 'BTCUSDT', 'direction': 'LONG', 'pnl_pct': 2.5, 'asset_class': 'CRYPTO'},
        {'strategy': 'crypto_keltner_v1', 'symbol': 'BTCUSDT', 'direction': 'LONG', 'pnl_pct': -1.2, 'asset_class': 'CRYPTO'},
        {'strategy': 'crypto_keltner_v1', 'symbol': 'BTCUSDT', 'direction': 'LONG', 'pnl_pct': 3.1, 'asset_class': 'CRYPTO'},
        {'strategy': 'crypto_keltner_v1', 'symbol': 'ETHUSDT', 'direction': 'LONG', 'pnl_pct': -2.0, 'asset_class': 'CRYPTO'},
        {'strategy': 'fear_greed_contrarian', 'symbol': 'BTCUSDT', 'direction': 'LONG', 'pnl_pct': 1.8, 'asset_class': 'CRYPTO'},
        {'strategy': 'quality_minus_junk', 'symbol': 'XOM', 'direction': 'LONG', 'pnl_pct': 1.5, 'asset_class': 'EQUITY'},
    ] * 10  # Repeat for sample size
    
    scorer = EmpiricalBayesScorer(mock_trades)
    
    # Test predictions
    tests = [
        ('BTCUSDT', 'crypto_keltner_v1', 'LONG'),
        ('ETHUSDT', 'crypto_keltner_v1', 'LONG'),
        ('SOLUSDT', 'fear_greed_contrarian', 'LONG'),  # No specific data
    ]
    
    for sym, strat, dir in tests:
        r = scorer.win_prob(sym, strat, dir)
        print(f"{sym:12} {strat:25} {dir:5} → WR: {r['win_prob']:.1%} | "
              f"Tier: {r['tier']:30} | N: {r['n_trades']:3} | "
              f"CI: [{r['ci_95_low']:.1%}, {r['ci_95_high']:.1%}]")
