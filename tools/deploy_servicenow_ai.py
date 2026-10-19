"""Deploy ServiceNow AI Features page to 50webs via FTPS."""
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

# Create remote directory structure
remote_base = "/findtorontoevents.ca"
dirs = [
    f"{remote_base}/servicenow",
    f"{remote_base}/servicenow/AIFeaturesOct2026",
]
for d in dirs:
    try:
        ftp.mkd(d)
        print(f"MKD {d}")
    except Exception as e:
        # Directory might already exist
        pass

uploads = [
    ("TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html", 
     f"{remote_base}/servicenow/AIFeaturesOct2026", "index.html"),
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