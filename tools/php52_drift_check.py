#!/usr/bin/env python3
"""Compare the PHP deployed on 50webs against the repository, byte for byte.

The movie-refresh outage in 2026-11 was caused by a stale deployed file, not by a
code bug: the live api_status.php was 2,068 B while the repo copy was 3,044 B. This
tool makes that class of drift visible instead of a mystery 500.

Usage:
    python3 tools/php52_drift_check.py            # summary + drifted files
    python3 tools/php52_drift_check.py --report f # also write a markdown report

Credentials: FTP_SERVER / FTP_USER from the environment (default ftps2.50webs.com,
ejaguiar1) and the 50WEBS password from the line after the 50WEBS key in
~/dbpasses.txt. Nothing is printed.
"""
import argparse
import ftplib
import hashlib
import io
import os
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGETS = [
    ("MOVIESHOWS3", "TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3"),
    ("MOVIESHOWS3/api", "TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api"),
    ("MOVIESHOWS3/log", "TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/log"),
    ("movieshows2", "TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2"),
    ("movieshows2/api", "TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/api"),
    ("fc/api", "favcreators/docs/api"),
]


def read_pass() -> str:
    p = pathlib.Path.home() / "dbpasses.txt"
    lines = p.read_text(errors="replace").splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^50WEBS", line.strip(), re.I):
            for nxt in lines[i + 1:]:
                if nxt.strip():
                    return nxt.strip()
    raise SystemExit("no 50WEBS entry in ~/dbpasses.txt")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="write a markdown report to this path")
    args = ap.parse_args()

    ftp = ftplib.FTP(os.environ.get("FTP_SERVER", "ftps2.50webs.com"), timeout=40)
    ftp.login(os.environ.get("FTP_USER", "ejaguiar1"), read_pass())
    ftp.cwd("/findtorontoevents.ca")

    rows = []
    tot = {"same": 0, "drift": 0, "live_only": 0, "repo_only": 0}
    for remote, rel in TARGETS:
        local = REPO_ROOT / rel
        try:
            ftp.cwd("/findtorontoevents.ca")
            ftp.cwd(remote)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"-- {remote}: unreachable ({str(exc)[:40]})")
            continue
        live = {n for n in ftp.nlst() if n.lower().endswith(".php")}
        repo = {p.name for p in local.glob("*.php")} if local.is_dir() else set()
        for name in sorted(live & repo):
            buf = io.BytesIO()
            ftp.retrbinary(f"RETR {name}", buf.write)
            same = hashlib.sha256(buf.getvalue()).digest() == hashlib.sha256(
                (local / name).read_bytes()).digest()
            if same:
                tot["same"] += 1
            else:
                tot["drift"] += 1
                rows.append(f"| `{remote}/{name}` | {len(buf.getvalue())} B | "
                            f"{(local / name).stat().st_size} B | stale |")
        only_live, only_repo = live - repo, repo - live
        tot["live_only"] += len(only_live)
        tot["repo_only"] += len(only_repo)
        print(f"-- {remote}: live={len(live)} repo={len(repo)} "
              f"drifted={len([r for r in rows if r.startswith(f'| `{remote}/')])} "
              f"live-only={len(only_live)} repo-only={len(only_repo)}")
        for name in sorted(only_repo):
            rows.append(f"| `{remote}/{name}` | — | {(local / name).stat().st_size} B | not deployed |")
    ftp.quit()

    print(f"SUMMARY identical={tot['same']} drifted={tot['drift']} "
          f"live_only={tot['live_only']} repo_only={tot['repo_only']}")
    if args.report:
        body = ("# 50webs PHP drift report\n\n"
                "| Path | Live | Repo | Status |\n|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
                f"identical={tot['same']} drifted={tot['drift']} "
                f"live_only={tot['live_only']} repo_only={tot['repo_only']}\n")
        pathlib.Path(args.report).write_text(body)
        print(f"report -> {args.report}")
    return 1 if tot["drift"] or tot["repo_only"] else 0


if __name__ == "__main__":
    sys.exit(main())
