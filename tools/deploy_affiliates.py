#!/usr/bin/env python3
"""Deploy affiliate page and related updates to live site via FTP."""
import os
import ftplib
import sys

FTP_SERVER = os.environ.get('FTP_SERVER')
FTP_USER = os.environ.get('FTP_USER')
FTP_PASS = os.environ.get('FTP_PASS')

if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
    print("ERROR: FTP_SERVER, FTP_USER, FTP_PASS env vars required")
    sys.exit(1)

LOCAL_BASE = r"e:\findtorontoevents_antigravity.ca"
REMOTE_BASE = "/findtorontoevents.ca"

FILES = [
    ("affiliates/index.html", "affiliates/index.html"),
    ("index.html", "index.html"),
    ("updates/index.html", "updates/index.html"),
]

def upload():
    ftp = ftplib.FTP_TLS(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print(f"Connected to {FTP_SERVER}")

    for local_rel, remote_rel in FILES:
        local_path = os.path.join(LOCAL_BASE, local_rel)
        remote_path = f"{REMOTE_BASE}/{remote_rel}"

        # Ensure remote directory exists
        remote_dir = "/".join(remote_path.split("/")[:-1])
        try:
            ftp.mkd(remote_dir)
            print(f"  Created dir: {remote_dir}")
        except ftplib.error_perm:
            pass  # already exists

        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_path}", f)
        print(f"  Uploaded: {local_rel} -> {remote_path}")

    ftp.quit()
    print("\nDone! All files deployed.")

if __name__ == "__main__":
    upload()
