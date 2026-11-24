#!/usr/bin/env python3
"""
Deploy movieshows2 PHP scripts to FTP.
Uploads only the new fetch/log scripts (does not touch existing files).

Uses environment variables:
  FTP_HOST - FTP hostname (default: ftps2.50webs.com)
  FTP_USER - FTP username
  FTP_PASS - FTP password

Run from project root:
  python tools/deploy_movieshows2.py
"""
import os
import ftplib
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent

# Load .env if present
_env_file = WORKSPACE / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k and os.environ.get(k) in (None, ""):
                os.environ.setdefault(k, v)
    if "FTP_HOST" in os.environ and "FTP_SERVER" not in os.environ:
        os.environ.setdefault("FTP_SERVER", os.environ["FTP_HOST"])

REMOTE_BASE = "findtorontoevents.ca/movieshows2"

# Files to deploy (relative to TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/)
FILES_TO_DEPLOY = [
    "fetch_new_content.php",
    "log/index.php",
    "log/api_status.php",
    "admin.html",
    "admin_search.php",
    "admin_add_single.php",
    "admin_fetch_year.php",
]

def _env(key, fallback=""):
    return os.environ.get(key, fallback).strip()


def _ensure_dir(ftp, remote_dir):
    """Create remote directory tree if it doesn't exist."""
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
                print(f"  Warning: mkd/cwd {part}: {e}")
                return False
    return True


def _upload_file(ftp, local_path, remote_path):
    """Upload a single file to FTP."""
    remote_dir = "/".join(remote_path.split("/")[:-1])
    remote_filename = remote_path.split("/")[-1]

    ftp.cwd("/")
    if remote_dir and not _ensure_dir(ftp, remote_dir):
        return False

    try:
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_filename}", f)
        print(f"  Uploaded: {remote_path}")
        return True
    except Exception as e:
        print(f"  ERROR uploading {remote_path}: {e}")
        return False


def main():
    host = _env("FTP_HOST") or _env("FTP_SERVER")
    user = _env("FTP_USER")
    password = _env("FTP_PASS")

    if not host or not user or not password:
        print("ERROR: Set FTP_HOST, FTP_USER, FTP_PASS in environment or .env file.")
        raise SystemExit(1)

    local_base = WORKSPACE / "TORONTOEVENTS_ANTIGRAVITY" / "MOVIESHOWS2"

    print(f"Deploying movieshows2 scripts to {host}")
    print(f"Remote path: {REMOTE_BASE}/")
    print(f"Local source: {local_base}")
    print()

    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user, password)
            print("Connected to FTP.\n")

            uploaded = 0
            failed = 0

            for rel_path in FILES_TO_DEPLOY:
                local_file = local_base / rel_path
                remote_file = f"{REMOTE_BASE}/{rel_path}"

                if not local_file.exists():
                    print(f"  SKIP (not found): {local_file}")
                    continue

                if _upload_file(ftp, local_file, remote_file):
                    uploaded += 1
                else:
                    failed += 1

            print(f"\nDone: {uploaded} uploaded, {failed} failed")

            if failed > 0:
                raise SystemExit(1)

    except ftplib.all_errors as e:
        print(f"FTP error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
