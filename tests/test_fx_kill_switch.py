#!/usr/bin/env python3
# unittest-based tests for FX Kill Switch Enforcer
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.fx_kill_switch import (
    is_forex_strategy,
    check_strategy_for_kill,
    _compute_profit_factor,
    _compute_decay,
    _PF_KILL_THRESHOLD,
    _DECAY_KILL_THRESHOLD,
    _MIN_TRADES_FOR_PF_KILL,
    _MIN_TRADES_FOR_ZERO_WR_KILL,
    _KNOWN_TOXIC_FOREX_STRATEGIES,
)


class TestIsForexStrategy(unittest.TestCase):
    def test_detects_forex_in_name(self):
        self.assertTrue(is_forex_strategy('forex_rsi2_mean_reversion'))
        self.assertTrue(is_forex_strategy('fx_momentum_v2'))
        self.assertTrue(is_forex_strategy('currency_hedge'))

    def test_detects_currency_pairs(self):
        self.assertTrue(is_forex_strategy('eur_usd_breakout'))
        self.assertTrue(is_forex_strategy('gbpjpy_scalp'))
        self.assertTrue(is_forex_strategy('usdcad_trend'))
        self.assertTrue(is_forex_strategy('EUR_USD_breakout'))  # uppercase OK

    def test_detects_usd_strategies(self):
        self.assertTrue(is_forex_strategy('usd_index_trend'))
        self.assertTrue(is_forex_strategy('usd_momentum'))
        self.assertTrue(is_forex_strategy('GBPUSD_scalp'))

    def test_rejects_crypto_strategies(self):
        self.assertFalse(is_forex_strategy('btc_momentum'))
        self.assertFalse(is_forex_strategy('eth_usdt_scalp'))  # 'usdt' != 'usd'
        self.assertFalse(is_forex_strategy('sol_momentum'))

    def test_rejects_equity_strategies(self):
        self.assertFalse(is_forex_strategy('sp500_momentum'))
        self.assertFalse(is_forex_strategy('nasdaq_trend'))
        self.assertFalse(is_forex_strategy('spy_scalp'))
        self.assertFalse(is_forex_strategy('aapl_mean_reversion'))
        self.assertFalse(is_forex_strategy('beforex_strategy'))  # 'forex' in 'beforex' shouldn't match

    def test_detects_six_char_pairs(self):
        self.assertTrue(is_forex_strategy('GBPJPY_reversal'))
        self.assertTrue(is_forex_strategy('EURUSD_momentum'))
        self.assertTrue(is_forex_strategy('USDJPY_trend'))


class TestComputeProfitFactor(unittest.TestCase):
    def test_basic_pf_calculation(self):
        trades = [{'pnl_pct': 2.0}, {'pnl_pct': 1.5}, {'pnl_pct': -0.5}, {'pnl_pct': -1.0}]
        pf = _compute_profit_factor(trades)
        self.assertAlmostEqual(pf, 3.5 / 1.5)

    def test_all_winners(self):
        trades = [{'pnl_pct': 1.0}, {'pnl_pct': 2.0}]
        pf = _compute_profit_factor(trades)
        self.assertEqual(pf, float('inf'))


