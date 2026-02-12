#!/usr/bin/env python3
"""FTP Upload with proper password handling"""
import ftplib
import sys
import os

# Password with caret - use raw string to avoid escape issues
FTP_HOST = 'ftps2.50webs.com'
FTP_USER = 'ejaguiar1'
FTP_PASS = r'$a^FzN7BqKapSQMsZxD&^FeTJ'

def upload_file(local_path, remote_path):
    """Upload a file via FTP"""
    try:
        ftp = ftplib.FTP(FTP_HOST, timeout=30)
        ftp.login(FTP_USER, FTP_PASS)
        
        # Navigate to directory
        directory = os.path.dirname(remote_path)
        filename = os.path.basename(remote_path)
        
        if directory:
            ftp.cwd(directory)
        
        # Upload file
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {filename}', f)
        
        ftp.quit()
        print(f'[OK] Uploaded: {local_path} -> {remote_path}')
        return True
        
    except Exception as e:
        print(f'[FAIL] {e}')
        return False

def delete_remote_file(remote_path):
    """Delete a file via FTP"""
    try:
        ftp = ftplib.FTP(FTP_HOST, timeout=30)
        ftp.login(FTP_USER, FTP_PASS)
        
        directory = os.path.dirname(remote_path)
        filename = os.path.basename(remote_path)
        
        if directory:
            ftp.cwd(directory)
        
        ftp.delete(filename)
        ftp.quit()
        print(f'[OK] Deleted: {remote_path}')
        return True
        
    except Exception as e:
        print(f'[FAIL] {e}')
        return False

def list_remote_files(remote_dir='/'):
    """List files in remote directory"""
    try:
        ftp = ftplib.FTP(FTP_HOST, timeout=30)
        ftp.login(FTP_USER, FTP_PASS)
        
        if remote_dir != '/':
            ftp.cwd(remote_dir)
        
        files = ftp.nlst()
        ftp.quit()
        return files
        
    except Exception as e:
        print(f'[FAIL] {e}')
        return []

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python ftp_upload.py <local_file> [remote_path]")
        sys.exit(1)
    
    local_file = sys.argv[1]
    remote_file = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(local_file)
    
    upload_file(local_file, remote_file)
