#!/usr/bin/env python3
"""
Meme Coin Scanner Monitor
Tracks data freshness, alerts on issues, and provides health checks
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

# Configuration
SCANNER_API = "https://findtorontoevents.ca/findcryptopairs/api/meme_scanner.php"
FRESHNESS_THRESHOLD_MINUTES = 15
ALERT_WEBHOOK = os.getenv('DISCORD_WEBHOOK_URL', '')  # Optional Discord alerts

class MemeScannerMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MemeScanner-Monitor/1.0'
        })
        self.alerts_sent = []
    
    def check_freshness(self) -> Dict:
        """Check if scanner data is fresh"""
        try:
            resp = self.session.get(
                f"{SCANNER_API}?action=stats",
                timeout=30
            )
            data = resp.json()
            
            if not data.get('ok'):
                return {
                    'status': 'error',
                    'message': data.get('error', 'Unknown error'),
                    'fresh': False
                }
            
            stats = data.get('stats', {})
            last_scan = stats.get('last_scan')
            freshness = stats.get('data_freshness', 'unknown')
            
            if last_scan:
                last_scan_time = datetime.fromisoformat(last_scan.replace('Z', '+00:00'))
                minutes_ago = (datetime.utcnow() - last_scan_time.replace(tzinfo=None)).total_seconds() / 60
                
                return {
                    'status': freshness,
                    'last_scan': last_scan,
                    'minutes_ago': round(minutes_ago, 1),
                    'fresh': minutes_ago < FRESHNESS_THRESHOLD_MINUTES,
                    'win_rate': stats.get('overall_win_rate'),
                    'total_signals': stats.get('total_signals'),
                    'version': stats.get('scanner_version', 'unknown')
                }
            else:
                return {
                    'status': 'no_data',
                    'message': 'No scan data available',
                    'fresh': False
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'fresh': False
            }
    
    def check_performance(self) -> Dict:
        """Check recent performance metrics"""
        try:
            resp = self.session.get(
                f"{SCANNER_API}?action=stats",
                timeout=30
            )
            data = resp.json()
            
            if not data.get('ok'):
                return {'status': 'error', 'message': data.get('error')}
            
            stats = data.get('stats', {})
            win_rate = stats.get('overall_win_rate', 0)
            
            # Determine performance status
            if win_rate >= 40:
                perf_status = 'good'
            elif win_rate >= 20:
                perf_status = 'fair'
            elif win_rate >= 5:
                perf_status = 'poor'
            else:
                perf_status = 'critical'
            
            return {
                'status': perf_status,
                'win_rate': win_rate,
                'avg_pnl': stats.get('avg_pnl'),
                'total_signals': stats.get('total_signals'),
                'signals_7d': stats.get('signals_7d'),
                'assessment': self._get_assessment(perf_status, win_rate)
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _get_assessment(self, status: str, win_rate: float) -> str:
        """Get human-readable assessment"""
        assessments = {
            'good': f"Win rate {win_rate}% meets 40%+ target",
            'fair': f"Win rate {win_rate}% below target but functional",
            'poor': f"Win rate {win_rate}% critically low - immediate attention needed",
            'critical': f"Win rate {win_rate}% - scanner fundamentally broken"
        }
        return assessments.get(status, 'Unknown status')
    
    def send_alert(self, message: str, severity: str = 'warning'):
        """Send alert via Discord webhook or console"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        full_message = f"[{timestamp}] [{severity.upper()}] {message}"
        
        print(full_message)
        self.alerts_sent.append({'time': timestamp, 'message': message, 'severity': severity})
        
        # Send to Discord if configured
        if ALERT_WEBHOOK and severity in ['error', 'critical']:
            try:
                color = {'warning': 0xffa500, 'error': 0xff0000, 'critical': 0x8b0000}
                payload = {
                    'embeds': [{
                        'title': f'Meme Scanner Alert - {severity.upper()}',
                        'description': message,
                        'color': color.get(severity, 0xffa500),
                        'timestamp': datetime.utcnow().isoformat()
                    }]
                }
                import time as _time
                for _attempt in range(3):
                    try:
                        _r = requests.post(ALERT_WEBHOOK, json=payload, timeout=10)
                        if _r.status_code in (200, 204):
                            break
                        if _r.status_code == 429:
                            _time.sleep(_r.json().get("retry_after", 3))
                            continue
                        if _attempt < 2:
                            _time.sleep(2 * (_attempt + 1))
                        break
                    except Exception as _e:
                        if _attempt == 2:
                            print(f"Failed to send Discord alert after 3 attempts: {_e}")
                        else:
                            _time.sleep(2 * (_attempt + 1))
            except Exception as e:
                print(f"Failed to send Discord alert: {e}")
    
    def run_health_check(self) -> Dict:
        """Run complete health check"""
        print("="*60)
        print("MEME COIN SCANNER HEALTH CHECK")
        print("="*60)
        print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {},
            'overall_status': 'unknown'
        }
        
        # Check 1: Data Freshness
        print("[1/3] Checking data freshness...")
        freshness = self.check_freshness()
        results['checks']['freshness'] = freshness
        
        if freshness.get('fresh'):
            print(f"   ✅ Data is fresh ({freshness['minutes_ago']} min ago)")
        elif freshness.get('status') == 'stale':
            print(f"   ⚠️  Data is stale ({freshness['minutes_ago']} min ago)")
            self.send_alert(f"Scanner data is stale: {freshness['minutes_ago']:.1f} minutes old", 'warning')
        else:
            print(f"   ❌ Data freshness issue: {freshness.get('message', 'Unknown')}")
            self.send_alert(f"Scanner data freshness critical: {freshness.get('message')}", 'critical')
        
        print(f"   Version: {freshness.get('version', 'unknown')}")
        print()
        
        # Check 2: Performance
        print("[2/3] Checking performance metrics...")
        performance = self.check_performance()
        results['checks']['performance'] = performance
        
        status_icons = {'good': '✅', 'fair': '⚠️', 'poor': '❌', 'critical': '🔴', 'error': '💥'}
        icon = status_icons.get(performance.get('status'), '❓')
        
        print(f"   {icon} Win Rate: {performance.get('win_rate')}%")
        print(f"   📊 Avg P&L: {performance.get('avg_pnl')}%")
        print(f"   📈 Total Signals: {performance.get('total_signals')}")
        print(f"   📝 Assessment: {performance.get('assessment')}")
        
        if performance.get('status') == 'critical':
            self.send_alert(f"Scanner performance critical: {performance.get('win_rate')}% WR", 'critical')
        elif performance.get('status') == 'poor':
            self.send_alert(f"Scanner performance poor: {performance.get('win_rate')}% WR", 'error')
        
        print()
        
        # Check 3: Signal Count
        print("[3/3] Checking signal volume...")
        signals_7d = performance.get('signals_7d', 0)
        
        if signals_7d >= 50:
            print(f"   ✅ Good signal volume: {signals_7d} signals (7d)")
            results['checks']['volume'] = {'status': 'good', 'count': signals_7d}
        elif signals_7d >= 20:
            print(f"   ⚠️  Low signal volume: {signals_7d} signals (7d)")
            results['checks']['volume'] = {'status': 'fair', 'count': signals_7d}
        else:
            print(f"   ❌ Very low signal volume: {signals_7d} signals (7d)")
            results['checks']['volume'] = {'status': 'poor', 'count': signals_7d}
            self.send_alert(f"Low signal volume: only {signals_7d} signals in 7 days", 'warning')
        
        print()
        
        # Overall status
        if all(c.get('fresh') or c.get('status') in ['good', 'fair'] for c in results['checks'].values()):
            results['overall_status'] = 'healthy'
            print("="*60)
            print("✅ OVERALL STATUS: HEALTHY")
        else:
            results['overall_status'] = 'issues_detected'
            print("="*60)
            print("❌ OVERALL STATUS: ISSUES DETECTED")
        
        print("="*60)
        
        return results
    
    def save_report(self, results: Dict, filename: str = 'meme_scanner_health.json'):
        """Save health check results"""
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nReport saved to: {filename}")

def main():
    monitor = MemeScannerMonitor()
    results = monitor.run_health_check()
    monitor.save_report(results)
    
    # Exit with error code if critical issues
    if results['overall_status'] == 'issues_detected':
        sys.exit(1)
    
    sys.exit(0)

if __name__ == '__main__':
    main()
