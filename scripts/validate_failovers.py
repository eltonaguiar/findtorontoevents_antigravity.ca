#!/usr/bin/env python3
"""
Failover System Validation Script
=================================
Validates all failover mechanisms are operational.
Run this after deploying failover changes.

Usage:
    python scripts/validate_failovers.py
    python scripts/validate_failovers.py --quick    # Fast check
    python scripts/validate_failovers.py --full     # Comprehensive test
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from typing import List, Dict, Tuple

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import all failover components
from quan_engine.failover_system import (
    get_failover_fetcher, 
    fetch_klines_with_failover,
    fetch_price_with_failover,
    get_health_report,
    clear_cache
)
from quan_engine.health_dashboard import HealthDashboard
from shared.failover_notifications import (
    notify_info, notify_warning, notify_error, notify_critical,
    get_notification_health, Level
)


class Colors:
    """Terminal colors."""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}\n")


def print_result(name: str, success: bool, details: str = ""):
    """Print a test result."""
    status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if success else f"{Colors.RED}❌ FAIL{Colors.RESET}"
    print(f"  {status} {name}")
    if details:
        print(f"      {details}")


def test_data_source_failovers() -> Tuple[int, int]:
    """Test all data source failovers."""
    print_header("DATA SOURCE FAILOVER TESTS")
    
    passed = 0
    failed = 0
    
    fetcher = get_failover_fetcher()
    test_symbols = ["BTCUSDT", "ETHUSDT"]
    
    # Test 1: yfinance fetch
    print("Testing yfinance...")
    try:
        for symbol in test_symbols:
            df = fetcher._fetch_yfinance(symbol, "1h", 100)
            if df is not None and len(df) > 50:
                print_result(f"yfinance {symbol}", True, f"{len(df)} rows")
                passed += 1
            else:
                print_result(f"yfinance {symbol}", False, "Insufficient data")
                failed += 1
    except Exception as e:
        print_result("yfinance", False, str(e))
        failed += len(test_symbols)
    
    # Test 2: Binance fetch
    print("\nTesting Binance...")
    try:
        for symbol in test_symbols:
            df = fetcher._fetch_binance(symbol, "1h", 100)
            if df is not None and len(df) > 50:
                print_result(f"Binance {symbol}", True, f"{len(df)} rows")
                passed += 1
            else:
                print_result(f"Binance {symbol}", False, "Insufficient data")
                failed += 1
    except Exception as e:
        print_result("Binance", False, str(e))
        failed += len(test_symbols)
    
    # Test 3: CoinGecko fetch
    print("\nTesting CoinGecko...")
    try:
        for symbol in test_symbols[:1]:  # Rate limited, just test one
            df = fetcher._fetch_coingecko(symbol, "1h", 100)
            if df is not None and len(df) > 0:
                print_result(f"CoinGecko {symbol}", True, f"{len(df)} rows")
                passed += 1
            else:
                print_result(f"CoinGecko {symbol}", False, "No data")
                failed += 1
    except Exception as e:
        print_result("CoinGecko", False, str(e))
        failed += 1
    
    # Test 4: Full failover chain
    print("\nTesting full failover chain...")
    try:
        for symbol in test_symbols[:1]:
            result = fetcher.fetch_klines(symbol, "1h", 100)
            if result.success:
                source_info = f"source={result.source}"
                if result.is_stale:
                    source_info += " (stale)"
                print_result(f"Full chain {symbol}", True, source_info)
                passed += 1
            else:
                print_result(f"Full chain {symbol}", False, result.error)
                failed += 1
    except Exception as e:
        print_result("Full chain", False, str(e))
        failed += 1
    
    # Test 5: Price fetch
    print("\nTesting price fetch...")
    try:
        for symbol in test_symbols:
            price = fetch_price_with_failover(symbol)
            if price is not None:
                print_result(f"Price {symbol}", True, f"${price:,.2f}")
                passed += 1
            else:
                print_result(f"Price {symbol}", False, "No price returned")
                failed += 1
    except Exception as e:
        print_result("Price fetch", False, str(e))
        failed += len(test_symbols)
    
    return passed, failed


def test_cache_system() -> Tuple[int, int]:
    """Test cache system."""
    print_header("CACHE SYSTEM TESTS")
    
    passed = 0
    failed = 0
    
    fetcher = get_failover_fetcher()
    cache = fetcher.cache
    
    # Test 1: Write and read
    print("Testing cache write/read...")
    try:
        test_data = {"test": "data", "timestamp": datetime.utcnow().isoformat()}
        cache.set("test_key", test_data)
        result = cache.get("test_key")
        
        if result == test_data:
            print_result("Cache write/read", True)
            passed += 1
        else:
            print_result("Cache write/read", False, "Data mismatch")
            failed += 1
    except Exception as e:
        print_result("Cache write/read", False, str(e))
        failed += 1
    
    # Test 2: Expiration
    print("Testing cache expiration...")
    try:
        cache.set("expiring_key", {"data": "value"})
        # Should not be available with 0 max age
        result = cache.get("expiring_key", max_age_minutes=0)
        
        if result is None:
            print_result("Cache expiration", True)
            passed += 1
        else:
            print_result("Cache expiration", False, "Should have expired")
            failed += 1
    except Exception as e:
        print_result("Cache expiration", False, str(e))
        failed += 1
    
    # Test 3: Stale fallback
    print("Testing stale cache fallback...")
    try:
        cache.set("stale_key", {"data": "stale"})
        result = cache.get_stale("stale_key", max_age_hours=0)
        
        if result is not None:
            print_result("Stale fallback", True)
            passed += 1
        else:
            print_result("Stale fallback", False, "No stale data returned")
            failed += 1
    except Exception as e:
        print_result("Stale fallback", False, str(e))
        failed += 1
    
    return passed, failed


def test_notification_failovers() -> Tuple[int, int]:
    """Test notification failover channels."""
    print_header("NOTIFICATION FAILOVER TESTS")
    
    passed = 0
    failed = 0
    
    # Test 1: File fallback (always works)
    print("Testing file fallback...")
    try:
        results = notify_info("Test notification", {"test": True})
        if any(r.success for r in results):
            print_result("File fallback", True)
            passed += 1
        else:
            print_result("File fallback", False, "No channel succeeded")
            failed += 1
    except Exception as e:
        print_result("File fallback", False, str(e))
        failed += 1
    
    # Test 2: Health check
    print("\nTesting notification health...")
    try:
        health = get_notification_health()
        file_fallback = health.get("file_fallback", {})
        
        if file_fallback.get("available", False):
            print_result("Notification health", True, f"{len(health)} channels registered")
            passed += 1
        else:
            print_result("Notification health", False, "File fallback not available")
            failed += 1
    except Exception as e:
        print_result("Notification health", False, str(e))
        failed += 1
    
    return passed, failed


def test_health_dashboard() -> Tuple[int, int]:
    """Test health dashboard."""
    print_header("HEALTH DASHBOARD TESTS")
    
    passed = 0
    failed = 0
    
    dashboard = HealthDashboard()
    
    # Test 1: Generate report
    print("Testing report generation...")
    try:
        report = dashboard.generate_report()
        
        if "timestamp" in report and "overall_status" in report:
            print_result("Report generation", True, f"status={report['overall_status']}")
            passed += 1
        else:
            print_result("Report generation", False, "Missing fields")
            failed += 1
    except Exception as e:
        print_result("Report generation", False, str(e))
        failed += 1
    
    # Test 2: Data source health
    print("\nTesting data source health...")
    try:
        data_health = get_health_report()
        
        if isinstance(data_health, dict):
            healthy_count = sum(1 for h in data_health.values() if h.get("is_healthy", False))
            print_result("Data source health", True, f"{healthy_count}/{len(data_health)} healthy")
            passed += 1
        else:
            print_result("Data source health", False, "Invalid format")
            failed += 1
    except Exception as e:
        print_result("Data source health", False, str(e))
        failed += 1
    
    return passed, failed


def test_integration() -> Tuple[int, int]:
    """Test end-to-end integration."""
    print_header("INTEGRATION TESTS")
    
    passed = 0
    failed = 0
    
    # Test 1: Full scanner workflow
    print("Testing full data fetch...")
    try:
        df = fetch_klines_with_failover("BTCUSDT", "1h", 200)
        
        if not df.empty and len(df) >= 100:
            print_result("Full data fetch", True, f"{len(df)} rows")
            passed += 1
        else:
            print_result("Full data fetch", False, f"Only {len(df)} rows")
            failed += 1
    except Exception as e:
        print_result("Full data fetch", False, str(e))
        failed += 1
    
    # Test 2: Critical notification path
    print("\nTesting critical notification...")
    try:
        results = notify_critical("CRITICAL TEST", {"test_type": "integration"})
        
        if any(r.success for r in results):
            channels = ", ".join([r.channel for r in results if r.success])
            print_result("Critical notification", True, f"via {channels}")
            passed += 1
        else:
            print_result("Critical notification", False, "All channels failed")
            failed += 1
    except Exception as e:
        print_result("Critical notification", False, str(e))
        failed += 1
    
    return passed, failed


def main():
    parser = argparse.ArgumentParser(description="Validate Failover Systems")
    parser.add_argument("--quick", action="store_true", help="Quick validation")
    parser.add_argument("--full", action="store_true", help="Full comprehensive test")
    parser.add_argument("--no-color", action="store_true", help="Disable colors")
    args = parser.parse_args()
    
    global Colors
    if args.no_color:
        Colors.GREEN = Colors.RED = Colors.YELLOW = Colors.BLUE = Colors.BOLD = Colors.RESET = ""
    
    print(f"\n{Colors.BOLD}QuanEngine Failover Validation{Colors.RESET}")
    print(f"Started at: {datetime.utcnow().isoformat()}")
    
    total_passed = 0
    total_failed = 0
    
    # Run tests
    tests = [
        ("Data Sources", test_data_source_failovers),
        ("Cache System", test_cache_system),
        ("Notifications", test_notification_failovers),
        ("Health Dashboard", test_health_dashboard),
    ]
    
    if args.full:
        tests.append(("Integration", test_integration))
    
    for name, test_func in tests:
        try:
            passed, failed = test_func()
            total_passed += passed
            total_failed += failed
        except Exception as e:
            print(f"\n{Colors.RED}ERROR in {name}: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()
            total_failed += 1
    
    # Summary
    print_header("SUMMARY")
    total = total_passed + total_failed
    success_rate = (total_passed / total * 100) if total > 0 else 0
    
    color = Colors.GREEN if total_failed == 0 else Colors.YELLOW if total_failed < 3 else Colors.RED
    print(f"  Total Tests: {total}")
    print(f"  {Colors.GREEN}Passed: {total_passed}{Colors.RESET}")
    print(f"  {Colors.RED}Failed: {total_failed}{Colors.RESET}")
    print(f"  {color}Success Rate: {success_rate:.1f}%{Colors.RESET}")
    
    if total_failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ All failovers operational!{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}⚠️ Some tests failed. Check output above.{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
