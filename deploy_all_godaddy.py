#!/usr/bin/env python3
"""Deploy all meme scanner fixes to GoDaddy"""

import os
import sys
import ftplib

FTP_SERVER = os.getenv('FTPGODADDYHOST_TE_DOTNET', 'torontoevent.net')
FTP_USER = os.getenv('FTPGODADDYUSER', 'elton@torontoevent.net')
FTP_PASS = os.getenv('FTPGODADDYPASS', '')

# 2026-04-17 host-guard: writes to root paths. If FTPGODADDYHOST_TE_DOTNET ever
# resolves to a 50webs multi-site host, files land in 50webs FTP root and
# corrupt other sites' layouts.
if '50webs' in FTP_SERVER.lower() or 'ejaguiar' in FTP_SERVER.lower():
    sys.exit(f"REFUSED: FTP_SERVER={FTP_SERVER!r} is a 50webs host; this script is GoDaddy-only.")

FILES = [
    ('findcryptopairs/api/meme_scanner_fixed.php', '/findcryptopairs/api/meme_scanner_fixed.php'),
    ('scripts/meme_sentiment_scraper_v2.py', '/scripts/meme_sentiment_scraper_v2.py'),
    ('scripts/meme_scanner_monitor.py', '/scripts/meme_scanner_monitor.py'),
]

print("="*60)
print("MEME SCANNER FIX DEPLOYMENT")
print("="*60)
print(f"Server: {FTP_SERVER}")
print(f"User: {FTP_USER}")
print("")

try:
    print("Connecting to FTP...")
    ftp = ftplib.FTP(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    print("Connected!")
    print("")
    
    success = 0
    failed = 0
    
    for local_file, remote_path in FILES:
        print(f"Deploying: {os.path.basename(local_file)}")
        
        if not os.path.exists(local_file):
            print(f"  ERROR: File not found: {local_file}")
            failed += 1
            continue
        
        try:
            # Parse path
            parts = remote_path.strip('/').split('/')
            filename = parts[-1]
            dirs = parts[:-1]
            
            # Navigate/create directories
            ftp.cwd('/')
            for d in dirs:
                try:
                    ftp.cwd(d)
                except ftplib.error_perm:
                    ftp.mkd(d)
                    ftp.cwd(d)
            
            # Upload
            with open(local_file, 'rb') as f:
                ftp.storbinary(f'STOR {filename}', f)
            
            print(f"  SUCCESS")
            success += 1
            
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1
    
    ftp.quit()
    
    print("")
    print("="*60)
    print(f"SUMMARY: {success} success, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\nAll files deployed!")
        print("\nTest URLs:")
        print("  https://findtorontoevents.ca/findcryptopairs/api/meme_scanner_fixed.php?action=stats")
        print("  https://findtorontoevents.ca/findcryptopairs/api/meme_scanner_fixed.php?action=scan&key=memescan2026")
        sys.exit(0)
    else:
        sys.exit(1)
        
except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)
