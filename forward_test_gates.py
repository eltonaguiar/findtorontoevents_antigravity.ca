#!/usr/bin/env python3
"""
Forward Test Gate Filter — apply Smart Score quality gates BEFORE paper-trading entries.

From PERFORMANCE_ANALYSIS_REPORT.md: forward test shows 30% WR, 78.9% SL hits.
From audit dashboard: Smart tier shows 64.5% WR, +0.73% avg PnL.
The gap proves the gates work. The forward test just isn't using them.

This module wraps any pick generation pipeline and filters through gates
BEFORE the pick enters the forward test book.

Usage:
    from forward_test_gates import GateFilter
    gate = GateFilter(closed_history, active_picks)
    should_trade, reason = gate.should_take_trade(pick)
"""

from typing import Dict, List, Tuple, Optional
from collections import defaultdict


# Blocked systems from LEARNINGS.md — these are proven losers
BLOCKED_SYSTEMS = {
    'vol_spike_backfill',
    'winner_pattern',
    'ml_crypto_predictor',       # Had 365 picks at -8% to -10% PnL each
    'unknown',                    # "unknown" strategy with -29.3pp degradation
    'ema_stack_momentum',         # 66.7% source WR → 25% realized (-41.7pp)
}

# Systems that need PF check (from LEARNINGS.md learnings)
HIGH_RISK_SYSTEMS = {
    'crypto_drawdown_convexity_recovery_v1',  # 45.2% → 22.2% realized
    'MomentumEMA',                            # 45.5% → 28.6% realized
    'extreme_fear',                           # 43.2% → 27.3% realized
}


