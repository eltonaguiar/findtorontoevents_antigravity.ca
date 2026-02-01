#!/usr/bin/env python3
"""Download current server index.html and check for favcreators"""

import ssl
from ftplib import FTP_TLS
from pathlib import Path

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    download_path = workspace_root / "server-index-current.html"
    
    print("Downloading current server index.html...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        
        # Download index.html
        with open(download_path, 'wb') as f:
            ftp.retrbinary('RETR index.html', f.write)
        
        size = download_path.stat().st_size
        print(f"[OK] Downloaded: {size} bytes ({size/1024:.1f} KB)")
        
        # Check for favcreators
        with open(download_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("\n=== Checking content ===")
        if 'favcreators' in content.lower():
            print("[OK] 'favcreators' found in file")
            # Count occurrences
            count = content.lower().count('favcreators')
            print(f"  Occurrences: {count}")
        else:
            print("[ERROR] 'favcreators' NOT found in file")
        
        if 'Favorite Creators' in content:
            print("[OK] 'Favorite Creators' text found")
        else:
            print("[ERROR] 'Favorite Creators' text NOT found")
        
        if 'PERSONAL' in content:
            print("[OK] 'PERSONAL' section found")
        else:
            print("[ERROR] 'PERSONAL' section NOT found")
            
        # Check if it's the original or updated version
        if 'My Collection' in content:
            # Check where My Collection is
            if content.index('PERSONAL') < content.index('My Collection'):
                print("[OK] 'My Collection' is after 'PERSONAL' section (updated version)")
            else:
                print("[!] 'My Collection' is before 'PERSONAL' - may be old version")
        
        print(f"\nServer file saved to: {download_path}")
        
        ftp.quit()
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
