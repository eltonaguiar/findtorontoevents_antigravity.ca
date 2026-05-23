#!/usr/bin/env python3
"""Debug + fix events.json upload to torontoevent.net/next/."""
import os, sys, ftplib
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

host = os.environ.get("FTP_HOST", "")
user = os.environ.get("FTP_USER", "")
pw = os.environ.get("FTP_PASS", "")

ftp = ftplib.FTP(host, timeout=30)
ftp.login(user, pw)
ftp.set_pasv(True)

print("Listing /torontoevent.net/next/:")
ftp.cwd("/torontoevent.net/next")
files = []
ftp.retrlines("LIST", lambda x: files.append(x))
for f in files[:15]:
    print(f"  {f}")

print(f"\nCurrent events.json size via FTP:")
try:
    size = ftp.size("events.json")
    print(f"  events.json: {size} bytes")
except:
    print("  events.json: SIZE command failed")

src = WORKSPACE / "tmp" / "fte_clone" / "events.json"
content = src.read_text(encoding="utf-8").replace("findtorontoevents.ca", "torontoevent.net")
import tempfile
tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
tmp.write(content)
tmp.close()
local_size = os.path.getsize(tmp.name)

print(f"\nUploading {local_size} bytes to events.json...")
ftp.cwd("/torontoevent.net/next")
try:
    ftp.delete("events.json")
    print("  Deleted old events.json")
except:
    print("  No old events.json to delete")

with open(tmp.name, "rb") as f:
    ftp.storbinary("STOR events.json", f)
print("  Uploaded!")

try:
    new_size = ftp.size("events.json")
    print(f"  New size: {new_size} bytes")
except:
    print("  SIZE command failed after upload")

os.unlink(tmp.name)
ftp.quit()
print("Done!")
