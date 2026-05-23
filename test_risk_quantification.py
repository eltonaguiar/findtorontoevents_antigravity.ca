#!/usr/bin/env python3
"""
Risk Quantification Agent - Basic Test
=====================================
Simple test to verify the agent works correctly.
"""

import asyncio
from risk_quantification_agent import RiskQuantificationAgent, StressScenario

async def test_agent():
    """Test basic agent functionality"""
    print("🧪 Testing Risk Quantification Agent...")

    agent = RiskQuantificationAgent("redis://mock", "postgresql://mock")
    await agent.initialize()

    # Test VaR calculation
    var_result = agent.calculate_historical_var("BTC", confidence_level=0.95)
    print(".2%")

    # Test stress testing
    stress_result = agent.run_stress_test(StressScenario.MARKET_CRASH)
    print(".2%")

    # Test optimization
    optimal_weights = agent.optimize_portfolio(target_return=0.15)
    print(f"Optimal weights: {optimal_weights}")

    print("✅ Test completed successfully!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_agent())
    print("Result:", "PASS" if success else "FAIL")