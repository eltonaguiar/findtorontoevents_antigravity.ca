#!/usr/bin/env python3
"""Deploy stock navigation improvements to FTP server."""
import os, sys
from ftplib import FTP_TLS

server = os.environ.get('FTP_SERVER')
user = os.environ.get('FTP_USER')
pw = os.environ.get('FTP_PASS')
if not all([server, user, pw]):
    print("ERROR: FTP_SERVER, FTP_USER, FTP_PASS env vars required")
    sys.exit(1)

REMOTE_ROOT = '/findtorontoevents.ca'
LOCAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# All files to deploy
FILES = [
    # New files
    'findstocks/portfolio2/stock-nav.js',
    'findstocks/portfolio2/api-viewer.html',
    # Portfolio2 pages (nav injected)
    'findstocks/portfolio2/hub.html',
    'findstocks/portfolio2/picks.html',
    'findstocks/portfolio2/consolidated.html',
    'findstocks/portfolio2/leaderboard.html',
    'findstocks/portfolio2/learning-lab.html',
    'findstocks/portfolio2/dividends.html',
    'findstocks/portfolio2/horizon-picks.html',
    'findstocks/portfolio2/dashboard.html',
    'findstocks/portfolio2/daytrader-sim.html',
    'findstocks/portfolio2/stock-intel.html',
    'findstocks/portfolio2/learning-dashboard.html',
    'findstocks/portfolio2/smart-learning.html',
    'findstocks/portfolio2/algo-study.html',
    'findstocks/portfolio2/stock-profile.html',
    'findstocks/portfolio2/index.html',
    'findstocks/portfolio2/stats/index.html',
    # Live-monitor pages
    'live-monitor/live-monitor.html',
    'live-monitor/opportunity-scanner.html',
    'live-monitor/edge-dashboard.html',
    'live-monitor/winning-patterns.html',
    'live-monitor/hour-learning.html',
    # Cross-asset pages
    'findcryptopairs/portfolio/index.html',
    'findforex2/portfolio/index.html',
    # Global dashboard
    'findstocks2_global/index.html',
]

ftp = FTP_TLS(server)
ftp.login(user, pw)
ftp.prot_p()
print(f"Connected to {server}")

uploaded = 0
errors = 0

for rel_path in FILES:
    local_path = os.path.join(LOCAL_ROOT, rel_path.replace('/', os.sep))
    remote_path = REMOTE_ROOT + '/' + rel_path

    if not os.path.exists(local_path):
        print(f"  SKIP (not found): {rel_path}")
        errors += 1
        continue

    size = os.path.getsize(local_path)
    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        print(f"  OK: {rel_path} ({size:,} bytes)")
        uploaded += 1
    except Exception as e:
        print(f"  FAIL: {rel_path} -> {e}")
        errors += 1

ftp.quit()
print(f"\nDone: {uploaded} uploaded, {errors} errors out of {len(FILES)} files")
