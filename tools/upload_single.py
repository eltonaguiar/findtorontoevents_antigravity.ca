import ftplib
import os
from dotenv import load_dotenv

load_dotenv()

FTP_SERVER = os.getenv('FTP_SERVER')
FTP_USER = os.getenv('FTP_USER')
FTP_PASS = os.getenv('FTP_PASS')
FTP_REMOTE_PATH = os.getenv('FTP_REMOTE_PATH', '/findtorontoevents.ca/')

def upload_file(local_file, remote_file):
    with ftplib.FTP(FTP_SERVER) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(FTP_REMOTE_PATH)
        try:
            ftp.delete(remote_file)
            print(f'Deleted existing {remote_file}')
        except:
            print(f'No existing {remote_file} to delete')
        with open(local_file, 'rb') as f:
            ftp.storbinary(f'STOR {remote_file}', f)
        print(f'Uploaded {local_file} to {remote_file}')

def upload_list(files):
    with ftplib.FTP(FTP_SERVER) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(FTP_REMOTE_PATH)
        for local_file in files:
            remote_file = local_file.replace('\\', '/')
            try:
                ftp.delete(remote_file)
                print(f'Deleted existing {remote_file}')
            except:
                pass
            with open(local_file, 'rb') as f:
                ftp.storbinary(f'STOR {remote_file}', f)
            print(f'Uploaded {local_file} -> {remote_file}')

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        upload_list(sys.argv[1:])
    else:
        upload_list([
            'findstocks/portfolio2/api/audit_view.php',
            'findstocks/portfolio2/picks.html',
            'live-monitor/api/audit_setup.php',
        ])
