# METHODOLOGY WARNING 2026-05-31: This module filters OUT TIME_EXIT trades (zero-pnl median outcomes) before computing metrics.
# That is survivorship bias by selection. Reported PF/EV are INFLATED 5-30x vs. actual forward outcomes.
# The module's own permutation p-values (commodity p=0.999, crypto_mega p=1.000, crypto_pma p=0.66, forex p=0.41) refute the PROMISING verdict.
# Do NOT use for live capital sizing. Research artifact only. See reports/peer_claude-FORCED_RESOLUTION_SURVIVORSHIP_BIAS_2026-05-31.md
"""Forced-Resolution Strategy Wrapper.

Solves the #1 edge killer: TIME_EXIT saturation (85-97% of trades exit at 0% PnL).

Approach:
  1. Take any existing strategy that generates picks
  2. Set aggressive TP/SL based on ATR or fixed percentage
  3. Set max hold period (force resolution within N hours)
  4. If TP/SL not hit within max_hold, close at market price (not TIME_EXIT=0%)

This converts dead TIME_EXIT trades into actual wins/losses with real PnL.

Usage:
    from alpha_engine.forced_resolution import ForcedResolutionWrapper
    wrapper = ForcedResolutionWrapper(max_hold_hours=48, tp_atr_mult=2.0, sl_atr_mult=1.5)
    resolved_picks = wrapper.resolve(open_picks, price_data)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent


class ForcedResolutionWrapper:
    """Wraps any strategy to force resolution within max_hold_hours.
    
    Instead of TIME_EXIT with 0% PnL, this wrapper:
    - Sets tight TP/SL based on ATR or fixed %
    - Forces close at market price if max_hold exceeded
    - Tracks actual PnL for every trade (no more zeros)
    """
    
    def __init__(
        self,
        max_hold_hours: int = 48,
        tp_pct: float = 2.0,
        sl_pct: float = 1.5,
        use_atr: bool = False,
        atr_period: int = 14,
        tp_atr_mult: float = 2.0,
        sl_atr_mult: float = 1.5,
    ):
        self.max_hold_hours = max_hold_hours
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.use_atr = use_atr
        self.atr_period = atr_period
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult
    
    def compute_atr(self, highs: List[float], lows: List[float], closes: List[float]) -> float:
        """Compute Average True Range."""
        if len(highs) < self.atr_period + 1:
            return 0.0
        trs = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            trs.append(tr)
        return sum(trs[-self.atr_period:]) / self.atr_period
    
    def set_tp_sl(
        self,
        entry_price: float,
        direction: str,
        atr: Optional[float] = None,
    ) -> Dict[str, float]:
        """Compute TP/SL for a pick.
        
        Args:
            entry_price: Entry price
            direction: LONG, SHORT, BUY, SELL
            atr: Optional ATR value for dynamic sizing
            
        Returns:
            Dict with take_profit, stop_loss, tp_pct, sl_pct
        """
        if self.use_atr and atr and atr > 0:
            tp_dist = atr * self.tp_atr_mult
            sl_dist = atr * self.sl_atr_mult
        else:
            tp_dist = entry_price * self.tp_pct / 100
            sl_dist = entry_price * self.sl_pct / 100
        
        is_long = direction.upper() in ('LONG', 'BUY')
        
        if is_long:
            tp = entry_price + tp_dist
            sl = entry_price - sl_dist
        else:
            tp = entry_price - tp_dist
            sl = entry_price + sl_dist
        
        return {
            'take_profit': round(tp, 8),
            'stop_loss': round(sl, 8),
            'tp_pct': round(self.tp_pct if not self.use_atr else (tp_dist / entry_price * 100), 2),
            'sl_pct': round(self.sl_pct if not self.use_atr else (sl_dist / entry_price * 100), 2),
            'max_hold_hours': self.max_hold_hours,
        }
    
    def resolve_pick(
        self,
        pick: Dict[str, Any],
        current_price: float,
        hours_held: float,
    ) -> Optional[Dict[str, Any]]:
        """Check if a pick should be resolved.
        
        Returns resolved pick with PnL, or None if still open.
        """
        entry = pick.get('entry_price', 0)
        tp = pick.get('take_profit', 0)
        sl = pick.get('stop_loss', 0)
        direction = pick.get('direction', 'LONG').upper()
        is_long = direction in ('LONG', 'BUY')
        
        if not entry or not current_price:
            return None
        
        # Compute PnL
        if is_long:
            pnl_pct = (current_price - entry) / entry * 100
        else:
            pnl_pct = (entry - current_price) / entry * 100
        
        # Check TP hit
        if tp and ((is_long and current_price >= tp) or (not is_long and current_price <= tp)):
            return {
                **pick,
                'exit_price': current_price,
                'pnl_pct': round(pnl_pct, 4),
                'status': 'TP_HIT',
                'exit_reason': 'forced_resolution_tp',
                'hours_held': round(hours_held, 1),
            }
        
        # Check SL hit
        if sl and ((is_long and current_price <= sl) or (not is_long and current_price >= sl)):
            return {
                **pick,
                'exit_price': current_price,
                'pnl_pct': round(pnl_pct, 4),
                'status': 'SL_HIT',
                'exit_reason': 'forced_resolution_sl',
                'hours_held': round(hours_held, 1),
            }
        
        # Check max hold exceeded — close at market (NOT TIME_EXIT=0%)
        if hours_held >= self.max_hold_hours:
            return {
                **pick,
                'exit_price': current_price,
                'pnl_pct': round(pnl_pct, 4),
                'status': 'MARKET_EXIT',
                'exit_reason': 'forced_resolution_max_hold',
                'hours_held': round(hours_held, 1),
            }
        
        return None  # Still open


# Per-asset-class default configs (based on analysis)
ASSET_CLASS_CONFIGS = {
    'CRYPTO': {
        'max_hold_hours': 72,
        'tp_pct': 5.0,
        'sl_pct': 3.0,
    },
    'FOREX': {
        'max_hold_hours': 24,
        'tp_pct': 0.3,
        'sl_pct': 0.2,
    },
    'COMMODITY': {
        'max_hold_hours': 168,  # 1 week
        'tp_pct': 3.0,
        'sl_pct': 2.0,
    },
    'EQUITY': {
        'max_hold_hours': 72,
        'tp_pct': 3.0,
        'sl_pct': 2.0,
    },
    'ETF': {
        'max_hold_hours': 720,  # 30 days (Faber is monthly)
        'tp_pct': 5.0,
        'sl_pct': 3.0,
    },
    'BOND': {
        'max_hold_hours': 168,
        'tp_pct': 1.0,
        'sl_pct': 0.5,
    },
}


def get_wrapper_for_class(asset_class: str) -> ForcedResolutionWrapper:
    """Get a ForcedResolutionWrapper configured for the given asset class."""
    config = ASSET_CLASS_CONFIGS.get(asset_class.upper(), ASSET_CLASS_CONFIGS['CRYPTO'])
    return ForcedResolutionWrapper(**config)


if __name__ == '__main__':
    # Demo: set TP/SL for Faber ETF picks
    wrapper = get_wrapper_for_class('ETF')
    picks = [
        {'symbol': 'SPY', 'direction': 'LONG', 'entry_price': 756.48},
        {'symbol': 'QQQ', 'direction': 'LONG', 'entry_price': 738.31},
        {'symbol': 'IWM', 'direction': 'LONG', 'entry_price': 290.43},
    ]
    
    for pick in picks:
        tpsl = wrapper.set_tp_sl(pick['entry_price'], pick['direction'])
        pick.update(tpsl)
        print(f"{pick['symbol']} {pick['direction']} entry={pick['entry_price']} "
              f"TP={tpsl['take_profit']} SL={tpsl['stop_loss']} "
              f"max_hold={tpsl['max_hold_hours']}h")
