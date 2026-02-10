"""Deploy meme coin scanner to production via FTP."""
import os, ftplib, sys

FTP_SERVER = os.environ.get('FTP_SERVER')
FTP_USER = os.environ.get('FTP_USER')
FTP_PASS = os.environ.get('FTP_PASS')
if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
    print("ERROR: FTP credentials not found")
    sys.exit(1)

FILES = [
    ('findcryptopairs/api/meme_scanner.php', '/findtorontoevents.ca/findcryptopairs/api/meme_scanner.php'),
    ('findcryptopairs/meme.html', '/findtorontoevents.ca/findcryptopairs/meme.html'),
    ('findcryptopairs/winners.html', '/findtorontoevents.ca/findcryptopairs/winners.html'),
    ('updates/index.html', '/findtorontoevents.ca/updates/index.html'),
]

LOCAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ftp = ftplib.FTP_TLS(FTP_SERVER)
ftp.login(FTP_USER, FTP_PASS)
ftp.prot_p()
print("Connected")

for local_rel, remote_path in FILES:
    local_path = os.path.join(LOCAL_ROOT, local_rel.replace('/', os.sep))
    if not os.path.exists(local_path):
        print("SKIP: %s" % local_rel)
        continue
    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary('STOR %s' % remote_path, f)
        size = os.path.getsize(local_path)
        print("OK: %s (%s bytes)" % (local_rel, "{:,}".format(size)))
    except Exception as e:
        print("FAIL: %s - %s" % (local_rel, e))

ftp.quit()
print("Deploy complete!")
