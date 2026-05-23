#!/usr/bin/env python3
import ftplib
import time

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

def deploy():
    print("DEPLOYING MERCY FIX v3")
    print("=" * 50)
    
    # Read local file
    with open("fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html", "r", encoding="utf-8") as f:
        local_content = f.read()
    
    # Verify local file has the fix
    if "100vw;height:100vh" not in local_content:
        print("ERROR: Local file doesn't have the fix!")
        return
    print("[OK] Local file has 100vw/100vh fix")
    
    # Connect FTP
    ftp = ftplib.FTP(FTP_HOST, timeout=30)
    ftp.login(FTP_USER, FTP_PASS)
    print("[OK] Connected")
    
    ftp.cwd("MOVIESHOWS3")
    print("[OK] In MOVIESHOWS3")
    
    # Backup
    backup = f"index.html.backup_v3_{int(time.time())}"
    ftp.rename("index.html", backup)
    print(f"[OK] Backup: {backup}")
    
    # Upload
    with open("fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html", "rb") as f:
        ftp.storbinary("STOR index.html", f)
    
    # Verify
    size = ftp.size("index.html")
    print(f"[OK] Uploaded: {size} bytes")
    
    # Download and verify
    ftp.retrlines("RETR index.html", lambda line: None)  # Just to check it exists
    
    ftp.quit()
    print("=" * 50)
    print("DEPLOYED! Test Mercy now.")

if __name__ == "__main__":
    deploy()
