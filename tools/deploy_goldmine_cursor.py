"""Deploy GOLDMINE_CURSOR — Cross-System Prediction Intelligence dashboard to FTP production."""
import ftplib
import ssl
import os
import sys
from pathlib import Path

# Load .env
_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent
_env_file = WORKSPACE / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k and os.environ.get(k) in (None, ""):
                os.environ.setdefault(k, v)
    if "FTP_SERVER" not in os.environ and os.environ.get("FTP_HOST"):
        os.environ.setdefault("FTP_SERVER", os.environ["FTP_HOST"])

SERVER = os.environ.get("FTP_SERVER", "")
USER = os.environ.get("FTP_USER", "")
PASS = os.environ.get("FTP_PASS", "")

if not SERVER or not USER or not PASS:
    print("ERROR: Set FTP_SERVER, FTP_USER, FTP_PASS environment variables (or create .env)")
    sys.exit(1)

BASE_LOCAL = str(WORKSPACE)
BASE_REMOTE = "/findtorontoevents.ca"

# Files to deploy (local path relative to project root -> remote path)
FILES = [
    # ── GOLDMINE_CURSOR dashboard ──
    ("goldmine_cursor/index.html", "goldmine_cursor/index.html"),
    # ── GOLDMINE_CURSOR API ──
    ("goldmine_cursor/api/db_config.php", "goldmine_cursor/api/db_config.php"),
    ("goldmine_cursor/api/db_connect.php", "goldmine_cursor/api/db_connect.php"),
    ("goldmine_cursor/api/setup_tables.php", "goldmine_cursor/api/setup_tables.php"),
    ("goldmine_cursor/api/track_record.php", "goldmine_cursor/api/track_record.php"),
    ("goldmine_cursor/api/harvest.php", "goldmine_cursor/api/harvest.php"),
    ("goldmine_cursor/api/weekly_scorecard.php", "goldmine_cursor/api/weekly_scorecard.php"),
    ("goldmine_cursor/api/health_check.php", "goldmine_cursor/api/health_check.php"),
    # ── Updated index.html with Goldmines nav ──
    ("index.html", "index.html"),
]


def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print(f"Connecting to {SERVER}...")
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
                    print(f"  Created dir: {current}")
                except ftplib.error_perm:
                    pass
            ftp.cwd("/")

    # Upload files
    uploaded = 0
    errors = []
    for local_rel, remote_rel in FILES:
        local_path = os.path.join(BASE_LOCAL, local_rel)
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
        print("\n=== POST-DEPLOY STEPS ===")
        print("\n1. Setup tables (run once):")
        print("   https://findtorontoevents.ca/goldmine_cursor/api/setup_tables.php?key=goldmine2026")
        print("\n2. Run first harvest:")
        print("   https://findtorontoevents.ca/goldmine_cursor/api/harvest.php?key=goldmine2026")
        print("\n3. Build scorecard:")
        print("   https://findtorontoevents.ca/goldmine_cursor/api/weekly_scorecard.php?key=goldmine2026")
        print("\n4. View dashboard:")
        print("   https://findtorontoevents.ca/goldmine_cursor/")


if __name__ == "__main__":
    main()
