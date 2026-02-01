#!/usr/bin/env python3
"""Upload all fixes: .htaccess, sw.js, and index.html"""
import os
import ssl
from ftplib import FTP_TLS
from pathlib import Path

def ensure_remote_dir(ftp, remote_dir):
    if remote_dir in ("", "/"):
        return
    parts = [p for p in remote_dir.split("/") if p]
    cur = ""
    for p in parts:
        cur = cur + "/" + p if cur else p
        try:
            ftp.mkd(cur)
        except:
            pass

def upload_file(ftp, local_path, remote_path):
    ensure_remote_dir(ftp, os.path.dirname(remote_path))
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f)

def upload_file_content(ftp, content, remote_path):
    ensure_remote_dir(ftp, os.path.dirname(remote_path))
    from io import BytesIO
    bio = BytesIO(content.encode('utf-8'))
    ftp.storbinary(f"STOR {remote_path}", bio)

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        # Upload .htaccess
        print("\n=== Uploading .htaccess ===")
        upload_file(ftp, workspace_root / ".htaccess", ".htaccess")
        print("Uploaded .htaccess")
        
        # Upload sw.js
        print("\n=== Uploading sw.js ===")
        if (workspace_root / "sw.js").exists():
            upload_file(ftp, workspace_root / "sw.js", "sw.js")
            print("Uploaded sw.js")
        
        # Upload index.html
        print("\n=== Uploading index.html ===")
        upload_file(ftp, workspace_root / "index.html", "index.html")
        print("Uploaded index.html")
        
        print("\n=== All fixes uploaded! ===")
        
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