class GateFilter:
    """
    Two-stage quality gate filter for forward testing.
    
    Stage 1: Hard pass/fail gates (binary)
    Stage 2: Soft scoring gates (penalty-based)
    """
    
    # Gate thresholds
    MIN_ML_SCORE = 0.50          # Kill zone: bottom 20th percentile
    MIN_RR = 1.2                 # Minimum risk/reward after commission
    MAX_TP_REMAINING_PCT = 0.90  # Must have at least 10% room to TP
    MIN_TP_REMAINING_PCT = 0.10  # At least 10% upside remaining
    MIN_SYS_WR = 45              # Below this, system loses after commission
    MIN_SYS_PF = 1.0             # Profit factor < 1.0 = guaranteed loss
    MIN_SYS_CLOSED = 5           # Need at least 5 trades to evaluate
    MAX_AGE_HOURS = 48           # Stale picks excluded
    MAX_AGE_HOURS_COPY_TRADER = 168
    MIN_SCORE_DIRECTION_CONFLICT = 70  # Need high score to take conflicting direction
    
    # Commission assumptions (IBKR Canada)
    COMMISSION_CRYPTO_RT = 0.0030    # 0.15% per side
    COMMISSION_EQUITY_RT = 0.0070    # $1 min + $0.0035/share approx
    COMMISSION_FOREX_RT = 0.0002     # Spread only
    
    def __init__(self, closed_history: List[Dict], active_picks: List[Dict] = None):
        self.closed = closed_history
        self.active = active_picks or []
        
        # Build strategy stats from closed history
        self._strat_stats = self._build_strategy_stats()
        self._active_by_symbol = self._index_active_by_symbol()
    
    def _build_strategy_stats(self) -> Dict:
        """Compute per-strategy WR, PF, and trade count from closed history."""
        by_strat = defaultdict(list)
        for t in self.closed:
            by_strat[t.get('strategy', 'unknown')].append(t)
        
        stats = {}
        for strat, trades in by_strat.items():
            wins = [t for t in trades if float(t.get('pnl_pct', t.get('pnl', 0)) or 0) > 0]
            losses = [t for t in trades if float(t.get('pnl_pct', t.get('pnl', 0)) or 0) <= 0]
            
            n = len(trades)
            wr = (len(wins) / n * 100) if n > 0 else 0
            
            gross_profit = sum(float(t.get('pnl_pct', t.get('pnl', 0)) or 0) for t in wins)
            gross_loss = abs(sum(float(t.get('pnl_pct', t.get('pnl', 0)) or 0) for t in losses))
            pf = gross_profit / gross_loss if gross_loss > 0 else 999
            
            avg_pnl = sum(float(t.get('pnl_pct', t.get('pnl', 0)) or 0) for t in trades) / n if n > 0 else 0
            
            stats[strat] = {
                'n': n,
                'wr': wr,
                'pf': pf,
                'avg_pnl': avg_pnl,
                'wins': len(wins),
                'losses': len(losses),
            }
        
        return stats
    
    def _index_active_by_symbol(self) -> Dict:
        """Index active picks by symbol for conflict detection."""
        by_symbol = defaultdict(list)
        for p in self.active:
            by_symbol[p.get('symbol', '')].append(p)
        return by_symbol
    
    def should_take_trade(self, pick: Dict) -> Tuple[bool, str]:
        """
        Apply all quality gates to a pick. Returns (pass, reason).
        
        This is the main entry point — call this before paper-trading any pick.
        """
        strategy = pick.get('strategy', 'unknown')
        symbol = pick.get('symbol', '')
        direction = pick.get('direction', 'LONG')
        score = pick.get('score', 50)
        ml_score = pick.get('ml_score', pick.get('ml_composite_score', 0.5))
        
        # ===== STAGE 1: HARD GATES =====
        
        # Gate 1: Blocked systems
        if strategy in BLOCKED_SYSTEMS:
            return False, f"blocked_system: {strategy}"
        
        # Gate 2: Kill zone (ml_score too low)
        if ml_score < self.MIN_ML_SCORE:
            return False, f"kill_zone: ml_score={ml_score:.2f} < {self.MIN_ML_SCORE}"
        
        # Gate 3: R:R minimum
        entry = pick.get('entry', 0)
        tp = pick.get('tp', 0)
        sl = pick.get('sl', 0)
        
        if entry and tp and sl and entry != sl:
            risk = abs(entry - sl)
            reward = abs(tp - entry)
            rr = reward / risk if risk > 0 else 0
            
            # Net R:R after commission
            asset_class = pick.get('asset_class', 'CRYPTO')
            if asset_class == 'EQUITY':
                commission = self.COMMISSION_EQUITY_RT
            elif asset_class == 'FOREX':
                commission = self.COMMISSION_FOREX_RT
            else:
                commission = self.COMMISSION_CRYPTO_RT
            
            net_risk = risk + (entry * commission)
            net_reward = reward - (entry * commission)
            net_rr = net_reward / net_risk if net_risk > 0 else 0
            
            if net_rr < self.MIN_RR:
                return False, f"rr_too_low: net_rr={net_rr:.2f} < {self.MIN_RR}"
        
        # Gate 4: TP remaining ≥ 10%
        if tp and entry:
            current = pick.get('current_price', entry)
            if direction == 'LONG' and tp > entry:
                tp_remaining = (tp - current) / (tp - entry)
            elif direction == 'SHORT' and tp < entry:
                tp_remaining = (current - tp) / (entry - tp)
            else:
                tp_remaining = 0.5  # Unknown
            
            if tp_remaining < self.MIN_TP_REMAINING_PCT:
                return False, f"tp_exhausted: remaining={tp_remaining:.1%}"
        
        # Gate 5: Age limit
        age_h = pick.get('age_hours', 0)
        is_copy_trader = pick.get('is_copy_trader', False)
        max_age = self.MAX_AGE_HOURS_COPY_TRADER if is_copy_trader else self.MAX_AGE_HOURS
        if age_h > max_age:
            return False, f"stale_pick: age={age_h:.0f}h > {max_age}h"
        
        # Gate 6: Already resolved (TP/SL hit)
        if pick.get('tp_hit') or pick.get('sl_hit'):
            return False, "already_resolved"
        
        # Gate 7: Meme LONG in bear regime
        MEME_SYMBOLS = {'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'FLOKIUSDT', 'BONKUSDT'}
        regime = pick.get('regime', '')
        if symbol in MEME_SYMBOLS and direction == 'LONG' and regime in ('BEAR', 'STORM', 'HURRICANE'):
            return False, "meme_long_in_bear"
        
        # Gate 8: Strategy-level PF check (from closed history)
        if strategy in HIGH_RISK_SYSTEMS:
            strat_stat = self._strat_stats.get(strategy, {})
            if strat_stat.get('n', 0) >= self.MIN_SYS_CLOSED:
                if strat_stat['pf'] < self.MIN_SYS_PF:
                    return False, f"pf_below_1: {strategy} PF={strat_stat['pf']:.2f}"
                if strat_stat['wr'] < self.MIN_SYS_WR:
                    return False, f"wr_too_low: {strategy} WR={strat_stat['wr']:.1f}%"
        
        # ===== STAGE 2: SOFT GATES (score-dependent) =====
        
        # Soft 1: Direction conflict — same symbol, opposite direction in active
        same_symbol = self._active_by_symbol.get(symbol, [])
        has_conflict = any(p.get('direction') != direction for p in same_symbol)
        if has_conflict and score < self.MIN_SCORE_DIRECTION_CONFLICT:
            return False, f"direction_conflict: score={score} < {self.MIN_SCORE_DIRECTION_CONFLICT}"
        
        # Soft 2: Overconfidence cap
        strat_stat = self._strat_stats.get(strategy, {})
        if score > 85 and strat_stat.get('n', 0) < 10:
            pick['score'] = 60  # Cap, don't reject — just demote
        
        # Soft 3: Strategy momentum (after-WIN boost, after-LOSS penalty)
        # From LEARNINGS: after WIN = 65.6% WR, after LOSS = 24.1% WR
        # But ONLY for crypto — equities mean-revert
        asset_class = pick.get('asset_class', 'CRYPTO')
        if asset_class == 'CRYPTO':
            last_trade = self._get_last_trade_for(strategy, symbol)
            if last_trade:
                last_pnl = float(last_trade.get('pnl_pct', last_trade.get('pnl', 0)) or 0)
                if last_pnl < 0 and score < 65:
                    return False, f"post_loss_penalty: last trade was loss, score={score} < 65"
        
        return True, "passed_all_gates"
    
    def _get_last_trade_for(self, strategy: str, symbol: str) -> Optional[Dict]:
        """Get most recent closed trade for this strategy+symbol."""
        relevant = [
            t for t in self.closed
            if t.get('strategy') == strategy and t.get('symbol') == symbol
        ]
        if not relevant:
            return None
        return max(relevant, key=lambda t: t.get('closed_at', t.get('timestamp', '')))
    
    def filter_batch(self, picks: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter a batch of picks through all gates.
        
        Returns (passed_picks, rejected_picks_with_reasons).
        """
        passed = []
        rejected = []
        
        for pick in picks:
            should_trade, reason = self.should_take_trade(pick)
            if should_trade:
                passed.append(pick)
            else:
                rejected.append({**pick, '_reject_reason': reason})
        
        return passed, rejected
    
    def gate_stats(self) -> Dict:
        """Return statistics about the gate filter state."""
        return {
            'total_closed': len(self.closed),
            'total_active': len(self.active),
            'strategies_tracked': len(self._strat_stats),
            'blocked_systems': len(BLOCKED_SYSTEMS),
            'high_risk_systems': len(HIGH_RISK_SYSTEMS),
            'symbols_with_conflicts': len([
                s for s, picks in self._active_by_symbol.items()
                if len(set(p.get('direction') for p in picks)) > 1
            ]),
        }


if __name__ == '__main__':
    # Mock test
    mock_closed = [
        {'strategy': 'crypto_keltner_v1', 'symbol': 'BTCUSDT', 'direction': 'LONG', 'pnl_pct': 2.5, 'asset_class': 'CRYPTO'},
        {'strategy': 'crypto_keltner_v1', 'symbol': 'BTCUSDT', 'direction': 'LONG', 'pnl_pct': -1.2, 'asset_class': 'CRYPTO'},
        {'strategy': 'ml_crypto_predictor', 'symbol': 'ETHUSDT', 'direction': 'LONG', 'pnl_pct': -8.5, 'asset_class': 'CRYPTO'},
    ] * 10
    
    mock_active = [
        {'symbol': 'BTCUSDT', 'direction': 'LONG', 'strategy': 'drawdown_recovery'},
    ]
    
    gate = GateFilter(mock_closed, mock_active)
    
    test_picks = [
        {'symbol': 'ETHUSDT', 'direction': 'LONG', 'strategy': 'ml_crypto_predictor', 'score': 70, 'ml_score': 0.6, 'entry': 3200, 'tp': 3400, 'sl': 3100, 'asset_class': 'CRYPTO'},
        {'symbol': 'SOLUSDT', 'direction': 'LONG', 'strategy': 'fear_greed_contrarian', 'score': 75, 'ml_score': 0.65, 'entry': 140, 'tp': 155, 'sl': 135, 'asset_class': 'CRYPTO'},
        {'symbol': 'AAPL', 'direction': 'LONG', 'strategy': 'pead_earnings_drift', 'score': 80, 'ml_score': 0.7, 'entry': 185, 'tp': 192, 'sl': 180, 'asset_class': 'EQUITY'},
    ]
    
    passed, rejected = gate.filter_batch(test_picks)
    
    print(f"Passed: {len(passed)}")
    for p in passed:
        print(f"  ✅ {p['symbol']} ({p['strategy']})")
    
    print(f"\nRejected: {len(rejected)}")
    for r in rejected:
        print(f"  ❌ {r['symbol']} ({r['strategy']}) — {r['_reject_reason']}")
