#!/usr/bin/env python3
"""Deploy extend_navs.php for MF2."""
import os, ftplib
from pathlib import Path

W = Path(__file__).resolve().parent.parent
ef = W / ".env"
if ef.exists():
    for ln in ef.read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, _, v = ln.partition("=")
            k, v = k.strip(), v.strip()
            if k and not os.environ.get(k): os.environ[k] = v
    if "FTP_SERVER" not in os.environ and os.environ.get("FTP_HOST"):
        os.environ["FTP_SERVER"] = os.environ["FTP_HOST"]

host = os.environ.get("FTP_SERVER", "")
user = os.environ.get("FTP_USER", "")
pw = os.environ.get("FTP_PASS", "")
rp = os.environ.get("FTP_REMOTE_PATH", "findtorontoevents.ca")

local = W / "findmutualfunds2" / "portfolio2" / "api" / "extend_navs.php"
remote = f"{rp}/findmutualfunds2/portfolio2/api/extend_navs.php"

ftp = ftplib.FTP_TLS(host); ftp.login(user, pw); ftp.prot_p()
ftp.cwd("/")
for p in remote.rsplit("/", 1)[0].split("/"):
    if not p: continue
    try: ftp.cwd(p)
    except: ftp.mkd(p); ftp.cwd(p)
with open(local, "rb") as f:
    ftp.storbinary(f"STOR extend_navs.php", f)
print(f"OK: {remote}")
ftp.quit()
