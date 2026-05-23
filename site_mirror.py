"""
site_mirror.py - Mirror findtorontoevents.ca to two backup/mirror destinations.

PURPOSE:
    Downloads all files from the 50webs FTPS server (/findtorontoevents.ca)
    to a local temp directory, then uploads to:
      1. tdotevent.ca     - same 50webs FTPS account, file backup
      2. torontoevent.net - GoDaddy plain FTP, live mirror site

USAGE:
    python site_mirror.py [options]

OPTIONS:
    --skip-tdot      Skip upload to tdotevent.ca (50webs backup)
    --skip-godaddy   Skip upload to torontoevent.net (GoDaddy mirror)
    --dry-run        List files from source only, do not download or upload

EXCLUDED FILES/PATHS (never downloaded or uploaded):
    - db_config.php (any directory)
    - .env files (any .env or .env.*)
    - .htpasswd
    - _dbex_*.php (temp DB export scripts)
    - _backup_runner_tmp.php
    - db_backups/ directory

COMPARISON STRATEGY:
    Files are uploaded to a destination only if:
    - The file does not exist on the destination, OR
    - The file size on the destination differs from the local (source) copy

CREDENTIALS:
    Source (50webs FTPS):
        Host: ftps2.50webs.com  Port: 21 (explicit TLS)
        User: ejaguiar1
        Remote path: /findtorontoevents.ca

    Destination 1 (tdotevent.ca, same 50webs FTPS):
        Reuses same FTPS connection
        Remote path: /tdotevent.ca

    Destination 2 (torontoevent.net, GoDaddy plain FTP):
        Host: torontoevent.net  Port: 21
        User: elton@torontoevent.net
        Remote path: / (root)
"""

import sys
import os
import ftplib
import argparse
import tempfile
import shutil
import fnmatch
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Credentials & configuration
# ---------------------------------------------------------------------------

SOURCE_HOST = "ftps2.50webs.com"
SOURCE_PORT = 21
SOURCE_USER = "ejaguiar1"
SOURCE_PASS = os.environ.get("FTPGODADDYPASS", "")
SOURCE_REMOTE_PATH = "/findtorontoevents.ca"

TDOT_REMOTE_PATH = "/tdotevent.ca"  # same 50webs FTPS connection

GODADDY_HOST = "torontoevent.net"
GODADDY_PORT = 21
GODADDY_USER = "elton@torontoevent.net"
GODADDY_PASS = os.environ.get("FTPGODADDYPASS", "")
GODADDY_REMOTE_PATH = "/"

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds between retries

# ---------------------------------------------------------------------------
# Exclusion rules
# ---------------------------------------------------------------------------

# Exact filenames to exclude (case-sensitive, checked against basename)
EXCLUDED_FILENAMES = {
    "db_config.php",
    ".htpasswd",
    "_backup_runner_tmp.php",
}

# Glob patterns matched against basename
EXCLUDED_PATTERNS = [
    "_dbex_*.php",
    ".env",
    ".env.*",
]

# Directory names to exclude entirely (matched against any path component)
EXCLUDED_DIRS = {
    "db_backups",
}


def is_excluded(remote_path: str) -> bool:
    """
    Return True if the given remote path should be excluded from
    download/upload based on filename, glob pattern, or directory rules.

    remote_path is relative to the source root (e.g. 'subdir/db_config.php').
    """
    parts = Path(remote_path.replace("\\", "/")).parts

    # Check if any directory component is in the excluded dirs set
    for part in parts[:-1]:  # all but the last (filename) component
        if part in EXCLUDED_DIRS:
            return True

    # Also check if the path itself IS an excluded directory
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True

    basename = parts[-1] if parts else remote_path

    # Exact filename match
    if basename in EXCLUDED_FILENAMES:
        return True

    # Glob pattern match
    for pattern in EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(basename, pattern):
            return True

    return False


# ---------------------------------------------------------------------------
# FTP helpers
# ---------------------------------------------------------------------------

