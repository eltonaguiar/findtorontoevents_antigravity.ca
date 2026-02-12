"""
Deploy ESPN API enhanced modules to FTP server
"""
import ftplib
import os
import sys

FTP_HOST = "ftps2.50webs.com"
FTP_USER = "ejaguiar1"
FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
LOCAL_DIR = "live-monitor/api/scrapers"
REMOTE_DIR = "findtorontoevents.ca/live-monitor/api/scrapers"

ESPN_API_FILES = [
    "espn_api_enhanced.php",
    "unified_sports_feed.php"
]

def deploy():
    print("=" * 60)
    print("ESPN API ENHANCED MODULES DEPLOYMENT")
    print("Leveraging hidden ESPN APIs for all sports")
    print("=" * 60)
    print("")
    print("Connecting to FTP...")
    
    try:
        ftp = ftplib.FTP_TLS(FTP_HOST)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        
        ftp.cwd(REMOTE_DIR)
        
        success = 0
        failed = 0
        
        print("\nDeploying ESPN API Modules...")
        print("-" * 60)
        
        for filename in ESPN_API_FILES:
            local_path = os.path.join(LOCAL_DIR, filename)
            if not os.path.exists(local_path):
                print("NOT FOUND: " + local_path)
                failed += 1
                continue
            
            print("Uploading " + filename + "...")
            try:
                with open(local_path, 'rb') as f:
                    ftp.storbinary('STOR ' + filename, f)
                size = os.path.getsize(local_path)
                print("  OK - " + str(size) + " bytes")
                success += 1
            except Exception as e:
                print("  FAILED: " + str(e))
                failed += 1
        
        ftp.quit()
        
        print("")
        print("=" * 60)
        print("DEPLOYMENT COMPLETE")
        print("Success: " + str(success) + "/" + str(len(ESPN_API_FILES)))
        if failed > 0:
            print("Failed: " + str(failed))
        print("=" * 60)
        print("")
        print("Test the ESPN API integration:")
        print("  /espn_api_enhanced.php?action=sport&sport=nfl")
        print("  /unified_sports_feed.php?action=live")
        print("")
        
        return failed == 0
        
    except Exception as e:
        print("FTP Error: " + str(e))
        return False

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
