#!/usr/bin/env python3
"""
Deploy the tdotevent.ca staging folder to FTP.

FTP login is the same as findtorontoevents (same FTP_SERVER, FTP_USER, FTP_PASS).
Only the remote path differs: /tdotevent.ca (no findevents subfolder).

Uploads from STAGING_DIR (default E:\\tdotevent.ca) to FTP path
FTP_REMOTE_PATH (default: tdotevent.ca). Run stage_for_tdotevent.py first.

Uses environment variables:
  FTP_SERVER   (or FTP_HOST) - FTP hostname (same as findtorontoevents)
  FTP_USER     - FTP username (same)
  FTP_PASS     - FTP password (same)
  STAGING_DIR  - Local staging folder (default: E:\\tdotevent.ca)
  FTP_REMOTE_PATH - Remote path on FTP (default: tdotevent.ca, or /tdotevent.ca)

Run from project root (after staging):
  set FTP_SERVER=... FTP_USER=... FTP_PASS=...
  python tools/deploy_tdotevent_to_ftp.py
"""
import os
import ftplib
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent

DEFAULT_STAGING = "E:\\tdotevent.ca"
DEFAULT_REMOTE_PATH = "tdotevent.ca"


def _env(key: str, fallback: str = "") -> str:
    return os.environ.get(key, fallback).strip()


def _ensure_dir(ftp: ftplib.FTP, remote_dir: str) -> bool:
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


def _upload_tree(ftp: ftplib.FTP, local_dir: Path, remote_base: str) -> int:
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


def _upload_file(ftp: ftplib.FTP, local_path: Path, remote_path: str) -> bool:
    remote_dir = "/".join(remote_path.split("/")[:-1])
    ftp.cwd("/")
    if remote_dir and not _ensure_dir(ftp, remote_dir):
        return False
    try:
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_path.split('/')[-1]}", f)
        print(f"  {remote_path}")
        return True
    except Exception as e:
        print(f"  ERROR {remote_path}: {e}")
        return False


def deploy_from_staging(ftp: ftplib.FTP, staging: Path, remote_base: str) -> bool:
    """Upload staged site (index.html, .htaccess, events, next/_next/, fc/) to remote_base."""
    ok = True

    idx = staging / "index.html"
    if idx.is_file():
        if not _upload_file(ftp, idx, f"{remote_base}/index.html"):
            ok = False
    else:
        print(f"  Skip index.html (not found in staging)")

    ht = staging / ".htaccess"
    if ht.is_file():
        _upload_file(ftp, ht, f"{remote_base}/.htaccess")

    ev = staging / "events.json"
    if ev.is_file():
        _upload_file(ftp, ev, f"{remote_base}/events.json")

    ev_next = staging / "next" / "events.json"
    if ev_next.is_file():
        _upload_file(ftp, ev_next, f"{remote_base}/next/events.json")

    next_next = staging / "next" / "_next"
    if next_next.is_dir():
        n = _upload_tree(ftp, next_next, f"{remote_base}/next/_next")
        print(f"  -> {n} files under next/_next/")
    else:
        print(f"  Skip next/_next (not found in staging)")

    fc = staging / "fc"
    if fc.is_dir():
        n = _upload_tree(ftp, fc, f"{remote_base}/fc")
        print(f"  -> {n} files under fc/")

    return ok


def main() -> None:
    staging = Path(_env("STAGING_DIR") or DEFAULT_STAGING)
    remote_path = (_env("FTP_REMOTE_PATH") or DEFAULT_REMOTE_PATH).strip().lstrip("/")
    host = _env("FTP_SERVER") or _env("FTP_HOST")
    user = _env("FTP_USER")
    password = _env("FTP_PASS")

    if not host or not user or not password:
        print("Set FTP_SERVER (or FTP_HOST), FTP_USER, FTP_PASS in environment.")
        raise SystemExit(1)

    if not staging.is_dir():
        print(f"Staging folder not found: {staging}")
        print("Run first: python tools/stage_for_tdotevent.py")
        raise SystemExit(1)

    if not (staging / "index.html").is_file():
        print(f"No index.html in {staging}. Run stage_for_tdotevent.py first.")
        raise SystemExit(1)

    print(f"Deploy tdotevent.ca to FTP: {host}")
    print(f"From staging: {staging}")
    print(f"Remote path: {remote_path}")
    print()

    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user, password)
            print("Connected.\n")
            print(f"Uploading to {remote_path}/ ...")
            deploy_from_staging(ftp, staging, remote_path)
        print()
        print("Deploy complete. Verify: https://tdotevent.ca")
    except Exception as e:
        print(f"Deploy failed: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
