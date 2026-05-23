"""Deploy dashboard_live.html + dashboard_data.js + dashboard_logic.js + active_picks.json"""
import os, ftplib

ftp = ftplib.FTP('ftps2.50webs.com', timeout=60)
ftp.login('ejaguiar1', os.getenv('FTP_PASS', ''))

def ensure_dir(ftp, path):
    ftp.cwd('/')
    for part in path.split('/'):
        if not part: continue
        try: ftp.cwd(part)
        except:
            ftp.mkd(part)
            ftp.cwd(part)

def upload(ftp, local_path, remote_path):
    parts = remote_path.split('/')
    d = '/'.join(parts[:-1])
    if d: ensure_dir(ftp, d)
    ftp.cwd('/')
    if d: ftp.cwd(d)
    with open(local_path, 'rb') as f:
        ftp.storbinary(f'STOR {parts[-1]}', f)
    print(f'  \u2714 {remote_path}')

base = 'e:/findtorontoevents_antigravity.ca/KIMI_RISEOFTHECLAW'
remote_base = 'findtorontoevents.ca/KIMI_RISEOFTHECLAW'

files = [
    'dashboard_live.html',
    'dashboard_data.js',
    'dashboard_logic.js',
    'price_scraper.php',
]

for f in files:
    upload(ftp, f'{base}/{f}', f'{remote_base}/{f}')

# Also ensure data files are deployed
data_files = [
    'data/active_picks.json',
    'data/forward_signals_current.json',
    'data/live_signals_now.json',
]
for df in data_files:
    data_file = f'{base}/{df}'
    if os.path.exists(data_file):
        upload(ftp, data_file, f'{remote_base}/{df}')
    else:
        print(f'  ! {df} not found at {data_file}')

ftp.quit()
print('\nDone! All files deployed.')
