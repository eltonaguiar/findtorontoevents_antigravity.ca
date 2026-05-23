"""Deploy goldmine maintenance + research pages to live-monitor/"""
from ftplib import FTP
import os

HOST = 'ftps2.50webs.com'
USER = 'ejaguiar1'
PASS = os.environ.get('FTPGODADDYPASS', '')

ftp = FTP()
ftp.connect(HOST, 21, timeout=30)
ftp.login(USER, PASS)
print("Connected!")

# Ensure directories exist
for d in ['/findtorontoevents.ca/live-monitor',
          '/findtorontoevents.ca/live-monitor/api',
          '/findtorontoevents.ca/live-monitor/research']:
    try:
        ftp.cwd(d)
    except Exception:
        try:
            ftp.mkd(d)
            print(f"Created: {d}")
        except Exception:
            pass

# Upload files
uploads = [
    (r'e:\findtorontoevents_antigravity.ca\live-monitor\api\goldmine_maintenance.php',
     '/findtorontoevents.ca/live-monitor/api/goldmine_maintenance.php'),
    (r'e:\findtorontoevents_antigravity.ca\live-monitor\research\index.html',
     '/findtorontoevents.ca/live-monitor/research/index.html'),
    (r'e:\findtorontoevents_antigravity.ca\live-monitor\research\live-vs-research.html',
     '/findtorontoevents.ca/live-monitor/research/live-vs-research.html'),
    (r'e:\findtorontoevents_antigravity.ca\live-monitor\goldmine-alerts.html',
     '/findtorontoevents.ca/live-monitor/goldmine-alerts.html'),
]

for local, remote in uploads:
    if os.path.exists(local):
        print(f"Uploading {os.path.basename(local)}...", end=' ')
        with open(local, 'rb') as f:
            ftp.storbinary(f'STOR {remote}', f)
        print("OK")

ftp.quit()
print("\nDeployed!")
print("Maintenance: https://findtorontoevents.ca/live-monitor/api/goldmine_maintenance.php?action=status")
print("Research:    https://findtorontoevents.ca/live-monitor/research/")
