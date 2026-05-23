#!/usr/bin/env python3
"""
Deploy ads.txt, updated index.html (with direct AdSense tag), adsense-integration.js,
and fixed JS chunks to torontoevent.net.
"""
import ftplib
import io
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = SCRIPT_DIR.parent
SITE_ROOT = WORKSPACE / "tmp" / "fte_clone"

TARGET_DOMAIN = "torontoevent.net"
SOURCE_DOMAIN = "findtorontoevents.ca"
FTP_PATH = "torontoevent.net"


def load_env():
    env_file = WORKSPACE / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if k and not os.environ.get(k):
                    os.environ[k] = v
    if "FTP_SERVER" not in os.environ and os.environ.get("FTP_HOST"):
        os.environ["FTP_SERVER"] = os.environ["FTP_HOST"]


def rewrite(content):
    replacements = [
        ("https://www." + SOURCE_DOMAIN, "https://www." + TARGET_DOMAIN),
        ("http://www." + SOURCE_DOMAIN, "http://www." + TARGET_DOMAIN),
        ("https://" + SOURCE_DOMAIN, "https://" + TARGET_DOMAIN),
        ("http://" + SOURCE_DOMAIN, "http://" + TARGET_DOMAIN),
        ("'" + SOURCE_DOMAIN + "'", "'" + TARGET_DOMAIN + "'"),
        ('"' + SOURCE_DOMAIN + '"', '"' + TARGET_DOMAIN + '"'),
        (SOURCE_DOMAIN, TARGET_DOMAIN),
    ]
    for old, new in replacements:
        content = content.replace(old, new)
    return content


def ensure_ftp_dir(ftp, path):
    parts = path.strip("/").split("/")
    ftp.cwd("/")
    for p in parts:
        if not p:
            continue
        try:
            ftp.cwd(p)
        except ftplib.error_perm:
            try:
                ftp.mkd(p)
                ftp.cwd(p)
            except:
                pass


def upload_text(ftp, content, remote_path):
    parts = remote_path.rsplit("/", 1)
    if len(parts) == 2:
        ensure_ftp_dir(ftp, FTP_PATH + "/" + parts[0])
    else:
        ftp.cwd("/" + FTP_PATH)

    filename = parts[-1] if len(parts) == 2 else remote_path
    data = content.encode("utf-8")
    ftp.storbinary("STOR " + filename, io.BytesIO(data))
    print(f"  Uploaded {remote_path} ({len(data):,} bytes)")


def main():
    load_env()
    host = os.environ.get("FTP_SERVER", "").strip()
    user = os.environ.get("FTP_USER", "").strip()
    pw = os.environ.get("FTP_PASS", "").strip()

    if not all([host, user, pw]):
        print("ERROR: FTP_SERVER, FTP_USER, FTP_PASS must be set")
        sys.exit(1)

    # Files to deploy
    deploy_files = {
        # (local_path, remote_path, needs_rewrite)
        "ads.txt": (SITE_ROOT / "ads.txt", "ads.txt", False),
        "index.html": (SITE_ROOT / "index.html", "index.html", True),
        "adsense-integration.js": (SITE_ROOT / "adsense-integration.js", "adsense-integration.js", False),
    }

    # JS chunks that got the supercomputer text fix
    chunk_files = [
        "next/_next/static/chunks/afe53b3593ec888c.js",
        "next/_next/static/chunks/a2ec946db99436f9.js",
        "next/_next/static/chunks/8754972ee54e9a76.js",
        "next/_next/static/chunks/60a85cefa5d61d43.js",
        "next/static/chunks/8754972ee54e9a76.js",
        "next/static/chunks/60a85cefa5d61d43.js",
    ]

    # Also add _next/ paths (without next/ prefix)
    alt_chunks = [
        "_next/static/chunks/afe53b3593ec888c.js",
        "_next/static/chunks/a2ec946db99436f9.js",
        "_next/static/chunks/8754972ee54e9a76.js",
        "_next/static/chunks/60a85cefa5d61d43.js",
    ]

    for chunk in chunk_files:
        local = SITE_ROOT / chunk.replace("/", os.sep)
        if local.exists():
            deploy_files[chunk] = (local, chunk, True)

    for chunk in alt_chunks:
        # Map _next/ to the next/_next/ source
        src_chunk = "next/" + chunk
        local = SITE_ROOT / src_chunk.replace("/", os.sep)
        if local.exists():
            deploy_files[chunk] = (local, chunk, True)

    print(f"Deploying {len(deploy_files)} files to {TARGET_DOMAIN}...")
    print()

    # Connect
    print(f"Connecting to {host}...")
    ftp = ftplib.FTP(host, timeout=60)
    ftp.login(user, pw)
    print("Connected.\n")

    for name, (local_path, remote_path, needs_rewrite) in deploy_files.items():
        if not local_path.exists():
            print(f"  SKIP (not found): {name}")
            continue
        content = local_path.read_text(encoding="utf-8", errors="ignore")
        if needs_rewrite:
            content = rewrite(content)
        upload_text(ftp, content, remote_path)

    ftp.quit()

    print(f"\nDone! {len(deploy_files)} files deployed to {TARGET_DOMAIN}")
    print(f"\nVerify:")
    print(f"  https://{TARGET_DOMAIN}/ads.txt")
    print(f"  https://{TARGET_DOMAIN}/")
    print(f"  Text fix: 'without a supercomputer' should appear on the site")


if __name__ == "__main__":
    main()
