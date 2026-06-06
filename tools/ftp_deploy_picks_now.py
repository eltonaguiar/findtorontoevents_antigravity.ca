"""Deploy picks-now assets (HTML + JSON) to 50webs via FTPS."""
import os, ssl
from ftplib import FTP_TLS
from pathlib import Path

host = "ftps2.50webs.com"
user = os.environ.get("FTP_USER", "")
pw   = os.environ.get("FTP_PASS", "")

if not user or not pw:
    print("FTP_USER / FTP_PASS not set — skipping deploy")
    raise SystemExit(0)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ftp = FTP_TLS(context=ctx)
ftp.connect(host, 21, timeout=30)
ftp.login(user, pw)
ftp.prot_p()

uploads = [
    ("audit_dashboard/picks-now.html",        "/findtorontoevents.ca/audit",      "picks-now.html"),
    ("audit_dashboard/data/picks_now.json",   "/findtorontoevents.ca/audit/data", "picks_now.json"),
]

for local, remote_dir, remote_name in uploads:
    p = Path(local)
    if not p.exists():
        print(f"SKIP {local} (not found)")
        continue
    ftp.cwd(remote_dir)
    with open(p, "rb") as f:
        ftp.storbinary(f"STOR {remote_name}", f)
    print(f"OK  {local} -> {remote_dir}/{remote_name}  ({p.stat().st_size:,} bytes)")

ftp.quit()
print("FTP deploy complete")
