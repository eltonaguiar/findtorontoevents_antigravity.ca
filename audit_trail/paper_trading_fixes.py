#!/usr/bin/env python3
"""
Paper Trading Position Sizing Fixes
===================================
Reduces leverage, adds directional hedge, implements volatility-based sizing.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
import json
from datetime import datetime


@dataclass
class Position:
    symbol: str
    qty: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    leverage: float = 1.0
    
    @property
    def position_value(self) -> float:
        return abs(self.qty) * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.entry_price) * self.qty
    
    @property
    def unrealized_pct(self) -> float:
        return (self.unrealized_pnl / (self.entry_price * abs(self.qty))) * 100
    
    @property
    def risk_pct(self) -> float:
        if not self.stop_loss or self.stop_loss <= 0:
            return 0.05  # Default 5% if no stop
        risk_amount = abs(self.qty * (self.entry_price - self.stop_loss))
        return risk_amount / self.position_value if self.position_value > 0 else 0.05


class PositionFixer:
    """Fixes over-leverage and position sizing issues."""
    
    def __init__(self, account_value: float = 1000.0):
        self.account_value = account_value
        self.volatility_tiers = {
            "BTC": "LOW",
            "ETH": "LOW", 
            "SOL": "MEDIUM",
            "BNB": "MEDIUM",
            "XRP": "MEDIUM",
            "DOGE": "HIGH",
            "SHIB": "HIGH",
            "PEPE": "HIGH",
            "FET": "HIGH",
            "RENDER": "HIGH",
            "TON": "HIGH",
            "ADA": "HIGH",
            "AVAX": "HIGH",
            "LINK": "MEDIUM",
            "DOT": "HIGH",
            "DYDX": "HIGH",
            "SUI": "HIGH",
            "SEI": "HIGH"
        }
        
    def get_volatility_tier(self, symbol: str) -> str:
        base = symbol.replace("USDT", "").replace("USD", "").replace("PERP", "")
        return self.volatility_tiers.get(base, "HIGH")
    
    def calculate_fixed_position(self, symbol: str, entry: float, stop: float,
                                  direction: str = "LONG") -> Dict:
        """Calculate corrected position size based on risk parameters."""
        volatility = self.get_volatility_tier(symbol)
        
        # Volatility-based leverage limits
        leverage_limits = {
            "LOW": 5.0,      # BTC, ETH
            "MEDIUM": 3.0,   # SOL, BNB, etc
            "HIGH": 2.0      # Alts, meme coins
        }
        max_leverage = leverage_limits.get(volatility, 3.0)
        
        # Kelly sizing - quarter Kelly for safety
        kelly_pct = 0.25
        risk_per_trade = self.account_value * kelly_pct * 0.02
        
        # Calculate position
        risk_per_unit = abs(entry - stop)
        if risk_per_unit > 0:
            qty = risk_per_trade / risk_per_unit
            if direction == "SHORT":
                qty = -qty
            position_value = abs(qty) * entry
            margin_required = position_value / max_leverage
            
            return {
                "symbol": symbol,
                "direction": direction,
                "qty": abs(qty),
                "leverage": max_leverage,
                "margin": margin_required,
                "risk_pct": (risk_per_trade / self.account_value) * 100,
                "volatility_tier": volatility,
                "entry": entry,
                "stop": stop
            }
        return {}
    
    def generate_hedge_recommendation(self, current_positions: List[Position]) -> Dict:
        """Generate SHORT hedge to balance 100% LONG exposure."""
        total_long_exposure = sum(p.position_value for p in current_positions if p.qty > 0)
        hedge_pct = 0.15  # 15% hedge
        hedge_value = total_long_exposure * hedge_pct
        
        return {
            "action": "OPEN_SHORT_HEDGE",
            "recommended_size_usd": hedge_value,
            "suggested_instrument": "BTCUSDT-PERP",
            "leverage": 2.0,
            "rationale": f"Current portfolio is 100% LONG. Adding {hedge_pct*100:.0f}% SHORT hedge to reduce directional bias",
            "note": "Reduces portfolio beta to market moves"
        }


def main():
    fixer = PositionFixer(account_value=996.13)
    
    # Current portfolio (from analysis)
    current_positions = [
        Position("BTCUSDT", 0.00284, 74302.0, 74458.89, 72900.0, None, 10.0),
        Position("ETHUSDT", 0.0405, 3524.0, 3533.89, 3450.0, None, 10.0),
        Position("SOLUSDT", 0.315, 138.0, 138.45, 134.0, None, 10.0),
        Position("BNBUSDT", 0.115, 592.7, 594.82, 580.0, None, 10.0),
        Position("LINKUSDT", 0.85, 13.48, 13.63, 13.20, None, 10.0),
        Position("FETUSDT", 15.0, 0.619, 0.618, 0.595, None, 10.0),
        Position("RENDERUSDT", 2.5, 4.45, 4.48, 4.30, None, 10.0),
        Position("DYDXUSDT", 12.0, 0.847, 0.764, 0.820, None, 10.0)
    ]
    
    # Generate fixed positions
    fixed = []
    for pos in current_positions:
        stop = pos.stop_loss if pos.stop_loss else pos.entry_price * 0.95
        fixed_pos = fixer.calculate_fixed_position(pos.symbol, pos.entry_price, stop, "LONG")
        fixed.append(fixed_pos)
    
    # Generate hedge
    hedge = fixer.generate_hedge_recommendation(current_positions)
    
    # Summary
    print("=" * 60)
    print("PAPER TRADING POSITION FIXES")
    print("=" * 60)
    print(f"\nOriginal: 8 positions, 10x leverage on all")
    print(f"Fixed: Reduced leverage based on volatility tiers")
    print(f"\nNew Position Sizing:")
    for pos in fixed:
        print(f"  {pos['symbol']}: {pos['leverage']:.1f}x ({pos['volatility_tier']} vol)")
    
    print(f"\nHedge Recommendation:")
    print(f"  {hedge['action']}: ${hedge['recommended_size_usd']:.2f}")
    print(f"  Instrument: {hedge['suggested_instrument']}")
    print(f"  Leverage: {hedge['leverage']}x")
    print(f"  Rationale: {hedge['rationale']}")
    
    # Save fixes
    output = {
        "timestamp": datetime.now().isoformat(),
        "account_value": fixer.account_value,
        "original_positions": 8,
        "fixed_positions": fixed,
        "hedge_recommendation": hedge
    }
    
    with open("audit_trail/paper_trading_fixes.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n[OK] Fixes saved to audit_trail/paper_trading_fixes.json")


if __name__ == "__main__":
    main()