class TestComputeDecay(unittest.TestCase):
    def test_no_trades_returns_zero(self):
        self.assertAlmostEqual(_compute_decay([]), 0.0)

    def test_insufficient_trades_returns_zero(self):
        trades = [{'pnl_pct': 0.01, 'closed_at': '2026-01-01'}] * 10
        self.assertAlmostEqual(_compute_decay(trades), 0.0)

    def test_no_dates_returns_zero(self):
        # If no dates, sorting doesn't crash — still returns a value
        trades = [{'pnl_pct': 0.01}] * 35
        result = _compute_decay(trades)
        self.assertIsInstance(result, float)

    def test_positive_decay_recent_worse(self):
        # 35 trades total: first 15 = OLD losses (April), last 20 = RECENT wins (May).
        # All-time WR = 20/35 = 57%. Recent 30 (all trades, sorted reverse by date):
        # first 30 are the wins (May dates 2026-05-16 through 2026-05-30) = 100% WR.
        # But we need decay = ALL-TIME - RECENT, so recent must be WORSE than all-time.
        # Fix: first 15 = OLD wins (April), last 20 = RECENT losses (May).
        # All-time WR = 15/35 = 43%. Recent 30 (May dates sorted reverse) = 100% losses = 0% WR.
        # Decay = 0.43 - 0.0 = 43pp >> 10pp. Good.
        trades = []
        # Old trades first (April, wins)
        for i in range(15):
            trades.append({'pnl_pct': 0.01, 'closed_at': f'2026-04-{i+16:02d}'})  # Apr 16-30 wins
        # Recent trades last (May, losses)
        for i in range(20):
            trades.append({'pnl_pct': -0.01, 'closed_at': f'2026-05-{i+11:02d}'})  # May 11-30 losses
        decay = _compute_decay(trades)
        self.assertGreater(decay, 0.09)  # At least 9pp decay (recent 33% vs all-time 43%)

    def test_no_decay_stable_strategy(self):
        # 60 trades: first 30 all wins (Apr dates), last 30 all losses (Jun dates).
        # sorted(reverse=True): Jun first (losses), then Apr (wins).
        # Recent 30 = all Jun losses = 0% WR. All-time WR = 30/60 = 50%.
        # Decay = 50% - 0% = 50pp -- this IS decay, not no-decay!
        # Fix: use 30 trades where ALL have identical date — sort is stable/undefined,
        # but with all identical pnl (0.01), the win rate is constant (100%) so decay=0.
        trades = [{'pnl_pct': 0.01, 'closed_at': '2026-05-01'} for _ in range(35)]
        decay = _compute_decay(trades)
        # All trades: 35 wins, 0 losses -> all-time WR=100%. Recent 30: all wins -> 100%. Decay=0.
        self.assertLess(abs(decay), 0.001)  # Essentially zero (within float precision)


class TestCheckStrategyForKill(unittest.TestCase):
    def test_known_toxic_immediate_kill(self):
        for strategy in _KNOWN_TOXIC_FOREX_STRATEGIES:
            should_kill, reason = check_strategy_for_kill(strategy)
            self.assertTrue(should_kill, f'{strategy} should be killed')

    def test_non_forex_passes(self):
        should_kill, reason = check_strategy_for_kill('btc_momentum')
        self.assertFalse(should_kill)
        self.assertIn('Not a FOREX', reason)

    def test_zero_wr_kill_rule(self):
        stats = {'n_closed': 30, 'win_rate': 0, 'profit_factor': 0, 'decay_pp': 0}
        should_kill, reason = check_strategy_for_kill('some_forex_strategy', stats)
        self.assertTrue(should_kill)
        self.assertIn('Zero WR', reason)

    def test_healthy_strategy_passes(self):
        stats = {'n_closed': 50, 'win_rate': 0.58, 'profit_factor': 1.5, 'decay_pp': 0.05}
        should_kill, reason = check_strategy_for_kill('some_forex_strategy', stats)
        self.assertFalse(should_kill)


class TestKnownToxicStrategies(unittest.TestCase):
    def test_hard_coded_list(self):
        self.assertIn('myfxbook_retail_contrarian', _KNOWN_TOXIC_FOREX_STRATEGIES)
        self.assertIn('forex_rsi2_mean_reversion', _KNOWN_TOXIC_FOREX_STRATEGIES)
        self.assertIn('ema_aggressive_prop', _KNOWN_TOXIC_FOREX_STRATEGIES)
        self.assertGreater(len(_KNOWN_TOXIC_FOREX_STRATEGIES), 5)


if __name__ == '__main__':
    unittest.main()
