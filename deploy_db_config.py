import os
import sys
from ftplib import FTP_TLS

server = os.environ.get("FTP_SERVER")
user = os.environ.get("FTP_USER")
passwd = os.environ.get("FTP_PASS")

if not all([server, user, passwd]):
    print("ERROR: Missing FTP_SERVER, FTP_USER, or FTP_PASS environment variables.")
    sys.exit(1)

# Deploy db_config.php
local_path = r"e:\findtorontoevents_antigravity.ca\live-monitor\api\db_config.php"
remote_path = "/findtorontoevents.ca/live-monitor/api/db_config.php"

try:
    ftp = FTP_TLS(server)
    ftp.login(user, passwd)
    ftp.prot_p()
    print(f"Connected to {server}")
    
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {remote_path}", f)
    print(f"Uploaded: db_config.php -> {remote_path}")
    
    ftp.quit()
    print("SUCCESS: db_config.php deployed.")
    
except Exception as e:
    print(f"FAILURE: {e}")
    sys.exit(1)
