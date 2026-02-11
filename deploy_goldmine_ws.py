import os
import sys
from ftplib import FTP_TLS

server = os.environ.get("FTP_SERVER")
user = os.environ.get("FTP_USER")
passwd = os.environ.get("FTP_PASS")

if not all([server, user, passwd]):
    print("ERROR: Missing FTP_SERVER, FTP_USER, or FTP_PASS environment variables.")
    sys.exit(1)

BASE_LOCAL = r"e:\findtorontoevents_antigravity.ca"
BASE_REMOTE = "/findtorontoevents.ca"

files_to_deploy = [
    # GOLDMINE_WS dashboard page
    ("investments/goldmines/windsurf/index.html", "investments/goldmines/windsurf/index.html"),
    # Goldmines landing page (updated with Windsurf card)
    ("investments/goldmines/index.html", "investments/goldmines/index.html"),
    # Investment Hub page (updated with Goldmines section)
    ("investments/index.html", "investments/index.html"),
    # Main site homepage (updated Other Stuff menu with Windsurf links)
    ("index.html", "index.html"),
]

# Directories to ensure exist on remote
dirs_to_create = [
    "investments",
    "investments/goldmines",
    "investments/goldmines/windsurf",
]

try:
    ftp = FTP_TLS(server)
    ftp.login(user, passwd)
    ftp.prot_p()
    print(f"Connected to {server}")

    # Ensure remote directories exist
    for d in dirs_to_create:
        remote_dir = f"{BASE_REMOTE}/{d}"
        try:
            ftp.mkd(remote_dir)
            print(f"  Created dir: {remote_dir}")
        except Exception:
            print(f"  Dir exists: {remote_dir}")

    # Upload files
    success = 0
    for local_rel, remote_rel in files_to_deploy:
        local_path = os.path.join(BASE_LOCAL, local_rel)
        remote_path = f"{BASE_REMOTE}/{remote_rel}"
        if not os.path.exists(local_path):
            print(f"  SKIP (not found): {local_path}")
            continue
        try:
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
            size = os.path.getsize(local_path)
            print(f"  Uploaded: {remote_rel} ({size:,} bytes)")
            success += 1
        except Exception as e:
            print(f"  FAILED: {remote_rel} - {e}")

    ftp.quit()
    print(f"\nSUCCESS: Deployed {success}/{len(files_to_deploy)} files.")
except Exception as e:
    print(f"FAILURE: {e}")
    sys.exit(1)
