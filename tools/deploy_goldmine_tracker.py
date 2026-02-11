"""Deploy goldmine_tracker.php to server via FTP_TLS."""
import os
import sys
from ftplib import FTP_TLS

LOCAL_FILE = r"e:\findtorontoevents_antigravity.ca\live-monitor\api\goldmine_tracker.php"
REMOTE_PATH = "/findtorontoevents.ca/live-monitor/api/goldmine_tracker.php"

FTP_SERVER = os.environ.get("FTP_SERVER")
FTP_USER = os.environ.get("FTP_USER")
FTP_PASS = os.environ.get("FTP_PASS")

if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
    print("ERROR: Missing FTP_SERVER, FTP_USER, or FTP_PASS env vars.")
    sys.exit(1)

print(f"Connecting to {FTP_SERVER} ...")
ftp = FTP_TLS(FTP_SERVER)
ftp.login(FTP_USER, FTP_PASS)
ftp.prot_p()
print("Connected and secured.")

remote_dir = "/findtorontoevents.ca/live-monitor/api"
try:
    ftp.cwd(remote_dir)
    print(f"Remote dir OK: {remote_dir}")
except Exception:
    print(f"Creating remote dir: {remote_dir}")
    ftp.mkd(remote_dir)
    ftp.cwd(remote_dir)

local_size = os.path.getsize(LOCAL_FILE)
print(f"Uploading {LOCAL_FILE} ({local_size} bytes) -> {REMOTE_PATH}")
with open(LOCAL_FILE, "rb") as f:
    ftp.storbinary(f"STOR {REMOTE_PATH}", f)

remote_size = ftp.size(REMOTE_PATH)
print(f"Remote size: {remote_size} bytes")
if remote_size == local_size:
    print("SUCCESS: Upload verified - sizes match.")
else:
    print(f"WARNING: Size mismatch! Local={local_size}, Remote={remote_size}")

ftp.quit()
print("FTP connection closed.")
