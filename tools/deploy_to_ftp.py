#!/usr/bin/env python3
"""
Deploy Toronto Events + FavCreators to FTP (full set — no partial deploy).

Uploads to FTP_REMOTE_PATH: index.html, .htaccess, events.json, next/events.json,
next/_next/ (entire tree); then FavCreators to /fc/. See DEPLOYMENT_NOTES.md for
dependency-check and verify-after-deploy rules.

Uses environment variables:
  FTP_SERVER  (or FTP_HOST) - FTP hostname
  FTP_USER    - FTP username
  FTP_PASS    - FTP password
  FTP_REMOTE_PATH         - Remote path (default: findtorontoevents.ca/findevents)

Run from project root:
  set FTP_SERVER=... FTP_USER=... FTP_PASS=...
  python tools/deploy_to_ftp.py

After deploy: run npm run verify:remote.
"""
import os
import ftplib
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent

# Load workspace .env so FTP_* are set when not in shell (e.g. Cursor run)
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

# Default remote path (site under findevents subfolder)
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


def deploy_main_site(ftp: ftplib.FTP, remote_base: str) -> bool:
    """Upload index.html, .htaccess, events.json, next/_next/ to remote_base."""
    ok = True
    # index.html
    idx = WORKSPACE / "index.html"
    if idx.is_file():
        if _upload_file(ftp, idx, f"{remote_base}/index.html"):
            pass
        else:
            ok = False
    else:
        print(f"  Skip index.html (not found)")
    # .htaccess
    ht = WORKSPACE / ".htaccess"
    if ht.is_file():
        _upload_file(ftp, ht, f"{remote_base}/.htaccess")
    # events.json
    ev = WORKSPACE / "events.json"
    if ev.is_file():
        _upload_file(ftp, ev, f"{remote_base}/events.json")
    ev_next = WORKSPACE / "next" / "events.json"
    if ev_next.is_file():
        _upload_file(ftp, ev_next, f"{remote_base}/next/events.json")
    # last_update.json (stats page: last updated time + source)
    lu = WORKSPACE / "last_update.json"
    if lu.is_file():
        _upload_file(ftp, lu, f"{remote_base}/last_update.json")
    # next/_next/
    next_next = WORKSPACE / "next" / "_next"
    if next_next.is_dir():
        n = _upload_tree(ftp, next_next, f"{remote_base}/next/_next")
        print(f"  -> {n} files under next/_next/")
    else:
        print(f"  Skip next/_next (not found at {next_next})")
    return ok


def deploy_favcreators(ftp: ftplib.FTP, main_remote_base: str = "") -> bool:
    """Upload favcreators/docs as /fc/ (avoids 500 on host for /favcreators/). admin/admin in api/login.php."""
    local_docs = WORKSPACE / "favcreators" / "docs"
    if not local_docs.is_dir():
        print("  Skip FavCreators (favcreators/docs not found)")
        return True
    # Deploy to /fc/ only (path "fc" avoids host 500 that /favcreators/ triggers)
    remotes = [
        "findtorontoevents.ca/fc",
        "fc",
    ]
    if main_remote_base:
        remotes.extend([f"{main_remote_base}/fc"])
    for remote in remotes:
        print(f"  Uploading FavCreators to {remote}/ ...")
        n = _upload_tree(ftp, local_docs, remote)
        print(f"    -> {n} files")
    return True


def deploy_favcreators_api(ftp: ftplib.FTP, main_remote_base: str = "") -> bool:
    """Upload favcreators/public/api/ to fc/api/ (PHP + .env.example + initial_creators.json). Tables are auto-created via ensure_tables.php."""
    local_api = WORKSPACE / "favcreators" / "public" / "api"
    if not local_api.is_dir():
        print("  Skip FavCreators API (favcreators/public/api not found)")
        return True
    remotes = [
        "findtorontoevents.ca/fc/api",
        "fc/api",
    ]
    if main_remote_base:
        remotes.extend([f"{main_remote_base}/fc/api"])
    for remote in remotes:
        print(f"  Uploading FavCreators API to {remote}/ ...")
        n = _upload_tree(ftp, local_api, remote)
        print(f"    -> {n} files")
    return True


