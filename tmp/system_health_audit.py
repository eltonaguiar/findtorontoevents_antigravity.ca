"""
System Health Audit — checks ALL trading systems for:
  1. Missing API failover (single-source dependency)
  2. Geo-blocked endpoints (403/blocked responses)
  3. Missing or stale data files
  4. Dead URLs / 404s
  5. Empty/corrupt JSON data
  
Run: python tmp/system_health_audit.py
"""
import json, os, sys, time, re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent.parent

# ── All known data endpoints (internal JSON files + external APIs) ──
INTERNAL_DATA_FILES = {
    # Battleground
    "battleground/active_picks": "battleground/data/active_picks.json",
    "battleground/closed_picks": "battleground/data/closed_picks.json",
    "battleground/strategies": "battleground/data/strategies_status.json",
    "battleground/luxalgo_active": "battleground/data/luxalgo_active_picks.json",
    "battleground/luxalgo_closed": "battleground/data/luxalgo_closed_picks.json",
    # KIMI / Rise of the Claw
    "kimi/live_signals": "KIMI_RISEOFTHECLAW/data/live_signals_now.json",
    "kimi/signal_tracking": "KIMI_RISEOFTHECLAW/data/signal_tracking.json",
    "kimi/active_picks": "KIMI_RISEOFTHECLAW/data/active_picks.json",
    "kimi/closed_picks": "KIMI_RISEOFTHECLAW/data/closed_picks.json",
    # Alpha Engine
    "alpha/active_picks": "alpha_engine/data/active_picks.json",
    "alpha/closed_picks": "alpha_engine/data/closed_picks.json",
    # Genome / DNA
    "genome/active_picks": "genome/data/active_picks.json",
    "genome/dna_winner_picks": "genome/data/dna_winner_picks.json",
    "genome/mutation_lab": "genome/data/mutation_lab_picks.json",
    "genome/mega_mutation": "genome/data/mega_mutation_picks.json",
    # Mercury2
    "mercury2/active_picks": "mercury2/data/active_picks.json",
    "mercury2/closed_picks": "mercury2/data/closed_picks.json",
    # Paper Trading
    "paper_trading/active_picks": "paper_trading/data/active_picks.json",
    # Crypto Signal Engine
    "signal_engine/active_picks": "crypto_signal_engine/data/active_picks.json",
    # ML Systems
    "ml_crypto_pred/active_picks": "ml_crypto_predictor/data/active_picks.json",
    "ml_crypto_pred/predictions": "predictions/data/active_picks.json",
    # Claude Gainer
    "claude_gainer/active_picks": "claude_gainer_ml/data/active_picks.json",
    "claude_gainer/performance": "claude_gainer_ml/tracker/claude_performance.json",
    # Rapid Fire / NOW
    "rapid_fire/active_picks": "rapid_fire/data/active_picks.json",
    # Signal Aggregator
    "aggregator/dashboard_data": "signal_aggregator/data/dashboard_data.json",
    # Competition
    "competition/active_picks": "competition/data/active_picks.json",
    # Audit output
    "audit/dashboard_payload": "audit_trail/data/dashboard_payload.json",
    "audit/dashboard_html": "audit_dashboard/index.html",
    # Spike Scanner
    "spike/active_picks": "spike_scanner/data/active_picks.json",
    # Coinglass
    "coinglass/active_picks": "coinglass/data/active_picks.json",
    # Revival
    "revival/active_picks": "revival/data/active_picks.json",
    # Goldmine
    "goldmine/active_picks": "goldmine/data/active_picks.json",
    # Incubator
    "incubator/active_picks": "incubator/data/active_picks.json",
    # Multi-Asset
    "multi_asset/active_picks": "multi_asset/data/active_picks.json",
    # Agreement Alpha
    "agreement_alpha/active_picks": "agreement_alpha/data/active_picks.json",
}

EXTERNAL_APIS = {
    "Binance Prices": {
        "url": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "failover": "https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT",
        "geo_risk": "Blocked in some US states, Ontario CA sometimes throttled",
    },
    "CoinGecko": {
        "url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        "failover": None,
        "geo_risk": "Rate-limited globally (10-50 req/min free tier)",
    },
    "Binance Klines": {
        "url": "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1",
        "failover": "https://api.binance.us/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1",
        "geo_risk": "Same as Binance Prices — Ontario/US restrictions",
    },
    "CoinGlass OI": {
        "url": "https://open-api-v3.coinglass.com/api/futures/openInterest/current?symbol=BTC",
        "failover": None,
        "geo_risk": "Requires API key, may be geo-restricted",
    },
}

