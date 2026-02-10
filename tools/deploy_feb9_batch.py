"""Deploy Feb 9 batch: crypto/forex fixes, helper APIs, miracle sorting, updates page."""
import ftplib
import ssl
import os
import sys

SERVER = os.environ.get("FTP_SERVER", "")
USER = os.environ.get("FTP_USER", "")
PASS = os.environ.get("FTP_PASS", "")

if not SERVER or not USER or not PASS:
    print("ERROR: Set FTP_SERVER, FTP_USER, FTP_PASS environment variables")
    sys.exit(1)

BASE_LOCAL = r"e:/findtorontoevents_antigravity.ca"
BASE_REMOTE = "/findtorontoevents.ca"

FILES = [
    # Crypto portfolio fixes
    ("findcryptopairs/portfolio/index.html", "findcryptopairs/portfolio/index.html"),
    # Crypto helper API
    ("findcryptopairs/portfolio/api/crypto_insights.php", "findcryptopairs/portfolio/api/crypto_insights.php"),
    # Forex portfolio fixes
    ("findforex2/portfolio/index.html", "findforex2/portfolio/index.html"),
    # Forex helper API
    ("findforex2/portfolio/api/forex_insights.php", "findforex2/portfolio/api/forex_insights.php"),
    # DayTrades Miracle with sorting
    ("findstocks2_global/miracle.html", "findstocks2_global/miracle.html"),
    # Updates page
    ("updates/index.html", "updates/index.html"),
]

def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    ftp = ftplib.FTP_TLS(context=ctx)
    ftp.connect(SERVER, 21)
    ftp.login(USER, PASS)
    ftp.prot_p()
    print("Connected to %s" % SERVER)

    # Ensure directories exist
    dirs_needed = set()
    for _, remote in FILES:
        parts = remote.rsplit("/", 1)
        if len(parts) == 2:
            dirs_needed.add(parts[0])

    for d in sorted(dirs_needed):
        remote_dir = "%s/%s" % (BASE_REMOTE, d)
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
                    print("  Created: %s" % current)
                except ftplib.error_perm:
                    pass
            ftp.cwd("/")

    uploaded = 0
    errors = []
    for local_rel, remote_rel in FILES:
        local_path = "%s/%s" % (BASE_LOCAL, local_rel)
        remote_path = "%s/%s" % (BASE_REMOTE, remote_rel)

        if not os.path.exists(local_path):
            errors.append("NOT FOUND: %s" % local_path)
            continue

        try:
            with open(local_path, "rb") as f:
                ftp.storbinary("STOR %s" % remote_path, f)
            uploaded += 1
            size = os.path.getsize(local_path)
            print("  OK: %s (%s bytes)" % (remote_rel, "{:,}".format(size)))
        except Exception as e:
            errors.append("FAIL %s: %s" % (remote_rel, e))

    ftp.quit()

    print("\nDeployed %d/%d files." % (uploaded, len(FILES)))
    if errors:
        print("Errors:")
        for e in errors:
            print("  %s" % e)
    else:
        print("All files uploaded successfully!")

if __name__ == "__main__":
    main()
