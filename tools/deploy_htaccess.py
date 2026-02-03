"""
Deploy .htaccess to findtorontoevents.ca/ only (never FTP account root).
"""
import os
import ftplib
from io import BytesIO

def deploy_htaccess():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    if not all([host, user, password]):
        print("ERROR: Missing FTP credentials")
        return False
    
    local_file = '.htaccess'
    
    if not os.path.exists(local_file):
        print(f"ERROR: File not found: {local_file}")
        return False
    
    print("Deploying .htaccess to findtorontoevents.ca/ ...")
    
    remote_paths = ['findtorontoevents.ca']
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            with open(local_file, 'rb') as f:
                data = f.read()
            for remote in remote_paths:
                ftp.cwd('/')
                try:
                    for part in remote.split('/'):
                        if part:
                            ftp.cwd(part)
                except ftplib.error_perm:
                    print(f"Skip {remote} (no such dir)")
                    continue
                ftp.storbinary('STOR .htaccess', BytesIO(data))
                print(f"SUCCESS: .htaccess -> {remote}/.htaccess")
            return True
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    deploy_htaccess()