# Systems that are KNOWN to depend on a single external API with no failover
SINGLE_SOURCE_RISKS = {
    "coinglass": {"api": "CoinGlass OI", "risk": "CoinGlass API key required, no failover endpoint", "severity": "HIGH"},
    "spike_scanner": {"api": "Binance", "risk": "Uses Binance klines only, no failover to Binance.US or CoinGecko", "severity": "MEDIUM"},
    "rapid_fire": {"api": "Binance", "risk": "NOW.py uses Binance 1h klines directly, Binance.US failover exists in code", "severity": "LOW"},
    "mercury2": {"api": "Multiple", "risk": "Uses ccxt library with exchange selection, relatively robust", "severity": "LOW"},
    "kimi_riseoftheclaw": {"api": "Binance + TradingView", "risk": "KIMI v11 uses multiple data sources, moderately resilient", "severity": "LOW"},
    "luxalgo_filters": {"api": "Binance", "risk": "Python filters use Binance klines via ccxt, no explicit failover", "severity": "MEDIUM"},
    "claude_gainer_ml": {"api": "Binance + CoinGecko", "risk": "Uses both APIs, CoinGecko as failover", "severity": "LOW"},
    "alpha_engine": {"api": "Multiple (ccxt)", "risk": "Multi-exchange support via ccxt, lowest risk", "severity": "LOW"},
    "battleground": {"api": "Binance + ccxt", "risk": "Core scanner uses ccxt with config, failover-capable", "severity": "LOW"},
    "genome": {"api": "Binance", "risk": "DNA evolution uses Binance klines directly, no exchange failover", "severity": "MEDIUM"},
}


def check_file(label, rel_path):
    """Check if a data file exists, is recent, and has valid content."""
    full_path = ROOT / rel_path
    result = {"label": label, "path": str(rel_path), "exists": False, "status": "MISSING", "severity": ""}
    
    if not full_path.exists():
        result["severity"] = "WARNING"
        return result
    
    result["exists"] = True
    stat = full_path.stat()
    result["size_kb"] = round(stat.st_size / 1024, 1)
    
    # Check age
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    age = datetime.now(timezone.utc) - mtime
    result["age_hours"] = round(age.total_seconds() / 3600, 1)
    result["last_modified"] = mtime.isoformat()
    
    # Age thresholds
    if age > timedelta(days=7):
        result["status"] = "STALE"
        result["severity"] = "HIGH"
    elif age > timedelta(days=2):
        result["status"] = "AGING"
        result["severity"] = "MEDIUM"
    else:
        result["status"] = "OK"
        result["severity"] = "LOW"
    
    # Check JSON validity
    if rel_path.endswith(".json"):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                result["keys"] = len(data)
                if not data:
                    result["status"] = "EMPTY"
                    result["severity"] = "MEDIUM"
            elif isinstance(data, list):
                result["items"] = len(data)
                if not data:
                    result["status"] = "EMPTY_LIST"
                    result["severity"] = "MEDIUM"
        except json.JSONDecodeError as e:
            result["status"] = "CORRUPT_JSON"
            result["severity"] = "HIGH"
            result["error"] = str(e)[:100]
        except Exception as e:
            result["status"] = "READ_ERROR"
            result["severity"] = "HIGH"
            result["error"] = str(e)[:100]
    
    return result


