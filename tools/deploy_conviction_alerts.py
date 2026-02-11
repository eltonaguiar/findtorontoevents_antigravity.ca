#!/usr/bin/env python3
"""Deploy conviction alerts system (dashboard + updated API)."""
import os, sys
from ftplib import FTP_TLS

# Load .env file for FTP credentials
_env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(_env_file):
    for line in open(_env_file):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            k, v = k.strip(), v.strip()
            if k and not os.environ.get(k):
                os.environ[k] = v

server = os.environ.get('FTP_SERVER') or os.environ.get('FTP_HOST', '')
user = os.environ.get('FTP_USER', '')
pw = os.environ.get('FTP_PASS', '')
if not all([server, user, pw]):
    print("ERROR: FTP_SERVER/FTP_HOST, FTP_USER, FTP_PASS env vars required")
    sys.exit(1)

REMOTE_ROOT = '/findtorontoevents.ca'
LOCAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = [
    'live-monitor/api/multi_dimensional.php',
    'live-monitor/conviction-alerts.html',
]

try:
    ftp = FTP_TLS(server)
    ftp.login(user, pw)
    ftp.prot_p()
    print(f"Connected to {server} (TLS)")
except Exception as e:
    print(f"TLS failed ({e}), trying plain FTP...")
    from ftplib import FTP as FTP_PLAIN
    ftp = FTP_PLAIN(server)
    ftp.login(user, pw)
    print(f"Connected to {server} (plain)")

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
    # Ensure remote directory exists
    remote_dir = '/'.join(remote_path.split('/')[:-1])
    try:
        ftp.cwd('/')
        for part in remote_dir.split('/'):
            if not part:
                continue
            try:
                ftp.cwd(part)
            except:
                try:
                    ftp.mkd(part)
                    ftp.cwd(part)
                except:
                    pass
    except:
        pass
    try:
        ftp.cwd('/')
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        print(f"  OK: {rel_path} ({size:,} bytes)")
        uploaded += 1
    except Exception as e:
        print(f"  FAIL: {rel_path} -> {e}")
        errors += 1

ftp.quit()
print(f"\nDone: {uploaded} uploaded, {errors} errors")
