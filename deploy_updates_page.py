#!/usr/bin/env python3
"""
Deploy updates page to remote site via FTP
"""

import os
import sys
from ftplib import FTP, error_perm

# Get credentials from environment
FTP_SERVER = os.getenv('FTP_SERVER', 'ftps2.50webs.com')
FTP_USER = os.getenv('FTP_USER', 'ejaguiar1')
FTP_PASS = os.getenv('FTP_PASS')

if not FTP_PASS:
    print("Error: FTP_PASS environment variable not set")
    print("Set it with: $env:FTP_PASS='your_password'")
    sys.exit(1)

FILES = [
    # Updates page
    ('updates/index.html', '/findtorontoevents.ca/updates/index.html'),
    # Markdown updates (for reference)
    ('updates_findtorontoevents.md', '/findtorontoevents.ca/updates/updates_findtorontoevents.md'),
    # Prop firm analysis
    ('PROP_FIRM_FORWARD_ANALYSIS.json', '/findtorontoevents.ca/PROP_FIRM_FORWARD_ANALYSIS.json'),
    # Reports
    ('PROP_FIRM_FUTURES_COMPARISON_SUMMARY.md', '/findtorontoevents.ca/PROP_FIRM_FUTURES_COMPARISON_SUMMARY.md'),
    ('NEW_STRATEGIES_FINAL_REPORT.md', '/findtorontoevents.ca/NEW_STRATEGIES_FINAL_REPORT.md'),
    # Backtest results
    ('backtest_results/futures_comparison/futures_comparison_report.md', '/findtorontoevents.ca/backtest_results/futures_comparison/futures_comparison_report.md'),
    ('backtest_results/futures_comparison/comparison_data.json', '/findtorontoevents.ca/backtest_results/futures_comparison/comparison_data.json'),
    ('backtest_results/futures_comparison/visual_comparison.txt', '/findtorontoevents.ca/backtest_results/futures_comparison/visual_comparison.txt'),
]

print("="*70)
print("DEPLOYING UPDATES PAGE TO REMOTE SITE")
print("="*70)
print(f"Server: {FTP_SERVER}")
print(f"User: {FTP_USER}")
print(f"Files to deploy: {len(FILES)}")
print("")

try:
    # Connect to FTP
    print("Connecting to FTP...")
    ftp = FTP(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    print("Connected successfully")
    print("")
    
    success = 0
    failed = 0
    
    for local_file, remote_path in FILES:
        print(f"Deploying: {local_file}")
        print(f"  -> {remote_path}")
        
        if not os.path.exists(local_file):
            print(f"  [SKIP] Local file not found")
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
            
            print(f"  [OK] Upload successful")
            success += 1
            
        except Exception as e:
            print(f"  [FAIL] Upload failed: {e}")
            failed += 1
        
        print("")
    
    ftp.quit()
    
    print("="*70)
    print("DEPLOYMENT SUMMARY")
    print("="*70)
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n[OK] All files deployed successfully!")
        print("\nVerify at:")
        print("  https://findtorontoevents.ca/updates/")
        sys.exit(0)
    else:
        print("\n[WARNING] Some deployments failed")
        sys.exit(1)
        
except Exception as e:
    print(f"\n[ERROR] Deployment error: {e}")
    sys.exit(1)
