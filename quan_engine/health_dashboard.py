"""
QuanEngine Health Dashboard
===========================
Real-time health monitoring for all critical components and failovers.
Exposes a JSON endpoint for external monitoring and a CLI view.

Components Monitored:
  - Data sources (yfinance, Binance, CoinGecko, CryptoCompare)
  - Notification channels (Discord, Email, Slack)
  - Database connectivity
  - Disk space
  - API rate limits
  - Last successful scan

Usage:
    python health_dashboard.py --check     # Quick health check
    python health_dashboard.py --serve     # Start HTTP server
    python health_dashboard.py --report    # Generate full report
"""

import os
import sys
import json
import time
import sqlite3
import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from quan_engine import config
from quan_engine.failover_system import get_failover_fetcher, get_health_report as get_data_health
from shared.failover_notifications import get_notification_health

logger = logging.getLogger("QuanEngine.Health")

# ============================================================================
# HEALTH CHECK CLASSES
# ============================================================================

@dataclass
class HealthStatus:
    """Status of a health check."""
    component: str
    status: str  # "healthy", "degraded", "critical"
    message: str
    last_check: str
    metrics: dict = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
        if isinstance(self.last_check, datetime):
            self.last_check = self.last_check.isoformat()


class HealthChecker:
    """Base class for health checks."""
    
    def __init__(self, name: str):
        self.name = name
    
    def check(self) -> HealthStatus:
        raise NotImplementedError


class DataSourceHealthChecker(HealthChecker):
    """Check health of data sources."""
    
    def __init__(self):
        super().__init__("data_sources")
    
    def check(self) -> HealthStatus:
        health = get_data_health()
        
        # Count healthy sources
        total = len(health)
        healthy = sum(1 for h in health.values() if h.get("is_healthy", False))
        
        # Determine status
        if healthy == total:
            status = "healthy"
            message = f"All {total} data sources healthy"
        elif healthy >= total / 2:
            status = "degraded"
            message = f"{healthy}/{total} data sources healthy"
        else:
            status = "critical"
            message = f"Only {healthy}/{total} data sources healthy"
        
        return HealthStatus(
            component=self.name,
            status=status,
            message=message,
            last_check=datetime.utcnow().isoformat(),
            metrics={
                "total_sources": total,
                "healthy_sources": healthy,
                "sources": health,
            }
        )


class NotificationHealthChecker(HealthChecker):
    """Check health of notification channels."""
    
    def __init__(self):
        super().__init__("notifications")
    
    def check(self) -> HealthStatus:
        health = get_notification_health()
        
        total = len(health)
        available = sum(1 for h in health.values() if h.get("available", False))
        
        # Check if file fallback is available (it should always be)
        file_available = health.get("file_fallback", {}).get("available", False)
        
        if available == total:
            status = "healthy"
            message = f"All {total} notification channels available"
        elif file_available:
            status = "degraded"
            message = f"{available}/{total} channels available, file fallback active"
        else:
            status = "critical"
            message = f"Only {available}/{total} channels available, no fallback!"
        
        return HealthStatus(
            component=self.name,
            status=status,
            message=message,
            last_check=datetime.utcnow().isoformat(),
            metrics={
                "total_channels": total,
                "available_channels": available,
                "channels": health,
            }
        )


class DatabaseHealthChecker(HealthChecker):
    """Check database connectivity."""
    
    def __init__(self):
        super().__init__("database")
    
    def check(self) -> HealthStatus:
        try:
            conn = sqlite3.connect(config.DB_PATH, timeout=5)
            cursor = conn.execute("SELECT COUNT(*) FROM signals")
            count = cursor.fetchone()[0]
            conn.close()
            
            return HealthStatus(
                component=self.name,
                status="healthy",
                message=f"Database connected, {count} signals stored",
                last_check=datetime.utcnow().isoformat(),
                metrics={"total_signals": count, "path": config.DB_PATH}
            )
        except Exception as e:
            return HealthStatus(
                component=self.name,
                status="critical",
                message=f"Database error: {e}",
                last_check=datetime.utcnow().isoformat(),
                metrics={"error": str(e)}
            )


