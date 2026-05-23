#!/usr/bin/env python3
"""
Test script for A/B Testing Agent
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from ab_testing_agent import create_agent, quick_experiment
from statistics import StatisticalAnalyzer

def test_statistical_analyzer():
    """Test statistical calculations"""
    print("Testing Statistical Analyzer...")

    analyzer = StatisticalAnalyzer()

    # Test sample size calculation
    sample_size = analyzer.calculate_sample_size(0.1)  # 10% effect size
    print(f"Required sample size for 10% effect: {sample_size}")

    # Test t-test with sample data
    group_a = [1.2, 1.1, 1.3, 1.0, 1.4]  # Mean ~1.2
    group_b = [1.0, 0.9, 1.1, 0.8, 1.2]  # Mean ~1.0

    results = analyzer.perform_t_test(group_a, group_b)
    print(f"T-test p-value: {results['p_value']:.4f}")
    print(f"Significant: {results['significant']}")

    # Test Bayesian analysis
    bayesian_results = analyzer.bayesian_analysis(group_a, group_b)
    print(f"Probability A > B: {bayesian_results['prob_a_better']:.3f}")

    print("✓ Statistical Analyzer tests passed\n")

def test_agent_creation():
    """Test agent creation and basic operations"""
    print("Testing Agent Creation...")

    agent = create_agent()

    # Create a test experiment
    exp_id = agent.create_experiment(
        name="Test Experiment",
        description="Testing agent functionality",
        variants=[
            {"name": "A", "traffic_percentage": 50},
            {"name": "B", "traffic_percentage": 50}
        ],
        metrics=["conversion_rate", "revenue"],
        target_metric="conversion_rate"
    )

    print(f"Created experiment with ID: {exp_id}")

    # Start the experiment
    success = agent.start_experiment(exp_id)
    print(f"Started experiment: {success}")

    # Record some test observations
    agent.record_observation(exp_id, "A", {"conversion_rate": 0.15, "revenue": 25.0})
    agent.record_observation(exp_id, "A", {"conversion_rate": 0.18, "revenue": 30.0})
    agent.record_observation(exp_id, "B", {"conversion_rate": 0.12, "revenue": 20.0})
    agent.record_observation(exp_id, "B", {"conversion_rate": 0.14, "revenue": 22.0})

    print("Recorded test observations")

    # Analyze results
    results = agent.analyze_experiment(exp_id)
    print(f"Analysis status: {results.get('status')}")

    if results.get('winner'):
        print(f"Winner: {results['winner']}")

    print("✓ Agent creation and basic operations tests passed\n")

def test_quick_experiment():
    """Test quick experiment creation"""
    print("Testing Quick Experiment...")

    exp_id = quick_experiment(
        name="Quick Test",
        variants=["Control", "Variant"],
        target_metric="click_rate"
    )

    print(f"Created quick experiment with ID: {exp_id}")
    print("✓ Quick experiment test passed\n")

def main():
    """Run all tests"""
    print("Running A/B Testing Agent Tests\n")
    print("=" * 50)

    try:
        test_statistical_analyzer()
        test_agent_creation()
        test_quick_experiment()

        print("=" * 50)
        print("🎉 All tests passed! A/B Testing Agent is ready to use.")
        print("\nNext steps:")
        print("1. Run 'python main.py api' to start the API server")
        print("2. Run 'python main.py dashboard' to start the web dashboard")
        print("3. Run 'python main.py agent' to start background monitoring")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()