def make_ftps_connection() -> ftplib.FTP_TLS:
    """Create and return an authenticated FTPS (explicit TLS) connection."""
    ftp = ftplib.FTP_TLS()
    ftp.connect(SOURCE_HOST, SOURCE_PORT, timeout=30)
    ftp.login(SOURCE_USER, SOURCE_PASS)
    ftp.prot_p()   # switch to secure data connection
    return ftp


def make_ftp_connection() -> ftplib.FTP:
    """Create and return an authenticated plain FTP connection to GoDaddy."""
    ftp = ftplib.FTP()
    ftp.connect(GODADDY_HOST, GODADDY_PORT, timeout=30)
    ftp.login(GODADDY_USER, GODADDY_PASS)
    return ftp


def ftp_mlsd_or_list(ftp, remote_dir: str):
    """
    List directory contents using MLSD if available, otherwise fall back to
    LIST parsing.

    Returns a list of (name, facts) tuples where facts is a dict with at
    least 'type' ('file' or 'dir') and 'size' (str, bytes) when available.
    """
    try:
        entries = list(ftp.mlsd(remote_dir, facts=["type", "size", "modify"]))
        return entries
    except (ftplib.error_perm, ftplib.error_proto, AttributeError):
        pass

    # Fallback: parse raw LIST output
    raw_lines = []
    ftp.retrlines(f"LIST {remote_dir}", raw_lines.append)
    entries = []
    for line in raw_lines:
        parts = line.split(None, 8)
        if len(parts) < 9:
            continue
        name = parts[8].strip()
        if name in (".", ".."):
            continue
        is_dir = line.startswith("d")
        facts = {
            "type": "dir" if is_dir else "file",
            "size": parts[4] if not is_dir else "0",
        }
        entries.append((name, facts))
    return entries


def ftp_walk(ftp, remote_dir: str):
    """
    Recursively walk an FTP directory tree.

    Yields (remote_dir, [subdirs], [(filename, size_bytes)]) similar to
    os.walk.  remote_dir paths are absolute on the server.
    """
    entries = ftp_mlsd_or_list(ftp, remote_dir)
    dirs = []
    files = []
    for name, facts in entries:
        if name in (".", ".."):
            continue
        entry_type = facts.get("type", "file").lower()
        if entry_type in ("dir", "cdir", "pdir"):
            dirs.append(name)
        else:
            try:
                size = int(facts.get("size", 0))
            except (ValueError, TypeError):
                size = 0
            files.append((name, size))

    yield remote_dir, dirs, files

    for subdir in dirs:
        subpath = remote_dir.rstrip("/") + "/" + subdir
        yield from ftp_walk(ftp, subpath)


def get_remote_sizes(ftp, remote_dir: str) -> dict:
    """
    Walk remote_dir and return a dict mapping relative path -> size (bytes).
    Only files are included; directories are omitted.
    """
    sizes = {}
    base = remote_dir.rstrip("/")
    for dirpath, subdirs, files in ftp_walk(ftp, remote_dir):
        rel_dir = dirpath[len(base):].lstrip("/")
        for fname, fsize in files:
            rel_path = (rel_dir + "/" + fname).lstrip("/") if rel_dir else fname
            sizes[rel_path] = fsize
    return sizes


def ensure_remote_dir(ftp, remote_path: str):
    """
    Ensure all components of remote_path exist on the FTP server,
    creating missing directories as needed.
    """
    parts = [p for p in remote_path.replace("\\", "/").split("/") if p]
    current = ""
    for part in parts:
        current = current + "/" + part
        try:
            ftp.cwd(current)
        except ftplib.error_perm:
            try:
                ftp.mkd(current)
            except ftplib.error_perm:
                pass  # may already exist due to race or permission quirk


