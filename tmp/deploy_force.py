#!/usr/bin/env python3
import ftplib
import time

FTP_HOST = "torontoevent.net"
FTP_USER = "elton@torontoevent.net"
FTP_PASS = os.environ.get("FTPGODADDYPASS", "")

def deploy():
    print("FORCE DEPLOY - BYPASSING CACHE")
    print("=" * 60)
    
    ftp = ftplib.FTP(FTP_HOST, timeout=30)
    ftp.login(FTP_USER, FTP_PASS)
    print("[OK] Connected to", FTP_HOST)
    
    # List root first
    print("\nRoot directory:")
    ftp.retrlines("LIST")
    
    # Check if MOVIESHOWS3 exists
    print("\nEntering MOVIESHOWS3...")
    ftp.cwd("MOVIESHOWS3")
    print("Current dir:", ftp.pwd())
    
    # List files
    print("\nFiles in MOVIESHOWS3:")
    files = []
    ftp.retrlines("LIST", files.append)
    for f in files:
        print("  ", f)
    
    # Check current index.html size
    try:
        current_size = ftp.size("index.html")
        print(f"\nCurrent index.html size: {current_size}")
    except:
        print("\nCould not get index.html size")
    
    # Read local file
    with open("fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html", "rb") as f:
        local_content = f.read()
    
    print(f"Local file size: {len(local_content)}")
    
    # Check if fix is in local file
    if b"100vw;height:100vh" in local_content:
        print("[OK] Local file has the 100vw/100vh fix")
    else:
        print("[X] Local file MISSING the fix!")
        ftp.quit()
        return
    
    # Delete old file first (force new)
    print("\nDeleting old index.html...")
    try:
        ftp.delete("index.html")
        print("[OK] Deleted")
    except Exception as e:
        print(f"[!] Could not delete: {e}")
    
    # Upload new file
    print("\nUploading new index.html...")
    with open("fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html", "rb") as f:
        ftp.storbinary("STOR index.html", f)
    
    new_size = ftp.size("index.html")
    print(f"[OK] New file size: {new_size}")
    
    # Rename to bust cache
    cache_bust_name = f"index.html?v={int(time.time())}"
    print(f"\nCache bust version: {cache_bust_name}")
    
    ftp.quit()
    print("=" * 60)
    print("DEPLOYED! Clear browser cache and test.")

if __name__ == "__main__":
    deploy()
