#!/usr/bin/env python3
"""
Upload a specific file to fix the JavaScript error
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
    js_file = workspace_root / "_next" / "static" / "chunks" / "a2ac3a6616d60872.js"
    
    if not js_file.exists():
        print(f"ERROR: {js_file} not found!")
        return 1
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        # Upload to both paths to be safe
        remote_paths = [
            "_next/static/chunks/a2ac3a6616d60872.js",
            "next/_next/static/chunks/a2ac3a6616d60872.js"  # In case rewrite is the issue
        ]
        
        for remote_path in remote_paths:
            print(f"\n=== Uploading to {remote_path} ===")
            print(f"File size: {js_file.stat().st_size / 1024:.1f} KB")
            
            # Ensure directory exists
            dir_parts = remote_path.split("/")[:-1]
            current_dir = ""
            for part in dir_parts:
                if part:
                    current_dir = f"{current_dir}/{part}" if current_dir else part
                    try:
                        ftp.mkd(current_dir)
                    except:
                        pass  # Directory might already exist
            
            with open(js_file, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
            print(f"Uploaded successfully!")
        
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
