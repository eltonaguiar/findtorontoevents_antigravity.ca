#!/usr/bin/env python3
"""
Deploy Toronto Events to tdotevent.ca (mirror site with updated domain links).

This script:
1. Copies all files that would be deployed to findtorontoevents.ca
2. Replaces all references of findtorontoevents.ca with tdotevent.ca in HTML/JS files
3. Uploads to FTP path /tdotevent.ca

Uses environment variables:
  FTP_SERVER  (or FTP_HOST) - FTP hostname
  FTP_USER    - FTP username
  FTP_PASS    - FTP password

Run from project root:
  set FTP_SERVER=... FTP_USER=... FTP_PASS=...
  python tools/deploy_to_tdotevent.py
"""
import os
import ftplib
import tempfile
import shutil
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent

# Load workspace .env so FTP_* are set when not in shell
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

# Remote path for tdotevent.ca
REMOTE_PATH = "tdotevent.ca"

# Domain replacements
REPLACEMENTS = [
    ("findtorontoevents.ca", "tdotevent.ca"),
    ("www.findtorontoevents.ca", "www.tdotevent.ca"),
    ("support@findtorontoevents.ca", "support@tdotevent.ca"),
]

# File extensions that should have domain replacements
TEXT_EXTENSIONS = {".html", ".htm", ".js", ".css", ".json", ".php", ".txt", ".md"}


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


def replace_domains(content: str) -> str:
    """Replace all findtorontoevents.ca references with tdotevent.ca."""
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)
    return content


def process_file(src_path: Path, dst_path: Path) -> None:
    """Copy file, replacing domain references if it's a text file."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    
    if src_path.suffix.lower() in TEXT_EXTENSIONS:
        try:
            content = src_path.read_text(encoding="utf-8", errors="replace")
            content = replace_domains(content)
            dst_path.write_text(content, encoding="utf-8")
        except Exception as e:
            # If text processing fails, copy as binary
            print(f"  Warning: Text processing failed for {src_path.name}, copying as binary: {e}")
            shutil.copy2(src_path, dst_path)
    else:
        shutil.copy2(src_path, dst_path)


def prepare_deploy_folder(temp_dir: Path) -> None:
    """Prepare all files with domain replacements in a temp folder."""
    print("Preparing files with domain replacements...")
    
    # Directories to deploy
    dirs_to_copy = [
        ("next/_next", "next/_next"),
        ("favcreators/docs", "fc"),
        ("favcreators/public/api", "fc/api"),
        ("api/events", "fc/events-api"),
        ("api", "api"),
        ("stats", "stats"),
        ("WINDOWSFIXER", "WINDOWSFIXER"),
        ("MENTALHEALTHRESOURCES", "MENTALHEALTHRESOURCES"),
        ("MOVIESHOWS", "MOVIESHOWS"),
        ("findstocks", "findstocks"),
        ("2xko", "2xko"),
    ]
    
    # Single files to copy
    files_to_copy = [
        ("index.html", "index.html"),
        (".htaccess", ".htaccess"),
        ("events.json", "events.json"),
        ("events.json", "next/events.json"),
        ("last_update.json", "last_update.json"),
        ("favicon.ico", "favicon.ico"),
    ]
    
    # Copy directories
    for src_rel, dst_rel in dirs_to_copy:
        src_dir = WORKSPACE / src_rel
        if not src_dir.is_dir():
            print(f"  Skip {src_rel} (not found)")
            continue
        
        print(f"  Processing {src_rel} -> {dst_rel}")
        for root, dirs, files in os.walk(src_dir):
            for name in files:
                src_path = Path(root) / name
                rel_path = src_path.relative_to(src_dir)
                dst_path = temp_dir / dst_rel / rel_path
                process_file(src_path, dst_path)
    
    # Copy single files
    for src_rel, dst_rel in files_to_copy:
        src_path = WORKSPACE / src_rel
        if not src_path.is_file():
            print(f"  Skip {src_rel} (not found)")
            continue
        
        print(f"  Processing {src_rel} -> {dst_rel}")
        dst_path = temp_dir / dst_rel
        process_file(src_path, dst_path)


def _upload_tree(ftp: ftplib.FTP, local_dir: Path, remote_base: str) -> int:
    """Upload entire directory tree to FTP."""
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


def main() -> None:
    host = _env("FTP_SERVER") or _env("FTP_HOST")
    user = _env("FTP_USER")
    password = _env("FTP_PASS")

    if not host or not user or not password:
        print("Set FTP_SERVER (or FTP_HOST), FTP_USER, FTP_PASS in environment.")
        raise SystemExit(1)

    print(f"Deploy to tdotevent.ca via FTP: {host}")
    print(f"Remote path: /{REMOTE_PATH}")
    print()
    print("Domain replacements:")
    for old, new in REPLACEMENTS:
        print(f"  {old} -> {new}")
    print()

    # Create temp directory for processed files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Prepare all files with domain replacements
        prepare_deploy_folder(temp_path)
        print()
        
        # Count prepared files
        file_count = sum(1 for _ in temp_path.rglob("*") if _.is_file())
        print(f"Prepared {file_count} files for upload.")
        print()
        
        # Upload to FTP
        try:
            with ftplib.FTP(host) as ftp:
                ftp.login(user, password)
                print("Connected to FTP.\n")
                
                print(f"Uploading to /{REMOTE_PATH}/ ...")
                n = _upload_tree(ftp, temp_path, REMOTE_PATH)
                print(f"\n-> Uploaded {n} files to /{REMOTE_PATH}/")
            
            print()
            print("=" * 60)
            print("Deploy complete!")
            print("=" * 60)
            print()
            print("Your site is now available at: https://tdotevent.ca/")
            print()
            print("Post-deploy verification:")
            print("  1. Visit https://tdotevent.ca/ - main events page")
            print("  2. Visit https://tdotevent.ca/fc/#/guest - FavCreators")
            print("  3. Visit https://tdotevent.ca/WINDOWSFIXER/ - Windows Fixer")
            print("  4. Visit https://tdotevent.ca/MOVIESHOWS/ - Movie Shows")
            print()
            print("Setup database tables (if needed):")
            print("  https://tdotevent.ca/fc/events-api/setup_tables.php")
            
        except Exception as e:
            print(f"Deploy failed: {e}")
            raise SystemExit(1)


if __name__ == "__main__":
    main()
