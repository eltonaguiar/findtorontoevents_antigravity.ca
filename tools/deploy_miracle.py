"""
Deploy DayTrades Miracle Claude files to FTP
"""
import os
import sys
from ftplib import FTP_TLS

# Read credentials from environment variables
server = os.environ.get('FTP_SERVER', '')
user = os.environ.get('FTP_USER', '')
passwd = os.environ.get('FTP_PASS', '')

if not server or not user or not passwd:
    print("ERROR: FTP credentials not set in environment variables")
    print("Need: FTP_SERVER, FTP_USER, FTP_PASS")
    sys.exit(1)

LOCAL_BASE = r'e:\findtorontoevents_antigravity.ca'
REMOTE_ROOT = '/findtorontoevents.ca'

files_to_deploy = [
    ('findstocks2_global/api/db_config2.php', 'findstocks2_global/api/db_config2.php'),
    ('findstocks2_global/api/db_connect2.php', 'findstocks2_global/api/db_connect2.php'),
    ('findstocks2_global/api/questrade_fees2.php', 'findstocks2_global/api/questrade_fees2.php'),
    ('findstocks2_global/api/setup_schema2.php', 'findstocks2_global/api/setup_schema2.php'),
    ('findstocks2_global/api/scanner2.php', 'findstocks2_global/api/scanner2.php'),
    ('findstocks2_global/api/picks2.php', 'findstocks2_global/api/picks2.php'),
    ('findstocks2_global/api/dashboard2.php', 'findstocks2_global/api/dashboard2.php'),
    ('findstocks2_global/api/resolve_picks2.php', 'findstocks2_global/api/resolve_picks2.php'),
    ('findstocks2_global/api/learning2.php', 'findstocks2_global/api/learning2.php'),
    ('findstocks2_global/api/daily_scan2.php', 'findstocks2_global/api/daily_scan2.php'),
    ('findstocks2_global/miracle.html', 'findstocks2_global/miracle.html'),
]

print(f"Connecting to {server}...")
ftp = FTP_TLS(server)
ftp.login(user, passwd)
ftp.prot_p()
print("Connected and secured.")

# Ensure remote directories exist
dirs_to_create = [
    REMOTE_ROOT + '/findstocks2_global',
    REMOTE_ROOT + '/findstocks2_global/api',
]

for d in dirs_to_create:
    try:
        ftp.mkd(d)
        print(f"Created directory: {d}")
    except Exception:
        pass  # Already exists

# Upload files
for local_rel, remote_rel in files_to_deploy:
    local_path = os.path.join(LOCAL_BASE, local_rel)
    remote_path = REMOTE_ROOT + '/' + remote_rel

    if not os.path.exists(local_path):
        print(f"SKIP (not found): {local_path}")
        continue

    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        size = os.path.getsize(local_path)
        print(f"OK: {remote_rel} ({size:,} bytes)")
    except Exception as e:
        print(f"FAIL: {remote_rel} - {e}")

ftp.quit()
print("\nDeploy complete!")
print("Next steps:")
print("  1. Visit: https://findtorontoevents.ca/findstocks2_global/api/setup_schema2.php")
print("  2. Visit: https://findtorontoevents.ca/findstocks2_global/miracle.html")
