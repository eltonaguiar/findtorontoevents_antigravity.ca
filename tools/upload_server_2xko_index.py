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
            print("Upload successful!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    upload_file(r'e:\findtorontoevents.ca\server_2xko_index.html', 'findtorontoevents.ca/2xko', 'index.html')
