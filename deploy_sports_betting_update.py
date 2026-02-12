#!/usr/bin/env python3
"""
Deploy sports betting updates to both findtorontoevents.ca and tdotevent.ca
Files: live-monitor/sports-betting.html, updates/index.html
"""
import os
import sys
from ftplib import FTP_TLS

# FTP Credentials from .env
FTP_HOST = "ftps2.50webs.com"
FTP_USER = "ejaguiar1"
FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"

# Files to deploy
FILES = [
    {
        "local": r"e:\findtorontoevents_antigravity.ca\live-monitor\sports-betting.html",
        "remote_main": "/findtorontoevents.ca/live-monitor/sports-betting.html",
        "remote_sister": "/tdotevent.ca/live-monitor/sports-betting.html"
    },
    {
        "local": r"e:\findtorontoevents_antigravity.ca\updates\index.html",
        "remote_main": "/findtorontoevents.ca/updates/index.html",
        "remote_sister": "/tdotevent.ca/updates/index.html"
    }
]

def deploy_file(ftp, local_path, remote_path):
    """Upload a single file via FTPS"""
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f)
    print(f"  [UPLOADED] {local_path} -> {remote_path}")

def deploy_to_site(site_name, remote_root):
    """Deploy all files to a specific site"""
    print(f"\n[DEPLOY] Deploying to {site_name}...")
    try:
        ftp = FTP_TLS(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print(f"  [CONNECTED] {FTP_HOST}")
        
        for file in FILES:
            remote_path = file["remote_main"] if "findtorontoevents" in remote_root else file["remote_sister"]
            deploy_file(ftp, file["local"], remote_path)
        
        ftp.quit()
        print(f"  [DONE] {site_name} deployment complete!")
        return True
    except Exception as e:
        print(f"  [ERROR] {site_name} deployment failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SPORTS BETTING UPDATE DEPLOYMENT")
    print("=" * 60)
    print("\nFiles to deploy:")
    print("  1. live-monitor/sports-betting.html")
    print("     - System Analysis tab")
    print("     - Win Rate tooltip with alert icon")
    print("  2. updates/index.html")
    print("     - Sports betting analysis update entry")
    
    results = []
    
    # Deploy to main site
    results.append(("findtorontoevents.ca", deploy_to_site("findtorontoevents.ca", "/findtorontoevents.ca")))
    
    # Deploy to sister site
    results.append(("tdotevent.ca", deploy_to_site("tdotevent.ca", "/tdotevent.ca")))
    
    print("\n" + "=" * 60)
    print("DEPLOYMENT SUMMARY")
    print("=" * 60)
    for site, success in results:
        status = "[SUCCESS]" if success else "[FAILED]"
        print(f"  {site}: {status}")
    
    all_success = all(r[1] for r in results)
    sys.exit(0 if all_success else 1)
