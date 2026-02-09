#!/usr/bin/env python3
"""
Deploy portfolio2 files to FTP server.
Uploads findstocks/portfolio2/ directory to /findtorontoevents.ca/findstocks/portfolio2/
"""
import os
import sys
from ftplib import FTP_TLS

# FTP credentials from environment variables
FTP_SERVER = os.environ.get('FTP_SERVER', '')
FTP_USER = os.environ.get('FTP_USER', '')
FTP_PASS = os.environ.get('FTP_PASS', '')

if not FTP_SERVER or not FTP_USER or not FTP_PASS:
    print("ERROR: FTP credentials not found in environment variables.")
    print("Required: FTP_SERVER, FTP_USER, FTP_PASS")
    sys.exit(1)

# Local source directory
LOCAL_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'findstocks', 'portfolio2')
REMOTE_BASE = '/findtorontoevents.ca/findstocks/portfolio2'

def ensure_remote_dir(ftp, path):
    """Create remote directory if it doesn't exist."""
    dirs = path.strip('/').split('/')
    current = ''
    for d in dirs:
        current += '/' + d
        try:
            ftp.cwd(current)
        except:
            try:
                ftp.mkd(current)
                print(f"  Created dir: {current}")
            except:
                pass

def upload_file(ftp, local_path, remote_path):
    """Upload a single file."""
    with open(local_path, 'rb') as f:
        ftp.storbinary(f'STOR {remote_path}', f)
    print(f"  Uploaded: {remote_path}")

def main():
    print(f"Connecting to {FTP_SERVER}...")
    ftp = FTP_TLS(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print("Connected with TLS.")

    # Ensure directories exist
    ensure_remote_dir(ftp, REMOTE_BASE)
    ensure_remote_dir(ftp, REMOTE_BASE + '/api')
    ensure_remote_dir(ftp, REMOTE_BASE + '/stats')

    # Upload all files
    uploaded = 0
    for root, dirs, files in os.walk(LOCAL_BASE):
        for fname in files:
            local_path = os.path.join(root, fname)
            rel_path = os.path.relpath(local_path, LOCAL_BASE).replace('\\', '/')
            remote_path = REMOTE_BASE + '/' + rel_path
            try:
                upload_file(ftp, local_path, remote_path)
                uploaded += 1
            except Exception as e:
                print(f"  FAILED: {remote_path} - {e}")

    print(f"\nDone! Uploaded {uploaded} files.")
    ftp.quit()

if __name__ == '__main__':
    main()
