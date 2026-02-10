#!/usr/bin/env python3
"""Deploy Edge Finder system to production via FTP"""

import os
import sys
from ftplib import FTP_TLS

server = os.environ.get('FTP_SERVER')
user = os.environ.get('FTP_USER')
passwd = os.environ.get('FTP_PASS')

if not all([server, user, passwd]):
    print("ERROR: FTP credentials not found in environment variables")
    sys.exit(1)

FILES = [
    ('live-monitor/api/edge_finder.php', '/findtorontoevents.ca/live-monitor/api/edge_finder.php'),
    ('live-monitor/edge-dashboard.html', '/findtorontoevents.ca/live-monitor/edge-dashboard.html'),
    ('live-monitor/live-monitor.html', '/findtorontoevents.ca/live-monitor/live-monitor.html'),
]

BASE = r'e:\findtorontoevents_antigravity.ca'

ftp = FTP_TLS(server)
ftp.login(user, passwd)
ftp.prot_p()
print("Connected to FTP")

for local_rel, remote_path in FILES:
    local_path = os.path.join(BASE, local_rel)
    if not os.path.exists(local_path):
        print(f"SKIP (not found): {local_rel}")
        continue
    with open(local_path, 'rb') as f:
        ftp.storbinary(f'STOR {remote_path}', f)
    print(f"OK: {local_rel} -> {remote_path}")

ftp.quit()
print("\nAll files deployed!")
