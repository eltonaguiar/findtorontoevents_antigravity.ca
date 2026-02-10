#!/usr/bin/env python3
"""Deploy consolidated picks suite + updated pages to FTP.
Uploads new API files, new HTML pages, and modified nav pages.
"""
import os
import sys
from ftplib import FTP_TLS

FTP_SERVER = os.environ.get('FTP_SERVER', '')
FTP_USER = os.environ.get('FTP_USER', '')
FTP_PASS = os.environ.get('FTP_PASS', '')

if not FTP_SERVER or not FTP_USER or not FTP_PASS:
    print("ERROR: FTP credentials not found. Need FTP_SERVER, FTP_USER, FTP_PASS")
    sys.exit(1)

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
REMOTE_BASE = '/findtorontoevents.ca'

# Files to deploy: (local_relative_path, remote_path)
FILES = [
    # New API files
    ('findstocks/portfolio2/api/consolidated_schema.php', '/findtorontoevents.ca/findstocks/portfolio2/api/consolidated_schema.php'),
    ('findstocks/portfolio2/api/consolidated_picks.php', '/findtorontoevents.ca/findstocks/portfolio2/api/consolidated_picks.php'),
    ('findstocks/portfolio2/api/stock_intel.php', '/findtorontoevents.ca/findstocks/portfolio2/api/stock_intel.php'),
    ('findstocks/portfolio2/api/learning_dashboard.php', '/findtorontoevents.ca/findstocks/portfolio2/api/learning_dashboard.php'),
    ('findstocks/portfolio2/api/daytrader_sim.php', '/findtorontoevents.ca/findstocks/portfolio2/api/daytrader_sim.php'),
    # New HTML pages
    ('findstocks/portfolio2/consolidated.html', '/findtorontoevents.ca/findstocks/portfolio2/consolidated.html'),
    ('findstocks/portfolio2/stock-intel.html', '/findtorontoevents.ca/findstocks/portfolio2/stock-intel.html'),
    ('findstocks/portfolio2/learning-lab.html', '/findtorontoevents.ca/findstocks/portfolio2/learning-lab.html'),
    ('findstocks/portfolio2/daytrader-sim.html', '/findtorontoevents.ca/findstocks/portfolio2/daytrader-sim.html'),
    # Modified pages (nav links updated)
    ('findstocks/portfolio2/hub.html', '/findtorontoevents.ca/findstocks/portfolio2/hub.html'),
    ('findstocks/portfolio2/picks.html', '/findtorontoevents.ca/findstocks/portfolio2/picks.html'),
    ('findstocks/portfolio2/leaderboard.html', '/findtorontoevents.ca/findstocks/portfolio2/leaderboard.html'),
    # Updates page
    ('updates/index.html', '/findtorontoevents.ca/updates/index.html'),
]


def ensure_remote_dir(ftp, path):
    dirs = path.strip('/').split('/')
    current = ''
    for d in dirs:
        current += '/' + d
        try:
            ftp.cwd(current)
        except:
            try:
                ftp.mkd(current)
                ftp.cwd(current)
            except:
                pass


def main():
    print(f"Connecting to {FTP_SERVER}...")
    ftp = FTP_TLS(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print("Connected with TLS.\n")

    uploaded = 0
    failed = 0
    for local_rel, remote_path in FILES:
        local_path = os.path.join(WORKSPACE, local_rel.replace('/', os.sep))
        if not os.path.isfile(local_path):
            print(f"  SKIP (not found): {local_rel}")
            continue
        # Ensure remote directory exists
        remote_dir = '/'.join(remote_path.split('/')[:-1])
        remote_file = remote_path.split('/')[-1]
        ensure_remote_dir(ftp, remote_dir)
        try:
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_file}', f)
            print(f"  OK: {remote_path}")
            uploaded += 1
        except Exception as e:
            print(f"  FAIL: {remote_path} - {e}")
            failed += 1

    # Also ensure cache directory exists for consolidated_picks.php
    try:
        ensure_remote_dir(ftp, '/findtorontoevents.ca/findstocks/portfolio2/api/cache')
        print("  OK: Created/verified cache directory")
    except:
        pass

    print(f"\nDone! Uploaded {uploaded} files, {failed} failures.")
    ftp.quit()


if __name__ == '__main__':
    main()
