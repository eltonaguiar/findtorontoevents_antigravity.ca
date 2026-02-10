"""Deploy News Feed Aggregator to FTP production."""
import ftplib
import ssl
import os
import sys

# Read FTP credentials from Windows user environment variables
SERVER = os.environ.get("FTP_SERVER", "")
USER = os.environ.get("FTP_USER", "")
PASS = os.environ.get("FTP_PASS", "")

if not SERVER or not USER or not PASS:
    print("ERROR: Set FTP_SERVER, FTP_USER, FTP_PASS environment variables")
    sys.exit(1)

BASE_LOCAL = r"e:/findtorontoevents_antigravity.ca"
BASE_REMOTE = "/findtorontoevents.ca"

# Files to deploy (local path relative to project root -> remote path)
FILES = [
    # Backend API
    ("favcreators/public/api/news_feed_schema.php", "fc/api/news_feed_schema.php"),
    ("favcreators/public/api/news_feed.php", "fc/api/news_feed.php"),
    # Frontend dashboard
    ("news/index.html", "news/index.html"),
    # Updated AI chatbot
    ("ai-assistant.js", "ai-assistant.js"),
]

def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    ftp = ftplib.FTP_TLS(context=ctx)
    ftp.connect(SERVER, 21)
    ftp.login(USER, PASS)
    ftp.prot_p()
    print(f"Connected to {SERVER}")

    # Ensure directories exist
    dirs_needed = set()
    for _, remote in FILES:
        parts = remote.rsplit("/", 1)
        if len(parts) == 2:
            dirs_needed.add(parts[0])

    for d in sorted(dirs_needed):
        remote_dir = f"{BASE_REMOTE}/{d}"
        try:
            ftp.cwd(remote_dir)
            ftp.cwd("/")
        except ftplib.error_perm:
            current = ""
            for part in remote_dir.split("/"):
                if not part:
                    continue
                current += "/" + part
                try:
                    ftp.mkd(current)
                    print(f"  Created: {current}")
                except ftplib.error_perm:
                    pass
            ftp.cwd("/")

    # Upload files
    uploaded = 0
    errors = []
    for local_rel, remote_rel in FILES:
        local_path = f"{BASE_LOCAL}/{local_rel}"
        remote_path = f"{BASE_REMOTE}/{remote_rel}"

        if not os.path.exists(local_path):
            errors.append(f"NOT FOUND: {local_path}")
            continue

        try:
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
            uploaded += 1
            size = os.path.getsize(local_path)
            print(f"  OK: {remote_rel} ({size:,} bytes)")
        except Exception as e:
            errors.append(f"FAIL {remote_rel}: {e}")

    ftp.quit()

    print(f"\nDeployed {uploaded}/{len(FILES)} files.")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  {e}")
    else:
        print("All files uploaded successfully!")
        print("\nVerify:")
        print("  https://findtorontoevents.ca/fc/api/news_feed.php?action=sources")
        print("  https://findtorontoevents.ca/fc/api/news_feed.php?action=get&category=toronto")
        print("  https://findtorontoevents.ca/fc/api/news_feed.php?action=get&category=canada")
        print("  https://findtorontoevents.ca/fc/api/news_feed.php?action=get&category=us")
        print("  https://findtorontoevents.ca/fc/api/news_feed.php?action=get&category=world")
        print("  https://findtorontoevents.ca/news/")
        print("\nTest chatbot:")
        print("  Visit https://findtorontoevents.ca/ -> click robot icon -> type 'toronto news'")

if __name__ == "__main__":
    main()
