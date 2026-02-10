"""Deploy algorithm improvements to live-monitor."""
import ftplib, os, sys

server = os.environ.get('FTP_SERVER')
user = os.environ.get('FTP_USER')
pw = os.environ.get('FTP_PASS')
if not all([server, user, pw]):
    print("ERROR: FTP_SERVER, FTP_USER, FTP_PASS env vars required")
    sys.exit(1)

files = [
    ('live-monitor/api/live_signals.php', '/findtorontoevents.ca/live-monitor/api/live_signals.php'),
    ('updates/index.html', '/findtorontoevents.ca/updates/index.html'),
]

ftp = ftplib.FTP_TLS(server)
ftp.login(user, pw)
ftp.prot_p()

for local_rel, remote in files:
    local = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), local_rel)
    print(f"Uploading {local_rel} -> {remote}")
    with open(local, 'rb') as f:
        ftp.storbinary(f'STOR {remote}', f)
    print(f"  OK ({os.path.getsize(local)} bytes)")

ftp.quit()
print("Deploy complete!")
