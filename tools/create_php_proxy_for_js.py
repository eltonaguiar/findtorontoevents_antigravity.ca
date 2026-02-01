#!/usr/bin/env python3
"""Create a PHP proxy script that serves JS files and strips query params"""
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

def upload_file_content(ftp, content, remote_path):
    remote_dir = os.path.dirname(remote_path)
    ensure_remote_dir(ftp, remote_dir)
    from io import BytesIO
    bio = BytesIO(content.encode('utf-8'))
    ftp.storbinary(f"STOR {remote_path}", bio)

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    # Create a single PHP proxy that handles all JS files
    php_proxy = """<?php
// Proxy to serve JS files and bypass ModSecurity query param blocking
$file = basename($_SERVER['REQUEST_URI']);
$file = preg_replace('/\\?.*$/', '', $file); // Remove query params
$filePath = __DIR__ . '/' . $file;

if (file_exists($filePath) && pathinfo($filePath, PATHINFO_EXTENSION) === 'js') {
    header('Content-Type: application/javascript');
    header('Cache-Control: public, max-age=31536000');
    readfile($filePath);
    exit;
}
http_response_code(404);
?>"""
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        # Upload proxy.php to chunks directory
        print("\n=== Creating PHP proxy ===")
        upload_file_content(ftp, php_proxy, "next/_next/static/chunks/proxy.php")
        print("Created proxy.php")
        
        # Also create .htaccess to route .js requests to proxy.php
        htaccess_content = """RewriteEngine On
RewriteCond %{QUERY_STRING} .+
RewriteRule ^([^/]+\\.js)$ proxy.php?file=$1 [L]
"""
        upload_file_content(ftp, htaccess_content, "next/_next/static/chunks/.htaccess")
        print("Created .htaccess for routing")
        
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
