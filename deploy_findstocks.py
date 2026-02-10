import os
import sys
from ftplib import FTP_TLS

# Files to deploy: (local_path, remote_path)
FILES = [
    (r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\api\setup_schema.php", "/findtorontoevents.ca/findstocks/portfolio2/api/setup_schema.php"),
    (r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\api\data.php", "/findtorontoevents.ca/findstocks/portfolio2/api/data.php"),
    (r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\api\whatif.php", "/findtorontoevents.ca/findstocks/portfolio2/api/whatif.php"),
    (r"e:\findtorontoevents_antigravity.ca\findstocks\portfolio2\api\advanced_stats.php", "/findtorontoevents.ca/findstocks/portfolio2/api/advanced_stats.php"),
    (r"e:\findtorontoevents_antigravity.ca\findstocks2_global\index.html", "/findtorontoevents.ca/findstocks2_global/index.html"),
]

def ensure_remote_dirs(ftp, remote_path):
    """Create remote directories if they don't exist."""
    dirs = os.path.dirname(remote_path).split("/")
    current = ""
    for d in dirs:
        if not d:
            continue
        current += "/" + d
        try:
            ftp.cwd(current)
        except:
            try:
                ftp.mkd(current)
                print(f"  Created directory: {current}")
            except:
                pass  # may already exist

def main():
    server = os.environ.get("FTP_SERVER")
    user = os.environ.get("FTP_USER")
    password = os.environ.get("FTP_PASS")

    if not all([server, user, password]):
        print("ERROR: FTP_SERVER, FTP_USER, or FTP_PASS environment variable not set.")
        sys.exit(1)

    print(f"Connecting to {server} via FTP-TLS...")
    ftp = FTP_TLS()
    ftp.connect(server, 21)
    ftp.login(user, password)
    ftp.prot_p()
    print("Connected and secured with TLS.\n")

    success_count = 0
    fail_count = 0

    for local_path, remote_path in FILES:
        filename = os.path.basename(local_path)
        print(f"Deploying: {filename}")
        print(f"  Local:  {local_path}")
        print(f"  Remote: {remote_path}")

        if not os.path.exists(local_path):
            print(f"  FAILED: Local file does not exist!\n")
            fail_count += 1
            continue

        try:
            ensure_remote_dirs(ftp, remote_path)
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
            print(f"  SUCCESS\n")
            success_count += 1
        except Exception as e:
            print(f"  FAILED: {e}\n")
            fail_count += 1

    ftp.quit()
    print(f"Done. {success_count} succeeded, {fail_count} failed.")

if __name__ == "__main__":
    main()
