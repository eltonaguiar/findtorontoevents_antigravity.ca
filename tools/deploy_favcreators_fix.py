"""
Deploy the fixed favcreators JavaScript chunk file to the server via FTP
"""
import os
import ftplib
from pathlib import Path

def upload_to_path(ftp, local_path, remote_path):
    """Upload a file to a specific remote path, creating directories as needed"""
    print(f"Uploading to {remote_path}...")
    ftp.cwd('/')
    
    # Split path into directory and filename
    parts = remote_path.split('/')
    remote_file = parts[-1]
    remote_dir_parts = [p for p in parts[:-1] if p]
    
    # Navigate/create directory structure
    for part in remote_dir_parts:
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            try:
                ftp.mkd(part)
                ftp.cwd(part)
                print(f"  Created directory: {part}")
            except Exception as e:
                print(f"  Failed to create/enter {part}: {e}")
                return False
    
    # Upload the file
    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_file}', f)
        print(f"  SUCCESS: Uploaded {remote_file}")
        
        # Verify file size
        try:
            remote_size = ftp.size(remote_file)
            local_size = Path(local_path).stat().st_size
            if remote_size == local_size:
                print(f"  Verified: File sizes match ({local_size} bytes)")
            else:
                print(f"  WARNING: Size mismatch - local: {local_size}, remote: {remote_size}")
        except:
            pass  # Verification is optional
        
        return True
    except Exception as e:
        print(f"  ERROR: Failed to upload: {e}")
        return False

def deploy_fixed_chunk():
    # Get FTP credentials from environment variables
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    if not all([host, user, password]):
        print("ERROR: Missing FTP credentials in environment variables")
        print("Required: FTP_SERVER, FTP_USER, FTP_PASS")
        return False
    
    # Local file to upload
    local_file = Path('next/_next/static/chunks/a2ac3a6616d60872.js')
    
    if not local_file.exists():
        print(f"ERROR: Local file not found: {local_file}")
        return False
    
    # Multiple remote paths to deploy to (mirroring the deploy_targeted.py pattern)
    remote_paths = [
        'next/_next/static/chunks/a2ac3a6616d60872.js',  # Primary path
        '_next/static/chunks/a2ac3a6616d60872.js',      # Alternative path
        'findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js',  # Domain-specific
        'findtorontoevents.ca/_next/static/chunks/a2ac3a6616d60872.js',      # Domain-specific alt
    ]
    
    print(f"Connecting to FTP server: {host}")
    print(f"Local file: {local_file} ({local_file.stat().st_size} bytes)")
    print(f"Deploying to {len(remote_paths)} locations...\n")
    
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            print("Connected and logged in successfully\n")
            
            success_count = 0
            for remote_path in remote_paths:
                if upload_to_path(ftp, local_file, remote_path):
                    success_count += 1
                print()  # Blank line between uploads
            
            print(f"Deployment summary: {success_count}/{len(remote_paths)} locations successful")
            return success_count > 0
            
    except Exception as e:
        print(f"ERROR: Failed to deploy: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_fixed_chunk()
    if success:
        print("\n=== Deployment complete! ===")
        print("Please verify the fix by visiting https://findtorontoevents.ca")
        print("and checking that the FAVCREATORS link goes to /favcreators/#/guest")
    else:
        print("\n=== Deployment failed! ===")
        exit(1)
