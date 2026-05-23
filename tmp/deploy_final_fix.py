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
    
    print(f"\n[1/4] Connecting via FTP_TLS...")
    ftp = FTP_TLS(FTP_HOST, timeout=30)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print("[OK] Connected via TLS")
    
    print("\n[2/4] Navigating to MOVIESHOWS3...")
    ftp.cwd("/findtorontoevents.ca/MOVIESHOWS3")
    print(f"[OK] In: {ftp.pwd()}")
    
    print("\n[3/4] Creating backup...")
    try:
        backup = f"index.html.backup_{int(time.time())}"
        ftp.rename("index.html", backup)
        print(f"[OK] Backup: {backup}")
    except:
        print("[SKIP] No existing index.html to backup")
    
    print("\n[4/4] Uploading...")
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
