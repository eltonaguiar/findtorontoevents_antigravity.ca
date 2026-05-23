"""
Strategy 050: Triangular Arbitrage
Cross-exchange triangular arbitrage
"""
from dataclasses import dataclass
from typing import Dict
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class TriangularArbitrageStrategy:
    """
    Detects triangular arbitrage opportunities.
    Example: BTC -> ETH -> USDT -> BTC
    """
    
    def __init__(
        self,
        min_profit_pct: float = 0.001,
        max_slippage: float = 0.0005,
        fee_rate: float = 0.001
    ):
        self.min_profit = min_profit_pct
        self.max_slippage = max_slippage
        self.fee_rate = fee_rate
    
    def analyze(
        self,
        rates: Dict[str, float]  # {pair: price, ...}
    ) -> Signal:
        """
        Analyze for triangular arb opportunities.
        Expected pairs: BTC/USDT, ETH/USDT, BTC/ETH
        """
        required_pairs = ["BTC/USDT", "ETH/USDT", "BTC/ETH"]
        
        for pair in required_pairs:
            if pair not in rates:
                return Signal("hold", 0.0, {"error": f"Missing pair: {pair}"})
        
        btc_usdt = rates["BTC/USDT"]
        eth_usdt = rates["ETH/USDT"]
        btc_eth = rates["BTC/ETH"]
        
        # Path 1: BTC -> ETH -> USDT -> BTC
        # Start with 1 BTC
        btc_amount = 1.0
        eth_amount = btc_amount * btc_eth * (1 - self.fee_rate)
        usdt_amount = eth_amount * eth_usdt * (1 - self.fee_rate)
        btc_final_1 = usdt_amount / btc_usdt * (1 - self.fee_rate)
        profit_1 = (btc_final_1 - btc_amount) / btc_amount
        
        # Path 2: BTC -> USDT -> ETH -> BTC
        usdt_amount = btc_amount * btc_usdt * (1 - self.fee_rate)
        eth_amount = usdt_amount / eth_usdt * (1 - self.fee_rate)
        btc_final_2 = eth_amount / btc_eth * (1 - self.fee_rate)
        profit_2 = (btc_final_2 - btc_amount) / btc_amount
        
        # Implied rates check
        implied_btc_eth = btc_usdt / eth_usdt
        deviation = (btc_eth - implied_btc_eth) / implied_btc_eth
        
        metadata = {
            "btc_usdt": btc_usdt,
            "eth_usdt": eth_usdt,
            "btc_eth": btc_eth,
            "implied_btc_eth": implied_btc_eth,
            "deviation": deviation,
            "profit_path1": profit_1,
            "profit_path2": profit_2
        }
        
        # Check for profitable arb
        best_profit = max(profit_1, profit_2)
        
        if profit_1 > self.min_profit:
            confidence = min(0.9, 0.6 + profit_1 * 100)
            return Signal("buy", confidence, {**metadata, "reason": "Triangular arb path 1 profitable", "path": 1})
        
        if profit_2 > self.min_profit:
            confidence = min(0.9, 0.6 + profit_2 * 100)
            return Signal("buy", confidence, {**metadata, "reason": "Triangular arb path 2 profitable", "path": 2})
        
        # Significant deviation but not profitable after fees
        if abs(deviation) > 0.005:
            return Signal("hold", 0.4, {**metadata, "reason": "Rate deviation detected"})
        
        return Signal("hold", 0.1, metadata)


if __name__ == "__main__":
    # Normal rates
    rates = {
        "BTC/USDT": 40000,
        "ETH/USDT": 2200,
        "BTC/ETH": 18.2  # Should be ~18.18
    }
    
    # Create small arb opportunity
    rates["BTC/ETH"] = 18.5  # Overpriced
    
    strategy = TriangularArbitrageStrategy()
    signal = strategy.analyze(rates)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
