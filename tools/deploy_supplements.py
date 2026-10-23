#!/usr/bin/env python3
import ftplib
import ssl
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.ftp_credentials import get_ftp_credentials


def deploy_supplements(local_dir="findtorontoevents.ca/supplements/energy",
                       remote_base="/findtorontoevents.ca/supplements/energy"):
    credentials = get_ftp_credentials()
    local_path = Path(local_dir)
    if not local_path.is_dir():
        raise ValueError("Local supplements directory not found")
    with ftplib.FTP_TLS(context=ssl.create_default_context(), timeout=30) as ftp:
        ftp.connect(credentials.host, 21)
        ftp.login(credentials.user, credentials.password)
        ftp.prot_p()
        ftp.cwd(remote_base)
        uploaded = 0
        for file_path in local_path.glob("*.html"):
            with file_path.open("rb") as source:
                ftp.storbinary(f"STOR {file_path.name}", source)
            print(f"Uploaded: {file_path.name}")
            uploaded += 1
        print(f"Deploy complete: {uploaded} files")


if __name__ == "__main__":
    deploy_supplements()
