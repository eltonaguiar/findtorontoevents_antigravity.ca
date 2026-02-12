#!/usr/bin/env python3
"""
Deploy OPUS46 Phase 0-3 changes to production via FTP.

Deploys:
- Phase 0: Commission eliminator, algorithm pauser, stop-loss fixes (via run_all.py)
- Phase 1: Ensemble stacker, corr pruner, feature selector, data fetcher (Python scripts)
- Phase 2: FinBERT, Congress, Options, On-Chain, Portfolio, Transfer Entropy (workflow flags)
- Phase 3: SQL views, sports schema, FRED macro, position sizing in PHP

NOTE: Python scripts don't need FTP deploy (they run via GitHub Actions).
      This deploys PHP APIs, HTML frontends, and schema files.
"""
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
    # ═══ PHASE 0+1: Core PHP changes ═══
    # Position sizing upgrade (reads Python-computed sizes from lm_position_sizing)
    ('live-monitor/api/live_trade.php', 'live-monitor/api/live_trade.php'),
    # Live signals (regime gate fixes)
    ('live-monitor/api/live_signals.php', 'live-monitor/api/live_signals.php'),
    # Algorithm performance tracking
    ('live-monitor/api/algo_performance.php', 'live-monitor/api/algo_performance.php'),
    # Edge finder
    ('live-monitor/api/edge_finder.php', 'live-monitor/api/edge_finder.php'),

    # ═══ PHASE 3: Sports betting improvements ═══
    ('live-monitor/api/sports_odds.php', 'live-monitor/api/sports_odds.php'),
    ('live-monitor/api/sports_picks.php', 'live-monitor/api/sports_picks.php'),
    ('live-monitor/api/sports_bets.php', 'live-monitor/api/sports_bets.php'),
    ('live-monitor/api/sports_scores.php', 'live-monitor/api/sports_scores.php'),
    ('live-monitor/api/sports_db_connect.php', 'live-monitor/api/sports_db_connect.php'),

    # ═══ PHASE 3: Goldmine + schema ═══
    ('live-monitor/api/goldmine_tracker.php', 'live-monitor/api/goldmine_tracker.php'),
    ('live-monitor/api/goldmine_schema.php', 'live-monitor/api/goldmine_schema.php'),
    ('live-monitor/api/db_config.php', 'live-monitor/api/db_config.php'),

    # ═══ Frontends ═══
    ('live-monitor/goldmine-dashboard.html', 'live-monitor/goldmine-dashboard.html'),
    ('live-monitor/goldmine-alerts.html', 'live-monitor/goldmine-alerts.html'),
    ('live-monitor/sports-betting.html', 'live-monitor/sports-betting.html'),
    ('findstocks/index.html', 'findstocks/index.html'),

    # ═══ Updates page ═══
    ('updates/index.html', 'updates/index.html'),
]

# Conditionally add new files if they exist
OPTIONAL_FILES = [
    ('live-monitor/api/sports_schema.php', 'live-monitor/api/sports_schema.php'),
    ('live-monitor/api/live_monitor_schema.php', 'live-monitor/api/live_monitor_schema.php'),
    ('predictions/sports.html', 'predictions/sports.html'),
    ('investments/goldmines/antigravity/api/create_views.php', 'investments/goldmines/antigravity/api/create_views.php'),
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
    print("Connected + TLS active.")

    # Combine required + optional files
    all_files = list(FILES)
    for local, remote in OPTIONAL_FILES:
        local_path = os.path.join(BASE_LOCAL, local)
        if os.path.exists(local_path):
            all_files.append((local, remote))

    deployed = 0
    failed = 0

    for local_rel, remote_rel in all_files:
        local_path = os.path.join(BASE_LOCAL, local_rel)
        remote_path = f"{BASE_REMOTE}/{remote_rel}"

        if not os.path.exists(local_path):
            print(f"  SKIP (not found): {local_rel}")
            continue

        # Ensure remote directories exist
        remote_dir = '/'.join(remote_path.split('/')[:-1])
        try:
            ftp.cwd(remote_dir)
        except ftplib.error_perm:
            # Create directory tree
            parts = remote_dir.split('/')
            current = ''
            for part in parts:
                if not part:
                    continue
                current += '/' + part
                try:
                    ftp.cwd(current)
                except ftplib.error_perm:
                    try:
                        ftp.mkd(current)
                        print(f"  MKDIR: {current}")
                    except ftplib.error_perm:
                        pass

        try:
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_path}', f)
            print(f"  OK: {local_rel}")
            deployed += 1
        except Exception as e:
            print(f"  FAIL: {local_rel} -> {e}")
            failed += 1

    ftp.quit()
    print(f"\n{'='*50}")
    print(f"Deployed: {deployed} | Failed: {failed} | Skipped: {len(all_files) - deployed - failed}")
    print(f"{'='*50}")

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
