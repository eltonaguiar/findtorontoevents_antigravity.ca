#!/usr/bin/env python3
"""Deploy updated nav chunk and index.html to all FTP locations."""
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

CHUNK = '_next/static/chunks/a2ac3a6616d60872.js'

# Deploy chunk to all known paths
FILES = {
    'index.html': f'{REMOTE_BASE}/index.html',
    CHUNK: f'{REMOTE_BASE}/_next/static/chunks/a2ac3a6616d60872.js',
    CHUNK: f'{REMOTE_BASE}/next/_next/static/chunks/a2ac3a6616d60872.js',
}

# Additional chunk paths
EXTRA_CHUNK_PATHS = [
    f'{REMOTE_BASE}/_next/static/chunks/a2ac3a6616d60872.js',
    f'{REMOTE_BASE}/next/_next/static/chunks/a2ac3a6616d60872.js',
    f'{REMOTE_BASE}/TORONTOEVENTS_ANTIGRAVITY/_next/static/chunks/a2ac3a6616d60872.js',
    f'{REMOTE_BASE}/TORONTOEVENTS_ANTIGRAVITY/next/_next/static/chunks/a2ac3a6616d60872.js',
]

def main():
    print(f'Connecting to {FTP_SERVER}...')
    ftp = ftplib.FTP(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    print(f'Connected.')

    # Deploy index.html
    local_index = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'index.html')
    with open(local_index, 'rb') as f:
        ftp.storbinary(f'STOR {REMOTE_BASE}/index.html', f)
    print(f'  OK: index.html -> {REMOTE_BASE}/index.html')

    # Deploy chunk to all paths
    local_chunk = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), CHUNK)
    for remote_path in EXTRA_CHUNK_PATHS:
        try:
            with open(local_chunk, 'rb') as f:
                ftp.storbinary(f'STOR {remote_path}', f)
            print(f'  OK: chunk -> {remote_path}')
        except Exception as e:
            print(f'  SKIP: {remote_path} ({e})')

    # Also deploy taste profile files
    taste_files = {
        'favcreators/public/taste-profile/index.html': f'{REMOTE_BASE}/fc/taste-profile/index.html',
        'favcreators/public/taste-profile/taste_profile.json': f'{REMOTE_BASE}/fc/taste-profile/taste_profile.json',
    }
    for local_path, remote_path in taste_files.items():
        full_local = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), local_path)
        if os.path.exists(full_local):
            try:
                with open(full_local, 'rb') as f:
                    ftp.storbinary(f'STOR {remote_path}', f)
                print(f'  OK: {local_path} -> {remote_path}')
            except Exception as e:
                print(f'  SKIP: {remote_path} ({e})')

    ftp.quit()
    print('\nDeploy complete.')

if __name__ == '__main__':
    main()