class DiskSpaceHealthChecker(HealthChecker):
    """Check disk space availability."""
    
    def __init__(self):
        super().__init__("disk_space")
    
    def check(self) -> HealthStatus:
        try:
            import shutil
            stat = shutil.disk_usage(config.DATA_DIR)
            
            total_gb = stat.total / (1024**3)
            free_gb = stat.free / (1024**3)
            used_pct = (stat.used / stat.total) * 100
            
            if used_pct < 80:
                status = "healthy"
            elif used_pct < 90:
                status = "degraded"
            else:
                status = "critical"
            
            return HealthStatus(
                component=self.name,
                status=status,
                message=f"{free_gb:.1f}GB free ({100-used_pct:.1f}% available)",
                last_check=datetime.utcnow().isoformat(),
                metrics={
                    "total_gb": round(total_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "used_percent": round(used_pct, 2),
                }
            )
        except Exception as e:
            return HealthStatus(
                component=self.name,
                status="critical",
                message=f"Cannot check disk space: {e}",
                last_check=datetime.utcnow().isoformat(),
                metrics={"error": str(e)}
            )


class LastScanHealthChecker(HealthChecker):
    """Check when the last scan was performed."""
    
    def __init__(self):
        super().__init__("last_scan")
    
    def check(self) -> HealthStatus:
        try:
            # Check signals file
            if not os.path.exists(config.SIGNALS_PATH):
                return HealthStatus(
                    component=self.name,
                    status="critical",
                    message="No signals file found",
                    last_check=datetime.utcnow().isoformat(),
                    metrics={"file": config.SIGNALS_PATH}
                )
            
            mtime = os.path.getmtime(config.SIGNALS_PATH)
            last_scan = datetime.fromtimestamp(mtime)
            age_minutes = (datetime.now() - last_scan).total_seconds() / 60
            
            if age_minutes < 35:  # Scans run every 30 min
                status = "healthy"
                message = f"Last scan {age_minutes:.0f} minutes ago"
            elif age_minutes < 60:
                status = "degraded"
                message = f"Last scan {age_minutes:.0f} minutes ago (delayed)"
            else:
                status = "critical"
                message = f"Last scan {age_minutes:.0f} minutes ago (stale!)"
            
            return HealthStatus(
                component=self.name,
                status=status,
                message=message,
                last_check=datetime.utcnow().isoformat(),
                metrics={
                    "last_scan": last_scan.isoformat(),
                    "age_minutes": round(age_minutes, 1),
                }
            )
        except Exception as e:
            return HealthStatus(
                component=self.name,
                status="critical",
                message=f"Error checking last scan: {e}",
                last_check=datetime.utcnow().isoformat(),
                metrics={"error": str(e)}
            )


class GitHubActionsHealthChecker(HealthChecker):
    """Check GitHub Actions workflow status."""
    
    def __init__(self):
        super().__init__("github_actions")
    
    def check(self) -> HealthStatus:
        # This is a placeholder - in production, you'd query the GitHub API
        return HealthStatus(
            component=self.name,
            status="healthy",
            message="GitHub Actions workflows operational (assumed)",
            last_check=datetime.utcnow().isoformat(),
            metrics={}
        )


# ============================================================================
# HEALTH DASHBOARD
# ============================================================================

class HealthDashboard:
    """Main health dashboard coordinator."""
    
    def __init__(self):
        self.checkers: List[HealthChecker] = [
            DataSourceHealthChecker(),
            NotificationHealthChecker(),
            DatabaseHealthChecker(),
            DiskSpaceHealthChecker(),
            LastScanHealthChecker(),
            GitHubActionsHealthChecker(),
        ]
    
    def run_all_checks(self) -> Dict[str, HealthStatus]:
        """Run all health checks."""
        results = {}
        for checker in self.checkers:
            try:
                results[checker.name] = checker.check()
            except Exception as e:
                results[checker.name] = HealthStatus(
                    component=checker.name,
                    status="critical",
                    message=f"Health check failed: {e}",
                    last_check=datetime.utcnow().isoformat(),
                )
        return results
    
    def get_overall_status(self, results: Dict[str, HealthStatus]) -> str:
        """Determine overall system status."""
        statuses = [r.status for r in results.values()]
        
        if any(s == "critical" for s in statuses):
            return "critical"
        elif any(s == "degraded" for s in statuses):
            return "degraded"
        return "healthy"
    
    def generate_report(self) -> dict:
        """Generate full health report."""
        results = self.run_all_checks()
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": self.get_overall_status(results),
            "checks": {name: asdict(status) for name, status in results.items()},
        }
        
        # Add summary
        healthy = sum(1 for r in results.values() if r.status == "healthy")
        degraded = sum(1 for r in results.values() if r.status == "degraded")
        critical = sum(1 for r in results.values() if r.status == "critical")
        
        report["summary"] = {
            "total_checks": len(results),
            "healthy": healthy,
            "degraded": degraded,
            "critical": critical,
        }
        
        return report
    
    def print_report(self, report: dict = None):
        """Print report to console."""
        if report is None:
            report = self.generate_report()
        
        print("\n" + "=" * 70)
        print(f"QuanEngine Health Report - {report['timestamp']}")
        print("=" * 70)
        
        # Overall status with color
        status = report['overall_status']
        status_emoji = {"healthy": "✅", "degraded": "⚠️", "critical": "🚨"}.get(status, "❓")
        print(f"\nOverall Status: {status_emoji} {status.upper()}")
        
        # Summary
        summary = report['summary']
        print(f"\nSummary: {summary['healthy']} healthy, {summary['degraded']} degraded, {summary['critical']} critical")
        
        # Individual checks
        print("\n" + "-" * 70)
        print("Component Details:")
        print("-" * 70)
        
        for name, check in report['checks'].items():
            emoji = {"healthy": "✅", "degraded": "⚠️", "critical": "🚨"}.get(check['status'], "❓")
            print(f"\n{emoji} {name.upper()}")
            print(f"   Status: {check['status']}")
            print(f"   Message: {check['message']}")
            if check.get('metrics'):
                print(f"   Metrics: {json.dumps(check['metrics'], indent=6)[:200]}...")
        
        print("\n" + "=" * 70)


