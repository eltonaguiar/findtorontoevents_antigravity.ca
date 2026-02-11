#!/usr/bin/env python3
"""Deploy Kimi Swarm audit changes (Session 2) — 7 modified files."""
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

FILES = [
    'findstocks/api/analyze.php',
    'findstocks/api/setup_schema.php',
    'live-monitor/api/live_signals.php',
    'findcryptopairs/api/meme_scanner.php',
    'findforex2/api/seed_signals.php',
    'live-monitor/api/sports_odds.php',
    'findforex2/portfolio/api/forex_insights.php',
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

    # Ensure remote directory exists
    remote_dir = '/'.join(remote_path.split('/')[:-1])
    try:
        ftp.cwd(remote_dir)
    except:
        # Try to create directory structure
        parts = remote_dir.split('/')
        for i in range(1, len(parts) + 1):
            try:
                ftp.cwd('/'.join(parts[:i]))
            except:
                try:
                    ftp.mkd('/'.join(parts[:i]))
                except:
                    pass

    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        print(f"  OK: {rel_path}")
        uploaded += 1
    except Exception as e:
        print(f"  FAIL: {rel_path} — {e}")
        errors += 1

ftp.quit()
print(f"\nDone: {uploaded} uploaded, {errors} errors")
