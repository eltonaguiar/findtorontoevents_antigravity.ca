import os, ftplib
from pathlib import Path

host = os.environ['FTP_SERVER']
user = os.environ['FTP_USER']
passwd = os.environ['FTP_PASS']
remote_base = os.environ.get('FTP_REMOTE_PATH', 'findtorontoevents.ca')
local_file = Path('/home/eaguiar2015/findtorontoevents_antigravity.ca/findtorontoevents.ca/servicenow/javascript/index.html')
remote_path = f'{remote_base}/servicenow/javascript/index.html'

print(f'Uploading {local_file} to {remote_path} via {host} as {user}')
ftp = ftplib.FTP(host)
ftp.login(user, passwd)
# Ensure directory
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
ensure_dir(ftp, '/'.join(remote_path.split('/')[:-1]))
with open(local_file, 'rb') as f:
    ftp.storbinary(f'STOR {remote_path.split("/")[-1]}', f)
ftp.quit()
print('Upload complete')