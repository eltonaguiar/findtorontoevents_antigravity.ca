#!/usr/bin/env python3
import ftplib
import time

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

def deploy():
    print("DEPLOYING MERCY FIX - FINAL ATTEMPT")
    print("=" * 60)
    
    ftp = ftplib.FTP(FTP_HOST, timeout=30)
    ftp.login(FTP_USER, FTP_PASS)
    print("[OK] Connected")
    
    ftp.cwd("MOVIESHOWS3")
    print("[OK] In MOVIESHOWS3")
    
    # Backup current
    backup = f"index.html.backup_fix_{int(time.time())}"
    ftp.rename("index.html", backup)
    print(f"[OK] Backup: {backup}")
    
    # Read and upload local file
    with open("fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html", "rb") as f:
        content = f.read()
    
    # Verify it has our fix
    if b"100vw;height:100vh" not in content:
        print("[ERROR] Local file missing the fix!")
        ftp.quit()
        return
    
    print(f"[OK] Local file has fix ({len(content)} bytes)")
    
    # Upload
    with open("fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html", "rb") as f:
        ftp.storbinary("STOR index.html", f)
    
    size = ftp.size("index.html")
    print(f"[OK] Uploaded: {size} bytes")
    ftp.quit()
    
    print("=" * 60)
    print("DEPLOYED! Test now.")

if __name__ == "__main__":
    deploy()
