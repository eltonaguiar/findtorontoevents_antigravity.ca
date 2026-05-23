#!/usr/bin/env python3
"""Deploy index.html and updates/index.html to all 3 sites."""

import ftplib
from ftplib import FTP_TLS
import os
import sys
from io import BytesIO
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
SRC_DIR = WORKSPACE / "tmp" / "fte_clone"

# Files to deploy
FILES = [
    ("index.html", "/index.html"),
    ("updates/index.html", "/updates/index.html"),
]

# Read source files
sources = {}
for local_path, _ in FILES:
    full = SRC_DIR / local_path
    if full.exists():
        sources[local_path] = full.read_text(encoding="utf-8", errors="replace")
        print(f"Read {local_path}: {len(sources[local_path])} bytes")
    else:
        print(f"WARNING: {full} not found, skipping")

# Domain replacements for alt sites
REPLACEMENTS = {
    "torontoevent.net": [
        ("https://findtorontoevents.ca", "https://torontoevent.net"),
        ("https://www.findtorontoevents.ca", "https://www.torontoevent.net"),
        ("findtorontoevents.ca", "torontoevent.net"),
    ],
    "tdotevent.ca": [
        ("https://www.findtorontoevents.ca", "https://www.tdotevent.ca"),
        ("https://findtorontoevents.ca", "https://tdotevent.ca"),
        ("FindTorontoEvents.ca", "TdotEvent.ca"),
        ("findtorontoevents.ca", "tdotevent.ca"),
        ("FindTorontoEvents", "TdotEvent"),
    ],
}

def apply_replacements(content, domain):
    if domain not in REPLACEMENTS:
        return content
    result = content
    for old, new in REPLACEMENTS[domain]:
        result = result.replace(old, new)
    return result

def ensure_remote_dir(ftp, path):
    dirs = path.strip("/").split("/")
    current = ""
    for d in dirs:
        current += "/" + d
        try:
            ftp.cwd(current)
        except:
            try:
                ftp.mkd(current)
            except:
                pass

# ─── Site 1: findtorontoevents.ca (50webs) ───
print("\n" + "=" * 60)
print("Site 1: findtorontoevents.ca")
print("=" * 60)
FTP_SERVER = os.environ.get("FTP_SERVER", "").strip()
FTP_USER = os.environ.get("FTP_USER", "").strip()
FTP_PASS = os.environ.get("FTP_PASS", "").strip()

if FTP_SERVER and FTP_USER:
    try:
        ftp = ftplib.FTP(FTP_SERVER)
        ftp.login(FTP_USER, FTP_PASS)
        for local_path, remote_path in FILES:
            if local_path not in sources:
                continue
            full_remote = "/findtorontoevents.ca" + remote_path
            # Ensure directory exists
            remote_dir = "/".join(full_remote.split("/")[:-1])
            if remote_dir:
                ensure_remote_dir(ftp, remote_dir)
            data = sources[local_path].encode("utf-8")
            ftp.storbinary(f"STOR {full_remote}", BytesIO(data))
            print(f"  [OK] {full_remote} ({len(data)} bytes)")
        ftp.quit()
    except Exception as e:
        print(f"  [FAIL] {e}")
else:
    print("  [SKIP] FTP credentials not set")

# ─── Site 2: torontoevent.net (separate FTP) ───
print("\n" + "=" * 60)
print("Site 2: torontoevent.net")
print("=" * 60)
TEN_HOST = "torontoevent.net"
TEN_USER = "elton@torontoevent.net"
TEN_PASS = os.environ.get("FTPGODADDYPASS", "")

try:
    ftp = ftplib.FTP(TEN_HOST, TEN_USER, TEN_PASS)
    for local_path, remote_path in FILES:
        if local_path not in sources:
            continue
        content = apply_replacements(sources[local_path], "torontoevent.net")
        # Ensure directory
        remote_dir = "/".join(remote_path.strip("/").split("/")[:-1])
        if remote_dir:
            ensure_remote_dir(ftp, "/" + remote_dir)
        data = content.encode("utf-8")
        ftp.storbinary(f"STOR {remote_path}", BytesIO(data))
        print(f"  [OK] {remote_path} ({len(data)} bytes)")
    ftp.quit()
except Exception as e:
    print(f"  [FAIL] {e}")

# ─── Site 3: tdotevent.ca (50webs, FTP_TLS) ───
print("\n" + "=" * 60)
print("Site 3: tdotevent.ca")
print("=" * 60)

if FTP_SERVER and FTP_USER:
    try:
        ftp = FTP_TLS(FTP_SERVER)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        for local_path, remote_path in FILES:
            if local_path not in sources:
                continue
            content = apply_replacements(sources[local_path], "tdotevent.ca")
            full_remote = "/tdotevent.ca" + remote_path
            remote_dir = "/".join(full_remote.split("/")[:-1])
            if remote_dir:
                ensure_remote_dir(ftp, remote_dir)
            data = content.encode("utf-8")
            ftp.storbinary(f"STOR {full_remote}", BytesIO(data))
            print(f"  [OK] {full_remote} ({len(data)} bytes)")
        ftp.quit()
    except Exception as e:
        print(f"  [FAIL] {e}")
else:
    print("  [SKIP] FTP credentials not set")

print("\n" + "=" * 60)
print("Deployment complete!")
print("=" * 60)
print("\nVerify updates at:")
print("  https://findtorontoevents.ca/updates/")
print("  https://torontoevent.net/updates/")
print("  https://tdotevent.ca/updates/")
