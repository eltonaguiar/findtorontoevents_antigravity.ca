#!/usr/bin/env python3
"""FTP deploy GHA summary HTML to findtorontoevents.ca/updates/gha-summary.html."""
from __future__ import annotations

import ftplib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCAL = REPO_ROOT / "reports" / "gha_actions_summary.html"
REMOTE_PATH = "/findtorontoevents.ca/updates/gha-summary.html"


def deploy_summary(local_path: Path | None = None) -> None:
    local = local_path or DEFAULT_LOCAL
    if not local.is_file():
        raise FileNotFoundError(f"Summary HTML not found: {local}")

    server = os.environ.get("FTP_SERVER") or os.environ.get("FTP_HOST") or "ftps2.50webs.com"
    user = os.environ.get("FTP_USER") or ""
    password = os.environ.get("FTP_PASS") or ""
    if not user or not password:
        print("ERROR: FTP_USER and FTP_PASS must be set", file=sys.stderr)
        sys.exit(1)

    remote_dir = "/".join(REMOTE_PATH.split("/")[:-1])
    remote_name = REMOTE_PATH.split("/")[-1]
    size = local.stat().st_size

    print(f"Connecting to {server} as {user}…")
    ftp = ftplib.FTP_TLS(server)
    ftp.login(user, password)
    ftp.prot_p()

    try:
        ftp.cwd(remote_dir)
    except ftplib.error_perm:
        for part in remote_dir.strip("/").split("/"):
            try:
                ftp.cwd(part)
            except ftplib.error_perm:
                ftp.mkd(part)
                ftp.cwd(part)

    print(f"Uploading {local} ({size:,} bytes) -> {REMOTE_PATH}")
    with open(local, "rb") as fh:
        ftp.storbinary(f"STOR {remote_name}", fh)
    ftp.quit()
    print("Deploy OK: https://findtorontoevents.ca/updates/gha-summary.html")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_LOCAL,
        help="Local HTML file to upload",
    )
    args = ap.parse_args()
    deploy_summary(args.file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
