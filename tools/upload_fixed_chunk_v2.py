import os
import ftplib

def upload_file(local_path, remote_subdir, remote_filename):
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    print(f"Connecting to {host}...")
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            print(f"Logged in as {user}")
            
            ftp.cwd(remote_subdir)
            print(f"Uploading {local_path} to {remote_subdir}/{remote_filename}...")
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_filename}', f)
            print(f"Upload to {remote_subdir} successful!")
            
    except Exception as e:
        print(f"Error in {remote_subdir}: {e}")

if __name__ == "__main__":
    local = r'e:\findtorontoevents.ca\fixed_chunk_v2.js'
    upload_file(local, 'findtorontoevents.ca/_next/static/chunks', 'a2ac3a6616d60872.js')
    upload_file(local, 'findtorontoevents.ca/next/_next/static/chunks', 'a2ac3a6616d60872.js')
