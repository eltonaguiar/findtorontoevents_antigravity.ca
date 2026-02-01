#!/usr/bin/env python3
"""Download current index.html from FTP server"""
import os
import ssl
from ftplib import FTP_TLS
from pathlib import Path

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    download_path = workspace_root / "index_server_download.html"
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        print(f"\n=== Downloading index.html from server ===")
        with open(download_path, "wb") as f:
            ftp.retrbinary("RETR index.html", f.write)
        print(f"Downloaded to: {download_path}")
        print(f"File size: {download_path.stat().st_size / 1024:.1f} KB")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        try:
            ftp.quit()
        except:
            pass
    
    return 0

if __name__ == "__main__":
    exit(main())
