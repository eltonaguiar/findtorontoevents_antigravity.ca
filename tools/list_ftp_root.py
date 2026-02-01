import os
import ftplib

def list_ftp_root():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            print("Listing FTP Root:")
            ftp.retrlines('LIST')
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_ftp_root()
