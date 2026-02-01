import os
import ftplib

def check_dir(subdir):
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            try:
                ftp.cwd(subdir)
                print(f"Directory {subdir} exists.")
                print(ftp.nlst()[:5])
            except:
                print(f"Directory {subdir} does NOT exist.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_dir('findtorontoevents.ca/next')
    check_dir('findtorontoevents.ca/_next')
