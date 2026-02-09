#!/usr/bin/env python3
"""Deploy Alpha Suite files to FTP.

Uploads just the alpha_* PHP files, alpha/ dashboard, and updated global page.
"""
import os
import ftplib
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

# Load .env
env_file = WORKSPACE / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k and os.environ.get(k) in (None, ""):
                os.environ[k] = v

HOST = os.environ.get("FTP_HOST") or os.environ.get("FTP_SERVER")
USER = os.environ.get("FTP_USER")
PASS = os.environ.get("FTP_PASS")
ROOT = os.environ.get("FTP_ROOT", "/findtorontoevents.ca")

if not all([HOST, USER, PASS]):
    print("ERROR: FTP credentials not set. Check .env or env vars.")
    exit(1)

FILES = [
    # (local_path, remote_path)
    ("findstocks/api/alpha_setup.php",   f"{ROOT}/findstocks/api/alpha_setup.php"),
    ("findstocks/api/alpha_fetch.php",   f"{ROOT}/findstocks/api/alpha_fetch.php"),
    ("findstocks/api/alpha_engine.php",  f"{ROOT}/findstocks/api/alpha_engine.php"),
    ("findstocks/api/alpha_refresh.php", f"{ROOT}/findstocks/api/alpha_refresh.php"),
    ("findstocks/api/alpha_data.php",    f"{ROOT}/findstocks/api/alpha_data.php"),
    ("findstocks/alpha/index.html",      f"{ROOT}/findstocks/alpha/index.html"),
    ("findstocks2_global/index.html",    f"{ROOT}/findstocks2_global/index.html"),
]

def ensure_remote_dir(ftp, path):
    """Create remote directory tree if it doesn't exist."""
    parts = path.strip("/").split("/")
    current = ""
    for part in parts:
        current += "/" + part
        try:
            ftp.cwd(current)
        except ftplib.error_perm:
            try:
                ftp.mkd(current)
                print(f"  Created dir: {current}")
            except ftplib.error_perm:
                pass

print(f"Connecting to {HOST}...")
ftp = ftplib.FTP(HOST, timeout=30)
ftp.login(USER, PASS)
print(f"Logged in. CWD: {ftp.pwd()}")

uploaded = 0
for local_rel, remote_path in FILES:
    local_path = WORKSPACE / local_rel
    if not local_path.exists():
        print(f"  SKIP (missing): {local_rel}")
        continue

    # Ensure parent directory exists
    remote_dir = "/".join(remote_path.split("/")[:-1])
    ensure_remote_dir(ftp, remote_dir)

    print(f"  Uploading {local_rel} -> {remote_path}...")
    try:
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_path}", f)
        uploaded += 1
        print(f"    OK ({local_path.stat().st_size} bytes)")
    except Exception as e:
        print(f"    FAIL: {e}")

ftp.quit()
print(f"\nDone. Uploaded {uploaded}/{len(FILES)} files.")
