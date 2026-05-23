#!/usr/bin/env python3
"""
Production Monitoring System for Rise of the Claw
Monitors GitHub Actions runs, data freshness, and system health
"""

import json
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Configuration
PRODUCTION_URL = "https://findtorontoevents.ca/riseoftheclaw/data/live_competition.json"
LOCAL_DATA_PATH = Path("KIMI_RISEOFTHECLAW/data/live_competition.json")
FRESHNESS_THRESHOLD_MINUTES = 20
ALERT_FILE = Path("production_alerts.log")

class ProductionMonitor:
    def __init__(self):
        self.alerts = []

    def check_production_data_freshness(self):
        """Check if production data is fresh (< 20 minutes old)"""
        print("[CHECK] Checking production data freshness...")
        try:
            response = requests.get(PRODUCTION_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            last_updated = datetime.fromisoformat(data["competition"]["lastUpdated"].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_minutes = (now - last_updated).total_seconds() / 60

            print(f"   Last updated: {last_updated.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"   Age: {age_minutes:.1f} minutes")

            if age_minutes > FRESHNESS_THRESHOLD_MINUTES:
                alert = f"[WARN] STALE DATA: Production data is {age_minutes:.1f} minutes old (threshold: {FRESHNESS_THRESHOLD_MINUTES})"
                self.alerts.append(alert)
                print(f"   {alert}")
                return False
            else:
                print(f"   [OK] FRESH (within {FRESHNESS_THRESHOLD_MINUTES} min threshold)")
                return True

        except Exception as e:
            alert = f"[ERROR] PRODUCTION FETCH FAILED: {str(e)}"
            self.alerts.append(alert)
            print(f"   {alert}")
            return False

    def check_active_picks(self):
        """Check number of active picks across all strategies"""
        print("\n[CHECK] Checking active picks...")
        try:
            response = requests.get(PRODUCTION_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            total_picks = 0
            tier1_picks = 0
            scout_picks = 0

            for algo in data.get("algorithms", []):
                picks = len(algo.get("activePicks", []))
                total_picks += picks

                if algo.get("tier") == "TIER_1":
                    tier1_picks += picks
                    if picks > 0:
                        print(f"   [{algo['tier']}] {algo['name']}: {picks} picks")
                elif algo.get("tier") == "SCOUT":
                    scout_picks += picks
                    if picks > 0:
                        print(f"   [{algo['tier']}] {algo['name']}: {picks} picks")

            print(f"\n   Total: {total_picks} picks ({tier1_picks} TIER_1, {scout_picks} SCOUT)")

            if total_picks == 0:
                print("   [INFO] No active picks (strategies waiting for entry signals)")

            return total_picks

        except Exception as e:
            alert = f"[ERROR] PICKS CHECK FAILED: {str(e)}"
            self.alerts.append(alert)
            print(f"   {alert}")
            return None

    def check_market_status(self):
        """Check market status detection"""
        print("\n[CHECK] Checking market status...")
        try:
            response = requests.get(PRODUCTION_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            market_status = data.get("marketStatus", {})
            print(f"   US Markets: {market_status.get('usMarkets', 'UNKNOWN')}")
            print(f"   Crypto Markets: {market_status.get('cryptoMarkets', 'UNKNOWN')}")
            print(f"   Forex Markets: {market_status.get('forexMarkets', 'UNKNOWN')}")
            print(f"   Last Check: {market_status.get('lastMarketCheck', 'UNKNOWN')}")

            return True

        except Exception as e:
            alert = f"[ERROR] MARKET STATUS CHECK FAILED: {str(e)}"
            self.alerts.append(alert)
            print(f"   {alert}")
            return False

    def check_strategy_health(self):
        """Check that all expected strategies are present"""
        print("\n[CHECK] Checking strategy health...")
        expected_tier1 = [
            "Funding Rate Arbitrage",
            "Pairs Trading (Cointegration)",
            "Betting Against Beta",
            "Flash Crash Reversal",
            "Quality Minus Junk",
            "Bollinger Mean Reversion (Meme)"
        ]

        try:
            response = requests.get(PRODUCTION_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            found_strategies = {algo["name"] for algo in data.get("algorithms", [])}
            tier1_strategies = {algo["name"] for algo in data.get("algorithms", []) if algo.get("tier") == "TIER_1"}

            print(f"   Total strategies: {len(found_strategies)}")
            print(f"   TIER_1 strategies: {len(tier1_strategies)}")

            missing = set(expected_tier1) - tier1_strategies
            if missing:
                alert = f"[WARN] MISSING TIER_1 STRATEGIES: {', '.join(missing)}"
                self.alerts.append(alert)
                print(f"   {alert}")
                return False
            else:
                print("   [OK] All 6 TIER_1 strategies present")
                return True

        except Exception as e:
            alert = f"[ERROR] STRATEGY HEALTH CHECK FAILED: {str(e)}"
            self.alerts.append(alert)
            print(f"   {alert}")
            return False

    def check_dashboard_accessibility(self):
        """Check if production dashboard is accessible"""
        print("\n[CHECK] Checking dashboard accessibility...")
        urls = [
            "https://findtorontoevents.ca/riseoftheclaw.html",
            "https://findtorontoevents.ca/riseoftheclaw/css/dashboard.css",
            "https://findtorontoevents.ca/riseoftheclaw/js/dashboard.js"
        ]

        all_accessible = True
        for url in urls:
            try:
                response = requests.head(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    print(f"   [OK] {url.split('/')[-1]}: HTTP {response.status_code}")
                else:
                    print(f"   [WARN] {url.split('/')[-1]}: HTTP {response.status_code}")
                    all_accessible = False
            except Exception as e:
                print(f"   [ERROR] {url.split('/')[-1]}: {str(e)}")
                all_accessible = False

        return all_accessible

    def generate_report(self):
        """Generate comprehensive health report"""
        print("\n" + "="*60)
        print("PRODUCTION HEALTH REPORT")
        print("="*60)
        print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()

        checks = {
            "Production Data Freshness": self.check_production_data_freshness(),
            "Active Picks": self.check_active_picks() is not None,
            "Market Status": self.check_market_status(),
            "Strategy Health": self.check_strategy_health(),
            "Dashboard Accessibility": self.check_dashboard_accessibility()
        }

        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)

        for check, status in checks.items():
            status_str = "[PASS]" if status else "[FAIL]"
            print(f"{status_str}  {check}")

        print(f"\nOverall: {passed}/{total} checks passed ({passed/total*100:.0f}%)")

        if self.alerts:
            print("\n[ALERTS]")
            for alert in self.alerts:
                print(f"   {alert}")
        else:
            print("\n[OK] No alerts - system healthy")

        # Write alerts to log
        if self.alerts:
            with open(ALERT_FILE, "a") as f:
                timestamp = datetime.now(timezone.utc).isoformat()
                for alert in self.alerts:
                    f.write(f"{timestamp} - {alert}\n")

        return passed == total

if __name__ == "__main__":
    monitor = ProductionMonitor()
    healthy = monitor.generate_report()
    exit(0 if healthy else 1)
