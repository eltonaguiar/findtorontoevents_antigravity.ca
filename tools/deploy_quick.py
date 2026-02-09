#!/usr/bin/env python3
"""Quick targeted deploy — uploads only specific files/dirs instead of the full site."""
import os
import sys
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
    remote_dir = "/".join(remote_path.split("/")[:-1])
    ftp.cwd("/")
    if remote_dir and not _ensure_dir(ftp, remote_dir):
        return False
    try:
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_path.split('/')[-1]}", f)
        print(f"  OK: {remote_path}")
        return True
    except Exception as e:
        print(f"  ERROR {remote_path}: {e}")
        return False


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

    # Items to deploy: list of (local_path, remote_path_relative_to_site_root)
    # Allow command-line args to override items
    if len(sys.argv) > 1:
        items = []
        for arg in sys.argv[1:]:
            local = WORKSPACE / arg.replace("/", os.sep)
            items.append((local, arg.replace("\\", "/")))
    else:
        items = [
            # Main page
            (WORKSPACE / "index.html", "index.html"),
            # Investment Tools landing page
            (WORKSPACE / "investments", "investments"),
            # FindStocks API + Portfolio
            (WORKSPACE / "findstocks" / "api", "findstocks/api"),
            (WORKSPACE / "findstocks" / "portfolio", "findstocks/portfolio"),
            # Forex API + Portfolio
            (WORKSPACE / "findforex2" / "api", "findforex2/api"),
            (WORKSPACE / "findforex2" / "portfolio", "findforex2/portfolio"),
            # Crypto API + Portfolio
            (WORKSPACE / "findcryptopairs" / "api", "findcryptopairs/api"),
            (WORKSPACE / "findcryptopairs" / "portfolio", "findcryptopairs/portfolio"),
            # Updates page
            (WORKSPACE / "updates", "updates"),
            # Game prototypes page (already deployed, but include for safety)
            (WORKSPACE / "vr" / "game-arena" / "fps-v5" / "index.html", "vr/game-arena/fps-v5/index.html"),
        ]

    print(f"Quick deploy to FTP: {host}")
    print(f"Remote path: {remote_path}\n")

    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user, password)
            print("Connected.\n")

            for local, rel_remote in items:
                full_remote = f"{remote_path}/{rel_remote}"
                if local.is_dir():
                    print(f"Uploading directory {rel_remote}/ ...")
                    n = upload_tree(ftp, local, full_remote)
                    print(f"  -> {n} files\n")
                elif local.is_file():
                    print(f"Uploading {rel_remote} ...")
                    upload_file(ftp, local, full_remote)
                    print()
                else:
                    print(f"  Skip {rel_remote} (not found)\n")

        print("Quick deploy complete.")
    except Exception as e:
        print(f"Deploy failed: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
