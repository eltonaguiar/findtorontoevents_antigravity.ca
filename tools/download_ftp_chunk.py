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
    download_file('next/_next/static/chunks', 'a2ac3a6616d60872.js', r'e:\findtorontoevents.ca\problematic_chunk.js')
