import ftplib
import os

def verify():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    remote_path = "index.html"
    local_path = "temp_index.html"
    
    print("Checking remote index.html...")
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user, password)
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f"RETR {remote_path}", f.write)
                
        with open(local_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if '/favcreators/#/guest' in content:
            print("SUCCESS: index.html is Patched.")
        else:
            print("FAIL: index.html is NOT Patched.")
            if '/favcreators/' in content:
                 print("Found OLD link in index.html")
                
    except Exception as e:
        print(f"Error: {e}")
            
if __name__ == "__main__":
    verify()
