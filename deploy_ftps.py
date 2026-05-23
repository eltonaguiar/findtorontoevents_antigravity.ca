#!/usr/bin/env python3
"""FTPS deployment for meme scanner fixes"""

import os
import sys
import ssl
from ftplib import FTP_TLS

# Get credentials
FTP_SERVER = 'ftps2.50webs.com'
FTP_USER = 'ejaguiar1'
FTP_PASS = os.getenv('FTP_PASS', '')

if not FTP_PASS:
    print("Error: FTP_PASS not set")
    sys.exit(1)

FILES = [
    ('findcryptopairs/api/meme_scanner_fixed.php', '/findtorontoevents.ca/findcryptopairs/api/meme_scanner_fixed.php'),
    ('scripts/meme_sentiment_scraper_v2.py', '/findtorontoevents.ca/scripts/meme_sentiment_scraper_v2.py'),
    ('scripts/meme_scanner_monitor.py', '/findtorontoevents.ca/scripts/meme_scanner_monitor.py'),
]

print("="*60)
print("MEME SCANNER FIX DEPLOYMENT (FTPS)")
print("="*60)

try:
    print("Connecting to FTPS...")
    ftps = FTP_TLS(FTP_SERVER)
    ftps.login(FTP_USER, FTP_PASS)
    ftps.prot_p()  # Switch to secure data connection
    print("Connected!")
    print("")
    
    success = 0
    failed = 0
    
    for local_file, remote_path in FILES:
        print(f"Deploying: {os.path.basename(local_file)}")
        
        if not os.path.exists(local_file):
            print(f"  ERROR: Local file not found")
            failed += 1
            continue
        
        try:
            # Parse remote path
            parts = remote_path.strip('/').split('/')
            filename = parts[-1]
            dirs = parts[:-1]
            
            # Navigate to directory
            ftps.cwd('/')
            for d in dirs:
                try:
                    ftps.mkd(d)
                except:
                    pass
                ftps.cwd(d)
            
            # Upload
            with open(local_file, 'rb') as f:
                ftps.storbinary(f'STOR {filename}', f)
            
            print(f"  SUCCESS")
            success += 1
            
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1
    
    ftps.quit()
    
    print("")
    print("="*60)
    print(f"SUMMARY: {success} success, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\nAll files deployed!")
        print("\nTest: https://findtorontoevents.ca/findcryptopairs/api/meme_scanner_fixed.php?action=stats")
        sys.exit(0)
    else:
        sys.exit(1)
        
except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)
