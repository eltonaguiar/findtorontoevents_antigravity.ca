"""
Deploy the fixed js-proxy.php file
"""
import os
import ftplib
from pathlib import Path

def deploy_proxy():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    if not all([host, user, password]):
        print("ERROR: Missing FTP credentials")
        return False
    
    local_file = Path('next/_next/static/chunks/proxy.php')
    remote_path = 'next/_next/static/chunks/proxy.php'
    
    if not local_file.exists():
        print(f"ERROR: File not found: {local_file}")
        return False
    
    print(f"Deploying fixed js-proxy.php...")
    
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            
            # Navigate to directory
            ftp.cwd('/')
            for part in remote_path.split('/')[:-1]:
                if part:
                    try:
                        ftp.cwd(part)
                    except ftplib.error_perm:
                        ftp.mkd(part)
                        ftp.cwd(part)
            
            # Upload file
            with open(local_file, 'rb') as f:
                ftp.storbinary(f'STOR proxy.php', f)
            
            print("SUCCESS: js-proxy.php deployed")
            
            # Also deploy to root js-proxy.php if it exists
            root_proxy = Path('js-proxy.php')
            if root_proxy.exists():
                ftp.cwd('/')
                with open(root_proxy, 'rb') as f:
                    ftp.storbinary('STOR js-proxy.php', f)
                print("SUCCESS: Root js-proxy.php deployed")
            
            return True
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    deploy_proxy()
