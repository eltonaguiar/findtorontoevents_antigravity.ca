"""Deploy Goldmine Checker — Multi-Page Recommendations vs Reality system to FTP production."""
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
    # ── New Goldmine API files ──
    ("live-monitor/api/goldmine_schema.php", "live-monitor/api/goldmine_schema.php"),
    ("live-monitor/api/goldmine_tracker.php", "live-monitor/api/goldmine_tracker.php"),
    ("live-monitor/api/sec_edgar.php", "live-monitor/api/sec_edgar.php"),
    ("live-monitor/api/news_sentiment.php", "live-monitor/api/news_sentiment.php"),

    # ── New frontend pages ──
    ("live-monitor/goldmine-dashboard.html", "live-monitor/goldmine-dashboard.html"),
    ("live-monitor/goldmine-alerts.html", "live-monitor/goldmine-alerts.html"),

    # ── Updated files ──
    ("findstocks/portfolio2/stock-nav.js", "findstocks/portfolio2/stock-nav.js"),
    ("live-monitor/api/live_signals.php", "live-monitor/api/live_signals.php"),
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
        print("\nVerify APIs:")
        print("  https://findtorontoevents.ca/live-monitor/api/goldmine_tracker.php?action=schema")
        print("  https://findtorontoevents.ca/live-monitor/api/goldmine_tracker.php?action=dashboard")
        print("  https://findtorontoevents.ca/live-monitor/api/goldmine_tracker.php?action=alerts")
        print("  https://findtorontoevents.ca/live-monitor/api/goldmine_tracker.php?action=leaderboard")
        print("  https://findtorontoevents.ca/live-monitor/api/sec_edgar.php?action=insider_clusters")
        print("  https://findtorontoevents.ca/live-monitor/api/news_sentiment.php?action=buzz")
        print("\nVerify pages:")
        print("  https://findtorontoevents.ca/live-monitor/goldmine-dashboard.html")
        print("  https://findtorontoevents.ca/live-monitor/goldmine-alerts.html")
        print("\nFirst-time setup (run once):")
        print("  https://findtorontoevents.ca/live-monitor/api/goldmine_tracker.php?action=archive&key=livetrader2026")
        print("  https://findtorontoevents.ca/live-monitor/api/goldmine_tracker.php?action=update_outcomes&key=livetrader2026")
        print("  https://findtorontoevents.ca/live-monitor/api/goldmine_tracker.php?action=check_health&key=livetrader2026")

if __name__ == "__main__":
    main()
