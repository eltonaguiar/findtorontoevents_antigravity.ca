"""Deploy updates/index.html to server via FTP_TLS."""
import os
import sys
from ftplib import FTP_TLS

LOCAL_FILE = r"e:\findtorontoevents_antigravity.ca\updates\index.html"
REMOTE_DIR = "/findtorontoevents.ca/updates"
REMOTE_FILE = "index.html"

def main():
    local_size = os.path.getsize(LOCAL_FILE)
    print(f"Local file size: {local_size} bytes")

    server = os.environ["FTP_SERVER"]
    user = os.environ["FTP_USER"]
    passwd = os.environ["FTP_PASS"]

    print(f"Connecting to {server} ...")
    ftp = FTP_TLS(server)
    ftp.login(user, passwd)
    ftp.prot_p()
    print("Connected and secured with TLS.")

    # Ensure remote directory exists
    try:
        ftp.mkd(REMOTE_DIR)
        print(f"Created remote directory: {REMOTE_DIR}")
    except Exception:
        pass  # already exists

    ftp.cwd(REMOTE_DIR)
    print(f"Changed to remote dir: {REMOTE_DIR}")

    # Upload file in binary mode
    with open(LOCAL_FILE, "rb") as f:
        ftp.storbinary(f"STOR {REMOTE_FILE}", f)
    print("Upload complete.")

    # Verify remote size
    remote_size = ftp.size(REMOTE_FILE)
    print(f"Remote file size: {remote_size} bytes")

    ftp.quit()

    if remote_size == local_size:
        print(f"SUCCESS: sizes match ({local_size} bytes)")
        return 0
    else:
        print(f"MISMATCH: local={local_size}, remote={remote_size}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
