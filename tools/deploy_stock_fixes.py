#!/usr/bin/env python3
"""Deploy stock portfolio fixes via FTP_TLS."""

import os
import sys
from ftplib import FTP_TLS

# Files to upload: (local_path, remote_path)
FILES = [
    (
        r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\api\consolidated_picks.php",
        "/findtorontoevents.ca/findstocks/portfolio2/api/consolidated_picks.php",
    ),
    (
        r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\api\advanced_stats.php",
        "/findtorontoevents.ca/findstocks/portfolio2/api/advanced_stats.php",
    ),
    (
        r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\consolidated.html",
        "/findtorontoevents.ca/findstocks/portfolio2/consolidated.html",
    ),
    (
        r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\picks.html",
        "/findtorontoevents.ca/findstocks/portfolio2/picks.html",
    ),
    (
        r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\horizon-picks.html",
        "/findtorontoevents.ca/findstocks/portfolio2/horizon-picks.html",
    ),
    (
        r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\dashboard.html",
        "/findtorontoevents.ca/findstocks/portfolio2/dashboard.html",
    ),
    (
        r"e:\findtorontoevents_antigravity.ca\live-monitor\edge-dashboard.html",
        "/findtorontoevents.ca/live-monitor/edge-dashboard.html",
    ),
]


def main():
    # Read FTP credentials from Windows user environment variables
    ftp_server = os.environ.get("FTP_SERVER")
    ftp_user = os.environ.get("FTP_USER")
    ftp_pass = os.environ.get("FTP_PASS")

    if not all([ftp_server, ftp_user, ftp_pass]):
        print("ERROR: Missing FTP credentials in environment variables.")
        print(f"  FTP_SERVER={'set' if ftp_server else 'MISSING'}")
        print(f"  FTP_USER={'set' if ftp_user else 'MISSING'}")
        print(f"  FTP_PASS={'set' if ftp_pass else 'MISSING'}")
        sys.exit(1)

    # Verify all local files exist before connecting
    missing = []
    for local_path, _ in FILES:
        if not os.path.isfile(local_path):
            missing.append(local_path)
    if missing:
        print("ERROR: The following local files are missing:")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)

    # Connect via FTP_TLS
    print(f"Connecting to {ftp_server} ...")
    ftp = FTP_TLS()
    ftp.connect(ftp_server, 21)
    ftp.login(ftp_user, ftp_pass)
    ftp.prot_p()  # Switch to secure data connection
    print("Connected and secured.\n")

    success_count = 0
    fail_count = 0

    for local_path, remote_path in FILES:
        file_size = os.path.getsize(local_path)
        filename = os.path.basename(local_path)
        try:
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
            print(f"  OK  {remote_path}  ({file_size:,} bytes)")
            success_count += 1
        except Exception as e:
            print(f"  FAIL  {remote_path}  -- {e}")
            fail_count += 1

    ftp.quit()

    print(f"\nDone. {success_count} succeeded, {fail_count} failed out of {len(FILES)} files.")
    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
