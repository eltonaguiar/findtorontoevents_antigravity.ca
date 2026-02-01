import os, ftplib

def upload(ftp, local, remote):
    print(f"Uploading {local} to {remote}...")
    ftp.cwd('/')
    parts = remote.split('/')
    remote_file = parts[-1]
    remote_dirs = parts[:-1]
    
    for part in remote_dirs:
        if not part: continue
        try:
            ftp.cwd(part)
        except:
            print(f"  Creating {part}")
            ftp.mkd(part)
            ftp.cwd(part)
    
    with open(local, 'rb') as f:
        ftp.storbinary(f'STOR {remote_file}', f)
    print("  Success.")

def fix_all():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)
        print("Logged in.")
        
        # 1. Deploy the WAF-bypass .htaccess
        htaccess = "next/_next/.htaccess"
        targets = [
            "findtorontoevents.ca/next/_next/.htaccess",
            "findtorontoevents.ca/_next/.htaccess",
            "next/_next/.htaccess",
            "_next/.htaccess"
        ]
        for t in targets:
            try: upload(ftp, htaccess, t)
            except Exception as e: print(f"  FAILED {t}: {e}")

        # 2. Deploy event data
        events = "events.json"
        event_targets = [
            "findtorontoevents.ca/next/events.json",
            "findtorontoevents.ca/events.json",
            "findtorontoevents.ca/data/events.json",
            "next/events.json",
            "events.json"
        ]
        for t in event_targets:
             try: upload(ftp, events, t)
             except Exception as e: print(f"  FAILED {t}: {e}")

        # 3. Re-deploy index.html with diagnostics
        upload(ftp, "index.html", "findtorontoevents.ca/index.html")
        upload(ftp, "index.html", "index.html")

if __name__ == "__main__":
    fix_all()
