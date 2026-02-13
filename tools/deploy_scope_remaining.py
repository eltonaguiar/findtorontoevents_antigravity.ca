#!/usr/bin/env python3
"""Deploy remaining scope-labeled pages."""
import os, sys
from ftplib import FTP_TLS

server = os.environ.get('FTP_SERVER')
user = os.environ.get('FTP_USER')
pw = os.environ.get('FTP_PASS')
if not all([server, user, pw]):
    print("ERROR: FTP_SERVER, FTP_USER, FTP_PASS env vars required")
    sys.exit(1)

REMOTE_ROOT = '/findtorontoevents.ca'
LOCAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = [
    ('findcryptopairs/winners.html',           '/findcryptopairs/winners.html'),
    ('findcryptopairs/meme.html',              '/findcryptopairs/meme.html'),
    ('findcryptopairs/index.html',             '/findcryptopairs/index.html'),
    ('findcryptopairs/portfolio/index.html',   '/findcryptopairs/portfolio/index.html'),
    ('findcryptopairs/portfolio/stats/index.html', '/findcryptopairs/portfolio/stats/index.html'),
    ('findforex2/portfolio/index.html',        '/findforex2/portfolio/index.html'),
    ('findforex2/portfolio/stats/index.html',  '/findforex2/portfolio/stats/index.html'),
    ('findstocks/index.html',                  '/fc/findstocks/index.html'),
    ('findstocks/tools.html',                  '/fc/findstocks/tools.html'),
    ('findstocks/updates.html',                '/fc/findstocks/updates.html'),
    ('findstocks/portfolio2/hub.html',         '/findstocks/portfolio2/hub.html'),
    ('findstocks/portfolio2/learning-lab.html', '/findstocks/portfolio2/learning-lab.html'),
    ('findstocks/portfolio2/learning-dashboard.html', '/findstocks/portfolio2/learning-dashboard.html'),
    ('findstocks/portfolio2/stock-profile.html', '/findstocks/portfolio2/stock-profile.html'),
    ('findstocks/portfolio2/smart-learning.html', '/findstocks/portfolio2/smart-learning.html'),
    ('findstocks/portfolio2/index.html',       '/findstocks/portfolio2/index.html'),
    ('live-monitor/hour-learning.html',        '/live-monitor/hour-learning.html'),
]

ftp = FTP_TLS(server)
ftp.login(user, pw)
ftp.prot_p()
print("Connected to %s" % server)

uploaded = 0
errors = 0
for local_rel, remote_rel in FILES:
    local_path = os.path.join(LOCAL_ROOT, local_rel.replace('/', os.sep))
    remote_path = REMOTE_ROOT + remote_rel
    if not os.path.exists(local_path):
        print("  SKIP: %s" % local_rel)
        errors += 1
        continue
    size = os.path.getsize(local_path)
    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary('STOR %s' % remote_path, f)
        print("  OK: %s (%s bytes)" % (local_rel, '{:,}'.format(size)))
        uploaded += 1
    except Exception as e:
        print("  FAIL: %s -> %s" % (local_rel, str(e)))
        errors += 1

ftp.quit()
print("\nDone: %d uploaded, %d errors" % (uploaded, errors))
