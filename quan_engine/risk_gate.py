import sys, os
import numpy as np
from typing import List, Optional
from quan_engine import config

# Add ml_battleground to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from ml_battleground.shared.market_health import check_market_health, apply_health_gate, MarketHealth
from ml_battleground.shared.trade_filters import adaptive_threshold, atr_percentile_filter, volume_confirmation

class RiskGate:
    def __init__(self):
        self.active_positions = []  # List of TradeSetup objects currently open

    def kelly_size(self, win_rate: float, avg_win: float, avg_loss: float, mode: str) -> float:
        """Half-Kelly position sizing with per-mode caps."""
        if avg_loss == 0 or win_rate <= 0:
            return 0.0
        b = avg_win / abs(avg_loss)  # odds ratio
        kelly = (win_rate * b - (1 - win_rate)) / b
        half_kelly = kelly * config.KELLY_FRACTION
        cap = config.POSITION_CAPS.get(mode, 0.03)
        return max(0.0, min(half_kelly, cap))

    def check_capacity(self, mode: str) -> bool:
        """Check if we can take another position."""
        mode_count = sum(1 for p in self.active_positions if p.mode == mode)
        total = len(self.active_positions)
        return mode_count < config.MAX_CONCURRENT_PER_MODE and total < config.MAX_CONCURRENT_TOTAL

    def check_correlation(self, new_symbol: str, symbol_returns: dict) -> bool:
        """Check if new trade is too correlated with existing positions."""
        if not self.active_positions or new_symbol not in symbol_returns:
            return True
        new_returns = symbol_returns[new_symbol]
        for pos in self.active_positions:
            if pos.symbol in symbol_returns:
                existing_returns = symbol_returns[pos.symbol]
                min_len = min(len(new_returns), len(existing_returns))
                if min_len > 10:
                    corr = np.corrcoef(new_returns[-min_len:], existing_returns[-min_len:])[0, 1]
                    if abs(corr) > config.CORRELATION_THRESHOLD:
                        return False
        return True

    def evaluate(self, setup, fear_greed=50, btc_df=None, symbol_returns=None,
                 win_rate=0.6, avg_win=3.0, avg_loss=2.0) -> dict:
        """Full risk evaluation. Returns dict with 'approved', 'position_size', 'reason'."""
        result = {"approved": False, "position_size": 0.0, "reason": ""}

        # 1. Capacity check
        if not self.check_capacity(setup.mode):
            result["reason"] = f"Max positions reached for {setup.mode}"
            return result

        # 2. Correlation check
        if symbol_returns and not self.check_correlation(setup.symbol, symbol_returns):
            result["reason"] = f"{setup.symbol} too correlated with existing positions"
            return result

        # 3. Market health check (PROP FIRM MODE: must trade daily, can't sit idle)
        health, health_details = check_market_health(fear_greed, btc_df)
        # Prop firms require daily P&L — reduced sizing but NEVER zero
        if health == MarketHealth.PANIC:
            size_multiplier = 0.5  # 50% size during panic (was 10% — too aggressive)
        else:
            size_multiplier = 1.0

        # 4. Adaptive threshold check
        tp_dist = abs(setup.take_profit - setup.entry_price) / setup.entry_price
        sl_dist = abs(setup.stop_loss - setup.entry_price) / setup.entry_price
        min_conf = adaptive_threshold(tp_dist, sl_dist, config.ROUND_TRIP_COST_PCT)
        if setup.confidence < min_conf:
            result["reason"] = f"Confidence {setup.confidence:.3f} < threshold {min_conf:.3f}"
            return result

        # 5. Position sizing
        size = self.kelly_size(win_rate, avg_win, avg_loss, setup.mode)

        # Health-based scaling (PROP FIRM: reduced but never zero)
        if health == MarketHealth.PANIC:
            size *= size_multiplier  # 0.5 during panic
        elif health == MarketHealth.WARNING:
            size *= 0.5   # Was 0.25 — too restrictive for prop firms
        elif health == MarketHealth.CAUTION:
            size *= 0.75  # Was 0.50

        # Prop firm floor: always allow minimum position
        size = max(size, 0.01)  # 1% minimum position

        if size <= 0.001:
            result["reason"] = "Position size too small"
            return result

        result["approved"] = True
        result["position_size"] = round(size, 4)
        result["health"] = health.value
        result["min_confidence"] = min_conf
        return result

    def add_position(self, setup):
        self.active_positions.append(setup)

    def remove_position(self, symbol: str):
        self.active_positions = [p for p in self.active_positions if p.symbol != symbol]
