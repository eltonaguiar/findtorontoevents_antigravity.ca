"""
Deploy updated pages: findstocks/index.html, findstocks2_global/index.html, updates/index.html
"""
import os
import sys
from ftplib import FTP_TLS

server = os.environ.get('FTP_SERVER', '')
user = os.environ.get('FTP_USER', '')
passwd = os.environ.get('FTP_PASS', '')

if not server or not user or not passwd:
    print("ERROR: FTP credentials not set in environment variables")
    sys.exit(1)

LOCAL_BASE = r'e:\findtorontoevents_antigravity.ca'
REMOTE_ROOT = '/findtorontoevents.ca'

files_to_deploy = [
    ('updates/index.html', 'updates/index.html'),
]

print("Connecting to %s..." % server)
ftp = FTP_TLS(server)
ftp.login(user, passwd)
ftp.prot_p()
print("Connected and secured.")

# Ensure remote directories exist
for d in [REMOTE_ROOT + '/updates']:
    try:
        ftp.mkd(d)
        print("Created directory: %s" % d)
    except Exception:
        pass

for local_rel, remote_rel in files_to_deploy:
    local_path = os.path.join(LOCAL_BASE, local_rel)
    remote_path = REMOTE_ROOT + '/' + remote_rel

    if not os.path.exists(local_path):
        print("SKIP (not found): %s" % local_path)
        continue

    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary('STOR %s' % remote_path, f)
        size = os.path.getsize(local_path)
        print("OK: %s (%s bytes)" % (remote_rel, "{:,}".format(size)))
    except Exception as e:
        print("FAIL: %s - %s" % (remote_rel, e))

ftp.quit()
print("\nDeploy complete!")
print("Verify:")
print("  - https://findtorontoevents.ca/findstocks/")
print("  - https://findtorontoevents.ca/findstocks2_global/")
print("  - https://findtorontoevents.ca/updates/")
