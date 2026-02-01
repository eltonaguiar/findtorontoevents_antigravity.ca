import os
import ftplib

def list_ftp_subdir(subdir):
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            ftp.cwd(subdir)
            print(f"Listing {subdir}:")
            ftp.retrlines('LIST')
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_ftp_subdir('findtorontoevents.ca')
