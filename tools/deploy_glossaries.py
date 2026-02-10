"""Deploy all pages with new glossary sections to production via FTP."""
import os, sys
from ftplib import FTP_TLS

server = os.environ.get('FTP_SERVER')
user = os.environ.get('FTP_USER')
passwd = os.environ.get('FTP_PASS')
if not all([server, user, passwd]):
    print("ERROR: FTP credentials not set")
    sys.exit(1)

LOCAL_BASE = r'e:\findtorontoevents_antigravity.ca'
REMOTE_ROOT = '/findtorontoevents.ca'

files = [
    'findcryptopairs/winners.html',
    'live-monitor/live-monitor.html',
    'live-monitor/edge-dashboard.html',
    'live-monitor/winning-patterns.html',
    'findstocks/portfolio2/dashboard.html',
    'findstocks/portfolio2/picks.html',
    'findstocks/portfolio2/dividends.html',
]

ftp = FTP_TLS(server)
ftp.login(user, passwd)
ftp.prot_p()
print("Connected")

for rel in files:
    local = os.path.join(LOCAL_BASE, rel.replace('/', os.sep))
    remote = REMOTE_ROOT + '/' + rel
    if not os.path.exists(local):
        print("SKIP: %s" % rel)
        continue
    try:
        with open(local, 'rb') as f:
            ftp.storbinary('STOR %s' % remote, f)
        size = os.path.getsize(local)
        print("OK: %s (%s bytes)" % (rel, "{:,}".format(size)))
    except Exception as e:
        print("FAIL: %s - %s" % (rel, e))

ftp.quit()
print("\nDeploy complete!")
