"""
Deploy all JavaScript chunk files to fix the syntax errors
"""
import os
import ftplib
from pathlib import Path

def deploy_all_chunks():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    if not all([host, user, password]):
        print("ERROR: Missing FTP credentials")
        return False
    
    # All JS files that are erroring
    js_files = [
        '43a0077a15b1a098.js',
        '806bdb8e4a6a9b95.js',
        '628f1cf8c6948755.js',
        'a2ac3a6616d60872.js',
        'ff1a16fafef87110.js',
        'dde2c8e6322d1671.js',
        'turbopack-03e217c852f3e99c.js',
        'f1a9dd578dc871d3.js',
        '7c4eddd014120b50.js',
        'afe53b3593ec888c.js',
        '1bbf7aa8dcc742fe.js',
    ]
    
    local_dir = Path('next/_next/static/chunks')
    # Deploy to root, findtorontoevents.ca, and _next (in case server uses rewritten path)
    remote_bases = [
        'next/_next/static/chunks',
        'findtorontoevents.ca/next/_next/static/chunks',
        'findtorontoevents.ca/_next/static/chunks',
    ]
    
    print(f"Connecting to FTP: {host}")
    print(f"Deploying {len(js_files)} JavaScript files to {len(remote_bases)} locations...\n")
    
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            print("Connected successfully\n")
            
            success_count = 0
            for remote_base in remote_bases:
                for js_file in js_files:
                    local_file = local_dir / js_file
                    
                    if not local_file.exists():
                        print(f"SKIP: {js_file} - not found locally")
                        continue
                    
                    # Navigate to directory
                    ftp.cwd('/')
                    for part in remote_base.split('/'):
                        if part:
                            try:
                                ftp.cwd(part)
                            except ftplib.error_perm:
                                try:
                                    ftp.mkd(part)
                                    ftp.cwd(part)
                                except Exception:
                                    pass
                    
                    # Upload file
                    try:
                        with open(local_file, 'rb') as f:
                            ftp.storbinary(f'STOR {js_file}', f)
                        size = local_file.stat().st_size
                        print(f"OK: {remote_base}/{js_file} ({size} bytes)")
                        success_count += 1
                    except Exception as e:
                        print(f"ERROR: {js_file} at {remote_base} - {e}")
            
            print(f"\nDeployment complete: {success_count} uploads")
            return success_count > 0
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    deploy_all_chunks()
