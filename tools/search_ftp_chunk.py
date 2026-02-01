import os
import ftplib

def find_file_recursive(ftp, current_dir, filename):
    try:
        ftp.cwd(current_dir)
        files = ftp.nlst()
        for f in files:
            if f in ['.', '..']: continue
            if f == filename:
                print(f"FOUND: {current_dir}/{f}, Size: {ftp.size(f)}")
            try:
                # Try to cwd into it to see if it's a directory
                ftp.cwd(f)
                find_file_recursive(ftp, ftp.pwd(), filename)
                ftp.cwd('..')
            except:
                pass
    except:
        pass

def search():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user=user, passwd=password)
        find_file_recursive(ftp, '/', 'a2ac3a6616d60872.js')

if __name__ == "__main__":
    search()
