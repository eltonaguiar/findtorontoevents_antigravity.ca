import ftplib
import os

def fetch_config():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)
        try:
            ftp.cwd('findtorontoevents.ca/cakephp/config')
            print("Entered config directory.")
            files = []
            ftp.retrlines('LIST', files.append)
            for f in files:
                print(f)
                
            # Try to read app_local.php first (contains overrides)
            target = 'app_local.php'
            # If not found in list, fallback to app.php
            if not any('app_local.php' in line for line in files):
                print("app_local.php not found, trying app.php")
                target = 'app.php'

            print(f"\nReading {target}...")
            
            def handle_line(line):
                # Simple filter to only print lines with 'username', 'password', 'database'
                if any(k in line for k in ['username', 'password', 'database', 'host']):
                    print(line.strip())

            ftp.retrlines(f'RETR {target}', handle_line)

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    fetch_config()
