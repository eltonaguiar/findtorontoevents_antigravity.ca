#!/usr/bin/env python3
"""Deploy Mercy fix to 50webs using FTP_TLS"""
from ftplib import FTP_TLS
import os
import time

FTP_HOST = os.environ.get("FTP_SERVER", "ftps2.50webs.com")
FTP_USER = os.environ.get("FTP_USER", "ejaguiar1")
FTP_PASS = os.environ.get("FTP_PASS", "")

def deploy():
    print("=" * 60)
    print("DEPLOYING MERCY FIX TO 50WEBS")
    print("=" * 60)
    print(f"Server: {FTP_HOST}")
    print(f"User: {FTP_USER}")
    
    print(f"\n[1/5] Connecting via FTP_TLS...")
    ftp = FTP_TLS(FTP_HOST, timeout=30)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()  # Secure data connection
    print("[OK] Connected via TLS")
    
    print("\n[2/5] Navigating to MOVIESHOWS3...")
    ftp.cwd("/findtorontoevents.ca/MOVIESHOWS3")
    print(f"[OK] In: {ftp.pwd()}")
    
    print("\n[3/5] Creating backup...")
    backup = f"index.html.backup_{int(time.time())}"
    ftp.rename("index.html", backup)
    print(f"[OK] Backup: {backup}")
    
    print("\n[4/5] Reading local file...")
    with open("fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html", "rb") as f:
        content = f.read()
    print(f"[OK] Local file: {len(content)} bytes")
    
    if b"100vw;height:100vh" not in content:
        print("[ERROR] Local file missing the fix!")
        ftp.quit()
        return
    print("[OK] Local file has 100vw/100vh fix")
    
    print("\n[5/5] Uploading...")
    with open("fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html", "rb") as f:
        ftp.storbinary("STOR index.html", f)
    
    size = ftp.size("index.html")
    print(f"[OK] Uploaded: {size} bytes")
    
    ftp.quit()
    print("\n" + "=" * 60)
    print("DEPLOYED TO 50WEBS!")
    print("Test: https://findtorontoevents.ca/MOVIESHOWS3/")
    print("=" * 60)

if __name__ == "__main__":
    deploy()
