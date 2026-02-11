#!/usr/bin/env python3
"""
Deploy penny stock picks system to production via FTP.
Uploads PHP API, HTML frontend, and data files.
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
    # PHP API
    ("findstocks/portfolio2/api/penny_stock_picks.php",
     f"{FTP_ROOT}/findstocks/portfolio2/api/penny_stock_picks.php"),
    # HTML Frontend
    ("findstocks/portfolio2/penny-stocks.html",
     f"{FTP_ROOT}/findstocks/portfolio2/penny-stocks.html"),
    # Stock nav (in case updated)
    ("findstocks/portfolio2/stock-nav.js",
     f"{FTP_ROOT}/findstocks/portfolio2/stock-nav.js"),
]

# Also deploy to sister site
SISTER_FILES = [
    ("findstocks/portfolio2/api/penny_stock_picks.php",
     "/tdotevent.ca/findstocks/portfolio2/api/penny_stock_picks.php"),
    ("findstocks/portfolio2/penny-stocks.html",
     "/tdotevent.ca/findstocks/portfolio2/penny-stocks.html"),
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
            ftp.mkd(current)
        except ftplib.error_perm:
            pass


def upload_file(ftp, local_path, remote_path):
    """Upload a single file."""
    full_local = os.path.join(ROOT, local_path)
    if not os.path.exists(full_local):
        print(f"  SKIP  {local_path} (not found)")
        return False

    try:
        ensure_remote_dir(ftp, remote_path)
        with open(full_local, "rb") as f:
            ftp.storbinary(f"STOR {remote_path}", f)
        size = os.path.getsize(full_local)
        print(f"  OK    {remote_path} ({size:,} bytes)")
        return True
    except Exception as e:
        print(f"  FAIL  {remote_path}: {e}")
        return False


def main():
    print("=" * 60)
    print("DEPLOYING PENNY STOCK PICKS SYSTEM")
    print("=" * 60)

    # Connect with TLS
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    ftp = ftplib.FTP_TLS(context=ctx)
    ftp.connect(SERVER, 21)
    ftp.login(USER, PASS)
    ftp.prot_p()

    ok = 0
    fail = 0

    print("\n-- Main site --")
    for local, remote in FILES:
        if upload_file(ftp, local, remote):
            ok += 1
        else:
            fail += 1

    print("\n-- Sister site (tdotevent.ca) --")
    for local, remote in SISTER_FILES:
        if upload_file(ftp, local, remote):
            ok += 1
        else:
            fail += 1

    ftp.quit()

    print(f"\n{'=' * 60}")
    print(f"DONE: {ok} uploaded, {fail} failed")
    print(f"{'=' * 60}")

    if fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
