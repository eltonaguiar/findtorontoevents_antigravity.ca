import os
import sys
from ftplib import FTP_TLS

LOCAL_FILE = r"e:\findtorontoevents_antigravity.ca\findstocks\index.html"
REMOTE_PATH = "/findtorontoevents.ca/findstocks/index.html"

def main():
    # Read credentials from Windows environment variables
    server = os.environ.get("FTP_SERVER")
    user = os.environ.get("FTP_USER")
    password = os.environ.get("FTP_PASS")

    if not all([server, user, password]):
        missing = [k for k in ("FTP_SERVER", "FTP_USER", "FTP_PASS") if not os.environ.get(k)]
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    if not os.path.isfile(LOCAL_FILE):
        print(f"ERROR: Local file not found: {LOCAL_FILE}")
        sys.exit(1)

    file_size = os.path.getsize(LOCAL_FILE)
    print(f"File to upload: {LOCAL_FILE} ({file_size:,} bytes)")
    print(f"Remote path:    {REMOTE_PATH}")
    print(f"FTP server:     {server}")
    print()

    try:
        print("Connecting via FTP_TLS...")
        ftp = FTP_TLS(server)
        ftp.login(user, password)
        ftp.prot_p()
        print("Connected and secured with prot_p().")

        with open(LOCAL_FILE, "rb") as f:
            print(f"Uploading to {REMOTE_PATH} ...")
            ftp.storbinary(f"STOR {REMOTE_PATH}", f)

        print()
        print(f"SUCCESS: Uploaded {LOCAL_FILE} -> {REMOTE_PATH} ({file_size:,} bytes)")

        ftp.quit()
    except Exception as e:
        print(f"FAILURE: {type(e).__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
