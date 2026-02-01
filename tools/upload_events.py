#!/usr/bin/env python3
"""
Upload events.json to server
"""
import os
import ssl
from ftplib import FTP_TLS
from pathlib import Path

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    events_json = workspace_root / "events.json"
    
    if not events_json.exists():
        print(f"ERROR: {events_json} not found!")
        return 1
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        print(f"\n=== Uploading events.json ===")
        print(f"File size: {events_json.stat().st_size / 1024:.1f} KB")
        with open(events_json, "rb") as f:
            ftp.storbinary(f"STOR events.json", f)
        print("Uploaded events.json successfully!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    finally:
        try:
            ftp.quit()
        except:
            pass
    
    return 0

if __name__ == "__main__":
    exit(main())
