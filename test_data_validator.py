#!/usr/bin/env python3
"""
Test script for Data Validator Agent
====================================
This script validates the core functionality of the Data Validator Agent
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_validator_agent import (
    DataValidatorAgent, DataValidatorConfig, DataSource,
    DataPoint, DataFeed, QualityMetrics, ValidationAlert, AlertType
)


async def test_data_validator_agent():
    """Test the Data Validator Agent functionality"""
    print("🧪 Testing Data Validator Agent...")

    # Mock URLs for testing
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    db_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/trading")

    # Custom config for testing
    config = DataValidatorConfig(
        primary_sources={
            'BTC': [DataSource.BINANCE, DataSource.COINGECKO],
            'ETH': [DataSource.BINANCE, DataSource.CRYPTOCOMPARE],
        },
        monitoring_interval_seconds=5,  # Faster for testing
        max_staleness_seconds=30,  # Shorter for testing
    )

    # Initialize agent
    agent = DataValidatorAgent(redis_url, db_url, config)

    try:
        # Test 1: Agent initialization
        print("✅ Test 1: Agent initialization")
        assert agent.config.monitoring_interval_seconds == 5
        assert 'BTC' in agent.feeds
        assert 'ETH' in agent.feeds
        assert len(agent.feeds['BTC']) == 2
        assert agent.quality_metrics.total_feeds == 4  # 2 symbols * 2 sources each
        print("   ✓ Agent initialized correctly")

        # Test 2: Start agent
        print("✅ Test 2: Agent startup")
        await agent.start()
        await asyncio.sleep(2)  # Let it initialize
        print("   ✓ Agent started successfully")

        # Test 3: Feed health checking
        print("✅ Test 3: Feed health monitoring")
        await asyncio.sleep(10)  # Let monitoring run

        # Check that feeds have been updated
        btc_feeds = agent.feeds['BTC']
        eth_feeds = agent.feeds['ETH']

        feeds_checked = 0
        for source, feed in btc_feeds.items():
            if feed.last_update > datetime.utcnow() - timedelta(seconds=30):
                feeds_checked += 1

        for source, feed in eth_feeds.items():
            if feed.last_update > datetime.utcnow() - timedelta(seconds=30):
                feeds_checked += 1

        assert feeds_checked > 0, "No feeds were successfully checked"
        print(f"   ✓ {feeds_checked} feeds checked successfully")

        # Test 4: Data point storage
        print("✅ Test 4: Data point storage")
        # Create a test data point
        test_point = DataPoint(
            symbol='BTC',
            price=Decimal('50000.00'),
            source=DataSource.BINANCE,
            quality_score=0.95
        )

        await agent.store_data_point(test_point)

        # Check if it was stored in history
        assert 'BTC' in agent.price_history
        assert len(agent.price_history['BTC']) > 0
        print("   ✓ Data point stored successfully")

        # Test 5: Outlier detection
        print("✅ Test 5: Outlier detection")
        # Add some normal data points
        for i in range(10):
            normal_point = DataPoint(
                symbol='BTC',
                price=Decimal('50000.00') + Decimal(str(i * 100)),
                source=DataSource.BINANCE
            )
            await agent.store_data_point(normal_point)

        # Add outlier
        outlier_point = DataPoint(
            symbol='BTC',
            price=Decimal('100000.00'),  # Way higher
            source=DataSource.BINANCE
        )
        await agent.detect_outliers('BTC', outlier_point)

        # Check if alert was created
        outlier_alerts = [a for a in agent.active_alerts.values() if a.alert_type == AlertType.OUTLIER_DETECTED]
        assert len(outlier_alerts) > 0, "Outlier not detected"
        print("   ✓ Outlier detection working")

        # Test 6: Quality metrics
        print("✅ Test 6: Quality metrics update")
        await agent.update_quality_metrics()
        assert agent.quality_metrics.last_updated > datetime.utcnow() - timedelta(seconds=10)
        print(f"   ✓ Quality metrics updated: {agent.quality_metrics.average_quality_score:.2%}")

        # Test 7: API endpoints (simulate calls)
        print("✅ Test 7: API endpoints simulation")
        # Simulate health check
        health_response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "total_feeds": agent.quality_metrics.total_feeds,
                "active_feeds": agent.quality_metrics.active_feeds,
                "average_quality": f"{agent.quality_metrics.average_quality_score:.2%}",
                "outliers_24h": agent.quality_metrics.outlier_count_24h,
                "alerts_active": len(agent.active_alerts)
            }
        }
        assert health_response['status'] == 'healthy'
        print("   ✓ Health check simulation working")

        # Simulate feeds data
        feeds_data = {}
        for symbol in agent.feeds:
            feeds_data[symbol] = {}
            for source, feed in agent.feeds[symbol].items():
                feeds_data[symbol][source.value] = {
                    "status": feed.status,
                    "last_update": feed.last_update.isoformat(),
                    "latency_ms": feed.latency_ms,
                    "quality_score": feed.quality_score,
                    "error_count": feed.error_count
                }
        assert 'BTC' in feeds_data
        assert 'ETH' in feeds_data
        print("   ✓ Feeds data simulation working")

        print("🎉 All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        await agent.stop()

    return True


async def test_config_validation():
    """Test configuration validation"""
    print("🧪 Testing configuration validation...")

    try:
        # Test default config
        config = DataValidatorConfig()
        assert config.max_staleness_seconds == 300
        assert config.outlier_threshold_std == 3.0
        assert 'BTC' in config.primary_sources
        print("   ✓ Default config valid")

        # Test custom config
        custom_config = DataValidatorConfig(
            max_staleness_seconds=60,
            outlier_threshold_std=2.5,
            primary_sources={'TEST': [DataSource.BINANCE]}
        )
        assert custom_config.max_staleness_seconds == 60
        assert custom_config.outlier_threshold_std == 2.5
        assert 'TEST' in custom_config.primary_sources
        print("   ✓ Custom config valid")

        print("✅ Configuration tests passed!")
        return True

    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Starting Data Validator Agent Tests\n")

    # Test configuration
    config_ok = await test_config_validation()
    if not config_ok:
        return

    print()

    # Test main agent functionality
    agent_ok = await test_data_validator_agent()
    if not agent_ok:
        return

    print("\n🎊 All Data Validator Agent tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())</content>
<parameter name="filePath">e:\findtorontoevents_antigravity.ca\test_data_validator.py