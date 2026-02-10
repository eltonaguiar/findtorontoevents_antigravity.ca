"""Deploy VR scene fix: layout-fix.js + index.html to production."""
import ftplib
import os

# FTP credentials from .env
HOST = "ftps2.50webs.com"
USER = "ejaguiar1"
PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
ROOT = "/findtorontoevents.ca"

FILES = [
    ("vr/layout-fix.js", "vr/layout-fix.js"),
    ("vr/index.html", "vr/index.html"),
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    print(f"Connecting to {HOST}...")
    ftp = ftplib.FTP_TLS()
    ftp.connect(HOST, 21, timeout=30)
    ftp.login(USER, PASS)
    ftp.prot_p()
    print("Connected and secured.")

    for local_rel, remote_rel in FILES:
        local_path = os.path.join(BASE_DIR, local_rel)
        remote_path = ROOT + "/" + remote_rel

        if not os.path.exists(local_path):
            print(f"  SKIP (not found): {local_path}")
            continue

        print(f"  Uploading {local_rel} -> {remote_path}...")
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_path}", f)
        print(f"  OK: {local_rel}")

    ftp.quit()
    print("Done! All files deployed.")

if __name__ == "__main__":
    main()
