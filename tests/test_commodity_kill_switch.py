# -*- coding: utf-8 -*-
# Unit tests for alpha_engine/commodity_kill_switch.py
# Mirrors the test pattern of tests/test_fx_kill_switch.py.

import os
import sys
import unittest
from unittest.mock import patch

# Ensure alpha_engine is importable
sys.path.insert(0, 'alpha_engine')


class TestIsCommodityStrategy(unittest.TestCase):

    def test_exact_commodity_indicator(self):
        from alpha_engine.commodity_kill_switch import is_commodity_strategy
        self.assertTrue(is_commodity_strategy('commodity_inverse_momentum'))
        self.assertTrue(is_commodity_strategy('commodity_mean_reversion'))
        self.assertTrue(is_commodity_strategy('commodity_trend_following'))

    def test_gold_silver_oil_indicators(self):
        from alpha_engine.commodity_kill_switch import is_commodity_strategy
        self.assertTrue(is_commodity_strategy('gold_momentum'))
        self.assertTrue(is_commodity_strategy('silver_mean_reversion'))
        self.assertTrue(is_commodity_strategy('oil_trend_following'))
        self.assertTrue(is_commodity_strategy('crude_oil_swing'))

    def test_futures_roots(self):
        from alpha_engine.commodity_kill_switch import is_commodity_strategy
        self.assertTrue(is_commodity_strategy('futures_momentum'))
        self.assertTrue(is_commodity_strategy('futures_mean_reversion'))
        self.assertTrue(is_commodity_strategy('futures_trend'))

    def test_non_commodity_strategies(self):
        from alpha_engine.commodity_kill_switch import is_commodity_strategy
        self.assertFalse(is_commodity_strategy('crypto_momentum'))
        self.assertFalse(is_commodity_strategy('equity_long'))
        self.assertFalse(is_commodity_strategy('forex_rsi2'))
        self.assertFalse(is_commodity_strategy('etf_spy_momentum'))

    def test_empty_and_none(self):
        from alpha_engine.commodity_kill_switch import is_commodity_strategy
        self.assertFalse(is_commodity_strategy(''))
        self.assertFalse(is_commodity_strategy(None))


class TestIsInverseStrategy(unittest.TestCase):

    def test_inverse_indicator(self):
        from alpha_engine.commodity_kill_switch import is_inverse_strategy
        self.assertTrue(is_inverse_strategy('commodity_inverse_momentum'))
        self.assertTrue(is_inverse_strategy('inverse_commodity'))
        self.assertTrue(is_inverse_strategy('commodity_short_only'))

    def test_short_indicators(self):
        from alpha_engine.commodity_kill_switch import is_inverse_strategy
        self.assertTrue(is_inverse_strategy('short_only_momentum'))
        self.assertTrue(is_inverse_strategy('bearish_reversion'))
        self.assertTrue(is_inverse_strategy('inverse_trend'))

    def test_non_inverse_strategies(self):
        from alpha_engine.commodity_kill_switch import is_inverse_strategy
        self.assertFalse(is_inverse_strategy('commodity_momentum'))
        self.assertFalse(is_inverse_strategy('gold_long_only'))
        self.assertFalse(is_inverse_strategy('oil_trend_following'))

    def test_empty_and_none(self):
        from alpha_engine.commodity_kill_switch import is_inverse_strategy
        self.assertFalse(is_inverse_strategy(''))
        self.assertFalse(is_inverse_strategy(None))


class TestIsCommodityInverseStrategy(unittest.TestCase):

    def test_commodity_inverse_true(self):
        from alpha_engine.commodity_kill_switch import is_commodity_inverse_strategy
        self.assertTrue(is_commodity_inverse_strategy('commodity_inverse_momentum'))
        self.assertTrue(is_commodity_inverse_strategy('gold_short_only'))
        self.assertTrue(is_commodity_inverse_strategy('oil_inverse_trend'))

    def test_commodity_not_inverse(self):
        from alpha_engine.commodity_kill_switch import is_commodity_inverse_strategy
        self.assertFalse(is_commodity_inverse_strategy('commodity_momentum'))
        self.assertFalse(is_commodity_inverse_strategy('gold_long_only'))
        self.assertFalse(is_commodity_inverse_strategy('oil_trend_following'))

    def test_inverse_not_commodity(self):
        from alpha_engine.commodity_kill_switch import is_commodity_inverse_strategy
        self.assertFalse(is_commodity_inverse_strategy('crypto_inverse_momentum'))
        self.assertFalse(is_commodity_inverse_strategy('equity_short_only'))

    def test_non_commodity_non_inverse(self):
        from alpha_engine.commodity_kill_switch import is_commodity_inverse_strategy
        self.assertFalse(is_commodity_inverse_strategy('crypto_momentum'))
        self.assertFalse(is_commodity_inverse_strategy('equity_long'))


class TestComputeProfitFactor(unittest.TestCase):

    def test_no_trades(self):
        from alpha_engine.commodity_kill_switch import _compute_profit_factor
        result = _compute_profit_factor([])
        self.assertEqual(result, 1.0)

    def test_profitable_trades(self):
        from alpha_engine.commodity_kill_switch import _compute_profit_factor
        trades = [{'pnl_pct': 1.0}, {'pnl_pct': 2.0}, {'pnl_pct': 0.5}]
        result = _compute_profit_factor(trades)
        self.assertGreater(result, 1.0)

    def test_losing_trades(self):
        from alpha_engine.commodity_kill_switch import _compute_profit_factor
        trades = [{'pnl_pct': -1.0}, {'pnl_pct': -0.5}]
        result = _compute_profit_factor(trades)
        self.assertLess(result, 1.0)

    def test_infinite_profit_factor(self):
        from alpha_engine.commodity_kill_switch import _compute_profit_factor
        trades = [{'pnl_pct': 1.0}]
        result = _compute_profit_factor(trades)
        self.assertEqual(result, float('inf'))


