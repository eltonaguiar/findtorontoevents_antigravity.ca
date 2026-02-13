#!/usr/bin/env python3
"""
Deploy Command Center files to FTP server.
Uploads: command_center.php, command-center.html, scope_labels.js, stock-nav.js
"""
import os
import sys
from ftplib import FTP_TLS

server = os.environ.get('FTP_SERVER')
user = os.environ.get('FTP_USER')
pw = os.environ.get('FTP_PASS')

if not all([server, user, pw]):
    print("ERROR: FTP_SERVER, FTP_USER, FTP_PASS environment variables required")
    sys.exit(1)

REMOTE_ROOT = '/findtorontoevents.ca'
LOCAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files to deploy: (local_relative_path, remote_relative_path)
FILES = [
    # New Command Center files
    ('live-monitor/api/command_center.php',    '/live-monitor/api/command_center.php'),
    ('live-monitor/command-center.html',       '/live-monitor/command-center.html'),
    ('live-monitor/api/scope_labels.js',       '/live-monitor/api/scope_labels.js'),
    # Updated navigation
    ('findstocks/portfolio2/stock-nav.js',     '/findstocks/portfolio2/stock-nav.js'),
]

# Optional: also deploy scope-labeled HTML pages
SCOPE_LABEL_PAGES = [
    ('live-monitor/goldmine-dashboard.html',            '/live-monitor/goldmine-dashboard.html'),
    ('live-monitor/live-monitor.html',                  '/live-monitor/live-monitor.html'),
    ('live-monitor/sports-betting.html',                '/live-monitor/sports-betting.html'),
    ('live-monitor/edge-dashboard.html',                '/live-monitor/edge-dashboard.html'),
    ('live-monitor/algo-performance.html',              '/live-monitor/algo-performance.html'),
    ('live-monitor/smart-money.html',                   '/live-monitor/smart-money.html'),
    ('live-monitor/multi-dimensional.html',             '/live-monitor/multi-dimensional.html'),
    ('live-monitor/opportunity-scanner.html',           '/live-monitor/opportunity-scanner.html'),
    ('live-monitor/winning-patterns.html',              '/live-monitor/winning-patterns.html'),
    ('live-monitor/capital-efficiency.html',            '/live-monitor/capital-efficiency.html'),
    ('live-monitor/conviction-alerts.html',             '/live-monitor/conviction-alerts.html'),
    ('live-monitor/goldmine-alerts.html',               '/live-monitor/goldmine-alerts.html'),
    ('live-monitor/real_time_dashboard.html',           '/live-monitor/real_time_dashboard.html'),
    ('findstocks/portfolio2/consolidated.html',         '/findstocks/portfolio2/consolidated.html'),
    ('findstocks/portfolio2/picks.html',                '/findstocks/portfolio2/picks.html'),
    ('findstocks/portfolio2/leaderboard.html',          '/findstocks/portfolio2/leaderboard.html'),
    ('findstocks/portfolio2/penny-stocks.html',         '/findstocks/portfolio2/penny-stocks.html'),
    ('findstocks/portfolio2/dividends.html',            '/findstocks/portfolio2/dividends.html'),
    ('findstocks/portfolio2/horizon-picks.html',        '/findstocks/portfolio2/horizon-picks.html'),
    ('findstocks/portfolio2/dashboard.html',            '/findstocks/portfolio2/dashboard.html'),
    ('findstocks/portfolio2/stock-intel.html',          '/findstocks/portfolio2/stock-intel.html'),
    ('findstocks/portfolio2/daytrader-sim.html',        '/findstocks/portfolio2/daytrader-sim.html'),
    ('findstocks/portfolio2/algorithm-intelligence.html', '/findstocks/portfolio2/algorithm-intelligence.html'),
    ('findstocks/portfolio2/backtest-results.html',     '/findstocks/portfolio2/backtest-results.html'),
]

def main():
    deploy_pages = '--with-pages' in sys.argv

    ftp = FTP_TLS(server)
    ftp.login(user, pw)
    ftp.prot_p()
    print("Connected to %s" % server)

    # Ensure remote directories exist
    for d in ['/live-monitor', '/live-monitor/api', '/findstocks/portfolio2']:
        try:
            ftp.mkd(REMOTE_ROOT + d)
        except Exception:
            pass

    files_to_deploy = list(FILES)
    if deploy_pages:
        files_to_deploy.extend(SCOPE_LABEL_PAGES)
        print("Including %d scope-labeled HTML pages" % len(SCOPE_LABEL_PAGES))

    uploaded = 0
    errors = 0

    for local_rel, remote_rel in files_to_deploy:
        local_path = os.path.join(LOCAL_ROOT, local_rel.replace('/', os.sep))
        remote_path = REMOTE_ROOT + remote_rel

        if not os.path.exists(local_path):
            print("  SKIP (not found): %s" % local_rel)
            errors += 1
            continue

        size = os.path.getsize(local_path)
        try:
            with open(local_path, 'rb') as f:
                ftp.storbinary('STOR %s' % remote_path, f)
            print("  OK: %s (%s bytes)" % (local_rel, '{:,}'.format(size)))
            uploaded += 1
        except Exception as e:
            print("  FAIL: %s -> %s" % (local_rel, str(e)))
            errors += 1

    ftp.quit()
    print("")
    print("Done: %d uploaded, %d errors" % (uploaded, errors))

    if errors > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
