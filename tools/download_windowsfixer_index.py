import os
import ftplib

def download_file(subdir, filename, local_filename):
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    print(f"Connecting to {host}...")
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            print(f"Logged in as {user}")
            
            ftp.cwd(subdir)
            print(f"Downloading {filename} from {subdir}...")
            with open(local_filename, 'wb') as f:
                ftp.retrbinary(f'RETR {filename}', f.write)
            print(f"Downloaded to {local_filename}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    download_file('findtorontoevents.ca/WINDOWSFIXER', 'index.html', r'e:\findtorontoevents.ca\server_windowsfixer_index.html')
