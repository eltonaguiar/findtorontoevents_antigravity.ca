#!/usr/bin/env python3
"""Upload .htaccess file"""
import os
import ssl
from ftplib import FTP_TLS
from pathlib import Path

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    htaccess = workspace_root / ".htaccess"
    
    if not htaccess.exists():
        print(f"ERROR: {htaccess} not found!")
        return 1
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        print(f"\n=== Uploading .htaccess ===")
        with open(htaccess, "rb") as f:
            ftp.storbinary(f"STOR .htaccess", f)
        print("Uploaded .htaccess successfully!")
        
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
