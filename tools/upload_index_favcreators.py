#!/usr/bin/env python3
"""Upload updated index.html with favcreators menu fix"""
import os
import ssl
from ftplib import FTP_TLS
from pathlib import Path

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    index_html = workspace_root / "index.html"
    
    if not index_html.exists():
        print(f"ERROR: {index_html} not found!")
        return 1
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        print(f"\n=== Uploading index.html with favcreators fix ===")
        print(f"File size: {index_html.stat().st_size / 1024:.1f} KB")
        
        # Verify the file contains the fix
        with open(index_html, "r", encoding="utf-8") as f:
            content = f.read()
            if '"/favcreators/#/Guest"' in content:
                print("[OK] File contains corrected favcreators path (lowercase)")
            else:
                print("[WARNING] favcreators path not found in expected format")
        
        # Upload the file
        with open(index_html, "rb") as f:
            ftp.storbinary(f"STOR index.html", f)
        print("[OK] Uploaded index.html successfully!")
        
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
    
    print("\n[SUCCESS] Upload complete! The favcreators menu link has been updated on the server.")
    return 0

if __name__ == "__main__":
    exit(main())
