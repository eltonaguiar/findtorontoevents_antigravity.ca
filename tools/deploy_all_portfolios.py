#!/usr/bin/env python3
"""
Deploy ALL portfolio systems to FTP server.
Uploads:
  - findstocks/portfolio2/       -> /findtorontoevents.ca/findstocks/portfolio2/
  - findmutualfunds2/portfolio2/ -> /findtorontoevents.ca/findmutualfunds2/portfolio2/
  - findforex2/portfolio/        -> /findtorontoevents.ca/findforex2/portfolio/
  - findcryptopairs/portfolio/   -> /findtorontoevents.ca/findcryptopairs/portfolio/
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

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_ROOT = '/findtorontoevents.ca'

# Define all portfolio systems to deploy
DEPLOY_TARGETS = [
    {
        'name': 'Stocks Portfolio v2',
        'local': os.path.join(PROJECT_ROOT, 'findstocks', 'portfolio2'),
        'remote': REMOTE_ROOT + '/findstocks/portfolio2',
        'subdirs': ['api', 'stats']
    },
    {
        'name': 'Mutual Funds Portfolio v2',
        'local': os.path.join(PROJECT_ROOT, 'findmutualfunds2', 'portfolio2'),
        'remote': REMOTE_ROOT + '/findmutualfunds2/portfolio2',
        'subdirs': ['api', 'stats']
    },
    {
        'name': 'Forex Portfolio',
        'local': os.path.join(PROJECT_ROOT, 'findforex2', 'portfolio'),
        'remote': REMOTE_ROOT + '/findforex2/portfolio',
        'subdirs': ['api', 'stats']
    },
    {
        'name': 'Crypto Pairs Portfolio',
        'local': os.path.join(PROJECT_ROOT, 'findcryptopairs', 'portfolio'),
        'remote': REMOTE_ROOT + '/findcryptopairs/portfolio',
        'subdirs': ['api', 'stats']
    }
]

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

def deploy_target(ftp, target):
    """Deploy a single portfolio system."""
    name = target['name']
    local_base = target['local']
    remote_base = target['remote']
    subdirs = target['subdirs']

    if not os.path.exists(local_base):
        print(f"\n  SKIP: {name} — local directory not found: {local_base}")
        return 0

    print(f"\n{'='*60}")
    print(f"  Deploying: {name}")
    print(f"  Local:  {local_base}")
    print(f"  Remote: {remote_base}")
    print(f"{'='*60}")

    # Ensure remote directories exist
    ensure_remote_dir(ftp, remote_base)
    for sd in subdirs:
        ensure_remote_dir(ftp, remote_base + '/' + sd)

    # Upload all files
    uploaded = 0
    for root, dirs, files in os.walk(local_base):
        for fname in files:
            local_path = os.path.join(root, fname)
            rel_path = os.path.relpath(local_path, local_base).replace('\\', '/')
            remote_path = remote_base + '/' + rel_path

            # Ensure parent directory exists
            parent = '/'.join(remote_path.split('/')[:-1])
            ensure_remote_dir(ftp, parent)

            try:
                upload_file(ftp, local_path, remote_path)
                uploaded += 1
                print(f"    OK: {rel_path}")
            except Exception as e:
                print(f"    FAIL: {rel_path} — {e}")

    print(f"  Uploaded {uploaded} files for {name}")
    return uploaded

def main():
    # Allow deploying specific target via command line
    target_filter = sys.argv[1] if len(sys.argv) > 1 else 'all'

    print(f"Connecting to {FTP_SERVER}...")
    ftp = FTP_TLS(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print("Connected with TLS.")

    total_uploaded = 0
    targets_deployed = 0

    for target in DEPLOY_TARGETS:
        if target_filter != 'all':
            # Match by name keyword
            if target_filter.lower() not in target['name'].lower():
                continue

        count = deploy_target(ftp, target)
        total_uploaded += count
        if count > 0:
            targets_deployed += 1

    print(f"\n{'='*60}")
    print(f"  DONE! Deployed {targets_deployed} systems, {total_uploaded} total files.")
    print(f"{'='*60}")

    ftp.quit()

if __name__ == '__main__':
    main()
