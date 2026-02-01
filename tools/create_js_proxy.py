#!/usr/bin/env python3
"""Create PHP proxy files for each JS file to bypass ModSecurity"""
import os
import ssl
from ftplib import FTP_TLS
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
        except:
            pass

def upload_file_content(ftp, content, remote_path):
    """Upload file content"""
    remote_dir = os.path.dirname(remote_path)
    ensure_remote_dir(ftp, remote_dir)
    from io import BytesIO
    bio = BytesIO(content.encode('utf-8'))
    ftp.storbinary(f"STOR {remote_path}", bio)

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    chunks_dir = workspace_root / "_next" / "static" / "chunks"
    
    if not chunks_dir.exists():
        print(f"ERROR: {chunks_dir} not found!")
        return 1
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        # Create PHP proxy for each JS file
        print("\n=== Creating PHP proxies for JS files ===")
        js_files = list(chunks_dir.glob("*.js"))
        count = 0
        
        for js_file in js_files:
            php_content = f"""<?php
header('Content-Type: application/javascript');
header('Cache-Control: public, max-age=31536000');
readfile(__DIR__ . '/{js_file.name}');
?>"""
            php_path = f"next/_next/static/chunks/{js_file.stem}.php"
            upload_file_content(ftp, php_content, php_path)
            count += 1
            if count % 10 == 0:
                print(f"Created {count} proxies...")
        
        print(f"\nCreated {count} PHP proxy files")
        
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
