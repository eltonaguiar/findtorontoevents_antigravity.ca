"""
Deploy sports scrapers to FTP server
"""
import ftplib
import os
import sys

FTP_HOST = "ftps2.50webs.com"
FTP_USER = "ejaguiar1"
FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
LOCAL_DIR = "live-monitor/api/scrapers"
REMOTE_DIR = "findtorontoevents.ca/live-monitor/api/scrapers"

FILES = [
    "nba_scraper.php",
    "nhl_scraper.php",
    "nfl_scraper.php",
    "mlb_scraper.php",
    "scraper_controller.php",
    "cron_scheduler.php"
]

def deploy():
    print("Connecting to FTP...")
    ftp = ftplib.FTP_TLS(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    
    # Create remote directory if needed
    try:
        ftp.mkd(REMOTE_DIR)
        print("Created directory: " + REMOTE_DIR)
    except:
        pass
    
    ftp.cwd(REMOTE_DIR)
    
    success = 0
    failed = 0
    
    for filename in FILES:
        local_path = os.path.join(LOCAL_DIR, filename)
        if not os.path.exists(local_path):
            print("File not found: " + local_path)
            failed += 1
            continue
        
        print("Uploading " + filename + "...")
        try:
            with open(local_path, 'rb') as f:
                ftp.storbinary('STOR ' + filename, f)
            print("  Success")
            success += 1
        except Exception as e:
            print("  Failed: " + str(e))
            failed += 1
    
    ftp.quit()
    
    print("")
    print("=" * 40)
    print("Deployment Complete")
    print("Success: " + str(success))
    print("Failed: " + str(failed))
    print("=" * 40)
    
    return failed == 0

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
