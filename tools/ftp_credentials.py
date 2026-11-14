"""Load FTP credentials without storing passwords in deployment source."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import os
from pathlib import Path
import ssl
import subprocess
import sys
from ftplib import FTP_TLS, Error

HOST = "ftps2.50webs.com"
USER = "ejaguiar1"


@dataclass(frozen=True)
class FTPCredentials:
    host: str
    user: str
    password: str = field(repr=False)


def read_local_password(path: Path) -> str:
    with path.open(encoding="utf-8") as source:
        for line in source:
            label = line.strip().upper()
            if "50WEBS_FTP" in label and "PASS" in label:
                password = next(source, "").strip()
                if not password or password.startswith("#"):
                    raise ValueError("The 50WEBS_FTP password label has no following value")
                return password
    raise ValueError("The local credential file has no 50WEBS_FTP password label")


def get_ftp_credentials(environ=None, credential_file=None) -> FTPCredentials:
    env = os.environ if environ is None else environ
    if env.get("FTP_HOST") and env.get("FTP_SERVER") and env["FTP_HOST"] != env["FTP_SERVER"]:
        raise ValueError("FTP_HOST and FTP_SERVER disagree; refusing ambiguous credentials")
    host = env.get("FTP_HOST") or env.get("FTP_SERVER") or HOST
    user = env.get("FTP_USER") or env.get("FTP_USERNAME") or USER
    password = env.get("FTP_PASS") or env.get("FTP_PASSWORD")
    path = Path(credential_file or env.get("FTP_CREDENTIAL_FILE") or Path.home()/"dbpasses.txt")
    if path.is_file() and host == HOST and user == USER:
        password = read_local_password(path)
    elif not password:
        if host != HOST or user != USER:
            raise ValueError("Explicit FTP credentials required for a non-default account")
        raise ValueError("Set FTP_PASS or provide a local FTP_CREDENTIAL_FILE")
    if any("\n" in value or "\r" in value or "\x00" in value for value in (host, user, password)):
        raise ValueError("Invalid control character in FTP configuration")
    return FTPCredentials(host, user, password)


def load_ftp_environment() -> FTPCredentials:
    credentials = get_ftp_credentials()
    os.environ["FTP_HOST"] = credentials.host
    os.environ["FTP_SERVER"] = credentials.host
    os.environ["FTP_USER"] = credentials.user
    os.environ["FTP_PASS"] = credentials.password
    return credentials


def connect_ftp() -> FTP_TLS:
    credentials = get_ftp_credentials()
    ftp = FTP_TLS(context=ssl.create_default_context(), timeout=30)
    try:
        ftp.connect(credentials.host, 21)
        ftp.login(credentials.user, credentials.password)
        ftp.prot_p()
    except (OSError, Error):
        ftp.close()
        raise
    return ftp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify TLS login and site access without uploading")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Run a command with credentials in its environment")
    args = parser.parse_args()
    try:
        credentials = load_ftp_environment()
        if args.check:
            with FTP_TLS(context=ssl.create_default_context(), timeout=30) as ftp:
                ftp.connect(credentials.host, 21)
                ftp.login(credentials.user, credentials.password)
                ftp.prot_p()
                ftp.cwd("/findtorontoevents.ca")
                ftp.voidcmd("NOOP")
            print("FTPS authentication and site access verified; no files uploaded")
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        if command:
            return subprocess.run(command, check=False).returncode
        if not args.check:
            parser.error("Use --check or -- followed by a deployment command")
    except (OSError, ValueError, Error) as exc:
        print(f"FTP credential error: {type(exc).__name__}; verify local file or FTP_* environment", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
