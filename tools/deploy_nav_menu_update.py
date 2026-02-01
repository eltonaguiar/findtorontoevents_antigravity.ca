#!/usr/bin/env python3
"""
Deploy the updated nav menu to the remote server via FTP
1. Download current remote index.html as backup
2. Upload the modified local index.html
"""

import os
import ftplib
from datetime import datetime

def get_ftp_credentials():
    """Get FTP credentials from environment variables"""
    return {
        'host': os.getenv('FTP_HOST'),
        'user': os.getenv('FTP_USER'),
        'password': os.getenv('FTP_PASSWORD'),
        'port': int(os.getenv('FTP_PORT', '21'))
    }

def backup_remote_file(ftp, remote_file, local_backup_dir='backups/remote'):
    """Download remote file as backup before overwriting"""
    os.makedirs(local_backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_filename = f"remote-index-{timestamp}.html"
    backup_path = os.path.join(local_backup_dir, backup_filename)
    
    try:
        # Download remote file
        with open(backup_path, 'wb') as f:
            ftp.retrbinary(f'RETR {remote_file}', f.write)
        print(f"✓ Remote backup created: {backup_path}")
        return True
    except ftplib.error_perm as e:
        print(f"Warning: Could not backup remote file: {e}")
        return False
    except Exception as e:
        print(f"Error during backup: {e}")
        return False

def upload_file(ftp, local_file, remote_file):
    """Upload local file to remote server"""
    try:
        with open(local_file, 'rb') as f:
            ftp.storbinary(f'STOR {remote_file}', f)
        print(f"✓ Uploaded {local_file} -> {remote_file}")
        return True
    except Exception as e:
        print(f"Error uploading file: {e}")
        return False

def deploy_menu_update():
    """Main deployment function"""
    print("=" * 60)
    print("Quick Nav Menu Deployment")
    print("=" * 60)
    
    # Get FTP credentials
    creds = get_ftp_credentials()
    
    if not all([creds['host'], creds['user'], creds['password']]):
        print("ERROR: FTP credentials not found in environment variables")
        print("Required: FTP_HOST, FTP_USER, FTP_PASSWORD")
        return False
    
    print(f"\nConnecting to {creds['host']}...")
    
    try:
        # Connect to FTP
        ftp = ftplib.FTP()
        ftp.connect(creds['host'], creds['port'])
        ftp.login(creds['user'], creds['password'])
        print(f"✓ Connected as {creds['user']}")
        
        # Get current directory
        current_dir = ftp.pwd()
        print(f"Current remote directory: {current_dir}")
        
        # Step 1: Backup remote index.html
        print("\n[Step 1] Backing up remote index.html...")
        backup_remote_file(ftp, 'index.html')
        
        # Step 2: Upload modified index.html
        print("\n[Step 2] Uploading updated index.html...")
        if upload_file(ftp, 'index.html', 'index.html'):
            print("\n" + "=" * 60)
            print("DEPLOYMENT SUCCESSFUL")
            print("=" * 60)
            print("\nChanges deployed:")
            print("  ✓ FAVCREATORS link added to NETWORK section")
            print("  ✓ 'My Collection' moved to PERSONAL section (bottom)")
            print("  ✓ 'Data Management' section moved near bottom")
            print("  ✓ Menu options prioritized over management functions")
            success = True
        else:
            print("\nERROR: Upload failed")
            success = False
        
        ftp.quit()
        return success
        
    except ftplib.error_perm as e:
        print(f"FTP Permission Error: {e}")
        return False
    except ftplib.error_temp as e:
        print(f"FTP Temporary Error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    import sys
    success = deploy_menu_update()
    sys.exit(0 if success else 1)
