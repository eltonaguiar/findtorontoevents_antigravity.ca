#!/usr/bin/env python3
"""Deploy taste profile page and data to FTP."""
import ftplib
import os
import sys

FTP_SERVER = os.environ.get('FTP_SERVER', '')
FTP_USER = os.environ.get('FTP_USER', '')
FTP_PASS = os.environ.get('FTP_PASS', '')
REMOTE_BASE = '/findtorontoevents.ca'

if not FTP_SERVER or not FTP_USER or not FTP_PASS:
    print('ERROR: FTP credentials not set')
    sys.exit(1)

FILES = {
    'index.html': f'{REMOTE_BASE}/index.html',
    'favcreators/public/taste-profile/index.html': f'{REMOTE_BASE}/fc/taste-profile/index.html',
    'favcreators/public/taste-profile/taste_profile.json': f'{REMOTE_BASE}/fc/taste-profile/taste_profile.json',
    'taste_profile.json': f'{REMOTE_BASE}/taste_profile.json',
    'favcreators/public/api/taste_instagram.php': f'{REMOTE_BASE}/fc/api/taste_instagram.php',
}

def ensure_remote_dir(ftp, path):
    """Create remote directory if it doesn't exist."""
    dirs = path.strip('/').split('/')
    current = ''
    for d in dirs:
        current += '/' + d
        try:
            ftp.cwd(current)
        except ftplib.error_perm:
            try:
                ftp.mkd(current)
                print(f'  Created dir: {current}')
            except ftplib.error_perm:
                pass

def main():
    print(f'Connecting to {FTP_SERVER}...')
    ftp = ftplib.FTP(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    print(f'Connected. Remote base: {REMOTE_BASE}')
    
    # Ensure taste-profile directory exists
    ensure_remote_dir(ftp, f'{REMOTE_BASE}/fc/taste-profile')
    
    uploaded = 0
    failed = 0
    
    for local_path, remote_path in FILES.items():
        full_local = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), local_path)
        if not os.path.exists(full_local):
            print(f'  SKIP (not found): {local_path}')
            continue
        
        try:
            size = os.path.getsize(full_local)
            with open(full_local, 'rb') as f:
                ftp.storbinary(f'STOR {remote_path}', f)
            print(f'  OK: {local_path} -> {remote_path} ({size:,} bytes)')
            uploaded += 1
        except Exception as e:
            print(f'  FAIL: {local_path} -> {remote_path}: {e}')
            failed += 1
    
    ftp.quit()
    print(f'\nDone: {uploaded} uploaded, {failed} failed')
    sys.exit(1 if failed > 0 else 0)

if __name__ == '__main__':
    main()
