#!/usr/bin/env python3
"""
Force upload index.html by deleting old one first
"""
import os
import ssl
from ftplib import FTP_TLS, error_perm
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
        
        # Try to delete old file first
        try:
            ftp.delete("index.html")
            print("Deleted old index.html")
        except error_perm:
            print("Could not delete old file (might not exist or no permission)")
        
        # Upload new file
        print(f"\n=== Uploading index.html ===")
        print(f"File size: {index_html.stat().st_size / 1024:.1f} KB")
        with open(index_html, "rb") as f:
            ftp.storbinary(f"STOR index.html", f)
        print("Uploaded index.html successfully!")
        
        # Verify paths in uploaded file
        with open(index_html, "r", encoding="utf-8") as f:
            content = f.read(5000)
            if "/_next/static" in content and "/next/_next/static" not in content:
                print("✅ HTML has correct paths!")
            else:
                print("⚠️  WARNING: HTML might have wrong paths")
        
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
