#!/usr/bin/env python3
"""
Monitor Rise of the Claw Live Data
Checks every 15 minutes to verify live_competition.json is updating correctly
"""

import requests
import time
from datetime import datetime, timezone, timedelta
import json
import os

LIVE_DATA_URL = "https://findtorontoevents.ca/riseoftheclaw/data/live_competition.json"
CHECK_INTERVAL_SECONDS = 15 * 60  # 15 minutes
STALENESS_THRESHOLD_MINUTES = 20  # Alert if data older than 20 minutes

def fetch_live_data():
    """Fetch live competition data from production URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cache-Control': 'no-cache'
        }
        resp = requests.get(LIVE_DATA_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def check_data_freshness(data):
    """Check if data is fresh (updated within last 20 minutes)"""
    if "error" in data:
        return False, f"Failed to fetch data: {data['error']}"

    if "competition" not in data or "lastUpdated" not in data["competition"]:
        return False, "Missing competition.lastUpdated field"

    last_updated_str = data["competition"]["lastUpdated"]
    try:
        # Parse ISO timestamp
        last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        age_minutes = (now - last_updated).total_seconds() / 60

        is_fresh = age_minutes <= STALENESS_THRESHOLD_MINUTES
        status_msg = f"Data age: {age_minutes:.1f} minutes {'✓ FRESH' if is_fresh else '⚠ STALE'}"

        return is_fresh, status_msg
    except Exception as e:
        return False, f"Failed to parse timestamp: {e}"

def analyze_algorithms(data):
    """Analyze algorithm states and active picks"""
    if "error" in data or "algorithms" not in data:
        return {}

    total_algos = len(data["algorithms"])
    algos_with_picks = sum(1 for a in data["algorithms"] if a.get("activePicks", []))
    total_picks = sum(len(a.get("activePicks", [])) for a in data["algorithms"])
    algos_with_returns = sum(1 for a in data["algorithms"] if a.get("totalReturn", 0) != 0)

    # Category breakdown
    categories = {}
    for algo in data["algorithms"]:
        cat = algo.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"count": 0, "with_picks": 0, "total_picks": 0}
        categories[cat]["count"] += 1
        if algo.get("activePicks", []):
            categories[cat]["with_picks"] += 1
            categories[cat]["total_picks"] += len(algo["activePicks"])

    return {
        "total_algorithms": total_algos,
        "algorithms_with_picks": algos_with_picks,
        "total_active_picks": total_picks,
        "algorithms_with_returns": algos_with_returns,
        "categories": categories
    }

def print_status_report(data, is_fresh, freshness_msg, analysis):
    """Print formatted status report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*70)
    print(f"🔍 LIVE DATA MONITOR - {timestamp}")
    print("="*70)

    # Data freshness
    print(f"\n📊 Data Freshness: {freshness_msg}")

    if "competition" in data:
        print(f"   Last Updated: {data['competition'].get('lastUpdated', 'N/A')}")
        print(f"   Status: {data['competition'].get('status', 'N/A')}")

    # Algorithm analysis
    if analysis:
        print(f"\n🤖 Algorithms:")
        print(f"   Total: {analysis['total_algorithms']}")
        print(f"   With Active Picks: {analysis['algorithms_with_picks']}")
        print(f"   With Non-Zero Returns: {analysis['algorithms_with_returns']}")
        print(f"   Total Active Picks: {analysis['total_active_picks']}")

        if analysis['categories']:
            print(f"\n📈 By Category:")
            for cat, stats in analysis['categories'].items():
                emoji = {'stock': '📊', 'crypto': '₿', 'meme': '🚀', 'penny': '💎', 'forex': '💱'}.get(cat, '📉')
                print(f"   {emoji} {cat.upper()}: {stats['count']} algos, {stats['with_picks']} with picks ({stats['total_picks']} total)")

    # Detailed picks
    if "algorithms" in data:
        algos_with_picks = [a for a in data["algorithms"] if a.get("activePicks", [])]
        if algos_with_picks:
            print(f"\n💰 Active Picks Details:")
            for algo in algos_with_picks:
                print(f"\n   {algo['name']} ({algo['category'].upper()}):")
                print(f"   Portfolio: ${algo.get('currentValue', 0):,.2f} ({algo.get('totalReturn', 0):+.2f}%)")
                for pick in algo["activePicks"]:
                    entry = pick.get("entryPrice", 0)
                    current = pick.get("currentPrice", 0)
                    pl_pct = ((current - entry) / entry * 100) if entry > 0 else 0
                    print(f"      • {pick['symbol']}: ${entry:.2f} → ${current:.2f} ({pl_pct:+.2f}%)")
                    if pick.get("reason"):
                        print(f"        Reason: {pick['reason']}")

    # Health check summary
    print(f"\n{'✅' if is_fresh and analysis.get('total_active_picks', 0) > 0 else '⚠️'} Health Status:")
    health_checks = [
        ("Data freshness", is_fresh),
        ("Has active picks", analysis.get('total_active_picks', 0) > 0),
        ("Multiple algos trading", analysis.get('algorithms_with_picks', 0) > 1)
    ]
    for check_name, check_passed in health_checks:
        status = "✓ PASS" if check_passed else "✗ FAIL"
        print(f"   {check_name}: {status}")

    print("="*70 + "\n")

def monitor_loop(continuous=True):
    """Main monitoring loop"""
    iteration = 1

    while True:
        print(f"\n🔄 Check #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Fetch and analyze data
        data = fetch_live_data()
        is_fresh, freshness_msg = check_data_freshness(data)
        analysis = analyze_algorithms(data)

        # Print report
        print_status_report(data, is_fresh, freshness_msg, analysis)

        if not continuous:
            break

        # Wait for next check
        print(f"⏳ Next check in {CHECK_INTERVAL_SECONDS // 60} minutes...")
        iteration += 1
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    import sys
    import io

    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    # Check for --once flag for single check
    continuous = "--once" not in sys.argv

    print("🚀 Rise of the Claw - Live Data Monitor")
    print(f"📡 Monitoring: {LIVE_DATA_URL}")
    print(f"⏱️  Check interval: {CHECK_INTERVAL_SECONDS // 60} minutes")
    print(f"⚠️  Staleness threshold: {STALENESS_THRESHOLD_MINUTES} minutes")

    if not continuous:
        print("\n🔍 Running single check (--once mode)...")
    else:
        print(f"\n♾️  Running continuous monitoring (Ctrl+C to stop)...")

    try:
        monitor_loop(continuous)
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)
