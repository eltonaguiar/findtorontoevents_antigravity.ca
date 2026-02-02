#!/usr/bin/env python3
"""
Deploy Stats page and Events API to FTP.

Uploads:
  - /api/events/ (PHP endpoints for events database)
  - /stats/ (statistics page)

Uses environment variables:
  FTP_SERVER  (or FTP_HOST) - FTP hostname
  FTP_USER    - FTP username
  FTP_PASS    - FTP password
  FTP_REMOTE_PATH         - Remote path (default: findtorontoevents.ca/findevents)

Run from project root:
  set FTP_SERVER=... FTP_USER=... FTP_PASS=...
  python tools/deploy_stats_and_events_api.py

After deploy:
  1. Visit https://findtorontoevents.ca/api/events/setup_tables.php to create database tables
  2. Visit https://findtorontoevents.ca/api/events/sync_events.php to sync events from events.json
  3. Visit https://findtorontoevents.ca/stats/ to see the stats page
"""
import os
import ftplib
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent

# Default remote path
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


def deploy_events_api(ftp: ftplib.FTP, remote_base: str) -> bool:
    """Upload api/events/ to /fc/events-api/ (where PHP is known to work)"""
    local_api = WORKSPACE / "api" / "events"
    if not local_api.is_dir():
        print("  Skip Events API (api/events not found)")
        return False
    
    # Deploy to /fc/events-api/ where PHP is confirmed working
    remotes = [
        "findtorontoevents.ca/fc/events-api",
        "fc/events-api",
    ]
    if remote_base:
        remotes.append(f"{remote_base}/fc/events-api")
    
    for remote in remotes:
        print(f"  Uploading Events API to {remote}/ ...")
        n = _upload_tree(ftp, local_api, remote)
        print(f"    -> {n} files")
    return True


def deploy_stats_page(ftp: ftplib.FTP, remote_base: str) -> bool:
    """Upload stats/ to remote_base/stats/"""
    local_stats = WORKSPACE / "stats"
    if not local_stats.is_dir():
        print("  Skip Stats page (stats/ not found)")
        return False
    
    remotes = [
        f"{remote_base}/stats",
        "findtorontoevents.ca/stats",
    ]
    
    for remote in remotes:
        print(f"  Uploading Stats page to {remote}/ ...")
        n = _upload_tree(ftp, local_stats, remote)
        print(f"    -> {n} files")
    return True


def main() -> None:
    host = _env("FTP_SERVER") or _env("FTP_HOST")
    user = _env("FTP_USER")
    password = _env("FTP_PASS")
    remote_path = _env("FTP_REMOTE_PATH") or DEFAULT_REMOTE_PATH

    if not host or not user or not password:
        print("Set FTP_SERVER (or FTP_HOST), FTP_USER, FTP_PASS in environment.")
        raise SystemExit(1)

    # Parent root for deploying to domain root as well
    parent_root = ""
    if remote_path.rstrip("/").count("/") >= 1:
        parent_root = "/".join(remote_path.rstrip("/").split("/")[:-1])

    print(f"Deploy Stats & Events API to FTP: {host}")
    print(f"Remote path: {remote_path}")
    if parent_root:
        print(f"Also deploy to root: {parent_root}/")
    print()

    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user, password)
            print("Connected.\n")

            print("=== Deploying Events API ===")
            deploy_events_api(ftp, remote_path)
            if parent_root:
                deploy_events_api(ftp, parent_root)
            print()

            print("=== Deploying Stats Page ===")
            deploy_stats_page(ftp, remote_path)
            if parent_root:
                deploy_stats_page(ftp, parent_root)
            print()

        print("=" * 50)
        print("Deploy complete!")
        print()
        print("Next steps:")
        print("1. Setup database tables:")
        print("   https://findtorontoevents.ca/fc/events-api/setup_tables.php")
        print()
        print("2. Sync events from events.json:")
        print("   https://findtorontoevents.ca/fc/events-api/sync_events.php")
        print()
        print("3. View stats page:")
        print("   https://findtorontoevents.ca/stats/")
        print()
        print("4. Check API status:")
        print("   https://findtorontoevents.ca/fc/events-api/status.php")

    except Exception as e:
        print(f"Deploy failed: {e}")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
