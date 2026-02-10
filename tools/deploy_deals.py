#!/usr/bin/env python3
"""
Deploy Deals & Freebies feature to production.
Files: deals/index.html, favcreators/public/api/deals.php, ai-assistant.js
"""
import os
import sys
from ftplib import FTP_TLS

FTP_SERVER = os.environ.get('FTP_SERVER')
FTP_USER = os.environ.get('FTP_USER')
FTP_PASS = os.environ.get('FTP_PASS')
REMOTE_ROOT = '/findtorontoevents.ca/'

if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
    print("ERROR: FTP credentials not found in environment variables.")
    print("Set FTP_SERVER, FTP_USER, FTP_PASS in Windows user env vars.")
    sys.exit(1)

LOCAL_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = [
    ('favcreators/public/api/deals.php', 'favcreators/public/api/deals.php'),
    ('favcreators/public/api/deals.php', 'fc/api/deals.php'),
    ('deals/index.html', 'deals/index.html'),
    ('ai-assistant.js', 'ai-assistant.js'),
    ('updates/index.html', 'updates/index.html'),
]

def ensure_remote_dir(ftp, path):
    """Create remote directory tree if it doesn't exist."""
    parts = path.strip('/').split('/')
    current = ''
    for part in parts:
        current += '/' + part
        try:
            ftp.cwd(current)
        except:
            try:
                ftp.mkd(current)
                print(f"  Created directory: {current}")
            except:
                pass

def main():
    print(f"Connecting to {FTP_SERVER}...")
    ftp = FTP_TLS(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print("Connected with TLS.")

    for local_rel, remote_rel in FILES:
        local_path = os.path.join(LOCAL_BASE, local_rel)
        remote_path = REMOTE_ROOT + remote_rel

        if not os.path.exists(local_path):
            print(f"  SKIP (not found): {local_path}")
            continue

        # Ensure remote directory exists
        remote_dir = '/'.join(remote_path.split('/')[:-1])
        ensure_remote_dir(ftp, remote_dir)

        print(f"  Uploading: {local_rel} -> {remote_path}")
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        print(f"  OK: {local_rel}")

    ftp.quit()
    print("\nDeploy complete!")
    print("Verify at:")
    print("  https://findtorontoevents.ca/deals/")
    print("  https://findtorontoevents.ca/fc/api/deals.php?action=categories")
    print("  https://findtorontoevents.ca/fc/api/deals.php?action=birthday&category=food")

if __name__ == '__main__':
    main()
