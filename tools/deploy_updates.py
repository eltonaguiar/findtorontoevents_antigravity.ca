#!/usr/bin/env python3
"""Deploy updates/index.html to FTP."""
import os, ftplib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k and os.environ.get(k) in (None, ""):
                os.environ.setdefault(k, v)
    if "FTP_SERVER" not in os.environ and os.environ.get("FTP_HOST"):
        os.environ["FTP_SERVER"] = os.environ["FTP_HOST"]

server = os.environ.get("FTP_SERVER", os.environ.get("FTP_HOST", ""))
user = os.environ.get("FTP_USER", "")
passwd = os.environ.get("FTP_PASS", "")
remote_base = os.environ.get("FTP_ROOT", "findtorontoevents.ca")

local_file = ROOT / "updates" / "index.html"
if not local_file.exists():
    print("ERROR: updates/index.html not found"); exit(1)

ftp = ftplib.FTP()
ftp.connect(server, 21, timeout=30)
ftp.login(user, passwd)
ftp.set_pasv(True)
print(f"Connected to {server}")

# Ensure updates/ dir exists
try:
    ftp.cwd(f"/{remote_base}/updates")
except:
    ftp.cwd(f"/{remote_base}")
    try: ftp.mkd("updates")
    except: pass
    ftp.cwd("updates")

with open(local_file, "rb") as f:
    ftp.storbinary("STOR index.html", f)
print("Deployed updates/index.html")
ftp.quit()
