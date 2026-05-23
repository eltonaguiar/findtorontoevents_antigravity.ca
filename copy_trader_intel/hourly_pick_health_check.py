#!/usr/bin/env python3
"""
Hourly Pick Health Check
========================
Monitors the health of all copy trader data sources:
  - Checks data file freshness (last modified time)
  - Verifies each pick source is generating picks (not 0)
  - Tests price feeds (Binance + yfinance fallback)
  - Flags sources that haven't updated in 2+ hours
  - Saves health report to copy_trader_intel/data/health_report.json
  - Prints status summary

Run: python copy_trader_intel/hourly_pick_health_check.py
"""

import json
import sys
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

try:
    import requests
except ImportError:
    print("[ERROR] pip install requests")
    sys.exit(1)

DATA_DIR = Path(__file__).parent / "data"

# Stale threshold: 2 hours
STALE_THRESHOLD_HOURS = 2

# Data files to monitor with expected content structure
MONITORED_FILES = {
    # Copy trader picks
    "active_picks.json": {
        "category": "picks",
        "description": "Active copy trader picks",
        "count_key": None,  # Check array length at root or nested
        "count_paths": [("picks", None), ("active_picks", None)],
    },
    "okx_futures_picks.json": {
        "category": "picks",
        "description": "OKX futures picks",
        "count_paths": [("picks", None)],
    },
    "binance_picks.json": {
        "category": "picks",
        "description": "Binance picks",
        "count_paths": [("picks", None)],
    },
    "bitget_picks.json": {
        "category": "picks",
        "description": "Bitget picks",
        "count_paths": [("picks", None)],
    },
    "bybit_picks.json": {
        "category": "picks",
        "description": "Bybit picks",
        "count_paths": [("picks", None)],
    },
    "gmx_picks.json": {
        "category": "picks",
        "description": "GMX picks",
        "count_paths": [("picks", None)],
    },
    "dex_picks.json": {
        "category": "picks",
        "description": "DEX picks",
        "count_paths": [("picks", None)],
    },
    "drift_picks.json": {
        "category": "picks",
        "description": "Drift picks",
        "count_paths": [("picks", None)],
    },
    "dune_picks.json": {
        "category": "picks",
        "description": "Dune analytics picks",
        "count_paths": [("picks", None)],
    },
    "htx_picks.json": {
        "category": "picks",
        "description": "HTX picks",
        "count_paths": [("picks", None)],
    },
    "coinglass_picks.json": {
        "category": "picks",
        "description": "Coinglass picks",
        "count_paths": [("picks", None)],
    },
    # Trader profiles and databases
    "copytrader_database.json": {
        "category": "database",
        "description": "Master trader database",
        "count_paths": [("total_unique", None)],
    },
    "qualified_traders.json": {
        "category": "database",
        "description": "Qualified Hyperliquid traders",
        "count_paths": [("traders", None)],
    },
    "trader_profiles.json": {
        "category": "profiles",
        "description": "Trader profiles (all platforms)",
        "count_paths": [("profiles", None)],
    },
    "okx_trader_profiles.json": {
        "category": "profiles",
        "description": "OKX trader profiles",
        "count_paths": [("profiles", None)],
    },
    "bitget_trader_profiles.json": {
        "category": "profiles",
        "description": "Bitget trader profiles",
        "count_paths": [("profiles", None)],
    },
    "bybit_trader_profiles.json": {
        "category": "profiles",
        "description": "Bybit trader profiles",
        "count_paths": [("profiles", None)],
    },
    # Metadata and tracking
    "scan_metadata.json": {
        "category": "metadata",
        "description": "Scan metadata/timing",
        "count_paths": [],
    },
    "portfolio_tracker.json": {
        "category": "tracking",
        "description": "Portfolio tracker",
        "count_paths": [],
    },
    "health_report.json": {
        "category": "health",
        "description": "Previous health report",
        "count_paths": [],
        "skip_stale_check": True,
    },
}


def check_file_freshness(filepath):
    """Check if a file exists and when it was last modified.
    Returns (exists, mtime_utc, age_hours, is_stale).
    """
    if not filepath.exists():
        return False, None, None, True

    mtime = os.path.getmtime(filepath)
    mtime_utc = datetime.fromtimestamp(mtime, tz=timezone.utc)
    age = datetime.now(timezone.utc) - mtime_utc
    age_hours = age.total_seconds() / 3600
    is_stale = age_hours > STALE_THRESHOLD_HOURS

    return True, mtime_utc, round(age_hours, 2), is_stale