def deploy_events_api(ftp: ftplib.FTP, main_remote_base: str = "") -> bool:
    """Upload api/events/ to /fc/events-api/ (PHP endpoints for events database)."""
    local_api = WORKSPACE / "api" / "events"
    if not local_api.is_dir():
        print("  Skip Events API (api/events not found)")
        return True
    # Deploy to /fc/events-api/ where PHP is confirmed working
    remotes = [
        "findtorontoevents.ca/fc/events-api",
        "fc/events-api",
    ]
    if main_remote_base:
        remotes.extend([f"{main_remote_base}/fc/events-api"])
    for remote in remotes:
        print(f"  Uploading Events API to {remote}/ ...")
        n = _upload_tree(ftp, local_api, remote)
        print(f"    -> {n} files")
    return True


def deploy_api_auth(ftp: ftplib.FTP, main_remote_base: str = "") -> bool:
    """Upload api/ (google_auth, google_callback, auth_db_config, .htaccess) to /api/ for main-site login."""
    auth_files = [
        "google_auth.php",
        "google_callback.php",
        "auth_db_config.php",
        ".htaccess",
    ]
    remotes = [
        "findtorontoevents.ca/api",
        "api",
    ]
    if main_remote_base:
        remotes.extend([f"{main_remote_base}/api"])
    for remote in remotes:
        print(f"  Uploading API auth to {remote}/ ...")
        ftp.cwd("/")
        _ensure_dir(ftp, remote)
        for name in auth_files:
            local_path = WORKSPACE / "api" / name
            if local_path.is_file():
                _upload_file(ftp, local_path, f"{remote}/{name}")
    return True


def deploy_stats_page(ftp: ftplib.FTP, main_remote_base: str = "") -> bool:
    """Upload stats/ to /stats/ (statistics page)."""
    local_stats = WORKSPACE / "stats"
    if not local_stats.is_dir():
        print("  Skip Stats page (stats/ not found)")
        return True
    remotes = [
        "findtorontoevents.ca/stats",
        "stats",
    ]
    if main_remote_base:
        remotes.extend([f"{main_remote_base}/stats"])
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

    # If remote_path is e.g. findtorontoevents.ca/findevents, also deploy to root (findtorontoevents.ca)
    # so https://findtorontoevents.ca/ serves the updated site, not just /findevents/
    parent_root = ""
    if remote_path.rstrip("/").count("/") >= 1:
        parent_root = "/".join(remote_path.rstrip("/").split("/")[:-1])

    print(f"Deploy to FTP: {host}")
    print(f"Remote path: {remote_path}")
    if parent_root:
        print(f"Also deploy to root: {parent_root}/ (so site is live at domain root)")
    print()

    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user, password)
            print("Connected.\n")

            print(f"Uploading main site to {remote_path}/ ...")
            deploy_main_site(ftp, remote_path)
            if parent_root:
                print(f"Uploading main site to {parent_root}/ (domain root) ...")
                deploy_main_site(ftp, parent_root)
            print()

            print("Uploading FavCreators to /fc/ (guest + admin/admin) ...")
            deploy_favcreators(ftp, remote_path)
            print()

            print("Uploading FavCreators API to /fc/api/ (PHP, ensure_tables, seed) ...")
            deploy_favcreators_api(ftp, remote_path)
            print()

            print("Uploading API auth to /api/ (Google login for main site) ...")
            deploy_api_auth(ftp, parent_root or remote_path)
            print()

            print("Uploading Events API to /api/events/ (PHP endpoints for events DB) ...")
            deploy_events_api(ftp, remote_path)
            print()

            print("Uploading Stats page to /stats/ ...")
            deploy_stats_page(ftp, remote_path)
            print()

        print("Deploy complete.")
        print()
        print("Post-deploy steps for Events API:")
        print("  1. Setup tables: https://findtorontoevents.ca/fc/events-api/setup_tables.php")
        print("  2. Sync events: https://findtorontoevents.ca/fc/events-api/sync_events.php")
        print("  3. View stats: https://findtorontoevents.ca/stats/")
    except Exception as e:
        print(f"Deploy failed: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
