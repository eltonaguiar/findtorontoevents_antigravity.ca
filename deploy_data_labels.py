"""Deploy data type labels + whatif cache fix to production via FTP."""
import os, sys
from ftplib import FTP_TLS

FTP_SERVER = os.environ.get('FTP_SERVER')
FTP_USER = os.environ.get('FTP_USER')
FTP_PASS = os.environ.get('FTP_PASS')

if not all([FTP_SERVER, FTP_USER, FTP_PASS]):
    print("ERROR: FTP env vars not set")
    sys.exit(1)

# Files to deploy: (local_path, remote_path)
BASE = r'e:\findtorontoevents_antigravity.ca'
REMOTE_ROOT = '/findtorontoevents.ca'

files = [
    # whatif.php with cached_compare + compute_compare
    ('findstocks/portfolio2/api/whatif.php', 'findstocks/portfolio2/api/whatif.php'),
    # stats page rewrite
    ('findstocks/portfolio2/stats/index.html', 'findstocks/portfolio2/stats/index.html'),
    # All pages with data type labels
    ('findstocks/portfolio2/picks.html', 'findstocks/portfolio2/picks.html'),
    ('findstocks/portfolio2/consolidated.html', 'findstocks/portfolio2/consolidated.html'),
    ('findstocks/portfolio2/horizon-picks.html', 'findstocks/portfolio2/horizon-picks.html'),
    ('findstocks/portfolio2/leaderboard.html', 'findstocks/portfolio2/leaderboard.html'),
    ('findstocks/portfolio2/daytrader-sim.html', 'findstocks/portfolio2/daytrader-sim.html'),
    ('findstocks/portfolio2/smart-learning.html', 'findstocks/portfolio2/smart-learning.html'),
    ('findstocks/portfolio2/learning-lab.html', 'findstocks/portfolio2/learning-lab.html'),
    ('findstocks/portfolio2/dividends.html', 'findstocks/portfolio2/dividends.html'),
    ('findstocks/portfolio2/dashboard.html', 'findstocks/portfolio2/dashboard.html'),
    ('findstocks/portfolio2/hub.html', 'findstocks/portfolio2/hub.html'),
    ('findstocks/portfolio2/learning-dashboard.html', 'findstocks/portfolio2/learning-dashboard.html'),
]

ftp = FTP_TLS()
ftp.connect(FTP_SERVER, 21)
ftp.login(FTP_USER, FTP_PASS)
ftp.prot_p()
print("Connected to FTP")

success = 0
fail = 0
for local_rel, remote_rel in files:
    local_path = os.path.join(BASE, local_rel)
    remote_path = REMOTE_ROOT + '/' + remote_rel
    if not os.path.exists(local_path):
        print(f"SKIP (not found): {local_rel}")
        fail += 1
        continue
    try:
        with open(local_path, 'rb') as f:
            ftp.storbinary('STOR ' + remote_path, f)
        size = os.path.getsize(local_path)
        print(f"OK: {local_rel} ({size:,} bytes)")
        success += 1
    except Exception as e:
        print(f"FAIL: {local_rel} -> {e}")
        fail += 1

ftp.quit()
print(f"\nDone: {success} uploaded, {fail} failed")