class TestCheckStrategyForKill(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_known_toxic_hard_block(self):
        from alpha_engine import commodity_kill_switch as cm_ks
        should_kill, reason = cm_ks.check_strategy_for_kill(
            'commodity_inverse_momentum', stats={}
        )
        self.assertTrue(should_kill)
        self.assertIn('Known toxic COMMODITY', reason)

    def test_commodity_asset_class_plus_inverse_naming(self):
        from alpha_engine import commodity_kill_switch as cm_ks
        should_kill, reason = cm_ks.check_strategy_for_kill(
            'any_inverse_strategy',
            stats={},
            asset_class='COMMODITY'
        )
        self.assertTrue(should_kill)
        self.assertIn('COMMODITY asset_class + inverse naming', reason)

    def test_zero_wr_kill_rule(self):
        from alpha_engine import commodity_kill_switch as cm_ks
        stats = {'n_closed': 30, 'win_rate': 0.0, 'profit_factor': 0.5, 'decay_pp': 0.0}
        should_kill, reason = cm_ks.check_strategy_for_kill(
            'failing_strategy', stats=stats
        )
        self.assertTrue(should_kill)
        self.assertIn('Zero WR', reason)

    def test_pf_below_threshold_kill_rule(self):
        from alpha_engine import commodity_kill_switch as cm_ks
        stats = {'n_closed': 30, 'win_rate': 0.4, 'profit_factor': 0.5, 'decay_pp': 0.0}
        should_kill, reason = cm_ks.check_strategy_for_kill(
            'low_pf_strategy', stats=stats
        )
        self.assertTrue(should_kill)
        self.assertIn('PF', reason)

    def test_decay_kill_rule(self):
        from alpha_engine import commodity_kill_switch as cm_ks
        stats = {'n_closed': 30, 'win_rate': 0.5, 'profit_factor': 1.5, 'decay_pp': 0.20}
        should_kill, reason = cm_ks.check_strategy_for_kill(
            'decaying_strategy', stats=stats
        )
        self.assertTrue(should_kill)
        self.assertIn('Decay', reason)

    def test_passes_all_rules(self):
        from alpha_engine import commodity_kill_switch as cm_ks
        stats = {'n_closed': 100, 'win_rate': 0.55, 'profit_factor': 1.5, 'decay_pp': 0.05}
        should_kill, reason = cm_ks.check_strategy_for_kill(
            'good_commodity_strategy', stats=stats
        )
        self.assertFalse(should_kill)

    def test_insufficient_trades_no_kill(self):
        from alpha_engine import commodity_kill_switch as cm_ks
        stats = {'n_closed': 5, 'win_rate': 0.0, 'profit_factor': 0.3, 'decay_pp': 0.0}
        should_kill, reason = cm_ks.check_strategy_for_kill(
            'new_commodity_strategy', stats=stats
        )
        self.assertFalse(should_kill)


class TestStrategyBlocklistIntegration(unittest.TestCase):

    def test_is_commodity_inverse_killed_strategy_hard_block(self):
        from alpha_engine.strategy_blocklist import is_commodity_inverse_killed_strategy
        result = is_commodity_inverse_killed_strategy('commodity_inverse_momentum', 'COMMODITY')
        self.assertTrue(result)

    def test_is_commodity_inverse_killed_strategy_asset_class_plus_inverse(self):
        from alpha_engine.strategy_blocklist import is_commodity_inverse_killed_strategy
        result = is_commodity_inverse_killed_strategy('random_inverse_name', 'COMMODITY')
        self.assertTrue(result)

    def test_block_reason_returns_commodity_inverse_kill(self):
        from alpha_engine.strategy_blocklist import block_reason
        reason = block_reason('commodity_inverse_momentum', 'COMMODITY')
        self.assertEqual(reason, 'commodity-inverse-kill')

    def test_non_commodity_strategy_not_killed(self):
        from alpha_engine.strategy_blocklist import is_commodity_inverse_killed_strategy
        result = is_commodity_inverse_killed_strategy('crypto_inverse_momentum', 'CRYPTO')
        self.assertFalse(result)

    def test_commodity_non_inverse_not_killed(self):
        from alpha_engine.strategy_blocklist import is_commodity_inverse_killed_strategy
        result = is_commodity_inverse_killed_strategy('commodity_momentum', 'COMMODITY')
        self.assertFalse(result)


class TestFeedHygieneIntegration(unittest.TestCase):

    def test_commodity_inverse_pick_blocked(self):
        from alpha_engine.feed_hygiene import is_valid_active_pick
        pick = {
            'strategy': 'commodity_inverse_momentum',
            'asset_class': 'COMMODITY',
            'symbol': 'CL=F',
            'entry_price': 75.0,
            'status': 'ACTIVE',
            'direction': 'SHORT',
        }
        result = is_valid_active_pick(pick)
        self.assertFalse(result)

    def test_commodity_non_inverse_pick_allowed(self):
        from alpha_engine.feed_hygiene import is_valid_active_pick
        pick = {
            'strategy': 'commodity_momentum',
            'asset_class': 'COMMODITY',
            'symbol': 'CL=F',
            'entry_price': 75.0,
            'status': 'ACTIVE',
            'direction': 'LONG',
        }
        result = is_valid_active_pick(pick)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()