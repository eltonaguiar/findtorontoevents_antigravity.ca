#!/usr/bin/env python3
"""
Deploy missing MOVIESHOWS2 files to restore the player.

Uploads the missing _next/static/chunks/ and JS/CSS files that were
deleted from the server, breaking the MOVIESHOWS2 TikTok-style player.
"""

import os
import sys
from ftplib import FTP_TLS

# FTP config from environment
FTP_HOST = os.environ.get("FTP_SERVER") or os.environ.get("FTP_HOST")
FTP_USER = os.environ.get("FTP_USER")
FTP_PASS = os.environ.get("FTP_PASS")

if not all([FTP_HOST, FTP_USER, FTP_PASS]):
    print("ERROR: Set FTP_SERVER, FTP_USER, FTP_PASS environment variables")
    sys.exit(1)

LOCAL_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "TORONTOEVENTS_ANTIGRAVITY", "MOVIESHOWS2")
REMOTE_BASE = "/findtorontoevents.ca/MOVIESHOWS2"

# Files to upload - missing _next chunks
MISSING_CHUNKS = [
    "_next/static/chunks/06ac42a4f7bb5dfe.js",
    "_next/static/chunks/23ac701119827ad0.css",
    "_next/static/chunks/37336930028db52b.js",
    "_next/static/chunks/3964ad713a720516.js",
    "_next/static/chunks/6c0be65d49b4a5a4.js",
    "_next/static/chunks/bedb993eab73d440.css",
    "_next/static/chunks/ceb732f8b66acbff.js",
    "_next/static/chunks/da42d1a8dab68e4b.js",
    "_next/static/chunks/turbopack-8ecb9a6e7f81c1a0.js",
]

# Missing root-level JS/CSS files
MISSING_ROOT_FILES = [
    "app.js",
    "script.js",
    "scroll-fix.js",
    "styles.css",
    "db-connector.js",
    "ui-cleanup.js",
    "ui-minimal.js",
    "features.js",
    "features-batch2.js",
    "features-batch3.js",
    "features-batch4.js",
    "features-batch5.js",
    "features-batch6.js",
    "features-batch7.js",
    "features-batch8.js",
    "features-batch9.js",
    "features-batch10.js",
    "features-batch11.js",
    "features-batch12.js",
    "features-batch13.js",
    "movies-database.json",
    "404.html",
    "_not-found.html",
]

ALL_FILES = MISSING_CHUNKS + MISSING_ROOT_FILES


def ensure_remote_dir(ftp, path):
    """Create remote directory if it doesn't exist."""
    dirs = path.strip("/").split("/")
    current = ""
    for d in dirs:
        current += "/" + d
        try:
            ftp.cwd(current)
        except:
            try:
                ftp.mkd(current)
                print(f"  Created dir: {current}")
            except:
                pass


def main():
    print(f"Connecting to {FTP_HOST}...")
    ftp = FTP_TLS(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print("Connected!\n")

    success = 0
    failed = 0

    for rel_path in ALL_FILES:
        local_path = os.path.join(LOCAL_BASE, rel_path.replace("/", os.sep))
        remote_path = REMOTE_BASE + "/" + rel_path

        if not os.path.exists(local_path):
            print(f"SKIP (not found locally): {rel_path}")
            failed += 1
            continue

        # Ensure remote directory exists
        remote_dir = "/".join(remote_path.split("/")[:-1])
        ensure_remote_dir(ftp, remote_dir)

        try:
            size = os.path.getsize(local_path)
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
            print(f"OK: {rel_path} ({size:,} bytes)")
            success += 1
        except Exception as e:
            print(f"FAIL: {rel_path} - {e}")
            failed += 1

    ftp.quit()
    print(f"\nDone! {success} uploaded, {failed} failed")


if __name__ == "__main__":
    main()
