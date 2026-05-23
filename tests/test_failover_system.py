"""
Failover System Test Suite
============================
Comprehensive tests for all failover mechanisms.

Run with:
    pytest tests/test_failover_system.py -v
    python tests/test_failover_system.py --integration  # Live API tests

Tests:
  1. Data source failover chain
  2. Notification channel failover
  3. Cache read/write
  4. Health monitoring
  5. Rate limiting
  6. Circuit breaker behavior
"""

import os
import sys
import time
import json
import pytest
import tempfile
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np

# Import modules to test
from quan_engine.failover_system import (
    FailoverDataFetcher, CacheManager, HealthMonitor,
    fetch_klines_with_failover, fetch_price_with_failover,
    get_health_report, FAILOVER_CONFIG
)
from shared.failover_notifications import (
    NotificationManager, DiscordWebhookChannel, FileFallbackChannel,
    notify, notify_critical, Level, get_notification_health
)
from quan_engine.health_dashboard import (
    HealthDashboard, DataSourceHealthChecker, NotificationHealthChecker
)


def _dummy_klines_df(n: int = 55) -> pd.DataFrame:
    """fetch_klines accepts a source only when len(df) >= 50."""
    return pd.DataFrame({
        "open": [100.0] * n,
        "high": [110.0] * n,
        "low": [90.0] * n,
        "close": [105.0] * n,
        "volume": [1000.0] * n,
    })


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def cache_manager(temp_cache_dir):
    """Create a CacheManager with temp directory."""
    # Patch the cache directory
    original_dir = FAILOVER_CONFIG.get("cache_dir")
    FAILOVER_CONFIG["cache_dir"] = temp_cache_dir
    
    # Create new instance
    CacheManager._instance = None
    cm = CacheManager()
    
    yield cm
    
    # Cleanup
    FAILOVER_CONFIG["cache_dir"] = original_dir
    CacheManager._instance = None


@pytest.fixture
def health_monitor():
    """Create a fresh HealthMonitor."""
    HealthMonitor._instance = None
    hm = HealthMonitor()
    yield hm
    HealthMonitor._instance = None


@pytest.fixture
def fetcher(temp_cache_dir):
    """Create a FailoverDataFetcher with temp cache."""
    original_dir = FAILOVER_CONFIG.get("cache_dir")
    FAILOVER_CONFIG["cache_dir"] = temp_cache_dir
    
    CacheManager._instance = None
    fetcher = FailoverDataFetcher()
    
    yield fetcher
    
    FAILOVER_CONFIG["cache_dir"] = original_dir
    CacheManager._instance = None


# ============================================================================
# CACHE MANAGER TESTS
# ============================================================================

class TestCacheManager:
    """Test cache manager functionality."""
    
    def test_cache_write_and_read(self, cache_manager):
        """Test basic cache write and read."""
        key = "test_key"
        data = {"test": "data", "number": 42}
        
        cache_manager.set(key, data)
        result = cache_manager.get(key)
        
        assert result == data
    
    def test_cache_expiration(self, cache_manager):
        """Test that cache entries expire correctly."""
        key = "expiring_key"
        data = {"test": "data"}
        
        cache_manager.set(key, data)
        
        # Should be available immediately
        assert cache_manager.get(key, max_age_minutes=60) is not None
        
        # Should be expired with 0 age
        assert cache_manager.get(key, max_age_minutes=0) is None
    
    def test_stale_cache_fallback(self, cache_manager):
        """Test stale cache fallback."""
        key = "stale_key"
        data = {"test": "data"}
        
        cache_manager.set(key, data)
        
        # Should get stale data even if "expired"
        result = cache_manager.get_stale(key, max_age_hours=0)
        assert result == data
    
    def test_cache_persistence(self, cache_manager, temp_cache_dir):
        """Test that cache persists to disk."""
        key = "persistent_key"
        data = pd.DataFrame({"col": [1, 2, 3]})
        
        cache_manager.set(key, data)
        
        # Create new instance (simulating restart)
        CacheManager._instance = None
        new_manager = CacheManager()
        
        result = new_manager.get(key)
        assert result is not None
        pd.testing.assert_frame_equal(result, data)


