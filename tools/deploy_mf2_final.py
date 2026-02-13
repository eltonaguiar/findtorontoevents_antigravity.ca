"""Deploy updated MF2 index.html and mf2_track2.php to production."""
import os, sys
from ftplib import FTP_TLS

server = os.environ.get("FTP_SERVER")
user   = os.environ.get("FTP_USER")
passwd = os.environ.get("FTP_PASS")

if not all([server, user, passwd]):
    print("ERROR: FTP_SERVER / FTP_USER / FTP_PASS env vars required")
    sys.exit(1)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

files = [
    (os.path.join(BASE, "findmutualfunds2", "portfolio2", "index.html"),
     "/findtorontoevents.ca/findmutualfunds2/portfolio2/index.html"),
    (os.path.join(BASE, "findmutualfunds2", "portfolio2", "api", "mf2_track2.php"),
     "/findtorontoevents.ca/findmutualfunds2/portfolio2/api/mf2_track2.php"),
]

ftp = FTP_TLS(server)
ftp.login(user, passwd)
ftp.prot_p()
print("Connected to", server)

for local, remote in files:
    if not os.path.exists(local):
        print(f"SKIP (not found): {local}")
        continue
    with open(local, "rb") as f:
        ftp.storbinary("STOR " + remote, f)
    print(f"OK: {remote}")

ftp.quit()
print("Done!")
