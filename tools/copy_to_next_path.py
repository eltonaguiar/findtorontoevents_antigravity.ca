#!/usr/bin/env python3
"""Copy _next directory to next/_next on server to match server's path rewriting"""
import os
import ssl
from ftplib import FTP_TLS, error_perm
from pathlib import Path

def ensure_remote_dir(ftp, remote_dir):
    """Ensure remote directory exists"""
    if remote_dir in ("", "/"):
        return
    parts = [p for p in remote_dir.split("/") if p]
    cur = ""
    for p in parts:
        cur = cur + "/" + p if cur else p
        try:
            ftp.mkd(cur)
        except error_perm:
            pass

def upload_file(ftp, local_path, remote_path):
    """Upload a single file"""
    remote_dir = os.path.dirname(remote_path)
    ensure_remote_dir(ftp, remote_dir)
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f)

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    next_dir = workspace_root / "_next"
    
    if not next_dir.exists():
        print(f"ERROR: {next_dir} not found!")
        return 1
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        # Copy _next to next/_next
        print("\n=== Copying _next to next/_next ===")
        count = 0
        for dirpath, _, filenames in os.walk(next_dir):
            for filename in filenames:
                local_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(local_path, workspace_root)
                # Convert _next/... to next/_next/...
                remote_path = rel_path.replace("\\", "/").replace("_next/", "next/_next/")
                print(f"Uploading: {local_path} -> {remote_path}")
                upload_file(ftp, local_path, remote_path)
                count += 1
        
        print(f"\nUploaded {count} files to next/_next/")
        
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
