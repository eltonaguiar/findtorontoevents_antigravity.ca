#!/usr/bin/env python3
"""Simple FTP deployment for meme scanner fixes"""

import os
import sys
from ftplib import FTP, error_perm

# Get credentials from environment
FTP_SERVER = os.getenv('FTP_SERVER', 'ftps2.50webs.com')
FTP_USER = os.getenv('FTP_USER', 'ejaguiar1')
FTP_PASS = os.getenv('FTP_PASS')

if not FTP_PASS:
    print("Error: FTP_PASS environment variable not set")
    sys.exit(1)

FILES = [
    ('findcryptopairs/api/meme_scanner_fixed.php', '/findtorontoevents.ca/findcryptopairs/api/meme_scanner_fixed.php'),
    ('scripts/meme_sentiment_scraper_v2.py', '/findtorontoevents.ca/scripts/meme_sentiment_scraper_v2.py'),
    ('scripts/meme_scanner_monitor.py', '/findtorontoevents.ca/scripts/meme_scanner_monitor.py'),
]

print("="*60)
print("MEME COIN SCANNER FIX DEPLOYMENT")
print("="*60)
print(f"Server: {FTP_SERVER}")
print(f"User: {FTP_USER}")
print("")

try:
    # Connect to FTP
    print("Connecting to FTP...")
    ftp = FTP(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    print("✅ Connected successfully")
    print("")
    
    success = 0
    failed = 0
    
    for local_file, remote_path in FILES:
        print(f"Deploying: {local_file}")
        print(f"  -> {remote_path}")
        
        if not os.path.exists(local_file):
            print(f"  ❌ Local file not found")
            failed += 1
            continue
        
        try:
            # Get directory and filename
            remote_dir = os.path.dirname(remote_path)
            filename = os.path.basename(remote_path)
            
            # Try to create directory structure
            dirs = remote_dir.strip('/').split('/')
            current_path = ""
            for d in dirs:
                current_path += f"/{d}"
                try:
                    ftp.mkd(current_path)
                except error_perm:
                    pass  # Directory may already exist
            
            # Change to target directory
            ftp.cwd(remote_dir)
            
            # Upload file
            with open(local_file, 'rb') as f:
                ftp.storbinary(f'STOR {filename}', f)
            
            print(f"  ✅ Upload successful")
            success += 1
            
        except Exception as e:
            print(f"  ❌ Upload failed: {e}")
            failed += 1
        
        print("")
    
    ftp.quit()
    
    print("="*60)
    print("DEPLOYMENT SUMMARY")
    print("="*60)
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n✅ All files deployed successfully!")
        print("\nNext steps:")
        print("  1. Test: https://findtorontoevents.ca/findcryptopairs/api/meme_scanner_fixed.php?action=stats")
        print("  2. Enable new GitHub Actions workflow")
        sys.exit(0)
    else:
        print("\n🔴 Some deployments failed")
        sys.exit(1)
        
except Exception as e:
    print(f"\n❌ Deployment error: {e}")
    sys.exit(1)