# ============================================================================
# HEALTH MONITOR TESTS
# ============================================================================

class TestHealthMonitor:
    """Test health monitoring functionality."""
    
    def test_record_success(self, health_monitor):
        """Test recording successful operations."""
        health_monitor.record_success("test_source", 100.0)
        
        health = health_monitor.get_health("test_source")
        assert health.is_healthy
        assert health.success_count == 1
        assert health.avg_latency_ms == 100.0
    
    def test_record_failure(self, health_monitor):
        """Test recording failures."""
        # Record 3 failures to trigger unhealthy
        for _ in range(3):
            health_monitor.record_failure("test_source")
        
        health = health_monitor.get_health("test_source")
        assert not health.is_healthy
        assert health.failure_count == 3
    
    def test_get_healthy_sources(self, health_monitor):
        """Test filtering healthy sources."""
        health_monitor.record_success("healthy_source", 50.0)
        health_monitor.record_failure("unhealthy_source")
        health_monitor.record_failure("unhealthy_source")
        health_monitor.record_failure("unhealthy_source")
        
        healthy = health_monitor.get_healthy_sources()
        assert "healthy_source" in healthy
        assert "unhealthy_source" not in healthy


# ============================================================================
# DATA FETCHER TESTS
# ============================================================================

class TestFailoverDataFetcher:
    """Test data fetcher with failover."""
    
    def test_fetch_uses_cache_on_failure(self, fetcher, cache_manager):
        """Test that fetcher uses cache when all sources fail."""
        # Pre-populate cache
        symbol = "BTCUSDT"
        cached_df = pd.DataFrame({
            "open": [100.0], "high": [110.0],
            "low": [90.0], "close": [105.0], "volume": [1000.0]
        })
        cache_manager.set(f"klines:{symbol}:1h", cached_df)
        
        # Mock all fetch methods to fail
        fetcher._fetch_yfinance = Mock(return_value=None)
        fetcher._fetch_binance = Mock(return_value=None)
        fetcher._fetch_coingecko = Mock(return_value=None)
        fetcher._fetch_cryptocompare = Mock(return_value=None)
        
        result = fetcher.fetch_klines(symbol, "1h", 100)
        
        assert result.success
        assert result.source == "cache"
        assert result.is_stale
    
    def test_fetch_saves_to_cache(self, fetcher, cache_manager):
        """Test that successful fetches are cached."""
        symbol = "BTCUSDT"
        mock_df = _dummy_klines_df()

        # Mock yfinance to succeed
        fetcher._fetch_yfinance = Mock(return_value=mock_df)
        fetcher._fetch_binance = Mock(return_value=None)
        
        result = fetcher.fetch_klines(symbol, "1h", 100)
        
        assert result.success
        assert result.source == "yfinance"
        
        # Verify cache was populated
        cached = cache_manager.get(f"klines:{symbol}:1h")
        assert cached is not None
    
    def test_fallback_chain_order(self, fetcher):
        """Test that fallback chain follows correct order."""
        # Track call order
        call_order = []
        
        def mock_yfinance(*args):
            call_order.append("yfinance")
            return None
        
        def mock_binance(*args):
            call_order.append("binance")
            return None
        
        def mock_coingecko(*args):
            call_order.append("coingecko")
            return _dummy_klines_df()
        
        fetcher._fetch_yfinance = mock_yfinance
        fetcher._fetch_binance = mock_binance
        fetcher._fetch_coingecko = mock_coingecko
        fetcher._fetch_cryptocompare = Mock(return_value=None)
        
        result = fetcher.fetch_klines("BTCUSDT", "1h", 100)
        
        assert call_order == ["yfinance", "binance", "coingecko"]
        assert result.source == "coingecko"


# ============================================================================
# NOTIFICATION TESTS
# ============================================================================

