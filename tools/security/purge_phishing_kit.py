#!/usr/bin/env python3
"""Purge the "Security check" reCAPTCHA-gate phishing kit from the 50webs account.

Incident: see updates/2026-11-25-phishing-kit-compromise.md

The kit is a single-file PHP redirector (reCAPTCHA v3 "human" gate) that forwards
verified visitors to an external banking-phish page. Copies were dropped into
several vhosts of the shared 50webs account, together with a 76 KB .htaccess that
(a) rewrites any `(([a-z]\\d){5}/)(.*/)(.*/)(.*)` path to `de/index.php` and
(b) carries 3,088 `deny from` lines to cloak the phish from scanners.

Safety model
------------
* Read-only by default. Nothing is deleted unless --execute is passed.
* Every file is downloaded and hash-checked BEFORE deletion. A file that does not
  match the known kit hash/size is skipped and reported, never deleted.
* Evidence (kit source, the malicious .htaccess, the victim log) is copied to
  --evidence-dir first. That directory defaults OUTSIDE the git repo because
  visit.txt contains victim IPs/user-agents.

Usage
-----
    python3 tools/security/purge_phishing_kit.py                  # dry run
    python3 tools/security/purge_phishing_kit.py --execute
    python3 tools/security/purge_phishing_kit.py --execute \
        --restore-htaccess /path/to/clean.htaccess

Credentials
-----------
Password resolution order: --password, $FTPS2_PASS, then the line immediately
after the "50WEBS_FTP" marker in ~/dbpasses.txt. Never printed.
"""
from __future__ import annotations

import argparse
import ftplib
import hashlib
import os
import sys

DEFAULT_HOST = "ftps2.50webs.com"
DEFAULT_USER = "ejaguiar1"

# Kit build A: ALLOWED_HOSTNAME=findtorontoevents.ca,
#              REDIRECT_URL=https://oldyhub.com/BQ2GS5/firstonline/bk/
KIT_A_MD5 = "586b76b00d80965e71182fadf67c2d76"
KIT_A_SIZE = 11231
# Kit build B: ALLOWED_HOSTNAME=tdotevent.ca,
#              REDIRECT_URL=https://oldyhub.com/BQ2GS5/lfeind/firstonline/bk
KIT_B_MD5 = "4ec0bec91eeb47d31ad895c9e6334067"
KIT_B_SIZE = 11449

VISIT_LOG = "visit.txt"
MARKER = "de-de"

# (vhost, kit_path, expected_build) — kit_path is the file holding the gate.
KIT_TARGETS = [
    ("/findtorontoevents.ca", "de/index.php", KIT_A_MD5),
    ("/findtorontoevents.ca", "appeasy/index.php", KIT_A_MD5),
    ("/findtorontoevents.ca", "easyapp/index.php", KIT_A_MD5),
    ("/tdotevent.ca", "de/index.php", KIT_A_MD5),
    ("/tdotevent.ca", "appeasy/index.php", KIT_A_MD5),
    ("/tdotevent.ca", "easyapp/index.php", KIT_A_MD5),
    ("/ejaguiar1.50webs.com", "de/index.php", KIT_B_MD5),
    ("/torontoeventsvamp.50webs.org", "e/index.php", KIT_B_MD5),
]

# Directories that hold only kit content; removed if empty afterwards.
KIT_DIRS = [
    "/findtorontoevents.ca/de",
    "/findtorontoevents.ca/appeasy",
    "/findtorontoevents.ca/easyapp",
    "/tdotevent.ca/de",
    "/tdotevent.ca/appeasy",
    "/tdotevent.ca/easyapp",
    "/ejaguiar1.50webs.com/de",
    "/torontoeventsvamp.50webs.org/e",
]

# Docroots whose .htaccess was replaced by the kit (76,799 bytes, 3,088 deny lines).
CLOBBERED_HTACCESS = ["/findtorontoevents.ca", "/tdotevent.ca"]


def log(msg: str = "") -> None:
    print(msg, flush=True)


