#!/usr/bin/env python3
"""Deploy Mercy trailer fix to findtorontoevents.ca"""
import ftplib
import os
import sys
import time

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

LOCAL_FILE = "fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html"
REMOTE_FILE = "index.html"
REMOTE_DIR = "MOVIESHOWS3"

def deploy():
    print("=" * 50)
    print("DEPLOYING MERCY TRAILER FIX")
    print("=" * 50)
    
    # Check local file exists
    if not os.path.exists(LOCAL_FILE):
        print(f"[X] Local file not found: {LOCAL_FILE}")
        sys.exit(1)
    
    local_size = os.path.getsize(LOCAL_FILE)
    print(f"\n[OK] Local file: {LOCAL_FILE} ({local_size:,} bytes)")
    
    # Connect to FTP
    print(f"\n[1/4] Connecting to {FTP_HOST}...")
    try:
        ftp = ftplib.FTP(FTP_HOST, timeout=30)
        ftp.login(FTP_USER, FTP_PASS)
        print(f"[OK] Connected")
    except Exception as e:
        print(f"[X] Connection failed: {e}")
        sys.exit(1)
    
    # Navigate to MOVIESHOWS3
    print(f"\n[2/4] Navigating to {REMOTE_DIR}...")
    try:
        ftp.cwd(REMOTE_DIR)
        print(f"[OK] In directory: {ftp.pwd()}")
    except Exception as e:
        print(f"[X] Cannot change directory: {e}")
        ftp.quit()
        sys.exit(1)
    
    # Backup current index.html
    print(f"\n[3/4] Creating backup...")
    try:
        # List files to check if index.html exists
        files = ftp.nlst()
        if REMOTE_FILE in files:
            backup_name = f"index.html.backup_{int(time.time() * 1000)}"
            ftp.rename(REMOTE_FILE, backup_name)
            print(f"[OK] Backup created: {backup_name}")
        else:
            print("[!] No existing index.html to backup")
    except Exception as e:
        print(f"[!] Backup warning: {e}")
    
    # Upload fixed file
    print(f"\n[4/4] Uploading fixed index.html...")
    try:
        with open(LOCAL_FILE, 'rb') as f:
            ftp.storbinary(f'STOR {REMOTE_FILE}', f)
        print(f"[OK] Upload complete")
        
        # Verify upload
        uploaded_size = ftp.size(REMOTE_FILE)
        print(f"[OK] Remote file size: {uploaded_size:,} bytes")
        
        if uploaded_size == local_size:
            print(f"[OK] Size matches - upload verified!")
        else:
            print(f"[!] Size mismatch - local: {local_size}, remote: {uploaded_size}")
    except Exception as e:
        print(f"[X] Upload failed: {e}")
        ftp.quit()
        sys.exit(1)
    
    # Close connection
    ftp.quit()
    
    print("\n" + "=" * 50)
    print("DEPLOYMENT COMPLETE!")
    print("=" * 50)
    print("\nTest the fix:")
    print("1. Go to: https://findtorontoevents.ca/MOVIESHOWS3/")
    print("2. Click the magnifying glass (search)")
    print("3. Type 'Mercy'")
    print("4. Click on the Mercy movie card")
    print("5. The trailer should now play correctly!")
    print("\nIf issues occur, check the backup file on the server.")

if __name__ == "__main__":
    deploy()