def count_items(filepath, count_paths):
    """Count items in a JSON file based on the specified paths.
    Returns (count, field_name) or (None, None) if not countable.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None, None

    if not count_paths:
        return None, None

    # If root is a list, return its length directly
    if isinstance(data, list):
        return len(data), "root_array"

    for key, subkey in count_paths:
        if not isinstance(data, dict):
            continue
        val = data.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            return len(val), key
        elif isinstance(val, (int, float)):
            return int(val), key
        elif isinstance(val, dict) and subkey:
            sub_val = val.get(subkey)
            if isinstance(sub_val, list):
                return len(sub_val), f"{key}.{subkey}"
            elif isinstance(sub_val, (int, float)):
                return int(sub_val), f"{key}.{subkey}"

    # Try counting top-level arrays
    if isinstance(data, list):
        return len(data), "root_array"

    return None, None


def check_price_feed_binance():
    """Test Binance price feed with BTCUSDT."""
    print("  [PRICE] Testing Binance price feed (BTCUSDT)...")
    urls = [
        "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "https://api1.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "https://api2.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "https://api3.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
    ]

    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                price = float(data.get("price", 0))
                if price > 0:
                    print(f"    [OK] Binance BTCUSDT: ${price:,.2f}")
                    return {"status": "ok", "source": "binance", "symbol": "BTCUSDT", "price": price}
        except Exception:
            continue

    print("    [WARN] All Binance endpoints failed")
    return {"status": "failed", "source": "binance", "error": "All endpoints unreachable"}


def check_price_feed_coingecko():
    """Fallback: CoinGecko price feed."""
    print("  [PRICE] Testing CoinGecko price feed (BTC)...")
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            price = data.get("bitcoin", {}).get("usd", 0)
            if price > 0:
                print(f"    [OK] CoinGecko BTC: ${price:,.2f}")
                return {"status": "ok", "source": "coingecko", "symbol": "BTC", "price": price}
    except Exception as e:
        print(f"    [WARN] CoinGecko failed: {e}")

    return {"status": "failed", "source": "coingecko", "error": "Unreachable"}


def check_price_feed_yfinance():
    """Fallback: yfinance for forex/equity."""
    print("  [PRICE] Testing yfinance (EURUSD=X)...")
    try:
        import yfinance as yf
        ticker = yf.Ticker("EURUSD=X")
        hist = ticker.history(period="1d")
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            print(f"    [OK] yfinance EURUSD: {price:.4f}")
            return {"status": "ok", "source": "yfinance", "symbol": "EURUSD", "price": price}
    except ImportError:
        print("    [SKIP] yfinance not installed")
        return {"status": "skipped", "source": "yfinance", "error": "Not installed (pip install yfinance)"}
    except Exception as e:
        print(f"    [WARN] yfinance failed: {e}")

    return {"status": "failed", "source": "yfinance", "error": "Could not fetch data"}


def run_health_check():
    """Run full health check and save report."""
    now = datetime.now(timezone.utc)
    print("=" * 70)
    print("  COPY TRADER HEALTH CHECK")
    print(f"  {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    report = {
        "check_time": now.isoformat(),
        "stale_threshold_hours": STALE_THRESHOLD_HOURS,
        "files": {},
        "price_feeds": {},
        "summary": {
            "total_files": 0,
            "files_found": 0,
            "files_missing": 0,
            "files_stale": 0,
            "files_fresh": 0,
            "sources_with_zero_picks": 0,
            "price_feeds_ok": 0,
            "price_feeds_failed": 0,
            "overall_status": "UNKNOWN",
        },
        "alerts": [],
    }

    # 1. Check all monitored data files
    print("\n  FILE FRESHNESS CHECK")
    print("  " + "-" * 60)
    print(f"  {'File':40s} {'Status':>8s} {'Age (h)':>8s} {'Items':>8s}")
    print("  " + "-" * 60)

    for filename, config in MONITORED_FILES.items():
        filepath = DATA_DIR / filename
        exists, mtime, age_hours, is_stale = check_file_freshness(filepath)

        file_report = {
            "description": config.get("description", ""),
            "category": config.get("category", ""),
            "exists": exists,
            "last_modified": mtime.isoformat() if mtime else None,
            "age_hours": age_hours,
            "is_stale": is_stale,
            "item_count": None,
            "count_field": None,
        }

        report["summary"]["total_files"] += 1

        if not exists:
            report["summary"]["files_missing"] += 1
            status_str = "MISSING"
            age_str = "---"
            count_str = "---"
            report["alerts"].append({
                "severity": "warning",
                "file": filename,
                "message": f"File missing: {config.get('description', filename)}",
            })
        else:
            report["summary"]["files_found"] += 1

            skip_stale = config.get("skip_stale_check", False)
            if is_stale and not skip_stale:
                report["summary"]["files_stale"] += 1
                status_str = "STALE"
                report["alerts"].append({
                    "severity": "warning",
                    "file": filename,
                    "message": f"Stale data ({age_hours:.1f}h old): {config.get('description', filename)}",
                })
            else:
                report["summary"]["files_fresh"] += 1
                status_str = "OK"

            age_str = f"{age_hours:.1f}h" if age_hours is not None else "---"

            # Count items
            count_paths = config.get("count_paths", [])
            if count_paths:
                count, field = count_items(filepath, count_paths)
                file_report["item_count"] = count
                file_report["count_field"] = field
                if count is not None:
                    count_str = str(count)
                    if count == 0 and config.get("category") == "picks":
                        report["summary"]["sources_with_zero_picks"] += 1
                        report["alerts"].append({
                            "severity": "critical",
                            "file": filename,
                            "message": f"Zero picks in {config.get('description', filename)}!",
                        })
                        status_str = "EMPTY"
                else:
                    count_str = "---"
            else:
                count_str = "---"

        report["files"][filename] = file_report
        print(f"  {filename:40s} {status_str:>8s} {age_str:>8s} {count_str:>8s}")

    # 2. Check price feeds
    print("\n  PRICE FEED CHECK")
    print("  " + "-" * 60)

    binance_result = check_price_feed_binance()
    report["price_feeds"]["binance"] = binance_result
    if binance_result["status"] == "ok":
        report["summary"]["price_feeds_ok"] += 1
    else:
        report["summary"]["price_feeds_failed"] += 1
        report["alerts"].append({
            "severity": "critical",
            "source": "binance",
            "message": "Binance price feed unreachable!",
        })

    coingecko_result = check_price_feed_coingecko()
    report["price_feeds"]["coingecko"] = coingecko_result
    if coingecko_result["status"] == "ok":
        report["summary"]["price_feeds_ok"] += 1
    else:
        report["summary"]["price_feeds_failed"] += 1

    yfinance_result = check_price_feed_yfinance()
    report["price_feeds"]["yfinance"] = yfinance_result
    if yfinance_result["status"] == "ok":
        report["summary"]["price_feeds_ok"] += 1
    elif yfinance_result["status"] == "failed":
        report["summary"]["price_feeds_failed"] += 1

    # 3. Determine overall status
    critical_alerts = [a for a in report["alerts"] if a.get("severity") == "critical"]
    warning_alerts = [a for a in report["alerts"] if a.get("severity") == "warning"]

    if critical_alerts:
        report["summary"]["overall_status"] = "CRITICAL"
    elif len(warning_alerts) > 3:
        report["summary"]["overall_status"] = "DEGRADED"
    elif warning_alerts:
        report["summary"]["overall_status"] = "WARNING"
    else:
        report["summary"]["overall_status"] = "HEALTHY"

    # 4. Save report
    report_path = DATA_DIR / "health_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str, ensure_ascii=False)

    # 5. Print summary
    s = report["summary"]
    print("\n" + "=" * 70)
    print("  HEALTH SUMMARY")
    print("=" * 70)
    print(f"  Overall Status: {s['overall_status']}")
    print(f"  Files: {s['files_found']}/{s['total_files']} found, {s['files_fresh']} fresh, {s['files_stale']} stale, {s['files_missing']} missing")
    print(f"  Pick Sources: {s['sources_with_zero_picks']} with zero picks")
    print(f"  Price Feeds: {s['price_feeds_ok']} ok, {s['price_feeds_failed']} failed")

    if report["alerts"]:
        print(f"\n  ALERTS ({len(report['alerts'])} total):")
        for alert in report["alerts"]:
            sev = alert["severity"].upper()
            msg = alert["message"]
            print(f"    [{sev}] {msg}")

    print(f"\n  Report saved -> {report_path}")
    print("=" * 70)

    return report


if __name__ == "__main__":
    run_health_check()