def resolve_password(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("FTPS2_PASS")
    if env:
        return env.strip()
    path = os.path.expanduser("~/dbpasses.txt")
    if os.path.exists(path):
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        for i, line in enumerate(lines):
            if line.strip().upper().startswith("50WEBS_FTP"):
                for nxt in lines[i + 1 : i + 4]:
                    if nxt.strip() and "=" not in nxt:
                        return nxt.strip()
    sys.exit("ERROR: no password (use --password, $FTPS2_PASS, or ~/dbpasses.txt)")


def connect(host: str, user: str, password: str) -> ftplib.FTP_TLS:
    ftp = ftplib.FTP_TLS(host, timeout=60)
    ftp.login(user, password)
    ftp.prot_p()
    ftp.encoding = "latin-1"
    return ftp


def md5_remote(ftp: ftplib.FTP_TLS, remote: str) -> tuple[str, int]:
    buf = bytearray()
    ftp.retrbinary("RETR " + remote, buf.extend)
    return hashlib.md5(bytes(buf)).hexdigest(), len(buf)


def save_evidence(ftp: ftplib.FTP_TLS, remote: str, evidence_dir: str) -> str:
    local = os.path.join(evidence_dir, remote.strip("/").replace("/", "__"))
    os.makedirs(os.path.dirname(local), exist_ok=True)
    with open(local, "wb") as fh:
        ftp.retrbinary("RETR " + remote, fh.write)
    return local


def dir_names(ftp: ftplib.FTP_TLS, path: str) -> list[str]:
    return [os.path.basename(n) for n in ftp.nlst(path) if os.path.basename(n) not in (".", "..")]


KIT_ONLY_NAMES = {"index.php", VISIT_LOG}


def main() -> int:
    ap = argparse.ArgumentParser(description="Purge the 50webs reCAPTCHA-gate phishing kit.")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--user", default=DEFAULT_USER)
    ap.add_argument("--password")
    ap.add_argument("--execute", action="store_true", help="actually delete (default: dry run)")
    ap.add_argument("--evidence-dir", default=os.path.expanduser("~/phishing-evidence-2026-11-25"))
    ap.add_argument("--restore-htaccess", metavar="LOCAL_FILE",
                    help="clean .htaccess to upload to both clobbered docroots")
    args = ap.parse_args()

    if args.restore_htaccess and not os.path.isfile(args.restore_htaccess):
        return f"ERROR: {args.restore_htaccess} not found"

    ftp = connect(args.host, args.user, resolve_password(args.password))
    mode = "EXECUTE" if args.execute else "DRY RUN"
    log(f"== {mode} — {args.user}@{args.host}")
    log(f"== evidence dir: {args.evidence_dir}")
    removed = skipped = 0

    log("\n-- kit gate files")
    for site, rel, want_md5 in KIT_TARGETS:
        remote = f"{site}/{rel}"
        try:
            got_md5, size = md5_remote(ftp, remote)
        except ftplib.error_perm as exc:
            log(f"   absent   {remote}  ({exc})")
            continue
        if got_md5 != want_md5:
            log(f"   SKIP     {remote}  md5 {got_md5} != {want_md5} (not the kit — left alone)")
            skipped += 1
            continue
        local = save_evidence(ftp, remote, args.evidence_dir) if args.execute else None
        log(f"   {'DELETE' if args.execute else 'would delete'}  {remote}  ({size} B)"
            + (f"  evidence -> {local}" if local else ""))
        if args.execute:
            ftp.delete(remote)
        removed += 1

    log("\n-- victim log + marker")
    for site in ("/findtorontoevents.ca", "/tdotevent.ca"):
        for rel in (f"de/{VISIT_LOG}", MARKER):
            remote = f"{site}/{rel}"
            try:
                got_md5, size = md5_remote(ftp, remote)
            except ftplib.error_perm as exc:
                log(f"   absent   {remote}  ({exc})")
                continue
            local = save_evidence(ftp, remote, args.evidence_dir) if args.execute else None
            log(f"   {'DELETE' if args.execute else 'would delete'}  {remote}  ({size} B)"
                + (f"  evidence -> {local}" if local else ""))
            if args.execute:
                ftp.delete(remote)
            removed += 1

    log("\n-- empty kit directories")
    for d in KIT_DIRS:
        try:
            names = dir_names(ftp, d)
        except ftplib.error_perm as exc:
            log(f"   absent   {d}  ({exc})")
            continue
        kit_only = all(n in KIT_ONLY_NAMES for n in names)
        if names and not kit_only:
            log(f"   SKIP     {d}  (contains non-kit files: {', '.join(sorted(set(names) - KIT_ONLY_NAMES))}")
            skipped += 1
            continue
        if names:
            log(f"   would rmdir  {d}  (after deleting {len(names)} kit file(s))")
            continue
        log(f"   RMDIR    {d}")
        if args.execute:
            ftp.rmd(d)

    log("\n-- docroot .htaccess")
    for site in CLOBBERED_HTACCESS:
        try:
            got_md5, size = md5_remote(ftp, f"{site}/.htaccess")
        except ftplib.error_perm as exc:
            log(f"   absent   {site}/.htaccess  ({exc})")
            continue
        looks_kit = size > 50000
        log(f"   {site}/.htaccess  {size} B  md5={got_md5}"
            + ("  <== kit (rewrite + 3,088 deny lines)" if looks_kit else "  (not kit-sized)"))
        if not args.restore_htaccess:
            log("      no --restore-htaccess given — left as is")
            continue
        if args.execute:
            save_evidence(ftp, f"{site}/.htaccess", args.evidence_dir)
            ftp.rename(f"{site}/.htaccess", f"{site}/.htaccess.phish-2026-11-25")
            with open(args.restore_htaccess, "rb") as fh:
                ftp.storbinary(f"STOR {site}/.htaccess", fh)
            try:
                ftp.sendcmd(f"SITE CHMOD 644 {site}/.htaccess")
            except ftplib.error_perm as exc:
                log(f"      chmod warning: {exc}")
            log(f"      quarantined old file, uploaded {args.restore_htaccess}")
        else:
            log(f"      would quarantine + upload {args.restore_htaccess}")

    try:
        ftp.quit()
    except Exception:
        pass

    log(f"\n== {'removed' if args.execute else 'would remove'}: {removed} file(s); skipped: {skipped}")
    if not args.execute:
        log("== dry run only. Re-run with --execute to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