def check_api(label, config):
    """Test an external API endpoint for availability and geo-blocking."""
    result = {
        "label": label,
        "url": config["url"],
        "status": "UNKNOWN",
        "failover": config.get("failover"),
        "geo_risk": config.get("geo_risk", ""),
        "has_failover": config.get("failover") is not None,
    }
    
    # Test primary endpoint
    try:
        req = Request(config["url"], headers={"User-Agent": "Mozilla/5.0 (audit-check)"})
        resp = urlopen(req, timeout=10)
        result["status_code"] = resp.getcode()
        body = resp.read().decode("utf-8", errors="replace")[:500]
        result["response_size"] = len(body)
        
        if resp.getcode() == 200:
            result["status"] = "OK"
            result["severity"] = "LOW"
            # Try to parse JSON
            try:
                data = json.loads(body)
                if isinstance(data, dict) and data.get("code"):
                    # Some APIs return 200 but with error codes
                    result["api_code"] = data.get("code")
                    result["api_msg"] = data.get("msg", "")[:100]
            except:
                pass
        elif resp.getcode() == 403:
            result["status"] = "GEO_BLOCKED"
            result["severity"] = "HIGH"
        elif resp.getcode() == 429:
            result["status"] = "RATE_LIMITED"
            result["severity"] = "MEDIUM"
        else:
            result["status"] = f"HTTP_{resp.getcode()}"
            result["severity"] = "MEDIUM"
    except HTTPError as e:
        result["status_code"] = e.code
        if e.code == 451 or e.code == 403:
            result["status"] = "GEO_BLOCKED"
            result["severity"] = "HIGH"
        elif e.code == 429:
            result["status"] = "RATE_LIMITED"
            result["severity"] = "MEDIUM"
        else:
            result["status"] = f"HTTP_{e.code}"
            result["severity"] = "MEDIUM"
    except URLError as e:
        result["status"] = "CONNECTION_FAILED"
        result["severity"] = "HIGH"
        result["error"] = str(e.reason)[:100]
    except Exception as e:
        result["status"] = "ERROR"
        result["severity"] = "HIGH"
        result["error"] = str(e)[:100]
    
    # Test failover if primary failed and failover exists
    if result.get("severity") in ("HIGH", "MEDIUM") and config.get("failover"):
        try:
            req2 = Request(config["failover"], headers={"User-Agent": "Mozilla/5.0 (audit-check)"})
            resp2 = urlopen(req2, timeout=10)
            result["failover_status"] = "OK" if resp2.getcode() == 200 else f"HTTP_{resp2.getcode()}"
            result["failover_works"] = resp2.getcode() == 200
        except Exception as e2:
            result["failover_status"] = "FAILED"
            result["failover_works"] = False
            result["failover_error"] = str(e2)[:100]
    
    return result


def check_github_actions():
    """Check GitHub Actions workflow files for data pipeline reliability."""
    workflows_dir = ROOT / ".github" / "workflows"
    if not workflows_dir.exists():
        return {"status": "NO_WORKFLOWS_DIR", "severity": "HIGH"}
    
    results = []
    for yml_file in sorted(workflows_dir.glob("*.yml")):
        name = yml_file.stem
        content = yml_file.read_text(encoding="utf-8", errors="replace")
        
        has_retry = "retry" in content.lower() or "attempts" in content.lower()
        has_timeout = "timeout" in content.lower()
        has_error_handling = "continue-on-error" in content or "if: failure()" in content
        has_cron = "cron" in content.lower() or "schedule" in content.lower()
        
        # Check for API calls without failover
        apis_used = []
        if "binance" in content.lower():
            apis_used.append("Binance")
        if "coingecko" in content.lower():
            apis_used.append("CoinGecko")
        if "coinglass" in content.lower():
            apis_used.append("CoinGlass")
        if "ccxt" in content.lower():
            apis_used.append("ccxt (multi-exchange)")
        
        severity = "LOW"
        issues = []
        if apis_used and not has_retry:
            issues.append("No retry logic for API calls")
            severity = "MEDIUM"
        if apis_used and not has_error_handling:
            issues.append("No continue-on-error for API steps")
        if not has_timeout:
            issues.append("No timeout specified")
        
        results.append({
            "workflow": name,
            "has_retry": has_retry,
            "has_timeout": has_timeout,
            "has_error_handling": has_error_handling,
            "has_schedule": has_cron,
            "apis_used": apis_used,
            "issues": issues,
            "severity": severity,
        })
    
    return results


