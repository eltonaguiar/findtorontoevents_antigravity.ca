import os
import ftplib

def check_file(remote_path):
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user=user, passwd=password)
        try:
            size = ftp.size(remote_path)
            print(f"File: {remote_path}, Size: {size}")
        except Exception as e:
            print(f"Error checking {remote_path}: {e}")

if __name__ == "__main__":
    check_file('findtorontoevents.ca/_next/static/chunks/a2ac3a6616d60872.js')
    check_file('_next/static/chunks/a2ac3a6616d60872.js')
    check_file('next/_next/static/chunks/a2ac3a6616d60872.js')
