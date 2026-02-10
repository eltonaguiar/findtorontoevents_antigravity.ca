#!/usr/bin/env python3
"""Deploy Algorithm Study page and updated changelog to FTP server."""
import os, sys
from ftplib import FTP_TLS

server = os.environ.get('FTP_SERVER')
user = os.environ.get('FTP_USER')
pw = os.environ.get('FTP_PASS')
if not all([server, user, pw]):
    print("ERROR: FTP_SERVER, FTP_USER, FTP_PASS env vars required")
    sys.exit(1)

REMOTE_ROOT = '/findtorontoevents.ca'

FILES = [
    ('findstocks/portfolio2/algo-study.html', '/findstocks/portfolio2/algo-study.html'),
    ('updates/index.html',                    '/updates/index.html'),
]

LOCAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ftp = FTP_TLS(server)
ftp.login(user, pw)
ftp.prot_p()
print(f"Connected to {server}")

uploaded = 0
errors = 0

for local_rel, remote_rel in FILES:
    local_path = os.path.join(LOCAL_ROOT, local_rel.replace('/', os.sep))
    remote_path = REMOTE_ROOT + remote_rel

    if not os.path.exists(local_path):
        print(f"  SKIP (not found): {local_rel}")
        errors += 1
        continue

    size = os.path.getsize(local_path)
    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        print(f"  OK: {local_rel} ({size:,} bytes)")
        uploaded += 1
    except Exception as e:
        print(f"  FAIL: {local_rel} -> {e}")
        errors += 1

ftp.quit()
print(f"\nDone: {uploaded} uploaded, {errors} errors")
