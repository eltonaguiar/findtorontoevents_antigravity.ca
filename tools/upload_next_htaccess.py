#!/usr/bin/env python3
"""Upload .htaccess to _next directory"""
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

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    htaccess_content = """# Allow all files in _next directory
<IfModule mod_security.c>
  SecRuleEngine Off
</IfModule>

# Allow access to all files
<Files "*">
  Order Allow,Deny
  Allow from all
</Files>
"""
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        # Upload .htaccess to _next directory
        ensure_remote_dir(ftp, "_next")
        print("\n=== Uploading .htaccess to _next/ ===")
        from io import BytesIO
        bio = BytesIO(htaccess_content.encode('utf-8'))
        ftp.storbinary("STOR _next/.htaccess", bio)
        print("Uploaded _next/.htaccess successfully!")
        
        # Also upload to next/_next for compatibility
        ensure_remote_dir(ftp, "next/_next")
        print("\n=== Uploading .htaccess to next/_next/ ===")
        bio = BytesIO(htaccess_content.encode('utf-8'))
        ftp.storbinary("STOR next/_next/.htaccess", bio)
        print("Uploaded next/_next/.htaccess successfully!")
        
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
