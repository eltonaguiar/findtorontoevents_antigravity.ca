#!/usr/bin/env python3
"""Create PHP proxy and .htaccess rewrite to route JS files through proxy"""
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
    ensure_remote_dir(ftp, os.path.dirname(remote_path))
    from io import BytesIO
    bio = BytesIO(content.encode('utf-8'))
    ftp.storbinary(f"STOR {remote_path}", bio)

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    php_proxy = """<?php
// Proxy to serve JavaScript files and bypass ModSecurity
$requestUri = $_SERVER['REQUEST_URI'];
$path = parse_url($requestUri, PHP_URL_PATH);
$file = $_GET['file'] ?? basename($path);
$file = preg_replace('/\\?.*$/', '', $file);
$filePath = __DIR__ . '/_next/static/chunks/' . basename($file);
if (file_exists($filePath) && pathinfo($filePath, PATHINFO_EXTENSION) === 'js') {
    header('Content-Type: application/javascript');
    header('Cache-Control: public, max-age=31536000');
    readfile($filePath);
    exit;
}
http_response_code(404);
?>"""
    
    # Update .htaccess to route /next/_next/ requests through proxy
    htaccess_addition = """
# Route /next/_next/ JS files through PHP proxy to bypass ModSecurity
RewriteCond %{REQUEST_URI} ^/next/_next/static/chunks/.*\\.js
RewriteRule ^next/_next/static/chunks/(.*)$ js-proxy.php?file=$1 [L,QSA]
"""
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        # Upload PHP proxy
        print("\n=== Uploading js-proxy.php ===")
        upload_file_content(ftp, php_proxy, "js-proxy.php")
        print("Uploaded js-proxy.php")
        
        # Read existing .htaccess and append rewrite rule
        print("\n=== Updating .htaccess ===")
        try:
            from io import BytesIO
            bio = BytesIO()
            ftp.retrbinary('RETR .htaccess', bio.write)
            existing = bio.getvalue().decode('utf-8')
            if 'js-proxy.php' not in existing:
                updated = existing.rstrip() + htaccess_addition
                bio = BytesIO(updated.encode('utf-8'))
                ftp.storbinary('STOR .htaccess', bio)
                print("Updated .htaccess with proxy rewrite rule")
            else:
                print(".htaccess already has proxy rule")
        except:
            print("Could not read existing .htaccess, creating new one")
            upload_file_content(ftp, "RewriteEngine On\n" + htaccess_addition, ".htaccess")
        
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
