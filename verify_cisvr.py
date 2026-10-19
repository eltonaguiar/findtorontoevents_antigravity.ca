import os, ftplib
from pathlib import Path

host = os.environ['FTP_SERVER']
user = os.environ['FTP_USER']
passwd = os.environ['FTP_PASS']
remote_base = os.environ.get('FTP_REMOTE_PATH', 'findtorontoevents.ca')
remote_path = f'{remote_base}/servicenow/CIS-VR/index.html'

print(f'Verifying {remote_path} on {host}')
ftp = ftplib.FTP(host)
ftp.login(user, passwd)
ftp.cwd('/')
# Try to get file size
try:
    size = ftp.size(remote_path)
    print(f'Remote file size: {size} bytes')
except Exception as e:
    print(f'Could not get size: {e}')
    size = None
# Download first 200 bytes to compare with local
local_file = Path('/home/eaguiar2015/findtorontoevents_antigravity.ca/.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html')
local_size = local_file.stat().st_size
print(f'Local file size: {local_size} bytes')
if size is not None and size == local_size:
    print('Size matches.')
else:
    print('Size mismatch or unable to verify.')
ftp.quit()