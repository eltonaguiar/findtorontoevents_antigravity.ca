import os, ftplib
from pathlib import Path

host = os.environ['FTP_SERVER']
user = os.environ['FTP_USER']
passwd = os.environ['FTP_PASS']
remote_base = os.environ.get('FTP_REMOTE_PATH', 'findtorontoevents.ca')

files = [
    ('findtorontoevents.ca/servicenow/javascript/index.html', f'{remote_base}/servicenow/javascript/index.html'),
    ('findtorontoevents.ca/servicenow/javascript/quiz.html', f'{remote_base}/servicenow/javascript/quiz.html'),
    ('diagrams/acl_flow.excalidraw', f'{remote_base}/diagrams/acl_flow.excalidraw'),
]

def ensure_dir(ftp, dirpath):
    if not dirpath:
        return
    parts = dirpath.strip('/').split('/')
    ftp.cwd('/')
    for p in parts:
        if not p:
            continue
        try:
            ftp.cwd(p)
        except ftplib.error_perm:
            ftp.mkd(p)
            ftp.cwd(p)
    ftp.cwd('/')

for local, remote in files:
    print(f'Uploading {local} to {remote}')
    ftp = ftplib.FTP(host)
    ftp.login(user, passwd)
    # Ensure remote directory exists
    remote_dir = str(Path(remote).parent)
    ensure_dir(ftp, remote_dir)
    with open(local, 'rb') as f:
        ftp.storbinary(f'STOR {Path(remote).name}', f)
    ftp.quit()
    print('  -> done')