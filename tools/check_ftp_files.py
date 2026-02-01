#!/usr/bin/env python3
"""Check FTP server files and their modification times"""
import ssl
from ftplib import FTP_TLS
from datetime import datetime

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!\n")
        
        # Check key files
        files_to_check = [
            'index.html',
            '.htaccess',
            'js-proxy.php',
            'sw.js',
            'events.json',
            'data/events.json'
        ]
        
        print("=== Key Files ===")
        for filepath in files_to_check:
            try:
                # Get file details
                ftp.voidcmd('TYPE I')  # Binary mode for size
                size = ftp.size(filepath)
                # Get modification time
                mdtm = ftp.sendcmd(f'MDTM {filepath}')
                if mdtm.startswith('213'):
                    timestamp = mdtm.split()[1]
                    # Parse YYYYMMDDHHmmss format
                    dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
                    print(f"{filepath:30} Size: {size:>8} bytes  Modified: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    print(f"{filepath:30} Size: {size:>8} bytes  (no timestamp)")
            except Exception as e:
                print(f"{filepath:30} ERROR: {e}")
        
        # Check directories
        print("\n=== Directory Structure ===")
        dirs_to_check = ['_next', 'next', 'next/_next']
        for dirpath in dirs_to_check:
            try:
                ftp.cwd(dirpath)
                files = []
                ftp.retrlines('LIST', files.append)
                if files:
                    print(f"\n{dirpath}/ ({len(files)} items)")
                    # Show first few files
                    for f in files[:5]:
                        print(f"  {f}")
                    if len(files) > 5:
                        print(f"  ... and {len(files) - 5} more")
                ftp.cwd('/')
            except Exception as e:
                print(f"{dirpath}: {e}")
        
        # Check .htaccess in subdirectories
        print("\n=== .htaccess Files ===")
        htaccess_paths = ['_next/.htaccess', 'next/_next/.htaccess', 'next/_next/static/chunks/.htaccess']
        for path in htaccess_paths:
            try:
                size = ftp.size(path)
                mdtm = ftp.sendcmd(f'MDTM {path}')
                if mdtm.startswith('213'):
                    timestamp = mdtm.split()[1]
                    dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
                    print(f"{path:40} Size: {size:>6} bytes  Modified: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    print(f"{path:40} Size: {size:>6} bytes")
            except Exception as e:
                print(f"{path:40} Not found or error: {e}")
        
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
