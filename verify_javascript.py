import os, ftplib
from pathlib import Path

host = os.environ['FTP_SERVER']
user = os.environ['FTP_USER']
passwd = os.environ['FTP_PASS']
remote_base = os.environ.get('FTP_REMOTE_PATH', 'findtorontoevents.ca')
local_file = Path('/home/eaguiar2015/findtorontoevents_antigravity.ca/findtorontoevents.ca/servicenow/javascript/index.html')
remote_path = f'{remote_base}/servicenow/javascript/index.html'

local_size = local_file.stat().st_size
print(f'Local size: {local_size} bytes')

ftp = ftplib.FTP(host)
ftp.login(user, passwd)
ftp.cwd('/'.join(remote_path.split('/')[:-1]) or '/')
resp = ftp.sendcmd(f'SIZE {remote_path.split("/")[-1]}')
# SIZE response: 213 <size>
size = int(resp.split()[1])
print(f'Remote size: {size} bytes')
ftp.quit()

if local_size == size:
    print('Size match ✅')
else:
    print('Size mismatch ❌')
    exit(1)