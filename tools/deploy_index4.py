#!/usr/bin/env python3
"""
Deploy index4.html and all dependencies to the remote site (no partial deploy).

Uploads the full set so the page works: index4.html, data/menu4.json,
data/events.json, events.json, next/events.json, favicon.ico, next/_next/
to both remote_path and parent (domain root). See DEPLOYMENT_NOTES.md.

Uses environment variables (see .cursor/rules/ftp-credentials.mdc):
  FTP_SERVER  (or FTP_HOST) - FTP hostname
  FTP_USER    - FTP username
  FTP_PASS    - FTP password
  FTP_REMOTE_PATH - Remote path (default: findtorontoevents.ca/findevents)

Run from project root:
  set FTP_SERVER=... FTP_USER=... FTP_PASS=...
  python tools/deploy_index4.py

After deploy: verify https://findtorontoevents.ca/index4.html (menu, events, no 404s).
"""
import os
import ftplib
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent
DEFAULT_REMOTE_PATH = "findtorontoevents.ca/findevents"


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
                count += 1
            except Exception as e:
                print(f"  ERROR {remote_path}: {e}")
    return count


def main() -> None:
    host = _env("FTP_SERVER") or _env("FTP_HOST")
    user = _env("FTP_USER")
    password = _env("FTP_PASS")
    remote_path = _env("FTP_REMOTE_PATH") or DEFAULT_REMOTE_PATH

    if not host or not user or not password:
        print("Set FTP_SERVER (or FTP_HOST), FTP_USER, FTP_PASS in environment.")
        raise SystemExit(1)

    index4 = WORKSPACE / "index4.html"
    menu4 = WORKSPACE / "data" / "menu4.json"
    events_root = WORKSPACE / "events.json"
    events_next = WORKSPACE / "next" / "events.json"
    events_data = WORKSPACE / "data" / "events.json"
    favicon = WORKSPACE / "favicon.ico"
    next_next = WORKSPACE / "next" / "_next"
    if not index4.is_file():
        print(f"index4.html not found at {index4}")
        raise SystemExit(1)
    if not menu4.is_file():
        print(f"data/menu4.json not found at {menu4}")
        raise SystemExit(1)

    print(f"Deploy index4 + menu, events, favicon, next/_next to FTP: {host}")
    print(f"Remote path: {remote_path}")
    print()

    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user, password)
            print("Connected.\n")
            parent = "/".join(remote_path.rstrip("/").split("/")[:-1]) if remote_path.rstrip("/").count("/") else ""
            # index4.html
            ok1 = _upload_file(ftp, index4, f"{remote_path}/index4.html")
            if parent:
                _upload_file(ftp, index4, f"{parent}/index4.html")
            # data/menu4.json
            _upload_file(ftp, menu4, f"{remote_path}/data/menu4.json")
            if parent:
                _upload_file(ftp, menu4, f"{parent}/data/menu4.json")
            # events so "Could not load events" is fixed (path-aware: pathBase + next/events.json, events.json, data/events.json)
            if events_root.is_file():
                _upload_file(ftp, events_root, f"{remote_path}/events.json")
                if parent:
                    _upload_file(ftp, events_root, f"{parent}/events.json")
            if events_next.is_file():
                _upload_file(ftp, events_next, f"{remote_path}/next/events.json")
                if parent:
                    _upload_file(ftp, events_next, f"{parent}/next/events.json")
            if events_data.is_file():
                _upload_file(ftp, events_data, f"{remote_path}/data/events.json")
                if parent:
                    _upload_file(ftp, events_data, f"{parent}/data/events.json")
            # favicon (relative link in index4)
            if favicon.is_file():
                _upload_file(ftp, favicon, f"{remote_path}/favicon.ico")
                if parent:
                    _upload_file(ftp, favicon, f"{parent}/favicon.ico")
            # next/_next so CSS next/_next/static/chunks/cd9d6741b3ff3a25.css works from root
            if next_next.is_dir() and parent:
                n = _upload_tree(ftp, next_next, f"{parent}/next/_next")
                print(f"  -> {n} files under {parent}/next/_next/")
            if ok1:
                print("\nDeploy complete. index4, menu, events, favicon, next/_next at root and findevents.")
            else:
                raise SystemExit(1)
    except Exception as e:
        print(f"Deploy failed: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
