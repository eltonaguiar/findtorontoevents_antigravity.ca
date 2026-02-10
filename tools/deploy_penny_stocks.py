#!/usr/bin/env python3
"""Deploy penny stock finder to FTP server."""
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
    'findstocks/portfolio2/api/penny_stocks.php',
    'findstocks/portfolio2/penny-stocks.html',
    'findstocks/portfolio2/stock-nav.js',
    'findstocks/portfolio2/hub.html',
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
print(f"\nDone: {uploaded} uploaded, {errors} errors")
