#!/usr/bin/env python3
"""Deploy Sports Bet Winner Finder to FTP."""
import ftplib
import ssl
import os
import sys

# Read FTP credentials from Windows environment variables
SERVER = os.environ.get('FTP_SERVER', '')
USER = os.environ.get('FTP_USER', '')
PASS = os.environ.get('FTP_PASS', '')

if not SERVER or not USER or not PASS:
    print("ERROR: Set FTP_SERVER, FTP_USER, FTP_PASS environment variables")
    sys.exit(1)

BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_REMOTE = '/findtorontoevents.ca'

# Files to deploy (local path -> remote path)
FILES = [
    # DB config + connection
    ('live-monitor/api/db_config.php', 'live-monitor/api/db_config.php'),
    ('live-monitor/api/sports_db_connect.php', 'live-monitor/api/sports_db_connect.php'),
    # Sports APIs
    ('live-monitor/api/sports_odds.php', 'live-monitor/api/sports_odds.php'),
    ('live-monitor/api/sports_picks.php', 'live-monitor/api/sports_picks.php'),
    ('live-monitor/api/sports_bets.php', 'live-monitor/api/sports_bets.php'),
    ('live-monitor/api/sports_scores.php', 'live-monitor/api/sports_scores.php'),
    # Schema
    ('live-monitor/api/sports_schema.php', 'live-monitor/api/sports_schema.php'),
    # ML Integration
    ('live-monitor/api/sports_ml.php', 'live-monitor/api/sports_ml.php'),
    # NBA Stats Intelligence
    ('live-monitor/api/nba_stats.php', 'live-monitor/api/nba_stats.php'),
    # Frontend dashboard + JS module
    ('live-monitor/sports-betting.html', 'live-monitor/sports-betting.html'),
    ('live-monitor/sports-betting.js', 'live-monitor/sports-betting.js'),
    # Updated nav pages
    ('live-monitor/live-monitor.html', 'live-monitor/live-monitor.html'),
    ('live-monitor/edge-dashboard.html', 'live-monitor/edge-dashboard.html'),
    ('live-monitor/opportunity-scanner.html', 'live-monitor/opportunity-scanner.html'),
    ('live-monitor/winning-patterns.html', 'live-monitor/winning-patterns.html'),
    ('live-monitor/hour-learning.html', 'live-monitor/hour-learning.html'),
    # Updates page
    ('updates/index.html', 'updates/index.html'),
]

def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print(f"Connecting to {SERVER}...")
    ftp = ftplib.FTP_TLS(context=ctx)
    ftp.connect(SERVER, 21)
    ftp.login(USER, PASS)
    ftp.prot_p()
    print(f"Connected with TLS.")

    # Ensure remote directories exist
    for d in ['live-monitor', 'live-monitor/api']:
        remote_dir = f"{BASE_REMOTE}/{d}"
        try:
            ftp.cwd(remote_dir)
            ftp.cwd('/')
        except:
            try:
                ftp.mkd(remote_dir)
                print(f"  Created dir: {remote_dir}")
            except:
                pass

    # Upload files
    uploaded = 0
    errors = []

    for local_rel, remote_rel in FILES:
        local_path = os.path.join(BASE_LOCAL, local_rel.replace('/', os.sep))
        remote_path = f"{BASE_REMOTE}/{remote_rel}"

        if not os.path.exists(local_path):
            errors.append(f"NOT FOUND: {local_path}")
            continue

        size = os.path.getsize(local_path)
        try:
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_path}', f)
            uploaded += 1
            print(f"  OK: {remote_rel} ({size:,} bytes)")
        except Exception as e:
            errors.append(f"FAIL {remote_rel}: {e}")

    ftp.quit()

    print(f"\nDeployed {uploaded}/{len(FILES)} files.")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  {e}")
    else:
        print("All files uploaded successfully!")

    print("\nVerify APIs:")
    print("  https://findtorontoevents.ca/live-monitor/api/sports_odds.php?action=sports")
    print("  https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=today")
    print("  https://findtorontoevents.ca/live-monitor/api/sports_bets.php?action=dashboard")
    print("  https://findtorontoevents.ca/live-monitor/api/nba_stats.php?action=team_stats")
    print("  https://findtorontoevents.ca/live-monitor/api/sports_ml.php?action=status")
    print("  https://findtorontoevents.ca/live-monitor/sports-betting.html")


if __name__ == '__main__':
    main()
