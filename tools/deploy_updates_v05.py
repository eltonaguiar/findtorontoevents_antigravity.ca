#!/usr/bin/env python3
"""Targeted FTP_TLS deploy for v0.05 updates: updates/index.html + Pine Script."""
import os
import ftplib

FTP_SERVER = os.environ.get('FTP_SERVER', 'ftps2.50webs.com')
FTP_USER = os.environ.get('FTP_USER', '')
FTP_PASS = os.environ.get('FTP_PASS', '')
REMOTE_BASE = '/findtorontoevents.ca'

FILES = [
    ('updates/index.html', '/findtorontoevents.ca/updates/index.html'),
    ('Simpletonv0.04_Kimi_Cursor.pine', '/findtorontoevents.ca/Simpletonv0.04_Kimi_Cursor.pine'),
]

if not FTP_USER or not FTP_PASS:
    print("ERROR: FTP_USER / FTP_PASS not set")
    exit(1)

print(f"Connecting to {FTP_SERVER} as {FTP_USER}...")
ftp = ftplib.FTP_TLS(FTP_SERVER)
ftp.login(FTP_USER, FTP_PASS)
ftp.prot_p()
print("Connected (TLS).")

for local_path, remote_path in FILES:
    if not os.path.exists(local_path):
        print(f"SKIP (not found): {local_path}")
        continue
    size = os.path.getsize(local_path)
    print(f"Uploading {local_path} ({size:,} bytes) -> {remote_path}")
    remote_dir = '/'.join(remote_path.split('/')[:-1])
    try:
        ftp.cwd(remote_dir)
    except Exception:
        ftp.mkd(remote_dir)
        ftp.cwd(remote_dir)
    with open(local_path, 'rb') as f:
        ftp.storbinary(f'STOR {remote_path.split("/")[-1]}', f)
    print(f"  OK: {remote_path}")

ftp.quit()
print("\nAll files deployed successfully.")
