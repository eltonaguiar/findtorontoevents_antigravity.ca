#!/usr/bin/env python3
"""Deploy fetch_prices.php fix for NAV date range."""
import os
import ftplib
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent

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

DEFAULT_REMOTE_PATH = "findtorontoevents.ca"

def _env(key, fallback=""):
    return os.environ.get(key, fallback).strip()

def main():
    host = _env("FTP_SERVER") or _env("FTP_HOST")
    user = _env("FTP_USER")
    password = _env("FTP_PASS")
    remote_path = _env("FTP_REMOTE_PATH") or DEFAULT_REMOTE_PATH

    local_path = WORKSPACE / "findmutualfunds2" / "portfolio2" / "api" / "fetch_prices.php"
    remote_file = f"{remote_path}/findmutualfunds2/portfolio2/api/fetch_prices.php"

    print(f"Deploying fetch_prices.php to {host}")
    ftp = ftplib.FTP_TLS(host)
    ftp.login(user, password)
    ftp.prot_p()

    parts = remote_file.split("/")
    remote_dir = "/".join(parts[:-1])
    ftp.cwd("/")
    for part in remote_dir.split("/"):
        if not part: continue
        try: ftp.cwd(part)
        except: ftp.mkd(part); ftp.cwd(part)

    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {parts[-1]}", f)
    print(f"  OK: {remote_file}")
    ftp.quit()
    print("Done.")

if __name__ == "__main__":
    main()