class TestNotificationChannels:
    """Test notification channel functionality."""
    
    def test_file_fallback_always_available(self):
        """Test that file fallback channel is always available."""
        channel = FileFallbackChannel()
        assert channel.is_available()
        
        result = channel.send(Level.INFO, "Test", {"key": "value"})
        assert result.success
        assert result.channel == "file_fallback"
    
    def test_file_fallback_persists(self, temp_cache_dir):
        """Test that file fallback writes to disk."""
        channel = FileFallbackChannel()
        channel.log_dir = temp_cache_dir
        
        result = channel.send(Level.ERROR, "Test Error", {"error": "test"})
        assert result.success
        
        # Verify file was created
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = os.path.join(temp_cache_dir, f"notifications_{date_str}.jsonl")
        assert os.path.exists(log_file)
        
        # Verify content
        with open(log_file) as f:
            entry = json.loads(f.readline())
            assert entry["title"] == "Test Error"
            assert entry["level"] == Level.ERROR


class TestNotificationManager:
    """Test notification manager with failover."""
    
    def test_notification_batches_non_critical(self):
        """Test that non-critical notifications are batched."""
        manager = NotificationManager()
        
        # Send multiple info notifications
        results = []
        for i in range(3):
            result = manager.send(Level.INFO, f"Test {i}", {}, batch=True)
            results.extend(result)
        
        # Should all be batched
        assert all(r.channel == "batched" for r in results)
    
    def test_critical_notifications_not_batched(self):
        """Test that critical notifications are sent immediately."""
        manager = NotificationManager()
        
        # Clear any existing channels and add file fallback
        manager.channels = [FileFallbackChannel()]
        
        result = manager.send(Level.CRITICAL, "Critical Test", {}, batch=False, require_ack=False)
        
        # Should be sent immediately through file fallback
        assert any(r.channel == "file_fallback" and r.success for r in result)


# ============================================================================
# HEALTH DASHBOARD TESTS
# ============================================================================

class TestHealthDashboard:
    """Test health dashboard functionality."""
    
    def test_overall_status_healthy(self):
        """Test that all healthy returns healthy overall."""
        dashboard = HealthDashboard()
        
        results = {
            "check1": Mock(status="healthy"),
            "check2": Mock(status="healthy"),
        }
        
        assert dashboard.get_overall_status(results) == "healthy"
    
    def test_overall_status_degraded(self):
        """Test that one degraded returns degraded overall."""
        dashboard = HealthDashboard()
        
        results = {
            "check1": Mock(status="healthy"),
            "check2": Mock(status="degraded"),
        }
        
        assert dashboard.get_overall_status(results) == "degraded"
    
    def test_overall_status_critical(self):
        """Test that one critical returns critical overall."""
        dashboard = HealthDashboard()
        
        results = {
            "check1": Mock(status="healthy"),
            "check2": Mock(status="critical"),
        }
        
        assert dashboard.get_overall_status(results) == "critical"
    
    def test_report_structure(self):
        """Test that report has expected structure."""
        dashboard = HealthDashboard()
        report = dashboard.generate_report()
        
        assert "timestamp" in report
        assert "overall_status" in report
        assert "checks" in report
        assert "summary" in report
        assert report["summary"]["total_checks"] > 0


# ============================================================================
# INTEGRATION TESTS (Require network)
# ============================================================================

@pytest.mark.integration
class TestIntegration:
    """Integration tests that hit real APIs."""
    
    def test_yfinance_fetch(self):
        """Test actual yfinance fetch."""
        df = fetch_klines_with_failover("BTCUSDT", "1h", 100)
        assert not df.empty
        assert len(df) > 50
        assert all(col in df.columns for col in ["open", "high", "low", "close", "volume"])
    
    def test_price_fetch(self):
        """Test actual price fetch."""
        price = fetch_price_with_failover("BTCUSDT")
        assert price is not None
        assert 1000 < price < 100000  # Sanity check for BTC price
    
    def test_coingecko_fetch(self, fetcher):
        """Test CoinGecko API directly."""
        df = fetcher._fetch_coingecko("BTCUSDT", "1h", 100)
        assert df is not None
        assert len(df) > 0
    
    def test_health_report(self):
        """Test health report generation."""
        report = get_health_report()
        assert isinstance(report, dict)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Failover System")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    # Run pytest
    pytest_args = [__file__, "-v" if args.verbose else "-q"]
    if args.integration:
        pytest_args.extend(["-m", "integration"])
    else:
        pytest_args.extend(["-m", "not integration"])
    
    sys.exit(pytest.main(pytest_args))
