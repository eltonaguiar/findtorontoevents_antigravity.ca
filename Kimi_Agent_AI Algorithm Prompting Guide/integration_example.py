"""
Integration Example: Keltner/RSI + On-Chain Confidence Boost
=============================================================

This example shows how to integrate the on-chain data module with your
existing Battleground Keltner/RSI confluence system.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import the on-chain module
from onchain_data_module import OnChainDataProvider, SignalEnhancer, OnChainSignal


@dataclass
class TechnicalSignal:
    """Your existing technical signal structure"""
    symbol: str
    timestamp: datetime
    signal: str  # "buy" or "sell"
    confidence: float  # 0-1 from Keltner/RSI confluence
    keltner_position: str  # "above_upper", "below_lower", "inside"
    rsi_value: float
    entry_price: float
    stop_loss: float
    take_profit: float


class KeltnerOnChainStrategy:
    """
    Complete trading strategy combining:
    - Keltner Channels (trend/momentum)
    - RSI (mean reversion)
    - On-chain data (confidence boost)
    """

    def __init__(
        self,
        whale_alert_api_key: str = None,
        glassnode_api_key: str = None,
        min_confidence_threshold: float = 0.55,
        max_position_size: float = 1.25,
    ):
        # Initialize on-chain provider
        self.onchain = OnChainDataProvider(
            whale_alert_api_key=whale_alert_api_key,
            glassnode_api_key=glassnode_api_key,
        )

        # Initialize signal enhancer
        self.enhancer = SignalEnhancer(self.onchain)

        # Strategy parameters
        self.min_confidence = min_confidence_threshold
        self.max_position = max_position_size

        # Performance tracking
        self.signals_generated = 0
        self.signals_executed = 0
        self.onchain_boosts_applied = 0

    def generate_signal(
        self,
        symbol: str,
        ohlcv_df: pd.DataFrame,
        keltner_period: int = 20,
        keltner_multiplier: float = 2.0,
        rsi_period: int = 14,
    ) -> Dict:
        """
        Generate enhanced trading signal combining technical and on-chain analysis.

        Args:
            symbol: Trading pair (e.g., "BTC")
            ohlcv_df: DataFrame with OHLCV data
            keltner_period: Keltner channel period
            keltner_multiplier: ATR multiplier for Keltner
            rsi_period: RSI calculation period

        Returns:
            Complete signal dictionary with position sizing
        """
        # Calculate technical indicators
        tech_signal = self._calculate_technical_signal(
            ohlcv_df, keltner_period, keltner_multiplier, rsi_period
        )

        # Enhance with on-chain data
        enhanced = self.enhancer.enhance_signal(
            symbol=symbol,
            base_signal=tech_signal["signal"],
            base_confidence=tech_signal["confidence"],
        )

        self.signals_generated += 1

        if enhanced["execute"]:
            self.signals_executed += 1

        if enhanced["onchain_confidence"] > 0.6:
            self.onchain_boosts_applied += 1

        return {
            "symbol": symbol,
            "timestamp": datetime.now(),
            "technical": tech_signal,
            "onchain": {
                "confidence": enhanced["onchain_confidence"],
                "whale_score": enhanced["whale_score"],
                "exchange_score": enhanced["exchange_score"],
                "evidence": enhanced["evidence"],
                "warnings": enhanced["warnings"],
            },
            "combined": {
                "confidence": enhanced["combined_confidence"],
                "position_size": enhanced["position_size_pct"],
                "expected_value": enhanced["expected_value"],
                "execute": enhanced["execute"],
            },
            "risk_management": self._calculate_risk_params(
                tech_signal, enhanced["position_size_pct"]
            ),
        }

    def _calculate_technical_signal(
        self,
        df: pd.DataFrame,
        keltner_period: int,
        keltner_multiplier: float,
        rsi_period: int,
    ) -> Dict:
        """Calculate Keltner/RSI confluence signal"""

        # Calculate Keltner Channels
        df["atr"] = self._calculate_atr(df, keltner_period)
        df["ema"] = df["close"].ewm(span=keltner_period).mean()
        df["upper_band"] = df["ema"] + (df["atr"] * keltner_multiplier)
        df["lower_band"] = df["ema"] - (df["atr"] * keltner_multiplier)

        # Calculate RSI
        df["rsi"] = self._calculate_rsi(df["close"], rsi_period)

        # Get latest values
        latest = df.iloc[-1]
        price = latest["close"]
        upper = latest["upper_band"]
        lower = latest["lower_band"]
        ema = latest["ema"]
        rsi = latest["rsi"]

        # Determine signal
        signal = "neutral"
        confidence = 0.5
        keltner_pos = "inside"

        # Price above upper band + RSI < 70 = potential short
        if price > upper and rsi > 50:
            signal = "sell"
            keltner_pos = "above_upper"
            # Higher RSI = stronger signal (but not overbought)
            confidence = 0.5 + (min(rsi, 70) - 50) / 40

        # Price below lower band + RSI > 30 = potential long
        elif price < lower and rsi < 50:
            signal = "buy"
            keltner_pos = "below_lower"
            # Lower RSI = stronger signal (but not oversold)
            confidence = 0.5 + (50 - max(rsi, 30)) / 40

        # Price near EMA + RSI near 50 = neutral
        elif abs(price - ema) / ema < 0.01:
            confidence = 0.3

        return {
            "signal": signal,
            "confidence": min(confidence, 0.85),  # Cap technical confidence
            "keltner_position": keltner_pos,
            "rsi_value": rsi,
            "entry_price": price,
            "indicators": {
                "upper_band": upper,
                "lower_band": lower,
                "ema": ema,
                "atr": latest["atr"],
            }
        }

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)

        return true_range.rolling(period).mean()

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_risk_params(
        self, 
        tech_signal: Dict, 
        position_size: float
    ) -> Dict:
        """Calculate risk management parameters"""

        entry = tech_signal["entry_price"]
        atr = tech_signal["indicators"]["atr"]

        # Stop loss: 2 ATR for normal, 1.5 ATR for high confidence
        if tech_signal["confidence"] > 0.7:
            stop_distance = 1.5 * atr
        else:
            stop_distance = 2.0 * atr

        if tech_signal["signal"] == "buy":
            stop_loss = entry - stop_distance
            take_profit = entry + (stop_distance * 2)  # 2:1 R/R
        else:
            stop_loss = entry + stop_distance
            take_profit = entry - (stop_distance * 2)

        return {
            "entry_price": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_amount": stop_distance,
            "risk_reward_ratio": 2.0,
            "position_size_pct": position_size,
        }

    def get_stats(self) -> Dict:
        """Get strategy statistics"""
        return {
            "signals_generated": self.signals_generated,
            "signals_executed": self.signals_executed,
            "execution_rate": (
                self.signals_executed / self.signals_generated 
                if self.signals_generated > 0 else 0
            ),
            "onchain_boosts": self.onchain_boosts_applied,
            "api_usage": self.onchain.get_api_usage_stats(),
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_backtest():
    """
    Example of running a backtest with the enhanced strategy.

    This shows how the on-chain data can improve your existing
    Keltner/RSI system.
    """

    # Create sample OHLCV data (replace with your actual data)
    np.random.seed(42)
    n = 1000

    # Generate synthetic price data
    price = 50000
    prices = []
    for i in range(n):
        price *= (1 + np.random.normal(0, 0.02))
        prices.append(price)

    df = pd.DataFrame({
        "open": prices,
        "high": [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        "low": [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        "close": [p * (1 + np.random.normal(0, 0.005)) for p in prices],
        "volume": np.random.uniform(1000, 10000, n),
    })

    # Initialize strategy
    strategy = KeltnerOnChainStrategy(
        whale_alert_api_key=None,  # Add your key
        glassnode_api_key=None,    # Add your key
    )

    # Generate signal
    signal = strategy.generate_signal(
        symbol="BTC",
        ohlcv_df=df,
        keltner_period=20,
        keltner_multiplier=2.0,
        rsi_period=14,
    )

    # Print results
    print("\n" + "="*70)
    print("ENHANCED SIGNAL RESULT")
    print("="*70)

    print(f"\n📊 Technical Analysis:")
    print(f"  Signal: {signal['technical']['signal'].upper()}")
    print(f"  Confidence: {signal['technical']['confidence']:.1%}")
    print(f"  RSI: {signal['technical']['rsi_value']:.1f}")
    print(f"  Keltner Position: {signal['technical']['keltner_position']}")

    print(f"\n🔗 On-Chain Analysis:")
    print(f"  Confidence: {signal['onchain']['confidence']:.1%}")
    print(f"  Whale Score: {signal['onchain']['whale_score']:.1%}")
    print(f"  Exchange Score: {signal['onchain']['exchange_score']:.1%}")

    if signal['onchain']['evidence']:
        print(f"  Evidence:")
        for e in signal['onchain']['evidence']:
            print(f"    + {e}")

    if signal['onchain']['warnings']:
        print(f"  Warnings:")
        for w in signal['onchain']['warnings']:
            print(f"    ! {w}")

    print(f"\n🎯 Combined Signal:")
    print(f"  Confidence: {signal['combined']['confidence']:.1%}")
    print(f"  Position Size: {signal['combined']['position_size']:.0%}")
    print(f"  Expected Value: {signal['combined']['expected_value']:.3f}R")
    print(f"  Execute: {'✅ YES' if signal['combined']['execute'] else '❌ NO'}")

    print(f"\n💰 Risk Management:")
    rm = signal['risk_management']
    print(f"  Entry: ${rm['entry_price']:,.2f}")
    print(f"  Stop Loss: ${rm['stop_loss']:,.2f}")
    print(f"  Take Profit: ${rm['take_profit']:,.2f}")
    print(f"  Risk/Reward: 1:{rm['risk_reward_ratio']}")

    print(f"\n📈 Strategy Stats:")
    stats = strategy.get_stats()
    print(f"  Signals Generated: {stats['signals_generated']}")
    print(f"  Execution Rate: {stats['execution_rate']:.1%}")

    return signal


if __name__ == "__main__":
    # Run example
    result = example_backtest()
