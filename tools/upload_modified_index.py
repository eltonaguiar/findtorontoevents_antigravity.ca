import os
import ftplib

def upload_files(files_to_upload):
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    print(f"Connecting to {host}...")
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            print(f"Logged in as {user}")
            
            for local_path, remote_path in files_to_upload:
                if not os.path.exists(local_path):
                    print(f"Skipping {local_path} (does not exist)")
                    continue
                
                print(f"Uploading {local_path} to {remote_path}...")
                
                # Split remote_path into directory and filename
                remote_dir = os.path.dirname(remote_path)
                remote_file = os.path.basename(remote_path)
                
                # Navigate to the remote directory
                if remote_dir:
                    try:
                        ftp.cwd('/') # Start from root
                        for part in remote_dir.split('/'):
                            if part:
                                ftp.cwd(part)
                    except Exception as e:
                        print(f"Error navigating to {remote_dir}: {e}")
                        continue
                else:
                    ftp.cwd('/')
                
                with open(local_path, 'rb') as f:
                    ftp.storbinary(f'STOR {remote_file}', f)
                print(f"Successfully uploaded {remote_file} to {remote_dir or '/'}")
                
            print("All uploads completed!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    files = [
        (r'e:\findtorontoevents.ca\index.html', 'index.html'),
        (r'e:\findtorontoevents.ca\2xko\index.html', '2xko/index.html'),
        (r'e:\findtorontoevents.ca\WINDOWSFIXER\index.html', 'WINDOWSFIXER/index.html'),
    ]
    upload_files(files)