# ============================================================================
# HTTP SERVER
# ============================================================================

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for health endpoint."""
    
    dashboard = HealthDashboard()
    
    def do_GET(self):
        if self.path == "/health":
            report = self.dashboard.generate_report()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(report, indent=2).encode())
        elif self.path == "/healthz":
            # Kubernetes-style liveness probe
            report = self.dashboard.generate_report()
            if report['overall_status'] == 'critical':
                self.send_response(503)
            else:
                self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": report['overall_status']}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress request logging
        pass


def serve_dashboard(port: int = 8080):
    """Start HTTP server for health dashboard."""
    server = HTTPServer(("", port), HealthHandler)
    print(f"Health dashboard serving on http://localhost:{port}/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="QuanEngine Health Dashboard")
    parser.add_argument("--check", action="store_true", help="Quick health check (exit code 0 if healthy)")
    parser.add_argument("--report", action="store_true", help="Generate and print full report")
    parser.add_argument("--serve", action="store_true", help="Start HTTP server")
    parser.add_argument("--port", type=int, default=8080, help="HTTP server port (default: 8080)")
    parser.add_argument("--json", action="store_true", help="Output report as JSON")
    parser.add_argument("--watch", type=int, metavar="SECONDS", help="Watch mode - refresh every N seconds")
    
    args = parser.parse_args()
    
    dashboard = HealthDashboard()
    
    if args.serve:
        serve_dashboard(args.port)
    elif args.check:
        report = dashboard.generate_report()
        if args.json:
            print(json.dumps(report))
        else:
            dashboard.print_report(report)
        # Exit with error code if critical
        sys.exit(0 if report['overall_status'] != 'critical' else 1)
    elif args.report:
        report = dashboard.generate_report()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            dashboard.print_report(report)
    elif args.watch:
        while True:
            os.system('clear' if os.name != 'nt' else 'cls')
            report = dashboard.generate_report()
            dashboard.print_report(report)
            print(f"\nRefreshing in {args.watch} seconds... (Ctrl+C to exit)")
            time.sleep(args.watch)
    else:
        # Default: print report
        report = dashboard.generate_report()
        dashboard.print_report(report)


if __name__ == "__main__":
    main()
