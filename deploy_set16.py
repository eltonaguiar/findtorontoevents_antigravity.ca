import ftplib
import sys

FTP_HOST = 'ftps2.50webs.com'
FTP_USER = 'ejaguiar1'
FTP_PASS = '$a^FzN7BqKapSQMsZxD&^FeTJ'
REMOTE_DIR = '/findtorontoevents.ca/vr'

def upload(local_path, remote_name):
    try:
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(REMOTE_DIR)
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_name}', f)
        ftp.quit()
        print(f'[OK] {remote_name}')
        return True
    except Exception as e:
        print(f'[FAIL] {remote_name}: {e}')
        return False

files = [
    ('vr/quick-wins-substantial-set16.js', 'quick-wins-substantial-set16.js'),
    ('vr/index.html', 'index.html'),
    ('vr/movies.html', 'movies.html'),
    ('vr/creators.html', 'creators.html'),
    ('vr/weather-zone.html', 'weather-zone.html'),
    ('vr/stocks-zone.html', 'stocks-zone.html'),
    ('vr/movies-tiktok.html', 'movies-tiktok.html'),
]

success = sum(upload(l, r) for l, r in files)
print(f'DEPLOYED: {success}/{len(files)} files')
sys.exit(0 if success == len(files) else 1)
