import os
import ftplib

def check_file_exists(subdir, filename):
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    print(f"Connecting to {host}...")
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            print(f"Logged in as {user}")
            
            ftp.cwd(subdir)
            files = ftp.nlst()
            if filename in files:
                print(f"File {filename} exists in {subdir}")
                # Get size
                size = ftp.size(filename)
                print(f"Size: {size}")
            else:
                print(f"File {filename} does NOT exist in {subdir}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_file_exists('findtorontoevents.ca', 'index.html')
