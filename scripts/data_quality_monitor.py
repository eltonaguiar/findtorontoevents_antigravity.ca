#!/usr/bin/env python3
"""
Data Quality Monitor — Automated freshness, completeness, and health checks
for the stock prediction system.

Detects stale data, missing coverage, failed APIs, and degraded signal quality.
Sends Discord alerts for critical issues and retries failed operations.

Runs every 3 hours via GitHub Actions (data-quality-monitor.yml).
"""
import os
import sys
import json
import time
import traceback
from datetime import datetime, timedelta

import requests

# ---------------------------------------------------------------------------
# Configuration (all from environment variables)
# ---------------------------------------------------------------------------
API_BASE = os.environ.get('SM_API_BASE', 'https://findtorontoevents.ca/live-monitor/api')
ADMIN_KEY = os.environ.get('SM_ADMIN_KEY', 'livetrader2026')
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK_URL', '')

DB_HOST = os.environ.get('DB_HOST', 'mysql.50webs.com')
DB_USER = os.environ.get('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.environ.get('DB_PASS', 'stocks')
DB_NAME = os.environ.get('DB_NAME', 'ejaguiar1_stocks')

API_HEADERS = {"User-Agent": "WorldClassIntelligence/1.0"}

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 5  # seconds

# ---------------------------------------------------------------------------
# Freshness thresholds per table
# ---------------------------------------------------------------------------
FRESHNESS_THRESHOLDS = {
    'lm_price_cache': {'max_age_hours': 2, 'critical': True},
    'lm_signals': {'max_age_hours': 24, 'critical': True},
    'lm_trades': {'max_age_hours': 48, 'critical': False},
    'lm_market_regime': {'max_age_hours': 36, 'critical': True},
    'lm_snapshots': {'max_age_hours': 4, 'critical': False},
    'lm_kelly_fractions': {'max_age_hours': 48, 'critical': False},
    'lm_position_sizing': {'max_age_hours': 36, 'critical': False},
    'smart_money_consensus': {'max_age_hours': 48, 'critical': False},
    'daily_prices': {'max_age_hours': 48, 'critical': True},
}

# Completeness: expected minimum row counts
COMPLETENESS_EXPECTATIONS = {
    'lm_price_cache': {'expected_symbols': 52, 'min_pct': 80},  # 32 crypto + 8 forex + 12 stock
}

# API health check endpoints
API_HEALTH_CHECKS = [
    {'name': 'live_prices', 'url': f'{API_BASE}/live_prices.php?action=status'},
    {'name': 'dashboard', 'url': f'{API_BASE}/live_trade.php?action=dashboard'},
    {'name': 'signals', 'url': f'{API_BASE}/live_signals.php?action=list'},
    {'name': 'regime', 'url': f'{API_BASE}/regime.php?action=get_regime'},
    {'name': 'breakers', 'url': f'{API_BASE}/breaker_live.php?action=status'},
]

# Retry actions when data is stale
RETRY_ACTIONS = {
    'lm_price_cache': f'{API_BASE}/live_prices.php?action=fetch&key={ADMIN_KEY}',
    'lm_signals': f'{API_BASE}/live_signals.php?action=scan&key={ADMIN_KEY}',
}


# ---------------------------------------------------------------------------
# Discord alerting
# ---------------------------------------------------------------------------
def send_alert(title, message, severity='warning'):
    """Send alert to Discord webhook. Falls back to stdout if no webhook."""
    color_map = {'critical': 0xFF0000, 'warning': 0xFFAA00, 'ok': 0x00FF00}
    color = color_map.get(severity, 0xFFAA00)

    if not DISCORD_WEBHOOK:
        print(f"[{severity.upper()}] {title}: {message}")
        return

    payload = {
        'embeds': [{
            'title': f'Data Quality: {title}',
            'description': message,
            'color': color,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'footer': {'text': 'Data Quality Monitor'}
        }]
    }
    try:
        resp = requests.post(DISCORD_WEBHOOK, json=payload, headers=API_HEADERS, timeout=10)
        if resp.status_code == 204:
            print(f"  Discord alert sent: {title}")
        else:
            print(f"  Discord alert failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        print(f"  Discord alert error: {e}")


# ---------------------------------------------------------------------------
# 1. Check Data Freshness
# ---------------------------------------------------------------------------
def check_data_freshness(conn):
    """Check MAX(updated_at) or MAX(created_at) for each monitored table."""
    print("\n=== Data Freshness Check ===")
    cursor = conn.cursor(dictionary=True)
    now = datetime.utcnow()
    results = {}

    for table, config in FRESHNESS_THRESHOLDS.items():
        try:
            # Try updated_at first, fall back to created_at
            ts_col = None
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            cols = [row['Field'] for row in cursor.fetchall()]
            if 'updated_at' in cols:
                ts_col = 'updated_at'
            elif 'created_at' in cols:
                ts_col = 'created_at'
            elif 'timestamp' in cols:
                ts_col = 'timestamp'
            elif 'fetched_at' in cols:
                ts_col = 'fetched_at'

            if not ts_col:
                print(f"  {table}: No timestamp column found, skipping")
                results[table] = {
                    'status': 'UNKNOWN',
                    'last_update': None,
                    'age_hours': None,
                    'row_count': 0,
                    'critical': config['critical'],
                }
                continue

            cursor.execute(f"SELECT MAX(`{ts_col}`) as last_ts, COUNT(*) as cnt FROM `{table}`")
            row = cursor.fetchone()
            last_ts = row['last_ts']
            row_count = row['cnt']

            if last_ts is None or row_count == 0:
                status = 'CRITICAL' if config['critical'] else 'STALE'
                age_hours = None
                print(f"  {table}: EMPTY ({status})")
            else:
                if isinstance(last_ts, str):
                    last_ts = datetime.strptime(last_ts, '%Y-%m-%d %H:%M:%S')
                age = now - last_ts
                age_hours = round(age.total_seconds() / 3600, 1)

                if age_hours <= config['max_age_hours']:
                    status = 'FRESH'
                elif config['critical']:
                    status = 'CRITICAL'
                else:
                    status = 'STALE'

                print(f"  {table}: {status} (age={age_hours}h, threshold={config['max_age_hours']}h, rows={row_count})")

            results[table] = {
                'status': status,
                'last_update': str(last_ts) if last_ts else None,
                'age_hours': age_hours,
                'row_count': row_count,
                'critical': config['critical'],
                'max_age_hours': config['max_age_hours'],
            }

        except Exception as e:
            print(f"  {table}: ERROR - {e}")
            results[table] = {
                'status': 'ERROR',
                'error': str(e),
                'last_update': None,
                'age_hours': None,
                'row_count': 0,
                'critical': config['critical'],
            }

    cursor.close()
    return results


# ---------------------------------------------------------------------------
# 2. Check Data Completeness
# ---------------------------------------------------------------------------
def check_data_completeness(conn):
    """Check row counts against expected coverage thresholds."""
    print("\n=== Data Completeness Check ===")
    cursor = conn.cursor(dictionary=True)
    results = {}

    for table, config in COMPLETENESS_EXPECTATIONS.items():
        try:
            cursor.execute(f"SELECT COUNT(DISTINCT symbol) as distinct_symbols, COUNT(*) as total_rows FROM `{table}`")
            row = cursor.fetchone()
            distinct = row['distinct_symbols']
            total = row['total_rows']

            expected = config['expected_symbols']
            min_pct = config['min_pct']
            coverage_pct = round((distinct / expected) * 100, 1) if expected > 0 else 0
            is_ok = coverage_pct >= min_pct

            status = 'OK' if is_ok else 'LOW_COVERAGE'
            print(f"  {table}: {distinct}/{expected} symbols ({coverage_pct}%) - {status}")

            results[table] = {
                'status': status,
                'distinct_symbols': distinct,
                'expected_symbols': expected,
                'coverage_pct': coverage_pct,
                'total_rows': total,
            }

        except Exception as e:
            print(f"  {table}: ERROR - {e}")
            results[table] = {
                'status': 'ERROR',
                'error': str(e),
            }

    # Check lm_signals freshness (recent signals from last 24h)
    try:
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM lm_signals
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        row = cursor.fetchone()
        recent_signals = row['cnt']
        status = 'OK' if recent_signals > 0 else 'NO_RECENT_SIGNALS'
        print(f"  lm_signals (24h): {recent_signals} recent signals - {status}")
        results['lm_signals_24h'] = {
            'status': status,
            'recent_signal_count': recent_signals,
        }
    except Exception as e:
        print(f"  lm_signals (24h): ERROR - {e}")
        results['lm_signals_24h'] = {'status': 'ERROR', 'error': str(e)}

    # Check lm_market_regime has today's regime
    try:
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM lm_market_regime
            WHERE DATE(created_at) = CURDATE() OR DATE(updated_at) = CURDATE()
        """)
        row = cursor.fetchone()
        has_today = row['cnt'] > 0
        status = 'OK' if has_today else 'NO_TODAY_REGIME'
        print(f"  lm_market_regime (today): {'Present' if has_today else 'Missing'} - {status}")
        results['lm_market_regime_today'] = {
            'status': status,
            'has_today': has_today,
        }
    except Exception as e:
        print(f"  lm_market_regime (today): ERROR - {e}")
        results['lm_market_regime_today'] = {'status': 'ERROR', 'error': str(e)}

    cursor.close()
    return results


# ---------------------------------------------------------------------------
# 3. Check API Health
# ---------------------------------------------------------------------------
def check_api_health():
    """Hit each API endpoint and verify 200 response."""
    print("\n=== API Health Check ===")
    results = {}

    for check in API_HEALTH_CHECKS:
        name = check['name']
        url = check['url']
        try:
            start = time.time()
            resp = requests.get(url, headers=API_HEADERS, timeout=30)
            elapsed_ms = round((time.time() - start) * 1000)
            status_code = resp.status_code

            # Try to parse JSON to verify response validity
            is_json = False
            is_ok = False
            try:
                data = resp.json()
                is_json = True
                is_ok = data.get('ok', False) if isinstance(data, dict) else False
            except (ValueError, KeyError):
                pass

            if status_code == 200 and is_json:
                status = 'HEALTHY'
            elif status_code == 200:
                status = 'DEGRADED'
            else:
                status = 'UNHEALTHY'

            print(f"  {name}: HTTP {status_code} ({elapsed_ms}ms) - {status}")

            results[name] = {
                'status': status,
                'http_status': status_code,
                'response_time_ms': elapsed_ms,
                'is_json': is_json,
                'api_ok': is_ok,
            }

        except requests.Timeout:
            print(f"  {name}: TIMEOUT (>30s)")
            results[name] = {
                'status': 'TIMEOUT',
                'http_status': None,
                'response_time_ms': 30000,
                'is_json': False,
                'api_ok': False,
            }
        except Exception as e:
            print(f"  {name}: ERROR - {e}")
            results[name] = {
                'status': 'ERROR',
                'http_status': None,
                'response_time_ms': None,
                'error': str(e),
                'api_ok': False,
            }

    return results


# ---------------------------------------------------------------------------
# 4. Check Signal Quality
# ---------------------------------------------------------------------------
def check_signal_quality(conn):
    """Analyze recent signals for quality anomalies."""
    print("\n=== Signal Quality Check ===")
    cursor = conn.cursor(dictionary=True)
    results = {}

    try:
        # Signal count and average strength in last 24h
        cursor.execute("""
            SELECT COUNT(*) as total,
                   AVG(signal_strength) as avg_strength,
                   MIN(signal_strength) as min_strength,
                   MAX(signal_strength) as max_strength,
                   COUNT(DISTINCT algorithm_name) as algo_count
            FROM lm_signals
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        row = cursor.fetchone()
        total_24h = row['total']
        avg_strength = float(row['avg_strength']) if row['avg_strength'] else 0
        min_strength = float(row['min_strength']) if row['min_strength'] else 0
        max_strength = float(row['max_strength']) if row['max_strength'] else 0
        algo_count = row['algo_count']

        # Flag: no signals = critical
        if total_24h == 0:
            signal_status = 'CRITICAL'
        # Flag: all same strength (broken engine)
        elif min_strength == max_strength and total_24h > 5:
            signal_status = 'DEGRADED'
        # Flag: unreasonable distribution (all 0 or all 100)
        elif avg_strength <= 5 or avg_strength >= 95:
            signal_status = 'DEGRADED'
        else:
            signal_status = 'HEALTHY'

        print(f"  Signals (24h): {total_24h} signals, avg_strength={avg_strength:.1f}, "
              f"range=[{min_strength:.0f}-{max_strength:.0f}], algos={algo_count} - {signal_status}")

        results['signals_24h'] = {
            'status': signal_status,
            'count': total_24h,
            'avg_strength': round(avg_strength, 1),
            'min_strength': round(min_strength, 1),
            'max_strength': round(max_strength, 1),
            'algo_count': algo_count,
        }

    except Exception as e:
        print(f"  Signals (24h): ERROR - {e}")
        results['signals_24h'] = {'status': 'ERROR', 'error': str(e)}

    try:
        # Signal count by algorithm (last 24h)
        cursor.execute("""
            SELECT algorithm_name, COUNT(*) as cnt,
                   AVG(signal_strength) as avg_str
            FROM lm_signals
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY algorithm_name
            ORDER BY cnt DESC
        """)
        by_algo = cursor.fetchall()
        results['by_algorithm'] = []
        for row in by_algo:
            results['by_algorithm'].append({
                'algorithm': row['algorithm_name'],
                'count': row['cnt'],
                'avg_strength': round(float(row['avg_str']), 1) if row['avg_str'] else 0,
            })
            print(f"    {row['algorithm_name']:28s}: {row['cnt']} signals (avg {float(row['avg_str'] or 0):.1f})")

    except Exception as e:
        print(f"  By algorithm: ERROR - {e}")
        results['by_algorithm'] = []

    try:
        # Expired vs executed ratio (all time)
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'executed' THEN 1 ELSE 0 END) as executed,
                SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active
            FROM lm_signals
        """)
        row = cursor.fetchone()
        total = row['total']
        executed = row['executed']
        expired = row['expired']
        active = row['active']
        executed_pct = round((executed / total) * 100, 1) if total > 0 else 0

        print(f"  Signal lifecycle: total={total}, executed={executed} ({executed_pct}%), "
              f"expired={expired}, active={active}")

        results['lifecycle'] = {
            'total': total,
            'executed': executed,
            'expired': expired,
            'active': active,
            'executed_pct': executed_pct,
        }

    except Exception as e:
        print(f"  Lifecycle: ERROR - {e}")
        results['lifecycle'] = {'status': 'ERROR', 'error': str(e)}

    cursor.close()
    return results


# ---------------------------------------------------------------------------
# 5. Retry Failed Operations
# ---------------------------------------------------------------------------
def retry_stale_data(freshness_results):
    """Trigger refreshes for stale critical tables with exponential backoff."""
    print("\n=== Retry Stale Data ===")
    retries_attempted = 0
    retries_succeeded = 0

    for table, url in RETRY_ACTIONS.items():
        fr = freshness_results.get(table, {})
        status = fr.get('status', 'UNKNOWN')

        if status not in ('STALE', 'CRITICAL'):
            continue

        print(f"  {table} is {status}, attempting refresh...")
        retries_attempted += 1
        success = False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                backoff = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                if attempt > 1:
                    print(f"    Retry {attempt}/{MAX_RETRIES} (backoff {backoff}s)...")
                    time.sleep(backoff)

                resp = requests.get(url, headers=API_HEADERS, timeout=60)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if data.get('ok', False):
                            print(f"    Refresh succeeded on attempt {attempt}")
                            success = True
                            retries_succeeded += 1
                            break
                        else:
                            print(f"    API returned ok=false: {data.get('error', 'unknown')}")
                    except ValueError:
                        print(f"    Non-JSON response ({resp.status_code})")
                else:
                    print(f"    HTTP {resp.status_code}")

            except requests.Timeout:
                print(f"    Timeout on attempt {attempt}")
            except Exception as e:
                print(f"    Error on attempt {attempt}: {e}")

        if not success:
            print(f"    All {MAX_RETRIES} retries failed for {table}")

    if retries_attempted == 0:
        print("  No stale data needing retry")

    return retries_attempted, retries_succeeded


# ---------------------------------------------------------------------------
# 6. Compute Overall Health
# ---------------------------------------------------------------------------
def compute_overall_health(freshness, completeness, apis, signals):
    """Determine overall system health: HEALTHY, DEGRADED, or CRITICAL."""
    critical_issues = []
    warnings = []

    # Freshness issues
    for table, info in freshness.items():
        if info.get('status') == 'CRITICAL':
            critical_issues.append(f"{table} data is critically stale")
        elif info.get('status') == 'STALE':
            warnings.append(f"{table} data is stale")
        elif info.get('status') == 'ERROR':
            warnings.append(f"{table} check failed")

    # Completeness issues
    for table, info in completeness.items():
        if info.get('status') == 'LOW_COVERAGE':
            warnings.append(f"{table} has low symbol coverage")
        elif info.get('status') == 'NO_RECENT_SIGNALS':
            critical_issues.append("No signals generated in last 24h")
        elif info.get('status') == 'NO_TODAY_REGIME':
            warnings.append("No market regime update today")

    # API issues
    for name, info in apis.items():
        if info.get('status') in ('UNHEALTHY', 'ERROR', 'TIMEOUT'):
            critical_issues.append(f"API {name} is {info.get('status')}")
        elif info.get('status') == 'DEGRADED':
            warnings.append(f"API {name} is degraded")

    # Signal quality issues
    sig_24h = signals.get('signals_24h', {})
    if sig_24h.get('status') == 'CRITICAL':
        critical_issues.append("No trading signals in last 24h")
    elif sig_24h.get('status') == 'DEGRADED':
        warnings.append("Signal quality is degraded")

    if critical_issues:
        return 'CRITICAL', critical_issues, warnings
    elif warnings:
        return 'DEGRADED', critical_issues, warnings
    else:
        return 'HEALTHY', critical_issues, warnings


# ---------------------------------------------------------------------------
# 7. Generate Health Report
# ---------------------------------------------------------------------------
def generate_report(freshness, completeness, apis, signals, retries_attempted,
                    retries_succeeded, alerts_sent, overall, critical_issues, warnings):
    """Generate JSON health report."""
    report = {
        'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),
        'overall_health': overall,
        'critical_issues': critical_issues,
        'warnings': warnings,
        'tables': freshness,
        'completeness': completeness,
        'apis': apis,
        'signals': {
            'count_24h': signals.get('signals_24h', {}).get('count', 0),
            'avg_strength': signals.get('signals_24h', {}).get('avg_strength', 0),
            'executed_pct': signals.get('lifecycle', {}).get('executed_pct', 0),
            'by_algorithm': signals.get('by_algorithm', []),
        },
        'retries_attempted': retries_attempted,
        'retries_succeeded': retries_succeeded,
        'alerts_sent': alerts_sent,
    }
    return report


# ---------------------------------------------------------------------------
# 8. Post Report
# ---------------------------------------------------------------------------
def post_report(report):
    """Post health report to the API and print to stdout."""
    print("\n=== Health Report ===")
    print(json.dumps(report, indent=2, default=str))

    # Try posting to regime.php as a health update
    try:
        url = f'{API_BASE}/regime.php?action=health_report&key={ADMIN_KEY}'
        resp = requests.post(url, json=report, headers=API_HEADERS, timeout=15)
        if resp.status_code == 200:
            print(f"\n  Report posted to API (HTTP {resp.status_code})")
        else:
            print(f"\n  Report post returned HTTP {resp.status_code} (non-critical)")
    except Exception as e:
        print(f"\n  Could not post report to API: {e} (non-critical)")

    # Save locally for GitHub Actions artifact
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, 'data_quality_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Report saved to {report_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print(f"DATA QUALITY MONITOR -- {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    alerts_sent = 0
    conn = None

    # --- Connect to database ---
    try:
        import mysql.connector
        print(f"\nConnecting to {DB_HOST}/{DB_NAME}...")
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            connect_timeout=15,
        )
        print("  Database connected")
    except Exception as e:
        print(f"  Database connection FAILED: {e}")
        send_alert("Database Unreachable", f"Cannot connect to {DB_HOST}: {e}", severity='critical')
        # Continue with API checks even if DB is down
        conn = None

    # --- 1. Data Freshness ---
    if conn:
        freshness = check_data_freshness(conn)
    else:
        freshness = {t: {'status': 'ERROR', 'error': 'No DB connection'}
                     for t in FRESHNESS_THRESHOLDS}

    # --- 2. Data Completeness ---
    if conn:
        completeness = check_data_completeness(conn)
    else:
        completeness = {}

    # --- 3. API Health ---
    apis = check_api_health()

    # --- 4. Signal Quality ---
    if conn:
        signals = check_signal_quality(conn)
    else:
        signals = {}

    # --- 5. Retry stale data ---
    retries_attempted, retries_succeeded = retry_stale_data(freshness)

    # If retries succeeded, re-check freshness for those tables
    if retries_succeeded > 0 and conn:
        print("\n  Re-checking freshness after retries...")
        freshness = check_data_freshness(conn)

    # --- 6. Compute overall health ---
    overall, critical_issues, warnings = compute_overall_health(
        freshness, completeness, apis, signals
    )

    print(f"\n=== Overall Health: {overall} ===")
    if critical_issues:
        print(f"  Critical issues ({len(critical_issues)}):")
        for issue in critical_issues:
            print(f"    - {issue}")
    if warnings:
        print(f"  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    - {w}")

    # --- Send alerts ---
    if overall == 'CRITICAL':
        issues_text = '\n'.join(f'- {i}' for i in critical_issues)
        warn_text = '\n'.join(f'- {w}' for w in warnings) if warnings else 'None'
        send_alert(
            'CRITICAL - System Health Degraded',
            f"**Critical Issues:**\n{issues_text}\n\n**Warnings:**\n{warn_text}\n\n"
            f"Retries: {retries_succeeded}/{retries_attempted} succeeded",
            severity='critical'
        )
        alerts_sent += 1
    elif overall == 'DEGRADED':
        warn_text = '\n'.join(f'- {w}' for w in warnings)
        send_alert(
            'DEGRADED - Non-Critical Issues',
            f"**Warnings:**\n{warn_text}\n\n"
            f"Retries: {retries_succeeded}/{retries_attempted} succeeded",
            severity='warning'
        )
        alerts_sent += 1
    else:
        # Only send OK alert if there were retries (something was fixed)
        if retries_succeeded > 0:
            send_alert(
                'RECOVERED - All Systems Healthy',
                f"System recovered after {retries_succeeded} successful refresh(es).",
                severity='ok'
            )
            alerts_sent += 1

    # --- 7. Generate report ---
    report = generate_report(
        freshness, completeness, apis, signals,
        retries_attempted, retries_succeeded, alerts_sent,
        overall, critical_issues, warnings
    )

    # --- 8. Post report ---
    post_report(report)

    # --- Cleanup ---
    if conn:
        try:
            conn.close()
        except Exception:
            pass

    print(f"\n{'=' * 60}")
    print(f"DONE -- Overall: {overall} | Alerts: {alerts_sent} | "
          f"Retries: {retries_succeeded}/{retries_attempted}")
    print(f"{'=' * 60}")

    # Exit with non-zero code on critical for GitHub Actions failure detection
    if overall == 'CRITICAL':
        sys.exit(1)


if __name__ == '__main__':
    main()
