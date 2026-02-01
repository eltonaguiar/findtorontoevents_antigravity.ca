import os, ftplib

def check_next_dir():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)
        print("Logged in.")
        # Navigate to findtorontoevents.ca/next
        try:
            ftp.cwd('findtorontoevents.ca/next')
            print("\nContents of findtorontoevents.ca/next:")
            ftp.dir()
        except Exception as e:
            print(f"Error accessing findtorontoevents.ca/next: {e}")
        
        # Also check root events.json
        ftp.cwd('/')
        print("\nRoot directory:")
        ftp.dir()
        
        # Check if events.json is in root
        if 'events.json' in ftp.nlst():
             print("events.json found at root.")
        else:
             print("events.json NOT found at root.")

if __name__ == "__main__":
    check_next_dir()
