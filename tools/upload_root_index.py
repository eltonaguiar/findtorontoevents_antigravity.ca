import os
import ftplib

def upload():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    local_path = r"e:\findtorontoevents_antigravity.ca\index.html"
    remote_path = "index.html"
    
    print(f"Connecting to {host}...")
    with ftplib.FTP(host) as ftp:
        ftp.login(user=user, passwd=password)
        print(f"Logged in as {user}")
        
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        print("Uploaded index.html")

if __name__ == "__main__":
    upload()
