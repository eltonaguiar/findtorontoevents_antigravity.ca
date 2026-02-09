"""
Deploy dividend & earnings data files to FTP
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
    ('findstocks/portfolio2/api/dividend_earnings_schema.php', 'findstocks/portfolio2/api/dividend_earnings_schema.php'),
    ('findstocks/portfolio2/api/fetch_dividends_earnings.php', 'findstocks/portfolio2/api/fetch_dividends_earnings.php'),
    ('findstocks/portfolio2/api/setup_schema.php', 'findstocks/portfolio2/api/setup_schema.php'),
]

print(f"Connecting to {server}...")
ftp = FTP_TLS(server)
ftp.login(user, passwd)
ftp.prot_p()
print("Connected and secured.")

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
print("  1. Visit: https://findtorontoevents.ca/findstocks/portfolio2/api/dividend_earnings_schema.php")
print("  2. Visit: https://findtorontoevents.ca/findstocks/portfolio2/api/fetch_dividends_earnings.php?action=fetch_one&ticker=AAPL")
