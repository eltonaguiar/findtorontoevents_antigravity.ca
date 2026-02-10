"""Deploy 15 files to FTP using FTPS (FTP_TLS with prot_p)."""
import os
import sys
from ftplib import FTP_TLS

LOCAL_ROOT = r"e:\findtorontoevents_antigravity.ca"
REMOTE_ROOT = "/findtorontoevents.ca/"

FILES = [
    "findstocks/portfolio/stats.html",
    "findstocks/portfolio2/stats/index.html",
    "findstocks/alpha/index.html",
    "findstocks/portfolio2/horizon-picks.html",
    "findstocks/portfolio2/leaderboard.html",
    "findstocks/research/index.html",
    "findmutualfunds/portfolio1/index.html",
    "findmutualfunds/portfolio1/report.html",
    "findmutualfunds/portfolio1/stats.html",
    "findmutualfunds2/portfolio2/stats/index.html",
    "findforex2/portfolio/stats/index.html",
    "findcryptopairs/portfolio/stats/index.html",
    "investments/index.html",
    "findstocks_global/miracle.html",
    "findstocks2_global/miracle.html",
]


def ensure_remote_dirs(ftp, remote_path):
    """Create remote directories recursively if they don't exist."""
    dirs = os.path.dirname(remote_path).replace("\\", "/").split("/")
    current = ""
    for d in dirs:
        if not d:
            current = "/"
            continue
        current = current.rstrip("/") + "/" + d
        try:
            ftp.cwd(current)
        except Exception:
            try:
                ftp.mkd(current)
                print(f"  Created remote dir: {current}")
            except Exception:
                pass  # may already exist


def main():
    server = os.environ.get("FTP_SERVER")
    user = os.environ.get("FTP_USER")
    passwd = os.environ.get("FTP_PASS")

    if not all([server, user, passwd]):
        print("ERROR: FTP_SERVER, FTP_USER, or FTP_PASS environment variables not set.")
        sys.exit(1)

    print(f"Connecting to {server} via FTPS...")
    ftp = FTP_TLS()
    ftp.connect(server, 21)
    ftp.login(user, passwd)
    ftp.prot_p()
    print("Connected and secured with TLS.\n")

    success = 0
    fail = 0

    for rel_path in FILES:
        local_path = os.path.join(LOCAL_ROOT, rel_path.replace("/", os.sep))
        remote_path = REMOTE_ROOT + rel_path

        if not os.path.isfile(local_path):
            print(f"FAIL: {rel_path} -- local file not found")
            fail += 1
            continue

        try:
            ensure_remote_dirs(ftp, remote_path)
            file_size = os.path.getsize(local_path)
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
            print(f"OK:   {rel_path} ({file_size:,} bytes)")
            success += 1
        except Exception as e:
            print(f"FAIL: {rel_path} -- {e}")
            fail += 1

    ftp.quit()
    print(f"\nDone. {success} succeeded, {fail} failed out of {len(FILES)} files.")


if __name__ == "__main__":
    main()
