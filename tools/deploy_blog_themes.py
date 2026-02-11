#!/usr/bin/env python3
"""
Deploy blog200–blog249 themed pages to FTP.

Uploads all blog*.html files (200-249) to the remote site root.
Uses FTP credentials from .env or environment variables.

Usage:
    python tools/deploy_blog_themes.py
"""

import os
import ftplib
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent

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
        os.environ["FTP_SERVER"] = os.environ["FTP_HOST"]

REMOTE_BASE = os.environ.get("FTP_ROOT", os.environ.get("FTP_REMOTE_PATH", "findtorontoevents.ca"))

def deploy():
    server = os.environ.get("FTP_SERVER", os.environ.get("FTP_HOST", ""))
    user = os.environ.get("FTP_USER", "")
    passwd = os.environ.get("FTP_PASS", "")

    if not server or not user or not passwd:
        print("ERROR: FTP credentials not set. Set FTP_SERVER, FTP_USER, FTP_PASS.")
        return False

    # Collect blog files
    blog_files = sorted(WORKSPACE.glob("blog2[0-4][0-9].html"))
    if not blog_files:
        print("No blog200-blog249 files found!")
        return False

    print(f"Found {len(blog_files)} blog files to deploy")
    print(f"FTP: {server} -> /{REMOTE_BASE}/")
    print()

    # Connect
    ftp = ftplib.FTP()
    ftp.connect(server, 21, timeout=30)
    ftp.login(user, passwd)
    ftp.set_pasv(True)
    print(f"Connected to {server}")

    # Navigate to remote base
    try:
        ftp.cwd(f"/{REMOTE_BASE}")
    except ftplib.error_perm:
        print(f"ERROR: Cannot cd to /{REMOTE_BASE}")
        ftp.quit()
        return False

    # Check for existing files (conflict check)
    existing = []
    try:
        remote_files = ftp.nlst()
    except:
        remote_files = []

    for bf in blog_files:
        if bf.name in remote_files:
            existing.append(bf.name)

    if existing:
        print(f"\nNote: {len(existing)} blog files already exist on remote (will be overwritten):")
        for f in existing[:5]:
            print(f"  - {f}")
        if len(existing) > 5:
            print(f"  ... and {len(existing)-5} more")
        print()

    # Upload
    uploaded = 0
    failed = 0
    for bf in blog_files:
        try:
            with open(bf, "rb") as f:
                ftp.storbinary(f"STOR {bf.name}", f)
            uploaded += 1
            print(f"  [{uploaded:2d}/{len(blog_files)}] {bf.name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {bf.name}: {e}")

    ftp.quit()

    print(f"\n{'='*50}")
    print(f"  Deployed: {uploaded}/{len(blog_files)} blog pages")
    if failed:
        print(f"  Failed:   {failed}")
    print(f"  Remote:   https://findtorontoevents.ca/blog200.html")
    print(f"{'='*50}")
    return failed == 0

if __name__ == "__main__":
    import sys
    ok = deploy()
    sys.exit(0 if ok else 1)
