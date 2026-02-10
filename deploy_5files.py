import os
import sys
from ftplib import FTP_TLS

FTP_SERVER = os.environ.get("FTP_SERVER")
FTP_USER = os.environ.get("FTP_USER")
FTP_PASS = os.environ.get("FTP_PASS")

if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
    print("ERROR: Missing FTP environment variables (FTP_SERVER, FTP_USER, FTP_PASS)")
    sys.exit(1)

FILES = [
    (r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\api\advanced_stats.php",
     "/findtorontoevents.ca/findstocks/portfolio2/api/advanced_stats.php"),
    (r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\api\setup_schema.php",
     "/findtorontoevents.ca/findstocks/portfolio2/api/setup_schema.php"),
    (r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\api\data.php",
     "/findtorontoevents.ca/findstocks/portfolio2/api/data.php"),
    (r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\api\whatif.php",
     "/findtorontoevents.ca/findstocks/portfolio2/api/whatif.php"),
    (r"e:\findtorontoevents_antigravity.ca\findstocks2_global\index.html",
     "/findtorontoevents.ca/findstocks2_global/index.html"),
]

def ensure_remote_dirs(ftp, remote_path):
    """Create remote directories if they don't exist."""
    dirs = remote_path.rsplit("/", 1)[0]  # strip filename
    parts = dirs.split("/")
    current = ""
    for part in parts:
        if not part:
            current = "/"
            continue
        current = current.rstrip("/") + "/" + part
        try:
            ftp.cwd(current)
        except Exception:
            try:
                ftp.mkd(current)
                print(f"  Created directory: {current}")
            except Exception:
                pass  # may already exist

try:
    print(f"Connecting to {FTP_SERVER} ...")
    ftp = FTP_TLS(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    print("Connected and secured with TLS.\n")

    success = 0
    fail = 0
    for local_path, remote_path in FILES:
        try:
            if not os.path.isfile(local_path):
                print(f"FAIL: {local_path} — file not found locally")
                fail += 1
                continue
            ensure_remote_dirs(ftp, remote_path)
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
            size = os.path.getsize(local_path)
            print(f"OK:   {remote_path} ({size:,} bytes)")
            success += 1
        except Exception as e:
            print(f"FAIL: {remote_path} — {e}")
            fail += 1

    ftp.quit()
    print(f"\nDone. {success} succeeded, {fail} failed.")
except Exception as e:
    print(f"FTP connection error: {e}")
    sys.exit(1)
