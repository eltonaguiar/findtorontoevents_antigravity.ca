#!/usr/bin/env python3
"""Quick deploy edge_finder.php for debugging"""
import os, sys
from ftplib import FTP_TLS

server = os.environ.get('FTP_SERVER')
user = os.environ.get('FTP_USER')
passwd = os.environ.get('FTP_PASS')
if not all([server, user, passwd]):
    print("ERROR: FTP creds missing"); sys.exit(1)

ftp = FTP_TLS(server)
ftp.login(user, passwd)
ftp.prot_p()
with open(r'e:\findtorontoevents_antigravity.ca\live-monitor\api\edge_finder.php', 'rb') as f:
    ftp.storbinary('STOR /findtorontoevents.ca/live-monitor/api/edge_finder.php', f)
print("Deployed edge_finder.php")
ftp.quit()