def upload_file_with_retry(ftp, local_path: str, remote_path: str, retries: int = MAX_RETRIES):
    """
    Upload a single file to the FTP server with retry logic.
    Returns True on success, False on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
            return True
        except (ftplib.Error, OSError, EOFError) as exc:
            if attempt < retries:
                print(f"  ⚠️  Upload attempt {attempt} failed ({exc}), retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  ❌ Upload failed after {retries} attempts: {exc}")
    return False


def download_file_with_retry(ftp, remote_path: str, local_path: str, retries: int = MAX_RETRIES):
    """
    Download a single file from the FTP server with retry logic.
    Returns True on success, False on failure.
    """
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            with open(local_path, "wb") as f:
                ftp.retrbinary(f"RETR {remote_path}", f.write)
            return True
        except (ftplib.Error, OSError, EOFError) as exc:
            if attempt < retries:
                print(f"  ⚠️  Download attempt {attempt} failed ({exc}), retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  ❌ Download failed after {retries} attempts: {exc}")
    return False


# ---------------------------------------------------------------------------
# Core mirror logic
# ---------------------------------------------------------------------------

def collect_source_files(ftp, source_remote: str) -> list:
    """
    Walk the source remote directory and return a list of dicts:
        {
            'rel_path': str,   # relative path from source root, e.g. 'subdir/file.php'
            'remote':   str,   # full remote path on source server
            'size':     int,   # file size in bytes
        }

    Excludes any paths matching the exclusion rules.
    """
    files = []
    base = source_remote.rstrip("/")
    print(f"\n📂 Scanning source: {source_remote}")

    for dirpath, subdirs, dir_files in ftp_walk(ftp, source_remote):
        # Filter out excluded subdirectory names in-place so ftp_walk won't
        # descend into them (note: ftp_walk already yields them; we just skip)
        rel_dir = dirpath[len(base):].lstrip("/")

        for fname, fsize in dir_files:
            rel_path = (rel_dir + "/" + fname).lstrip("/") if rel_dir else fname

            if is_excluded(rel_path):
                print(f"  ⚠️  EXCLUDED: {rel_path}")
                continue

            files.append({
                "rel_path": rel_path,
                "remote": base + "/" + rel_path,
                "size": fsize,
            })

    return files


def download_all(ftp, source_files: list, temp_dir: str) -> tuple:
    """
    Download all source files to temp_dir.

    Returns (downloaded, failed) lists of rel_path strings.
    """
    downloaded = []
    failed = []
    total = len(source_files)

    print(f"\n⬇️  Downloading {total} files from source...")

    for i, finfo in enumerate(source_files, 1):
        rel = finfo["rel_path"]
        remote = finfo["remote"]
        local = os.path.join(temp_dir, rel.replace("/", os.sep))
        size_kb = finfo["size"] / 1024

        print(f"  [{i}/{total}] {rel} ({size_kb:.1f} KB)", end="")

        ok = download_file_with_retry(ftp, remote, local)
        if ok:
            print(f"  ✅")
            downloaded.append(rel)
        else:
            print(f"  ❌")
            failed.append(rel)

    return downloaded, failed


def upload_to_destination(
    ftp,
    dest_label: str,
    dest_remote_root: str,
    temp_dir: str,
    downloaded_files: list,
    source_files_map: dict,
) -> tuple:
    """
    Upload downloaded files to a destination FTP (already connected).

    dest_label:       human-readable name, e.g. 'tdotevent.ca'
    dest_remote_root: remote root path on destination, e.g. '/tdotevent.ca'
    temp_dir:         local staging directory
    downloaded_files: list of rel_path strings that were successfully downloaded
    source_files_map: dict mapping rel_path -> size (from source scan)

    Returns (uploaded, skipped, failed) counts.
    """
    print(f"\n⬆️  Uploading to {dest_label} ({dest_remote_root})...")

    # Build a map of existing remote file sizes for comparison
    print(f"  Scanning existing files on {dest_label}...")
    try:
        dest_sizes = get_remote_sizes(ftp, dest_remote_root)
    except Exception as exc:
        print(f"  ⚠️  Could not scan destination ({exc}), will upload all files.")
        dest_sizes = {}

    print(f"  Found {len(dest_sizes)} existing files on destination.")

    uploaded = 0
    skipped = 0
    failed = 0
    total = len(downloaded_files)

    for i, rel_path in enumerate(downloaded_files, 1):
        local = os.path.join(temp_dir, rel_path.replace("/", os.sep))
        remote = dest_remote_root.rstrip("/") + "/" + rel_path

        source_size = source_files_map.get(rel_path, -1)
        dest_size = dest_sizes.get(rel_path, None)

        # Decide whether to upload
        if dest_size is not None and dest_size == source_size:
            print(f"  [{i}/{total}] ⏭️  SKIP (same size {source_size}B): {rel_path}")
            skipped += 1
            continue

        reason = "new" if dest_size is None else f"size {dest_size}→{source_size}"
        print(f"  [{i}/{total}] {rel_path} ({reason})", end="")

        # Ensure parent directory exists on destination
        remote_dir = "/".join(remote.split("/")[:-1])
        if remote_dir:
            try:
                ensure_remote_dir(ftp, remote_dir)
            except Exception as exc:
                print(f"\n  ⚠️  Could not create dir {remote_dir}: {exc}")

        ok = upload_file_with_retry(ftp, local, remote)
        if ok:
            print(f"  ✅")
            uploaded += 1
        else:
            failed += 1

    return uploaded, skipped, failed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Mirror findtorontoevents.ca to tdotevent.ca and torontoevent.net"
    )
    parser.add_argument(
        "--skip-tdot",
        action="store_true",
        help="Skip upload to tdotevent.ca (50webs file backup)",
    )
    parser.add_argument(
        "--skip-godaddy",
        action="store_true",
        help="Skip upload to torontoevent.net (GoDaddy live mirror)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List source files only; do not download or upload anything",
    )
    return parser.parse_args()


def human_size(total_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if total_bytes < 1024:
            return f"{total_bytes:.1f} {unit}"
        total_bytes /= 1024
    return f"{total_bytes:.1f} TB"


def main():
    args = parse_args()

    print("=" * 60)
    print("  site_mirror.py — findtorontoevents.ca mirror script")
    print("=" * 60)
    if args.dry_run:
        print("  MODE: DRY RUN — no files will be downloaded or uploaded")
    if args.skip_tdot:
        print("  Skipping: tdotevent.ca")
    if args.skip_godaddy:
        print("  Skipping: torontoevent.net")
    print()

    temp_dir = None

    try:
        # ----------------------------------------------------------------
        # Connect to source (50webs FTPS)
        # ----------------------------------------------------------------
        print(f"🔌 Connecting to source FTPS: {SOURCE_HOST}...")
        ftps = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                ftps = make_ftps_connection()
                print(f"  ✅ Connected to {SOURCE_HOST} as {SOURCE_USER}")
                break
            except Exception as exc:
                print(f"  ❌ Connection attempt {attempt} failed: {exc}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                else:
                    print("  ❌ Could not connect to source. Aborting.")
                    sys.exit(1)

        # ----------------------------------------------------------------
        # Collect source file listing
        # ----------------------------------------------------------------
        source_files = collect_source_files(ftps, SOURCE_REMOTE_PATH)
        total_files = len(source_files)
        total_bytes = sum(f["size"] for f in source_files)
        source_files_map = {f["rel_path"]: f["size"] for f in source_files}

        print(f"\n📊 Source summary:")
        print(f"   Files found : {total_files}")
        print(f"   Total size  : {human_size(total_bytes)}")

        if args.dry_run:
            print("\n📋 File listing (dry run):")
            for f in source_files:
                print(f"  {f['rel_path']}  ({human_size(f['size'])})")
            print("\n✅ Dry run complete. No files downloaded or uploaded.")
            return

        if total_files == 0:
            print("\n⚠️  No files found on source. Nothing to do.")
            return

        # ----------------------------------------------------------------
        # Create temp directory for staging
        # ----------------------------------------------------------------
        temp_dir = tempfile.mkdtemp(prefix="site_mirror_")
        print(f"\n📁 Staging directory: {temp_dir}")

        # ----------------------------------------------------------------
        # Download from source
        # ----------------------------------------------------------------
        downloaded, dl_failed = download_all(ftps, source_files, temp_dir)
        print(f"\n📥 Download complete: {len(downloaded)} OK, {len(dl_failed)} failed")

        if dl_failed:
            print("  Failed downloads:")
            for p in dl_failed:
                print(f"    ❌ {p}")

        if not downloaded:
            print("⚠️  Nothing downloaded successfully. Aborting uploads.")
            return

        # ----------------------------------------------------------------
        # Upload to tdotevent.ca (reuse same FTPS connection)
        # ----------------------------------------------------------------
        tdot_uploaded = tdot_skipped = tdot_failed = 0
        if not args.skip_tdot:
            try:
                tdot_uploaded, tdot_skipped, tdot_failed = upload_to_destination(
                    ftp=ftps,
                    dest_label="tdotevent.ca",
                    dest_remote_root=TDOT_REMOTE_PATH,
                    temp_dir=temp_dir,
                    downloaded_files=downloaded,
                    source_files_map=source_files_map,
                )
            except Exception as exc:
                print(f"\n❌ tdotevent.ca upload error: {exc}")
        else:
            print("\n⏭️  Skipping tdotevent.ca upload (--skip-tdot)")

        # Done with 50webs FTPS
        try:
            ftps.quit()
        except Exception:
            pass

        # ----------------------------------------------------------------
        # Upload to torontoevent.net (GoDaddy plain FTP)
        # ----------------------------------------------------------------
        gd_uploaded = gd_skipped = gd_failed = 0
        if not args.skip_godaddy:
            print(f"\n🔌 Connecting to GoDaddy FTP: {GODADDY_HOST}...")
            ftp_gd = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    ftp_gd = make_ftp_connection()
                    print(f"  ✅ Connected to {GODADDY_HOST} as {GODADDY_USER}")
                    break
                except Exception as exc:
                    print(f"  ❌ Connection attempt {attempt} failed: {exc}")
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY)
                    else:
                        print("  ❌ Could not connect to GoDaddy. Skipping.")
                        ftp_gd = None

            if ftp_gd:
                try:
                    gd_uploaded, gd_skipped, gd_failed = upload_to_destination(
                        ftp=ftp_gd,
                        dest_label="torontoevent.net",
                        dest_remote_root=GODADDY_REMOTE_PATH,
                        temp_dir=temp_dir,
                        downloaded_files=downloaded,
                        source_files_map=source_files_map,
                    )
                except Exception as exc:
                    print(f"\n❌ torontoevent.net upload error: {exc}")
                finally:
                    try:
                        ftp_gd.quit()
                    except Exception:
                        pass
        else:
            print("\n⏭️  Skipping torontoevent.net upload (--skip-godaddy)")

        # ----------------------------------------------------------------
        # Final summary
        # ----------------------------------------------------------------
        print("\n" + "=" * 60)
        print("  MIRROR COMPLETE — Summary")
        print("=" * 60)
        print(f"  Source files scanned : {total_files} ({human_size(total_bytes)})")
        print(f"  Downloaded OK        : {len(downloaded)}")
        print(f"  Download failures    : {len(dl_failed)}")

        if not args.skip_tdot:
            print(f"\n  tdotevent.ca:")
            print(f"    ✅ Uploaded : {tdot_uploaded}")
            print(f"    ⏭️  Skipped  : {tdot_skipped}")
            print(f"    ❌ Failed   : {tdot_failed}")

        if not args.skip_godaddy:
            print(f"\n  torontoevent.net:")
            print(f"    ✅ Uploaded : {gd_uploaded}")
            print(f"    ⏭️  Skipped  : {gd_skipped}")
            print(f"    ❌ Failed   : {gd_failed}")

        print()

    finally:
        # Always clean up temp directory
        if temp_dir and os.path.exists(temp_dir):
            print(f"🧹 Cleaning up temp directory: {temp_dir}")
            try:
                shutil.rmtree(temp_dir)
                print("  ✅ Temp directory removed.")
            except Exception as exc:
                print(f"  ⚠️  Could not remove temp dir: {exc}")


if __name__ == "__main__":
    main()
