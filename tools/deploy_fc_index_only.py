#!/usr/bin/env python3
"""
Quick deploy: Upload only favcreators/docs/index.html to /fc/index.html.
Useful for fast iteration on index.html changes (like the redirect fix).

Usage:
  set FTP_SERVER=... FTP_USER=... FTP_PASS=...
  python tools/deploy_fc_index_only.py
"""
import os
import ftplib
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
LOCAL_FILE = WORKSPACE / "favcreators" / "docs" / "index.html"

def main():
    host = os.environ.get("FTP_SERVER") or os.environ.get("FTP_HOST", "").strip()
    user = os.environ.get("FTP_USER", "").strip()
    password = os.environ.get("FTP_PASS", "").strip()

    if not host or not user or not password:
        print("Set FTP_SERVER, FTP_USER, FTP_PASS in environment.")
        raise SystemExit(1)

    if not LOCAL_FILE.is_file():
        print(f"File not found: {LOCAL_FILE}")
        raise SystemExit(1)

    print(f"Deploying {LOCAL_FILE.name} to FTP: {host}")

    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user, password)
            print("Connected.")

            # Upload to multiple possible paths for /fc/
            paths = [
                "findtorontoevents.ca/fc",
                "fc",
            ]
            for remote_dir in paths:
                try:
                    ftp.cwd("/")
                    for part in remote_dir.split("/"):
                        if part:
                            try:
                                ftp.cwd(part)
                            except:
                                ftp.mkd(part)
                                ftp.cwd(part)
                    with open(LOCAL_FILE, "rb") as f:
                        ftp.storbinary("STOR index.html", f)
                    print(f"  Uploaded to /{remote_dir}/index.html")
                except Exception as e:
                    print(f"  Failed {remote_dir}: {e}")

        print("\nDone! Visit https://findtorontoevents.ca/fc/ to verify redirect.")
    except Exception as e:
        print(f"Deploy failed: {e}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
