#!/usr/bin/env python3
"""Quick targeted FTP upload for FIGHTGAME files only."""
import os
import ftplib
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

# Load .env
_env_file = WORKSPACE / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k and os.environ.get(k) in (None, ""):
                os.environ.setdefault(k, v)
    if "FTP_SERVER" not in os.environ and os.environ.get("FTP_HOST"):
        os.environ.setdefault("FTP_SERVER", os.environ["FTP_HOST"])

FTP_SERVER = os.environ.get("FTP_SERVER") or os.environ.get("FTP_HOST")
FTP_USER = os.environ.get("FTP_USER")
FTP_PASS = os.environ.get("FTP_PASS")
FTP_BASE = os.environ.get("FTP_REMOTE_PATH", "findtorontoevents.ca")

if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
    print("ERROR: Set FTP_SERVER, FTP_USER, FTP_PASS env vars")
    exit(1)

# Files to upload (relative to WORKSPACE)
FILES = [
    "FIGHTGAME/index.html",
    "FIGHTGAME/style.css",
    "FIGHTGAME/js/data.js",
    "FIGHTGAME/js/audio.js",
    "FIGHTGAME/js/engine.js",
    "FIGHTGAME/js/renderer.js",
    "FIGHTGAME/js/app.js",
]

print(f"Connecting to {FTP_SERVER}...")
ftp = ftplib.FTP(FTP_SERVER, timeout=30)
ftp.login(FTP_USER, FTP_PASS)
print(f"Logged in. Base path: /{FTP_BASE}/")

def ensure_dir(remote_dir):
    """Create remote directory if it doesn't exist."""
    parts = remote_dir.strip("/").split("/")
    current = ""
    for part in parts:
        current += "/" + part
        try:
            ftp.mkd(current)
        except ftplib.error_perm:
            pass  # already exists

for rel_path in FILES:
    local = WORKSPACE / rel_path
    if not local.exists():
        print(f"  SKIP (not found): {rel_path}")
        continue
    remote = f"/{FTP_BASE}/{rel_path}"
    remote_dir = "/".join(remote.split("/")[:-1])
    ensure_dir(remote_dir)
    with open(local, "rb") as f:
        ftp.storbinary(f"STOR {remote}", f)
    print(f"  OK: {rel_path}")

ftp.quit()
print("Done! All FIGHTGAME files uploaded.")
