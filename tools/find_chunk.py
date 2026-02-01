import os
import ftplib

def find_file(subdir, pattern):
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            ftp.cwd(subdir)
            files = ftp.nlst()
            matches = [f for f in files if pattern in f]
            for m in matches:
                print(f"File: {m}, Size: {ftp.size(m)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_file('next/_next/static/chunks', 'a2ac3a6616d60872')
