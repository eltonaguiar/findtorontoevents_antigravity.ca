#!/usr/bin/env python3
"""Quick deploy events.json to alt sites."""
import os, sys, ftplib, json
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

WORKSPACE = Path(__file__).resolve().parent.parent

env_file = WORKSPACE / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k and not os.environ.get(k):
                os.environ[k] = v

host = os.environ.get("FTP_HOST", os.environ.get("FTP_SERVER", ""))
user = os.environ.get("FTP_USER", "")
pw = os.environ.get("FTP_PASS", "")

src = WORKSPACE / "tmp" / "fte_clone" / "events.json"
events = json.loads(src.read_text(encoding="utf-8"))
total = len(events) if isinstance(events, list) else len(events.get("events", events))
print(f"Source: {src} ({total} events, {src.stat().st_size / 1024:.0f} KB)")

# Rewrite domain for alt sites
content = src.read_text(encoding="utf-8")

targets = [
    ("torontoevent.net", content.replace("findtorontoevents.ca", "torontoevent.net")),
]

ftp = ftplib.FTP(host, timeout=30)
ftp.login(user, pw)
ftp.set_pasv(True)

for domain, rewritten in targets:
    import tempfile
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    tmp.write(rewritten)
    tmp.close()

    for remote_path in [f"{domain}/events.json", f"{domain}/next/events.json"]:
        ftp.cwd("/")
        for part in remote_path.rsplit("/", 1)[0].split("/"):
            if part:
                try:
                    ftp.cwd(part)
                except ftplib.error_perm:
                    ftp.mkd(part)
                    ftp.cwd(part)
        fname = remote_path.split("/")[-1]
        with open(tmp.name, "rb") as f:
            ftp.storbinary(f"STOR {fname}", f)
        print(f"  OK {remote_path}")
    
    os.unlink(tmp.name)

ftp.quit()
print("Done!")
