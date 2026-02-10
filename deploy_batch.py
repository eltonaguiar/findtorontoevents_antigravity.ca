import os
import sys
from ftplib import FTP_TLS

# FTP credentials from environment
FTP_SERVER = "ftps2.50webs.com"
FTP_USER = "ejaguiar1"
FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"

LOCAL_ROOT = r"e:/findtorontoevents_antigravity.ca"
REMOTE_ROOT = "/findtorontoevents.ca"

# Files to deploy: (local_relative_path, remote_relative_path)
FILES = [
    ("findstocks/portfolio2/api/setup_schema.php", "findstocks/portfolio2/api/setup_schema.php"),
    ("findstocks/portfolio2/api/data.php", "findstocks/portfolio2/api/data.php"),
    ("findstocks/portfolio2/api/whatif.php", "findstocks/portfolio2/api/whatif.php"),
    ("findstocks/portfolio2/api/advanced_stats.php", "findstocks/portfolio2/api/advanced_stats.php"),
    ("findstocks2_global/index.html", "findstocks2_global/index.html"),
]

def ensure_remote_dirs(ftp, remote_path):
    """Create remote directories recursively if they don't exist."""
    dirs = remote_path.rsplit("/", 1)[0]  # everything except filename
    parts = dirs.split("/")
    current = ""
    for part in parts:
        if not part:
            continue
        current += "/" + part
        try:
            ftp.cwd(current)
        except Exception:
            try:
                ftp.mkd(current)
                print(f"  Created directory: {current}")
            except Exception as e:
                # might already exist, ignore
                pass

def main():
    print(f"Connecting to {FTP_SERVER}...")
    ftp = FTP_TLS(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()  # enable data channel encryption
    print("Connected and secured with TLS.")

    success = 0
    failed = 0

    for local_rel, remote_rel in FILES:
        local_path = os.path.join(LOCAL_ROOT, local_rel).replace("\\", "/")
        remote_path = REMOTE_ROOT + "/" + remote_rel

        print(f"\nUploading: {local_rel}")
        print(f"  Local:  {local_path}")
        print(f"  Remote: {remote_path}")

        if not os.path.isfile(local_path):
            print(f"  ERROR: Local file not found!")
            failed += 1
            continue

        try:
            ensure_remote_dirs(ftp, remote_path)
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
            size = os.path.getsize(local_path)
            print(f"  OK ({size:,} bytes)")
            success += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

    ftp.quit()
    print(f"\n{'='*50}")
    print(f"Deploy complete: {success} succeeded, {failed} failed")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
