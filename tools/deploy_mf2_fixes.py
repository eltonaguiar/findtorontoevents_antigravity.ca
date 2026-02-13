#!/usr/bin/env python3
"""Deploy Mutual Funds Portfolio v2 fixes: NAV fix, tracking, backtest seeding."""
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


def upload_file(ftp, local_path, remote_path):
    parts = remote_path.split("/")
    remote_file = parts[-1]
    remote_parent = "/".join(parts[:-1])
    ftp.cwd("/")
    _ensure_dir(ftp, remote_parent)
    try:
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_file}", f)
        print(f"  OK: {remote_path}")
        return True
    except Exception as e:
        print(f"  FAIL: {remote_path}: {e}")
        return False


def main():
    host = _env("FTP_SERVER") or _env("FTP_HOST")
    user = _env("FTP_USER")
    password = _env("FTP_PASS")
    remote_path = _env("FTP_REMOTE_PATH") or DEFAULT_REMOTE_PATH

    if not host or not user or not password:
        print("Set FTP_SERVER, FTP_USER, FTP_PASS.")
        raise SystemExit(1)

    # Files to deploy
    files = [
        ("findmutualfunds2/portfolio2/index.html", f"{remote_path}/findmutualfunds2/portfolio2/index.html"),
        ("findmutualfunds2/portfolio2/api/mf2_tracking.php", f"{remote_path}/findmutualfunds2/portfolio2/api/mf2_tracking.php"),
        ("findmutualfunds2/portfolio2/api/seed_backtests.php", f"{remote_path}/findmutualfunds2/portfolio2/api/seed_backtests.php"),
        ("findmutualfunds2/portfolio2/api/mf2_performance_tracking_schema.php", f"{remote_path}/findmutualfunds2/portfolio2/api/mf2_performance_tracking_schema.php"),
    ]

    print(f"Deploying MF2 fixes to FTP: {host}")
    print(f"Remote path: {remote_path}/findmutualfunds2/portfolio2/\n")

    try:
        ftp = ftplib.FTP_TLS(host)
        ftp.login(user, password)
        ftp.prot_p()
        print("Connected (TLS).\n")

        count = 0
        for local_rel, remote in files:
            local_path = WORKSPACE / local_rel
            if local_path.exists():
                if upload_file(ftp, local_path, remote):
                    count += 1
            else:
                print(f"  SKIP (not found): {local_rel}")

        ftp.quit()
        print(f"\nDeployed {count}/{len(files)} files.")
        print()
        print("Post-deploy steps:")
        print("  1. Seed backtests:    https://findtorontoevents.ca/findmutualfunds2/portfolio2/api/seed_backtests.php")
        print("  2. Init tracking:     https://findtorontoevents.ca/findmutualfunds2/portfolio2/api/mf2_tracking.php?action=init_tracking")
        print("  3. Refresh tracking:  https://findtorontoevents.ca/findmutualfunds2/portfolio2/api/mf2_tracking.php?action=refresh")
        print("  4. Create tables:     https://findtorontoevents.ca/findmutualfunds2/portfolio2/api/mf2_performance_tracking_schema.php")
        print("  5. View page:         https://findtorontoevents.ca/findmutualfunds2/portfolio2/")

    except Exception as e:
        print(f"Deploy failed: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
