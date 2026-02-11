#!/usr/bin/env python3
"""
Deploy news page to production via FTP.
Uploads news/index.html to both findtorontoevents.ca and tdotevent.ca.
"""
import ftplib
import ssl
import os
import sys

SERVER = os.environ.get("FTP_SERVER", "")
USER = os.environ.get("FTP_USER", "")
PASS = os.environ.get("FTP_PASS", "")

if not SERVER or not USER or not PASS:
    print("ERROR: Set FTP_SERVER, FTP_USER, FTP_PASS environment variables")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FTP_ROOT = "/findtorontoevents.ca"

FILES = [
    ("news/index.html", "{}/news/index.html".format(FTP_ROOT)),
]

SISTER_FILES = [
    ("news/index.html", "/tdotevent.ca/news/index.html"),
]


def ensure_remote_dir(ftp, remote_path):
    """Create remote directories recursively."""
    dirs = os.path.dirname(remote_path).split("/")
    current = ""
    for d in dirs:
        if not d:
            continue
        current += "/" + d
        try:
            ftp.cwd(current)
        except ftplib.error_perm:
            try:
                ftp.mkd(current)
            except ftplib.error_perm:
                pass


def upload_file(ftp, local_path, remote_path):
    """Upload a single file via FTP."""
    full_local = os.path.join(ROOT, local_path)
    if not os.path.exists(full_local):
        print("  SKIP (not found): {}".format(local_path))
        return False

    ensure_remote_dir(ftp, remote_path)
    with open(full_local, "rb") as f:
        ftp.storbinary("STOR " + remote_path, f)
    size = os.path.getsize(full_local)
    print("  OK: {} -> {} ({:,} bytes)".format(local_path, remote_path, size))
    return True


def main():
    print("Connecting to FTP...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    ftp = ftplib.FTP_TLS(SERVER, USER, PASS, context=ctx)
    ftp.prot_p()
    print("Connected to {}".format(SERVER))

    print("\nDeploying to findtorontoevents.ca:")
    for local, remote in FILES:
        upload_file(ftp, local, remote)

    print("\nDeploying to tdotevent.ca:")
    for local, remote in SISTER_FILES:
        upload_file(ftp, local, remote)

    ftp.quit()
    print("\nDeploy complete!")


if __name__ == "__main__":
    main()
