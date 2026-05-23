#!/usr/bin/env python3
import ftplib
import os
import sys
from pathlib import Path

def deploy_supplements(local_dir='findtorontoevents.ca/supplements/energy', remote_base='/findtorontoevents.ca/supplements/energy'):
    ftp_server = os.environ.get('FTP_SERVER', 'ftps2.50webs.com')
    ftp_user = os.environ.get('FTP_USER', 'ejaguiar1')
    ftp_pass = os.environ.get('FTP_PASS', 'DHidj7zK2BWI0&EMK42nW')

    if not all([ftp_server, ftp_user, ftp_pass]):
        print("Error: Missing FTP env vars (FTP_SERVER, FTP_USER, FTP_PASS)")
        sys.exit(1)

    local_path = Path(local_dir)
    if not local_path.exists():
        print(f"Error: Local dir {local_dir} not found")
        sys.exit(1)

    ftp = ftplib.FTP_TLS()
    try:
        ftp.connect(ftp_server, 21)
        ftp.login(ftp_user, ftp_pass)
        ftp.prot_p()  # Secure data

        ftp.cwd('/findtorontoevents.ca')
        ftp.cwd('supplements')
        ftp.cwd('energy')  # Assume exists or create if needed

        uploaded = 0
        for file_path in local_path.glob('*.html'):
            with open(file_path, 'rb') as f:
                ftp.storbinary(f'STOR {file_path.name}', f)
            print(f"Uploaded: {file_path.name}")
            uploaded += 1

        print(f"Deploy complete: {uploaded} files")
        ftp.quit()
    except Exception as e:
        print(f"FTP Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    deploy_supplements()