def main():
    print("=" * 80)
    print("  SYSTEM HEALTH AUDIT — API Failover & Data Integrity")
    print(f"  Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)
    
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_files": [],
        "api_endpoints": [],
        "single_source_risks": [],
        "github_actions": [],
        "summary": {},
    }
    
    # 1. Check internal data files
    print("\n🔍 Checking internal data files...")
    missing = 0
    stale = 0
    corrupt = 0
    ok = 0
    for label, rel_path in sorted(INTERNAL_DATA_FILES.items()):
        result = check_file(label, rel_path)
        report["data_files"].append(result)
        icon = {"OK": "✅", "AGING": "⚠️", "STALE": "🔴", "MISSING": "❌", "EMPTY": "📭", "EMPTY_LIST": "📭", "CORRUPT_JSON": "💥", "READ_ERROR": "💥"}.get(result["status"], "❓")
        extra = ""
        if result.get("age_hours"):
            extra = f" ({result['age_hours']}h old, {result.get('size_kb', 0)}KB)"
        if result.get("items") is not None:
            extra += f" [{result['items']} items]"
        elif result.get("keys") is not None:
            extra += f" [{result['keys']} keys]"
        print(f"  {icon} {label}: {result['status']}{extra}")
        if result["status"] == "MISSING": missing += 1
        elif result["status"] in ("STALE", "CORRUPT_JSON", "READ_ERROR"): stale += 1
        elif result["status"] == "OK": ok += 1
    
    # 2. Check external APIs
    print("\n🌐 Checking external API endpoints...")
    for label, config in EXTERNAL_APIS.items():
        result = check_api(label, config)
        report["api_endpoints"].append(result)
        icon = "✅" if result["status"] == "OK" else "🔴" if result["severity"] == "HIGH" else "⚠️"
        failover_info = ""
        if result.get("failover_works") is not None:
            failover_info = f" | Failover: {'✅' if result['failover_works'] else '❌'}"
        print(f"  {icon} {label}: {result['status']}{failover_info}")
        if result.get("geo_risk"):
            print(f"      ⚡ Geo risk: {result['geo_risk']}")
    
    # 3. Single-source dependency analysis
    print("\n⚡ Single-source API dependencies (no failover)...")
    for sys_name, info in sorted(SINGLE_SOURCE_RISKS.items(), key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x[1]["severity"], 3)):
        icon = {"HIGH": "🔴", "MEDIUM": "⚠️", "LOW": "✅"}.get(info["severity"], "❓")
        report["single_source_risks"].append({"system": sys_name, **info})
        print(f"  {icon} [{info['severity']}] {sys_name}")
        print(f"      API: {info['api']} — {info['risk']}")
    
    # 4. GitHub Actions audit
    print("\n🤖 Checking GitHub Actions workflows...")
    workflows = check_github_actions()
    if isinstance(workflows, dict):
        print(f"  ❌ {workflows['status']}")
    else:
        report["github_actions"] = workflows
        for wf in workflows:
            if wf["apis_used"]:
                icon = "⚠️" if wf["issues"] else "✅"
                apis = ", ".join(wf["apis_used"])
                print(f"  {icon} {wf['workflow']}: APIs=[{apis}]")
                for issue in wf["issues"]:
                    print(f"      ⚠️ {issue}")
    
    # 5. Summary
    high_issues = sum(1 for f in report["data_files"] if f["severity"] == "HIGH")
    high_issues += sum(1 for a in report["api_endpoints"] if a["severity"] == "HIGH")
    high_issues += sum(1 for r in report["single_source_risks"] if r["severity"] == "HIGH")
    
    medium_issues = sum(1 for f in report["data_files"] if f["severity"] == "MEDIUM")
    medium_issues += sum(1 for a in report["api_endpoints"] if a["severity"] == "MEDIUM")
    medium_issues += sum(1 for r in report["single_source_risks"] if r["severity"] == "MEDIUM")
    
    report["summary"] = {
        "total_files_checked": len(report["data_files"]),
        "files_ok": ok,
        "files_missing": missing,
        "files_stale": stale,
        "files_corrupt": corrupt,
        "total_apis_checked": len(report["api_endpoints"]),
        "apis_ok": sum(1 for a in report["api_endpoints"] if a["status"] == "OK"),
        "high_severity_issues": high_issues,
        "medium_severity_issues": medium_issues,
        "systems_no_failover": sum(1 for r in report["single_source_risks"] if r["severity"] in ("HIGH", "MEDIUM")),
    }
    
    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    s = report["summary"]
    print(f"  📁 Data Files: {s['files_ok']} OK, {s['files_missing']} missing, {s['files_stale']} stale/corrupt")
    print(f"  🌐 APIs: {s['apis_ok']}/{s['total_apis_checked']} reachable")
    print(f"  🔴 HIGH severity: {s['high_severity_issues']}")
    print(f"  ⚠️  MEDIUM severity: {s['medium_severity_issues']}")
    print(f"  ⚡ Systems with no/weak failover: {s['systems_no_failover']}")
    
    # Write report
    report_path = ROOT / "tmp" / "system_health_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  📄 Full report: {report_path}")
    
    return report


if __name__ == "__main__":
    main()
