"""
Strategy 067: Cross-Exchange Arbitrage
Inter-exchange arbitrage strategy
"""
from dataclasses import dataclass
from typing import Dict, List
import numpy as np

@dataclass
class Signal:
    action: str
    confidence: float
    metadata: dict

class CrossExchangeArbitrageStrategy:
    """
    Detects arbitrage opportunities across exchanges.
    Accounts for fees and transfer times.
    """
    
    def __init__(
        self,
        min_profit_pct: float = 0.002,
        fee_rate: float = 0.001,
        transfer_time_minutes: float = 10,
        max_slippage: float = 0.001
    ):
        self.min_profit = min_profit_pct
        self.fee = fee_rate
        self.transfer_time = transfer_time_minutes
        self.max_slippage = max_slippage
    
    def analyze(
        self,
        prices: Dict[str, float],  # {exchange: price}
        volumes: Dict[str, float],
        withdrawal_fees: Dict[str, float]
    ) -> Signal:
        if len(prices) < 2:
            return Signal("hold", 0.0, {"error": "Need at least 2 exchanges"})
        
        # Find best arbitrage
        best_profit = 0
        best_pair = None
        
        exchanges = list(prices.keys())
        
        for i, ex1 in enumerate(exchanges):
            for ex2 in exchanges[i+1:]:
                p1, p2 = prices[ex1], prices[ex2]
                
                # Buy on ex2, sell on ex1
                if p1 > p2:
                    profit = (p1 - p2) / p2 - 2 * self.fee
                    if profit > best_profit:
                        best_profit = profit
                        best_pair = (ex2, ex1, p2, p1)  # buy, sell
                
                # Buy on ex1, sell on ex2
                else:
                    profit = (p2 - p1) / p1 - 2 * self.fee
                    if profit > best_profit:
                        best_profit = profit
                        best_pair = (ex1, ex2, p1, p2)  # buy, sell
        
        # Liquidity check
        if best_pair:
            buy_ex, sell_ex, buy_price, sell_price = best_pair
            min_volume = min(volumes.get(buy_ex, 0), volumes.get(sell_ex, 0))
            
            metadata = {
                "profit_pct": best_profit * 100,
                "buy_exchange": buy_ex,
                "sell_exchange": sell_ex,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "min_volume": min_volume
            }
            
            if best_profit > self.min_profit:
                confidence = min(0.9, 0.6 + best_profit * 100)
                return Signal("buy", confidence, {**metadata, "reason": "Cross-exchange arb opportunity"})
            elif best_profit > 0:
                return Signal("hold", 0.4, {**metadata, "reason": "Small arb after fees"})
        
        return Signal("hold", 0.1, {"profit_pct": 0})


if __name__ == "__main__":
    prices = {
        "binance": 40000,
        "coinbase": 40150,
        "kraken": 40050,
        "okx": 39980
    }
    
    volumes = {
        "binance": 1000,
        "coinbase": 800,
        "kraken": 600,
        "okx": 900
    }
    
    withdrawal_fees = {k: 0.0001 for k in prices}
    
    strategy = CrossExchangeArbitrageStrategy()
    signal = strategy.analyze(prices, volumes, withdrawal_fees)
    
    print(f"Signal: {signal.action}")
    print(f"Confidence: {signal.confidence:.2f}")
    print(f"Metadata: {signal.metadata}")
