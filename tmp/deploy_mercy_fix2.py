#!/usr/bin/env python3
import ftplib
import os
import sys
import time

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")
LOCAL_FILE = "fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html"

def deploy():
    print("=" * 50)
    print("DEPLOYING MERCY FIX v2 - DIMENSION FIX")
    print("=" * 50)
    
    ftp = ftplib.FTP(FTP_HOST, timeout=30)
    ftp.login(FTP_USER, FTP_PASS)
    print(f"[OK] Connected to {FTP_HOST}")
    
    ftp.cwd("MOVIESHOWS3")
    print("[OK] In MOVIESHOWS3 directory")
    
    # Backup
    backup = f"index.html.backup_v2_{int(time.time())}"
    ftp.rename("index.html", backup)
    print(f"[OK] Backup: {backup}")
    
    # Upload
    with open(LOCAL_FILE, 'rb') as f:
        ftp.storbinary('STOR index.html', f)
    
    size = ftp.size("index.html")
    print(f"[OK] Uploaded: {size:,} bytes")
    ftp.quit()
    
    print("=" * 50)
    print("DEPLOYED! Test Mercy now.")
    print("=" * 50)

if __name__ == "__main__":
    deploy()
