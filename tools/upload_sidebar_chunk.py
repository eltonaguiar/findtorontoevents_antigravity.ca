import os
import ftplib

def upload():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    local = r"e:\findtorontoevents_antigravity.ca\next\_next\static\chunks\a2ac3a6616d60872.js"
    
    # Target 1: /_next/...
    targets = [
        "_next/static/chunks",
        "next/_next/static/chunks"
    ]
    
    remote_file = "a2ac3a6616d60872.js"
    
    print(f"Connecting to {host}...")
    with ftplib.FTP(host) as ftp:
        ftp.login(user=user, passwd=password)
        print("Logged in.")
        
        for remote_dir in targets:
            print(f"Uploading to {remote_dir}...")
            try:
                # Try to navigate or create path
                current = ""
                # Simple navigation logic (might fail if nesting implies multiple CWDs)
                # Better: always start from root
                ftp.cwd("/")
                for part in remote_dir.split("/"):
                    try:
                        ftp.cwd(part)
                    except:
                        try:
                            ftp.mkd(part)
                            ftp.cwd(part)
                        except Exception as e:
                            print(f"Failed to create/enter {part} in {remote_dir}: {e}")
                            break
                            
                # Upload
                with open(local, 'rb') as f:
                    ftp.storbinary(f'STOR {remote_file}', f)
                print(f"Uploaded {remote_file} to {remote_dir}")
                
            except Exception as e:
                 print(f"Failed to upload to {remote_dir}: {e}")

if __name__ == "__main__":
    upload()
