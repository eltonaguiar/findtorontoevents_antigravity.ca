#!/usr/bin/env python3
"""
Baby Strategy Adapter — wraps baby_strategies (generate_signals() → List[Signal])
into the verified_strategies run(dataframe, capital) → (equity_curve, trades) interface.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


class BabyStrategyAdapter:
    """
    Wraps any baby_strategy with a generate_signals(data, symbol) method.

    The baby strategy generates ONE signal per call (current bar's opinion).
    This adapter walks bar-by-bar, generates signals, and simulates TP/SL exits.
    """

    def __init__(self, strategy, name: str = "BabyStrategy", max_hold_bars: int = 15):
        self.strategy = strategy
        self.name = name
        self.max_hold_bars = max_hold_bars

    def run(self, market_data: pd.DataFrame, capital: float = 100000) -> Tuple[pd.Series, List[Dict]]:
        symbol = market_data.attrs.get('symbol', 'UNKNOWN')
        min_bars = getattr(self.strategy, 'sma_period', 200) + 20

        if len(market_data) < min_bars:
            return pd.Series([capital] * len(market_data), index=market_data.index), []

        equity_curve = [capital]
        trades = []
        position = None  # {entry_price, entry_bar, tp, sl, direction}

        for i in range(min_bars, len(market_data)):
            window = market_data.iloc[:i + 1]
            bar_open = float(window['open'].iloc[-1])
            bar_high = float(window['high'].iloc[-1])
            bar_low = float(window['low'].iloc[-1])
            bar_close = float(window['close'].iloc[-1])
            prev_close = float(market_data['close'].iloc[i - 1])

            exited_this_bar = False  # block same-bar re-entry after TP/SL/EXPIRE
            # Check for TP/SL/expiry on open position
            if position is not None:
                exit_price = None
                exit_reason = None

                if position['direction'] == 'BUY':
                    if bar_low <= position['sl']:
                        exit_price = position['sl']
                        exit_reason = 'SL'
                    elif bar_high >= position['tp']:
                        exit_price = position['tp']
                        exit_reason = 'TP'
                else:  # SELL
                    if bar_high >= position['sl']:
                        exit_price = position['sl']
                        exit_reason = 'SL'
                    elif bar_low <= position['tp']:
                        exit_price = position['tp']
                        exit_reason = 'TP'

                # Max hold expiry
                bars_held = i - position['entry_bar']
                if exit_price is None and bars_held >= self.max_hold_bars:
                    exit_price = bar_close
                    exit_reason = 'EXPIRE'

                if exit_price is not None:
                    if position['direction'] == 'BUY':
                        pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                    else:
                        pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']

                    pnl = pnl_pct * capital
                    trades.append({
                        'entry_date': market_data.index[position['entry_bar']],
                        'exit_date': market_data.index[i],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'exit_reason': exit_reason,
                        'bars_held': bars_held,
                    })
                    position = None
                    exited_this_bar = True

            # Generate new signal if flat — but NOT on the same bar an exit occurred.
            # Without this guard, persistent BUY/SELL signals re-enter every bar,
            # inflating trade counts and polluting Monte Carlo / Sharpe estimates.
            # (Identified by gx10 zoo session 2026-06-02 as the baby_strategy adapter
            # dedup bug; proven Sharpe 2.06 Keltner MR was reading as Rejected.)
            if position is None and not exited_this_bar:
                try:
                    signals = self.strategy.generate_signals(window, symbol)
                except Exception:
                    signals = []

                for sig in signals:
                    if sig.direction in ('BUY', 'SELL'):
                        position = {
                            'entry_price': sig.entry_price,
                            'entry_bar': i,
                            'tp': sig.take_profit,
                            'sl': sig.stop_loss,
                            'direction': sig.direction,
                        }
                        break

            # Daily mark-to-market
            if position is not None:
                if position['direction'] == 'BUY':
                    pnl_pct = (bar_close - prev_close) / prev_close
                else:
                    pnl_pct = (prev_close - bar_close) / prev_close
                new_equity = equity_curve[-1] * (1 + pnl_pct)
            else:
                new_equity = equity_curve[-1]

            equity_curve.append(new_equity)

        return pd.Series(equity_curve, index=market_data.index[min_bars - 1:]), trades
