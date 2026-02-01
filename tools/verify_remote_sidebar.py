import ftplib
import os

def verify():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    remote_path = "_next/static/chunks/a2ac3a6616d60872.js"
    local_path = "temp_check.js"
    
    print("Checking remote file...")
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user, password)
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f"RETR {remote_path}", f.write)
                
        with open(local_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if "/favcreators/#/guest" in content:
            print("SUCCESS: Remote file is Patched.")
        else:
            print("FAIL: Remote file is NOT Patched.")
            if "/favcreators/" in content:
                print("Found OLD link.")
                
    except Exception as e:
        print(f"Error: {e}")
            
if __name__ == "__main__":
    verify()
