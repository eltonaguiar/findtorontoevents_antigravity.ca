"""
Try to clear PHP opcode cache by touching js-proxy.php
"""
import os
import ftplib
from datetime import datetime

def clear_cache():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    print("Attempting to clear PHP cache by re-uploading js-proxy.php...")
    
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            ftp.cwd('/')
            
            # Re-upload the file to trigger cache clear
            with open('js-proxy.php', 'rb') as f:
                ftp.storbinary('STOR js-proxy.php', f)
            
            print("SUCCESS: File re-uploaded (this may clear opcode cache)")
            print("Please wait 30-60 seconds for cache to clear")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    clear_cache()
