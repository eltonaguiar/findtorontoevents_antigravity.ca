#!/usr/bin/env python3
"""FTP Utilities with proper password handling for special characters"""
import ftplib
import os

# FTP Credentials - using raw string to handle ^ characters
FTP_HOST = 'ftps2.50webs.com'
FTP_USER = 'ejaguiar1'
FTP_PASS = r'$a^FzN7BqKapSQMsZxD&^FeTJ'

class FTPClient:
    """Simple FTP client that handles special characters in password"""
    
    def __init__(self):
        self.ftp = None
        
    def connect(self):
        """Connect and login to FTP server"""
        self.ftp = ftplib.FTP(FTP_HOST, timeout=30)
        self.ftp.login(FTP_USER, FTP_PASS)
        return self
        
    def disconnect(self):
        """Close FTP connection"""
        if self.ftp:
            self.ftp.quit()
            self.ftp = None
            
    def __enter__(self):
        return self.connect()
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
        
    def upload(self, local_path, remote_path):
        """Upload a file"""
        directory = os.path.dirname(remote_path)
        filename = os.path.basename(remote_path)
        
        if directory:
            self.ftp.cwd(directory)
            
        with open(local_path, 'rb') as f:
            self.ftp.storbinary(f'STOR {filename}', f)
            
        return True
        
    def download(self, remote_path, local_path):
        """Download a file"""
        directory = os.path.dirname(remote_path)
        filename = os.path.basename(remote_path)
        
        if directory:
            self.ftp.cwd(directory)
            
        with open(local_path, 'wb') as f:
            self.ftp.retrbinary(f'RETR {filename}', f.write)
            
        return True
        
    def delete(self, remote_path):
        """Delete a file"""
        directory = os.path.dirname(remote_path)
        filename = os.path.basename(remote_path)
        
        if directory:
            self.ftp.cwd(directory)
            
        self.ftp.delete(filename)
        return True
        
    def list_files(self, remote_dir='/'):
        """List files in directory"""
        if remote_dir != '/':
            self.ftp.cwd(remote_dir)
        return self.ftp.nlst()
        
    def mkdir(self, remote_dir):
        """Create directory"""
        try:
            self.ftp.mkd(remote_dir)
        except:
            pass  # Directory may already exist
        return True

# Convenience functions for simple operations
def ftp_upload(local_path, remote_path):
    """Quick upload a file"""
    with FTPClient() as ftp:
        return ftp.upload(local_path, remote_path)

def ftp_download(remote_path, local_path):
    """Quick download a file"""
    with FTPClient() as ftp:
        return ftp.download(remote_path, local_path)

def ftp_delete(remote_path):
    """Quick delete a file"""
    with FTPClient() as ftp:
        return ftp.delete(remote_path)

def ftp_list(remote_dir='/'):
    """Quick list files"""
    with FTPClient() as ftp:
        return ftp.list_files(remote_dir)
