#!/usr/bin/env python3
"""Deploy Mercy fix to 50webs using FTP_TLS — ARCHIVED one-shot.

2026-04-17: ORIGINAL FILE LEAKED FTP_PASS IN PLAINTEXT. Password is still in
git history and MUST BE ROTATED on the 50webs side. See tmp/DEPLOY_SCRIPTS_ARCHIVED.md.
"""
import os
import sys

sys.exit(
    "ARCHIVED: tmp/deploy_50webs_tls.py is disabled. The original leaked a plaintext "
    "FTP password in git history (rotate at 50webs control panel). If you need "
    "to re-deploy, use tools/deploy_to_altsite.py with FTP_PASS in env."
)

# Historical content kept below as an inert comment for forensic reference only.
# FTP_HOST = "ftps2.50webs.com"
# FTP_USER = "ejaguiar1"
# FTP_PASS = os.environ.get("FTP_PASS", "")  # <-- password REMOVED 2026-04-17

def deploy():
    print("=" * 60)
    print("DEPLOYING TO 50WEBS VIA FTP_TLS")
    print("=" * 60)
    
    print(f"\n[1/5] Connecting to {FTP_HOST} via FTP_TLS...")
    ftp = FTP_TLS(FTP_HOST, timeout=30)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()  # Enable secure data connection
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
    
    if b"100vw;height:100vh" not in content:
        print("[ERROR] Local file missing the fix!")
        ftp.quit()
        return
    print(f"[OK] Local file has fix ({len(content)} bytes)")
    
    print("\n[5/5] Uploading...")
    with open("fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html", "rb") as f:
        ftp.storbinary("STOR index.html", f)
    
    size = ftp.size("index.html")
    print(f"[OK] Uploaded: {size} bytes")
    
    ftp.quit()
    print("\n" + "=" * 60)
    print("DEPLOYED TO 50WEBS (FTP_TLS)!")
    print("Test: https://findtorontoevents.ca/MOVIESHOWS3/")
    print("=" * 60)

if __name__ == "__main__":
    deploy()
