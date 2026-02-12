"""
Deploy hardened validation scrapers to FTP server
"""
import ftplib
import os
import sys

FTP_HOST = "ftps2.50webs.com"
FTP_USER = "ejaguiar1"
FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
LOCAL_DIR = "live-monitor/api/scrapers"
REMOTE_DIR = "findtorontoevents.ca/live-monitor/api/scrapers"

HARDENED_FILES = [
    "data_validator.php",      # Core validation engine
    "nfl_hardened.php"         # Hardened NFL scraper
]

def deploy():
    print("=" * 60)
    print("HARDENED SCRAPER DEPLOYMENT")
    print("Multi-Source Validation System")
    print("=" * 60)
    print("")
    print("Connecting to FTP...")
    
    ftp = ftplib.FTP_TLS(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    
    ftp.cwd(REMOTE_DIR)
    
    success = 0
    failed = 0
    
    print("\nDeploying Hardened Modules...")
    print("-" * 60)
    
    for filename in HARDENED_FILES:
        local_path = os.path.join(LOCAL_DIR, filename)
        if not os.path.exists(local_path):
            print("NOT FOUND: " + filename)
            failed += 1
            continue
        
        print("Uploading " + filename + "...")
        try:
            with open(local_path, 'rb') as f:
                ftp.storbinary('STOR ' + filename, f)
            print("  OK - " + str(os.path.getsize(local_path)) + " bytes")
            success += 1
        except Exception as e:
            print("  FAILED: " + str(e))
            failed += 1
    
    ftp.quit()
    
    print("")
    print("=" * 60)
    print("DEPLOYMENT COMPLETE")
    print("Success: " + str(success) + "/" + str(len(HARDENED_FILES)))
    if failed > 0:
        print("Failed: " + str(failed))
    print("=" * 60)
    print("")
    print("Test the validation system:")
    print("  /live-monitor/api/scrapers/data_validator.php?action=report&sport=nfl")
    print("")
    
    return failed == 0

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
