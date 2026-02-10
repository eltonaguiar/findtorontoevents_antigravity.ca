"""Deploy disclaimer-updated pages to production via FTP."""
import os, ftplib, sys

FTP_SERVER = os.environ.get('FTP_SERVER')
FTP_USER = os.environ.get('FTP_USER')
FTP_PASS = os.environ.get('FTP_PASS')
if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
    print("ERROR: FTP credentials not found in environment variables")
    sys.exit(1)

FILES = [
    ('findstocks/portfolio2/dividends.html', '/findtorontoevents.ca/findstocks/portfolio2/dividends.html'),
    ('findstocks/portfolio2/picks.html', '/findtorontoevents.ca/findstocks/portfolio2/picks.html'),
]

LOCAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ftp = ftplib.FTP_TLS(FTP_SERVER)
ftp.login(FTP_USER, FTP_PASS)
ftp.prot_p()
print("Connected to FTP")

for local_rel, remote_path in FILES:
    local_path = os.path.join(LOCAL_ROOT, local_rel.replace('/', os.sep))
    if not os.path.exists(local_path):
        print(f"SKIP (not found): {local_rel}")
        continue
    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        size = os.path.getsize(local_path)
        print(f"OK: {local_rel} ({size:,} bytes) -> {remote_path}")
    except Exception as e:
        print(f"FAIL: {local_rel} -> {e}")

ftp.quit()
print("Done!")
