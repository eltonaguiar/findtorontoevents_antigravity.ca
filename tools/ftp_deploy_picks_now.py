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
    ("audit_dashboard/data/picks_now_live_pnl.json",   "/findtorontoevents.ca/audit/data", "picks_now_live_pnl.json"),
    ("audit_dashboard/data/picks_now_track_record.json", "/findtorontoevents.ca/audit/data", "picks_now_track_record.json"),
]

# Freshness gate for the screener outputs. The hourly picks-now-live-pnl job calls this deployer
# WITHOUT regenerating picks_now.json, so it would re-ship the STALE committed picks_now.json (the
# commit-on-shared-main race leaves it days old) and OVERWRITE the fresh copy picks-now-refresh just
# deployed — observed 2026-06: the live page + TTWO/featured-trending reverted to an 11-day-old file
# within the hour. Skip picks-now.html + picks_now.json unless picks_now.json was regenerated this
# run (<2h old). The P&L files (live_pnl / track_record) always deploy (the hourly job regenerates them).
import json as _json, datetime as _dt
_SCREENER_OUTPUTS = {"picks-now.html", "picks_now.json"}
_picks_stale = True
try:
    _g = _json.load(open("audit_dashboard/data/picks_now.json")).get("generated_at", "")
    _age_h = (_dt.datetime.now(_dt.timezone.utc)
              - _dt.datetime.fromisoformat(_g.replace("Z", "+00:00"))).total_seconds() / 3600
    _picks_stale = _age_h > 2
    print(f"picks_now.json generated_at={_g[:19]} age={_age_h:.1f}h stale={_picks_stale}")
except Exception as _e:
    print(f"picks_now.json freshness check failed ({_e}); treating as stale (won't clobber live)")

for local, remote_dir, remote_name in uploads:
    p = Path(local)
    if not p.exists():
        print(f"SKIP {local} (not found)")
        continue
    if remote_name in _SCREENER_OUTPUTS and _picks_stale:
        print(f"SKIP {local} (picks_now.json not regenerated this run — not overwriting the fresh live copy)")
        continue
    ftp.cwd(remote_dir)
    with open(p, "rb") as f:
        ftp.storbinary(f"STOR {remote_name}", f)
    print(f"OK  {local} -> {remote_dir}/{remote_name}  ({p.stat().st_size:,} bytes)")

ftp.quit()
print("FTP deploy complete")
