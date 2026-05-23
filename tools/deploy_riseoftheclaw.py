#!/usr/bin/env python3
"""
Deploy KIMI Rise of the Claw dashboard to FTP.
Uploads riseoftheclaw.html to root and supporting files to /riseoftheclaw/ subdirectory.

Uses environment variables:
  FTP_HOST - FTP hostname (default: ftps2.50webs.com)
  FTP_USER - FTP username
  FTP_PASS - FTP password

Run from project root:
  python tools/deploy_riseoftheclaw.py
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

# torontoevent.net FTP root IS the document root — no subdirectory prefix needed
REMOTE_BASE = os.environ.get("FTP_REMOTE_BASE", "")
LOCAL_BASE = WORKSPACE / "deploy_riseoftheclaw"

# 2026-04-17 host-guard: this script writes to ROOT (REMOTE_BASE="") by default.
# That's only safe on a single-tenant host like torontoevent.net. If FTP_HOST ever
# resolves to a 50webs multi-site host, root writes corrupt other sites' layouts
# (incident: 2026-04-14 dumped /audit/ + /audit_dashboard/ folders to 50webs root).
# Refuse rather than silently corrupt. Override via FTP_REMOTE_BASE if you really
# need a 50webs deploy (e.g. FTP_REMOTE_BASE=findtorontoevents.ca).
_GUARD_HOST = os.environ.get("FTP_HOST", os.environ.get("FTP_SERVER", "")).lower()
if not REMOTE_BASE and ("50webs" in _GUARD_HOST or "ejaguiar" in _GUARD_HOST):
    raise SystemExit(
        f"REFUSED: FTP_HOST={_GUARD_HOST!r} is a 50webs multi-site host but "
        "REMOTE_BASE is empty (root). Set FTP_REMOTE_BASE=findtorontoevents.ca "
        "(or another site prefix) before running."
    )

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


def _upload_directory(ftp, local_dir, remote_base_path):
    """Recursively upload a directory."""
    uploaded = 0
    failed = 0

    for item in Path(local_dir).rglob("*"):
        if item.is_file():
            # Calculate relative path from local_dir
            rel_path = item.relative_to(local_dir)
            remote_path = f"{remote_base_path}/{rel_path}".replace("\\", "/")

            if _upload_file(ftp, item, remote_path):
                uploaded += 1
            else:
                failed += 1

    return uploaded, failed


def main():
    host = _env("FTP_HOST") or _env("FTP_SERVER")
    user = _env("FTP_USER")
    password = _env("FTP_PASS")

    if not host or not user or not password:
        print("ERROR: Set FTP_HOST, FTP_USER, FTP_PASS in environment or .env file.")
        raise SystemExit(1)

    def _rpath(*parts):
        """Build a clean remote path (no leading slash, no double slashes)."""
        segments = ([REMOTE_BASE] + list(parts)) if REMOTE_BASE else list(parts)
        return "/".join(s.strip("/") for s in segments if s)

    print(f"Deploying Rise of the Claw dashboard to {host}")
    print(f"Remote base: /{REMOTE_BASE}" if REMOTE_BASE else "Remote base: / (doc root)")
    print(f"Local source: {LOCAL_BASE}")
    print()

    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user, password)
            print("Connected to FTP.\n")

            uploaded = 0
            failed = 0

            # Upload main HTML file to root
            html_file = LOCAL_BASE / "riseoftheclaw.html"
            if html_file.exists():
                if _upload_file(ftp, html_file, _rpath("riseoftheclaw.html")):
                    uploaded += 1
                else:
                    failed += 1
            else:
                print(f"  ERROR: {html_file} not found")
                failed += 1

            # Upload riseoftheclaw directory recursively (css, js, data)
            riseoftheclaw_dir = LOCAL_BASE / "riseoftheclaw"
            if riseoftheclaw_dir.exists():
                dir_uploaded, dir_failed = _upload_directory(
                    ftp,
                    riseoftheclaw_dir,
                    _rpath("riseoftheclaw")
                )
                uploaded += dir_uploaded
                failed += dir_failed
            else:
                print(f"  ERROR: {riseoftheclaw_dir} not found")
                failed += 1

            print(f"\nDone: {uploaded} uploaded, {failed} failed")

            if failed > 0:
                raise SystemExit(1)

    except ftplib.all_errors as e:
        print(f"FTP error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
