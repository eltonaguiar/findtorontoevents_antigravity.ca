"""Deploy regime files to production via FTP-TLS."""
import os
import sys
from ftplib import FTP_TLS

# FTP credentials from environment
FTP_SERVER = os.environ.get("FTP_SERVER")
FTP_USER = os.environ.get("FTP_USER")
FTP_PASS = os.environ.get("FTP_PASS")

if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
    print("ERROR: FTP_SERVER, FTP_USER, or FTP_PASS not set in environment.")
    sys.exit(1)

# Files to deploy: (local_path, remote_path)
BASE_LOCAL = r"e:\findtorontoevents_antigravity.ca"
BASE_REMOTE = "/findtorontoevents.ca"

FILES = [
    ("live-monitor/api/regime.php", "live-monitor/api/regime.php"),
    ("live-monitor/regime-integration.js", "live-monitor/regime-integration.js"),
    ("live-monitor/live-monitor.html", "live-monitor/live-monitor.html"),
    ("live-monitor/smart-money.html", "live-monitor/smart-money.html"),
]


def ensure_remote_dir(ftp, remote_dir):
    """Ensure remote directory exists, creating if needed."""
    dirs = remote_dir.strip("/").split("/")
    current = ""
    for d in dirs:
        current += "/" + d
        try:
            ftp.cwd(current)
        except Exception:
            try:
                ftp.mkd(current)
                print(f"  Created directory: {current}")
            except Exception:
                pass


def main():
    print(f"Connecting to {FTP_SERVER} as {FTP_USER}...")
    ftp = FTP_TLS()
    ftp.connect(FTP_SERVER, 21)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print("Connected and secured with TLS.\n")

    success = 0
    failed = 0

    for local_rel, remote_rel in FILES:
        local_path = os.path.join(BASE_LOCAL, local_rel)
        remote_path = f"{BASE_REMOTE}/{remote_rel}"

        if not os.path.exists(local_path):
            print(f"SKIP: {local_path} does not exist locally.")
            failed += 1
            continue

        file_size = os.path.getsize(local_path)
        print(f"Uploading: {local_rel}")
        print(f"  Local:  {local_path} ({file_size:,} bytes)")
        print(f"  Remote: {remote_path}")

        remote_dir = "/".join(remote_path.split("/")[:-1])
        ensure_remote_dir(ftp, remote_dir)

        try:
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
            try:
                remote_size = ftp.size(remote_path)
                print(f"  OK - uploaded ({remote_size:,} bytes on server)")
            except Exception:
                print(f"  OK - uploaded (size check not supported)")
            success += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

        print()

    ftp.quit()
    print(f"Done. {success} succeeded, {failed} failed out of {len(FILES)} files.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
