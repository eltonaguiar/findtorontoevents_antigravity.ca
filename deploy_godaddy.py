#!/usr/bin/env python3
"""Deploy to GoDaddy hosting"""

import os
import sys
import ftplib

# GoDaddy FTP credentials
FTP_SERVER = os.getenv('FTPGODADDYHOST_TE_DOTNET', 'torontoevent.net')
FTP_USER = os.getenv('FTPGODADDYUSER', 'elton@torontoevent.net')
FTP_PASS = os.getenv('FTPGODADDYPASS', '')

# 2026-04-17 host-guard: writes to root paths (/findcryptopairs/...). If
# FTPGODADDYHOST_TE_DOTNET ever resolves to a 50webs multi-site host, files
# land in 50webs FTP root and corrupt other sites' layouts.
if '50webs' in FTP_SERVER.lower() or 'ejaguiar' in FTP_SERVER.lower():
    sys.exit(f"REFUSED: FTP_SERVER={FTP_SERVER!r} is a 50webs host; this script is GoDaddy-only.")

print(f"Server: {FTP_SERVER}")
print(f"User: {FTP_USER}")
print(f"Pass length: {len(FTP_PASS)}")

FILES = [
    ('findcryptopairs/api/meme_scanner_fixed.php', '/findcryptopairs/api/meme_scanner_fixed.php'),
]

try:
    print("Connecting...")
    ftp = ftplib.FTP(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    print("Connected!")
    print(ftp.getwelcome())
    
    for local, remote in FILES:
        print(f"\nUploading: {local}")
        dirs = remote.strip('/').split('/')[:-1]
        for d in dirs:
            try:
                ftp.cwd(d)
            except:
                ftp.mkd(d)
                ftp.cwd(d)
        
        filename = remote.split('/')[-1]
        with open(local, 'rb') as f:
            ftp.storbinary(f'STOR {filename}', f)
        print("OK")
    
    ftp.quit()
    print("\nDone!")
    
except Exception as e:
    print(f"Error: {e}")
