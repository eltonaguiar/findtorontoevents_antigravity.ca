#!/usr/bin/env python3
"""Deploy Feb 12 fixes: PAUSED badges, honest audit, clickable algo links."""
import os, sys
from ftplib import FTP_TLS

FTP_SERVER = os.environ.get('FTP_SERVER', '')
FTP_USER = os.environ.get('FTP_USER', '')
FTP_PASS = os.environ.get('FTP_PASS', '')

if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
    print("ERROR: FTP_SERVER, FTP_USER, FTP_PASS env vars required")
    sys.exit(1)

LOCAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_ROOT = '/findtorontoevents.ca'

# All changed files: (local_relative, remote_relative)
FILES = [
    # Updates page
    ('updates/index.html', '/updates/index.html'),
    # Findstocks portfolio2
    ('findstocks/portfolio2/consolidated.html', '/findstocks/portfolio2/consolidated.html'),
    ('findstocks/portfolio2/leaderboard.html', '/findstocks/portfolio2/leaderboard.html'),
    ('findstocks/portfolio2/picks.html', '/findstocks/portfolio2/picks.html'),
    # Live monitor
    ('live-monitor/live-monitor.html', '/live-monitor/live-monitor.html'),
    ('live-monitor/api/live_signals.php', '/live-monitor/api/live_signals.php'),
    ('live-monitor/api/live_prices.php', '/live-monitor/api/live_prices.php'),
    # Algo performance (#1 PICK)
    ('live-monitor/algo-performance.html', '/live-monitor/algo-performance.html'),
    # Goldmine
    ('live-monitor/goldmine-dashboard.html', '/live-monitor/goldmine-dashboard.html'),
    ('live-monitor/api/goldmine_tracker.php', '/live-monitor/api/goldmine_tracker.php'),
    ('live-monitor/conviction-alerts.html', '/live-monitor/conviction-alerts.html'),
    ('live-monitor/sports-betting.html', '/live-monitor/sports-betting.html'),
    ('live-monitor/smart-money.html', '/live-monitor/smart-money.html'),
    # Stock nav pages that got stock-nav.js added
    ('findcryptopairs/index.html', '/findcryptopairs/index.html'),
    ('findcryptopairs/meme.html', '/findcryptopairs/meme.html'),
    ('findcryptopairs/portfolio/index.html', '/findcryptopairs/portfolio/index.html'),
    ('findcryptopairs/portfolio/stats/index.html', '/findcryptopairs/portfolio/stats/index.html'),
    ('findcryptopairs/winners.html', '/findcryptopairs/winners.html'),
    ('findforex2/index.html', '/findforex2/index.html'),
    ('findforex2/portfolio/stats/index.html', '/findforex2/portfolio/stats/index.html'),
    ('findstocks/index.html', '/findstocks/index.html'),
    ('findstocks/tools.html', '/findstocks/tools.html'),
    ('findstocks/research/index.html', '/findstocks/research/index.html'),
    ('findstocks2_global/miracle.html', '/findstocks2_global/miracle.html'),
    # Best-by-class banners added
    ('findstocks/portfolio2/penny-stocks.html', '/findstocks/portfolio2/penny-stocks.html'),
    ('findforex2/portfolio/index.html', '/findforex2/portfolio/index.html'),
    ('findmutualfunds2/portfolio2/index.html', '/findmutualfunds2/portfolio2/index.html'),
    # Stock nav (glow badges on top pages)
    ('findstocks/portfolio2/stock-nav.js', '/findstocks/portfolio2/stock-nav.js'),
    # Root index
    ('index.html', '/index.html'),
    # fetch_prices.php bug fix (stale data check)
    ('findstocks/portfolio2/api/fetch_prices.php', '/findstocks/portfolio2/api/fetch_prices.php'),
]

def ensure_dir(ftp, path):
    parts = path.strip('/').split('/')
    current = ''
    for p in parts:
        current += '/' + p
        try:
            ftp.cwd(current)
        except:
            try:
                ftp.mkd(current)
            except:
                pass

def deploy(site_root):
    print(f"\n{'='*60}")
    print(f"Deploying to {site_root}")
    print(f"{'='*60}")

    ftp = FTP_TLS(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print(f"Connected to {FTP_SERVER}")

    ok = 0
    fail = 0
    for local_rel, remote_rel in FILES:
        local_path = os.path.join(LOCAL_ROOT, local_rel.replace('/', os.sep))
        remote_path = site_root + remote_rel

        if not os.path.exists(local_path):
            print(f"  SKIP (missing): {local_rel}")
            continue

        local_size = os.path.getsize(local_path)
        remote_dir = '/'.join(remote_path.split('/')[:-1])
        remote_file = remote_path.split('/')[-1]

        try:
            ensure_dir(ftp, remote_dir)
            ftp.cwd(remote_dir)
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_file}', f)
            remote_size = ftp.size(remote_file)
            if remote_size == local_size:
                print(f"  OK: {remote_rel} ({local_size} bytes)")
                ok += 1
            else:
                print(f"  WARN: {remote_rel} size mismatch local={local_size} remote={remote_size}")
                ok += 1  # still uploaded
        except Exception as e:
            print(f"  FAIL: {remote_rel} - {e}")
            fail += 1

    ftp.quit()
    print(f"\nResult: {ok} uploaded, {fail} failed")
    return fail

if __name__ == '__main__':
    errors = 0
    # Deploy to primary site
    errors += deploy('/findtorontoevents.ca')
    # Deploy to sister site
    errors += deploy('/tdotevent.ca')

    if errors:
        print(f"\n{errors} file(s) failed!")
        sys.exit(1)
    else:
        print("\nAll files deployed to both sites!")
        sys.exit(0)
