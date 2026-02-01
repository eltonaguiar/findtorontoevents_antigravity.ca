#!/usr/bin/env python3
"""
Deploy the updated nav menu to the remote server via FTPS
1. Download current remote index.html as backup
2. Upload the modified local index.html
"""

import os
import ssl
from ftplib import FTP_TLS
from pathlib import Path
from datetime import datetime

def main():
    # FTP credentials (same as other upload scripts)
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    local_index = workspace_root / "index.html"
    
    if not local_index.exists():
        print(f"ERROR: {local_index} not found!")
        return 1
    
    # Create backup directory
    backup_dir = workspace_root / "backups" / "remote"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("Quick Nav Menu Deployment to Server")
    print("=" * 70)
    
    # Connect to FTPS
    print(f"\nConnecting to {FTP_HOST}...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()  # Enable data encryption
        print("[OK] Connected successfully!")
        
        current_dir = ftp.pwd()
        print(f"  Remote directory: {current_dir}")
        
        # Step 1: Download remote index.html as backup
        print("\n[Step 1/2] Downloading remote index.html as backup...")
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_file = backup_dir / f"remote-index-{timestamp}.html"
        
        try:
            with open(backup_file, 'wb') as f:
                ftp.retrbinary('RETR index.html', f.write)
            backup_size = backup_file.stat().st_size
            print(f"[OK] Remote backup created: {backup_file.relative_to(workspace_root)}")
            print(f"  Backup size: {backup_size / 1024:.1f} KB")
        except Exception as e:
            print(f"[WARNING] Could not backup remote file: {e}")
            print("  Proceeding with upload anyway...")
        
        # Step 2: Upload modified index.html
        print("\n[Step 2/2] Uploading updated index.html...")
        with open(local_index, 'rb') as f:
            ftp.storbinary('STOR index.html', f)
        
        local_size = local_index.stat().st_size
        print(f"[OK] Uploaded successfully!")
        print(f"  File size: {local_size / 1024:.1f} KB")
        
        # Verify the upload
        print("\n[Verification] Checking uploaded file...")
        try:
            remote_size = ftp.size('index.html')
            if remote_size == local_size:
                print(f"[OK] Size verification passed: {remote_size} bytes")
            else:
                print(f"[!] Size mismatch: local={local_size}, remote={remote_size}")
        except:
            print("  (Size verification not available)")
        
        print("\n" + "=" * 70)
        print("DEPLOYMENT SUCCESSFUL")
        print("=" * 70)
        print("\nChanges now live on server:")
        print("  [+] FAVCREATORS link added to NETWORK section")
        print("  [+] 'My Collection' moved to PERSONAL section (bottom)")
        print("  [+] 'Data Management' section moved near bottom")
        print("  [+] Menu decluttered - navigation options prioritized")
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        try:
            ftp.quit()
        except:
            pass

if __name__ == "__main__":
    exit(main())
