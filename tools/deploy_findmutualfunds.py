#!/usr/bin/env python3
"""Deploy FindMutualFunds portfolio analysis system to FTP."""
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
        os.environ.setdefault("FTP_SERVER", os.environ["FTP_HOST"])

DEFAULT_REMOTE_PATH = "findtorontoevents.ca"


def _env(key, fallback=""):
    return os.environ.get(key, fallback).strip()


def _ensure_dir(ftp, remote_dir):
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


def upload_tree(ftp, local_dir, remote_base):
    ftp.cwd("/")
    if not _ensure_dir(ftp, remote_base):
        return 0
    count = 0
    for root, dirs, files in os.walk(local_dir):
        for name in files:
            local_path = Path(root) / name
            rel = local_path.relative_to(local_dir)
            remote_path = remote_base + "/" + str(rel).replace("\\", "/")
            remote_parts = remote_path.split("/")
            remote_file = remote_parts[-1]
            remote_parent = "/".join(remote_parts[:-1])
            ftp.cwd("/")
            _ensure_dir(ftp, remote_parent)
            try:
                with open(local_path, "rb") as f:
                    ftp.storbinary(f"STOR {remote_file}", f)
                print(f"  {remote_path}")
                count += 1
            except Exception as e:
                print(f"  ERROR {remote_path}: {e}")
    return count


def main():
    host = _env("FTP_SERVER") or _env("FTP_HOST")
    user = _env("FTP_USER")
    password = _env("FTP_PASS")
    remote_path = _env("FTP_REMOTE_PATH") or DEFAULT_REMOTE_PATH

    if not host or not user or not password:
        print("Set FTP_SERVER, FTP_USER, FTP_PASS.")
        raise SystemExit(1)

    print(f"Deploying FindMutualFunds to FTP: {host}")
    print(f"Remote path: {remote_path}/findmutualfunds/\n")

    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user, password)
            print("Connected.\n")

            # Upload findmutualfunds/api/
            local_api = WORKSPACE / "findmutualfunds" / "api"
            if local_api.is_dir():
                print("Uploading findmutualfunds/api/ ...")
                n = upload_tree(ftp, local_api, f"{remote_path}/findmutualfunds/api")
                print(f"  -> {n} files\n")

            # Upload findmutualfunds/portfolio1/
            local_portfolio = WORKSPACE / "findmutualfunds" / "portfolio1"
            if local_portfolio.is_dir():
                print("Uploading findmutualfunds/portfolio1/ ...")
                n = upload_tree(ftp, local_portfolio, f"{remote_path}/findmutualfunds/portfolio1")
                print(f"  -> {n} files\n")

        print("FindMutualFunds deploy complete.")
        print()
        print("Post-deploy steps:")
        print("  1. Setup schema:   https://findtorontoevents.ca/findmutualfunds/api/setup_schema.php")
        print("  2. Fetch NAV:      https://findtorontoevents.ca/findmutualfunds/api/fetch_nav.php?range=1y&batch=10")
        print("  3. Import funds:   https://findtorontoevents.ca/findmutualfunds/api/import_funds.php")
        print("  4. Daily refresh:  https://findtorontoevents.ca/findmutualfunds/api/daily_refresh.php")
        print("  5. View page:      https://findtorontoevents.ca/findmutualfunds/portfolio1/")
    except Exception as e:
        print(f"Deploy failed: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
