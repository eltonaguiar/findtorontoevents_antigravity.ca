#!/usr/bin/env python3
"""Upload index3.html to test if server caching is the issue"""
import os
import ssl
from ftplib import FTP_TLS
from pathlib import Path

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    index3_html = workspace_root / "index3.html"
    
    if not index3_html.exists():
        print(f"ERROR: {index3_html} not found!")
        return 1
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        print(f"\n=== Uploading index3.html ===")
        print(f"File size: {index3_html.stat().st_size / 1024:.1f} KB")
        with open(index3_html, "rb") as f:
            ftp.storbinary(f"STOR index3.html", f)
        print("Uploaded index3.html successfully!")
        
        # Verify paths in uploaded file
        with open(index3_html, "r", encoding="utf-8") as f:
            content = f.read(5000)
            if "/_next/static" in content and "/next/_next/static" not in content:
                print("HTML has correct paths!")
            else:
                print("WARNING: HTML might have wrong paths")
        
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
