import os
import sys
from ftplib import FTP_TLS

server = os.environ.get("FTP_SERVER")
user = os.environ.get("FTP_USER")
passwd = os.environ.get("FTP_PASS")

if not all([server, user, passwd]):
    print("ERROR: Missing FTP_SERVER, FTP_USER, or FTP_PASS environment variables.")
    sys.exit(1)

local_path = r"e:\findtorontoevents_antigravity.ca\findstocks\index.html"
remote_path = "/findtorontoevents.ca/findstocks/index.html"

try:
    ftp = FTP_TLS(server)
    ftp.login(user, passwd)
    ftp.prot_p()
    print(f"Connected to {server}")

    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f)
    print(f"Uploaded: {local_path} -> {remote_path}")

    ftp.quit()
    print("SUCCESS: Deployment complete.")
except Exception as e:
    print(f"FAILURE: {e}")
    sys.exit(1)
