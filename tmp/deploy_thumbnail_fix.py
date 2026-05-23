#!/usr/bin/env python3
"""Quick deploy of thumbnail fix files to findtorontoevents.ca via FTP."""
import os
import sys
import ftplib
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

WORKSPACE = Path(__file__).resolve().parent.parent
FTE_CLONE = WORKSPACE / "tmp" / "fte_clone"

env_file = WORKSPACE / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k and not os.environ.get(k):
                os.environ[k] = v

host = os.environ.get("FTP_HOST", os.environ.get("FTP_SERVER", ""))
user = os.environ.get("FTP_USER", "")
pw = os.environ.get("FTP_PASS", "")
remote_base = "findtorontoevents.ca"

if not host or not user or not pw:
    print("ERROR: Missing FTP credentials in .env")
    sys.exit(1)

files_to_upload = [
    (FTE_CLONE / "index.html", f"{remote_base}/index.html"),
    (FTE_CLONE / "events.json", f"{remote_base}/events.json"),
    (FTE_CLONE / "events.json", f"{remote_base}/next/events.json"),
    (FTE_CLONE / "api" / "image-proxy.php", f"{remote_base}/api/image-proxy.php"),
]

print(f"Connecting to {host}...")
ftp = ftplib.FTP(host, timeout=30)
ftp.login(user, pw)
ftp.set_pasv(True)
print(f"Connected. Deploying thumbnail fix files to /{remote_base}/")

for local, remote in files_to_upload:
    if not local.is_file():
        print(f"  SKIP {remote} (local not found: {local})")
        continue
    remote_dir = "/".join(remote.split("/")[:-1])
    ftp.cwd("/")
    for part in remote_dir.split("/"):
        if not part:
            continue
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            try:
                ftp.mkd(part)
                ftp.cwd(part)
            except Exception as e:
                print(f"  WARN: mkd {part}: {e}")
    fname = remote.split("/")[-1]
    with open(local, "rb") as f:
        ftp.storbinary(f"STOR {fname}", f)
    print(f"  OK {remote} ({local.stat().st_size / 1024:.0f} KB)")

ftp.quit()
print("\nDone! Deployed thumbnail fix to findtorontoevents.ca")
