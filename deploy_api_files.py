import os
import sys
from ftplib import FTP_TLS

server = os.environ.get("FTP_SERVER")
user = os.environ.get("FTP_USER")
passwd = os.environ.get("FTP_PASS")

if not all([server, user, passwd]):
    print("ERROR: Missing FTP_SERVER, FTP_USER, or FTP_PASS environment variables.")
    sys.exit(1)

# Files to deploy
files_to_deploy = [
    {
        "local": r"e:\findtorontoevents_antigravity.ca\live-monitor\api\supplemental_dimensions.php",
        "remote": "/findtorontoevents.ca/live-monitor/api/supplemental_dimensions.php"
    },
    {
        "local": r"e:\findtorontoevents_antigravity.ca\live-monitor\api\test_env_vars.php",
        "remote": "/findtorontoevents.ca/live-monitor/api/test_env_vars.php"
    }
]

try:
    ftp = FTP_TLS(server)
    ftp.login(user, passwd)
    ftp.prot_p()
    print(f"Connected to {server}")
    
    for file_info in files_to_deploy:
        local_path = file_info["local"]
        remote_path = file_info["remote"]
        
        if not os.path.exists(local_path):
            print(f"WARNING: Local file not found: {local_path}")
            continue
            
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_path}", f)
        print(f"Uploaded: {os.path.basename(local_path)} -> {remote_path}")
    
    ftp.quit()
    print("SUCCESS: All API files deployed.")
    
except Exception as e:
    print(f"FAILURE: {e}")
    sys.exit(1)
