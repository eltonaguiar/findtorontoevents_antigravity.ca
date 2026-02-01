import ftplib
import os

def upload():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    local = "js-proxy.php"
    remote = "js-proxy.php"
    
    print(f"Connecting to {host}...")
    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)
        with open(local, 'rb') as f:
            ftp.storbinary(f'STOR {remote}', f)
        print("Uploaded js-proxy.php")
            
if __name__ == "__main__":
    upload()
