#!/usr/bin/env python3
"""
On-Chain Data Module Demo
=========================

This demo shows the on-chain data system in action with:
- Simulated whale transactions
- Mock exchange flows
- Confidence score calculations
- Integration with existing signals

Run this to verify the system works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
from typing import List
import random

# Import our module
from onchain_data_module import (
    OnChainDataProvider, 
    SignalEnhancer,
    WhaleTransaction,
    ExchangeFlow,
    FlowType,
    OnChainSignal,
    RateLimiter,
    Cache
)


class MockOnChainProvider(OnChainDataProvider):
    """
    Mock provider for demonstration without real API keys.
    Generates realistic simulated data.
    """

    def __init__(self, scenario: str = "bullish"):
        # Initialize without API keys
        super().__init__()
        self.scenario = scenario

    def get_whale_flows(
        self,
        symbol: str,
        min_value_usd: float = 10_000_000,
        hours_back: int = 24,
        blockchain: str = None
    ) -> List[WhaleTransaction]:
        """Generate mock whale transactions"""

        transactions = []
        now = datetime.now()

        # Generate transactions based on scenario
        if self.scenario == "bullish":
            # More outflows (accumulation)
            outflow_count = random.randint(5, 10)
            inflow_count = random.randint(1, 3)
        elif self.scenario == "bearish":
            # More inflows (distribution)
            outflow_count = random.randint(1, 3)
            inflow_count = random.randint(5, 10)
        else:  # neutral
            outflow_count = random.randint(2, 4)
            inflow_count = random.randint(2, 4)

        # Generate outflows (bullish)
        for i in range(outflow_count):
            tx = WhaleTransaction(
                tx_hash=f"outflow_{i}_{random.randint(1000, 9999)}",
                timestamp=now - timedelta(hours=random.randint(0, hours_back)),
                from_address=f"exchange_{random.randint(1, 5)}",
                to_address=f"whale_wallet_{random.randint(1, 20)}",
                amount=random.uniform(100, 1000),
                amount_usd=random.uniform(50_000_000, 150_000_000),
                symbol=symbol,
                blockchain="bitcoin" if symbol == "BTC" else "ethereum",
                flow_type=FlowType.EXCHANGE_OUTFLOW,
                from_entity="Binance",
                to_entity="Unknown Whale",
                confidence_score=random.uniform(0.7, 0.95),
            )
            transactions.append(tx)

        # Generate inflows (bearish)
        for i in range(inflow_count):
            tx = WhaleTransaction(
                tx_hash=f"inflow_{i}_{random.randint(1000, 9999)}",
                timestamp=now - timedelta(hours=random.randint(0, hours_back)),
                from_address=f"whale_wallet_{random.randint(1, 20)}",
                to_address=f"exchange_{random.randint(1, 5)}",
                amount=random.uniform(50, 500),
                amount_usd=random.uniform(20_000_000, 80_000_000),
                symbol=symbol,
                blockchain="bitcoin" if symbol == "BTC" else "ethereum",
                flow_type=FlowType.EXCHANGE_INFLOW,
                from_entity="Unknown Whale",
                to_entity="Coinbase",
                confidence_score=random.uniform(0.6, 0.85),
            )
            transactions.append(tx)

        # Add some staking transactions (should be filtered)
        for i in range(random.randint(1, 3)):
            tx = WhaleTransaction(
                tx_hash=f"stake_{i}_{random.randint(1000, 9999)}",
                timestamp=now - timedelta(hours=random.randint(0, hours_back)),
                from_address="0xwhale_wallet",
                to_address="0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",  # Lido
                amount=random.uniform(100, 500),
                amount_usd=random.uniform(30_000_000, 70_000_000),
                symbol=symbol,
                blockchain="ethereum",
                flow_type=FlowType.STAKING,
                from_entity="Whale",
                to_entity="Lido",
                confidence_score=0.0,  # Filtered out
            )
            transactions.append(tx)

        return transactions

    def get_exchange_flows(
        self,
        symbol: str,
        hours_back: int = 24,
        exchange: str = None
    ) -> List[ExchangeFlow]:
        """Generate mock exchange flows"""

        flows = []
        now = datetime.now().replace(minute=0, second=0, microsecond=0)

        for i in range(hours_back):
            timestamp = now - timedelta(hours=i)

            if self.scenario == "bullish":
                # Net outflow (positive)
                netflow = random.uniform(500, 2000)
            elif self.scenario == "bearish":
                # Net inflow (negative)
                netflow = random.uniform(-2000, -500)
            else:
                netflow = random.uniform(-500, 500)

            inflow = max(0, -netflow) + random.uniform(100, 500)
            outflow = max(0, netflow) + random.uniform(100, 500)

            flow = ExchangeFlow(
                exchange=exchange or "aggregated",
                timestamp=timestamp,
                inflow=inflow,
                outflow=outflow,
                netflow=netflow,
                inflow_usd=inflow * 50000,  # Approximate BTC price
                outflow_usd=outflow * 50000,
                netflow_usd=netflow * 50000,
                symbol=symbol,
            )
            flows.append(flow)

        return flows


def demo_basic_functionality():
    """Demo basic provider functionality"""
    print("\n" + "="*70)
    print("DEMO 1: Basic Provider Functionality")
    print("="*70)

    provider = MockOnChainProvider(scenario="bullish")

    # Get whale flows
    whales = provider.get_whale_flows("BTC", hours_back=24)

    print(f"\n📊 Whale Transactions (24h):")
    print(f"  Total: {len(whales)}")

    outflows = [w for w in whales if w.flow_type == FlowType.EXCHANGE_OUTFLOW]
    inflows = [w for w in whales if w.flow_type == FlowType.EXCHANGE_INFLOW]
    staking = [w for w in whales if w.flow_type == FlowType.STAKING]

    print(f"  Exchange Outflows (Bullish): {len(outflows)}")
    print(f"  Exchange Inflows (Bearish): {len(inflows)}")
    print(f"  Staking (Filtered): {len(staking)}")

    outflow_volume = sum(w.amount_usd for w in outflows)
    inflow_volume = sum(w.amount_usd for w in inflows)

    print(f"\n💰 Volume Analysis:")
    print(f"  Outflow Volume: ${outflow_volume:,.0f}")
    print(f"  Inflow Volume: ${inflow_volume:,.0f}")
    print(f"  Net Flow: ${outflow_volume - inflow_volume:,.0f}")


def demo_confidence_calculation():
    """Demo confidence score calculation"""
    print("\n" + "="*70)
    print("DEMO 2: Confidence Score Calculation")
    print("="*70)

    scenarios = ["bullish", "bearish", "neutral"]

    for scenario in scenarios:
        print(f"\n🎯 Scenario: {scenario.upper()}")

        provider = MockOnChainProvider(scenario=scenario)

        # Calculate for long signal
        long_signal = provider.calculate_confidence_boost(
            symbol="BTC",
            signal_direction="long",
            lookback_hours=24
        )

        # Calculate for short signal
        short_signal = provider.calculate_confidence_boost(
            symbol="BTC",
            signal_direction="short",
            lookback_hours=24
        )

        print(f"  Long Signal Confidence: {long_signal.combined_score:.1%}")
        print(f"    - Whale Score: {long_signal.whale_score:.1%}")
        print(f"    - Exchange Score: {long_signal.exchange_score:.1%}")

        print(f"  Short Signal Confidence: {short_signal.combined_score:.1%}")
        print(f"    - Whale Score: {short_signal.whale_score:.1%}")
        print(f"    - Exchange Score: {short_signal.exchange_score:.1%}")


def demo_signal_enhancement():
    """Demo signal enhancement with existing strategy"""
    print("\n" + "="*70)
    print("DEMO 3: Signal Enhancement Integration")
    print("="*70)

    provider = MockOnChainProvider(scenario="bullish")
    enhancer = SignalEnhancer(provider)

    # Simulate your Keltner/RSI signal
    test_cases = [
        {"signal": "buy", "confidence": 0.55, "desc": "Weak long signal"},
        {"signal": "buy", "confidence": 0.70, "desc": "Strong long signal"},
        {"signal": "sell", "confidence": 0.60, "desc": "Moderate short signal"},
    ]

    for case in test_cases:
        print(f"\n📈 {case['desc']}")
        print(f"  Base Confidence: {case['confidence']:.0%}")

        enhanced = enhancer.enhance_signal(
            symbol="BTC",
            base_signal=case["signal"],
            base_confidence=case["confidence"],
        )

        print(f"  On-Chain Boost: {enhanced['onchain_confidence']:.0%}")
        print(f"  Combined: {enhanced['combined_confidence']:.0%}")
        print(f"  Position Size: {enhanced['position_size_pct']:.0%}")
        print(f"  Execute: {'✅' if enhanced['execute'] else '❌'}")

        if enhanced['evidence']:
            print(f"  Evidence: {enhanced['evidence'][0]}")


def demo_false_positive_filtering():
    """Demo false positive filtering"""
    print("\n" + "="*70)
    print("DEMO 4: False Positive Filtering")
    print("="*70)

    provider = MockOnChainProvider(scenario="bullish")

    # Get all whale transactions
    all_whales = provider.get_whale_flows("BTC", hours_back=24)

    # Filter out false positives
    valid_whales = [
        w for w in all_whales 
        if w.flow_type not in [FlowType.STAKING, FlowType.OTC]
    ]

    filtered_count = len(all_whales) - len(valid_whales)

    print(f"\n🛡️ Filtering Results:")
    print(f"  Total Transactions: {len(all_whales)}")
    print(f"  Valid Signals: {len(valid_whales)}")
    print(f"  Filtered (False Positives): {filtered_count}")
    print(f"  Filter Rate: {filtered_count/len(all_whales)*100:.1f}%")

    print(f"\n📋 Filtered Types:")
    for ft in FlowType:
        count = sum(1 for w in all_whales if w.flow_type == ft)
        if count > 0:
            status = "✅ USED" if ft not in [FlowType.STAKING, FlowType.OTC] else "❌ FILTERED"
            print(f"  {ft.value}: {count} {status}")


def demo_api_rate_limiting():
    """Demo rate limiting functionality"""
    print("\n" + "="*70)
    print("DEMO 5: Rate Limiting & Caching")
    print("="*70)

    limiter = RateLimiter(calls_per_minute=10)
    cache = Cache(default_ttl_seconds=60)

    print(f"\n⏱️ Rate Limiter:")
    print(f"  Max Calls/Min: 10")
    print(f"  Min Interval: {limiter.min_interval:.2f}s")

    # Simulate API calls
    import time
    start = time.time()
    for i in range(5):
        limiter.wait()
        print(f"  Call {i+1}: OK")
    elapsed = time.time() - start
    print(f"  Total time: {elapsed:.2f}s")

    print(f"\n💾 Cache Demo:")
    cache.set("test_value", 60, "key1", "key2")
    cached = cache.get("key1", "key2")
    print(f"  Set value: test_value")
    print(f"  Get value: {cached}")
    print(f"  Cache hits: Immediate")


def demo_complete_workflow():
    """Demo complete trading workflow"""
    print("\n" + "="*70)
    print("DEMO 6: Complete Trading Workflow")
    print("="*70)

    provider = MockOnChainProvider(scenario="bullish")
    enhancer = SignalEnhancer(provider)

    print("\n🔄 Simulating Trading Day...")

    # Simulate multiple signals throughout the day
    signals = [
        {"time": "09:00", "symbol": "BTC", "signal": "buy", "conf": 0.60},
        {"time": "11:30", "symbol": "ETH", "signal": "buy", "conf": 0.55},
        {"time": "14:00", "symbol": "BTC", "signal": "sell", "conf": 0.50},
        {"time": "16:30", "symbol": "BTC", "signal": "buy", "conf": 0.75},
    ]

    executed = 0
    skipped = 0

    for sig in signals:
        enhanced = enhancer.enhance_signal(
            symbol=sig["symbol"],
            base_signal=sig["signal"],
            base_confidence=sig["conf"],
        )

        status = "✅ EXECUTE" if enhanced["execute"] else "❌ SKIP"
        size = enhanced["position_size_pct"]

        print(f"\n  {sig['time']} {sig['symbol']} {sig['signal'].upper()}")
        print(f"    Base: {sig['conf']:.0%} | On-Chain: {enhanced['onchain_confidence']:.0%}")
        print(f"    Combined: {enhanced['combined_confidence']:.0%} | Size: {size:.0%}")
        print(f"    → {status}")

        if enhanced["execute"]:
            executed += 1
        else:
            skipped += 1

    print(f"\n📊 Day Summary:")
    print(f"  Signals: {len(signals)}")
    print(f"  Executed: {executed}")
    print(f"  Skipped: {skipped}")
    print(f"  Execution Rate: {executed/len(signals)*100:.0f}%")


def run_all_demos():
    """Run all demonstrations"""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + "   ON-CHAIN DATA MODULE DEMONSTRATION".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70)

    demo_basic_functionality()
    demo_confidence_calculation()
    demo_signal_enhancement()
    demo_false_positive_filtering()
    demo_api_rate_limiting()
    demo_complete_workflow()

    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + "   ALL DEMOS COMPLETED SUCCESSFULLY".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70 + "\n")


if __name__ == "__main__":
    run_all_demos()
