import os, ftplib, sys

def ensure_remote_dir(ftp, remote_dir):
    current = ""
    for part in remote_dir.split('/'):
        if not part: continue
        current += part + "/"
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            print(f"  Creating remote dir: {part}")
            ftp.mkd(part)
            ftp.cwd(part)

def upload_dir(ftp, local_dir, remote_dir):
    print(f"Syncing {local_dir} to {remote_dir}...")
    ensure_remote_dir(ftp, remote_dir)
    
    # Get current contents to avoid duplicate mkds
    remote_items = ftp.nlst()
    
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        if os.path.isfile(local_path):
            print(f"    Uploading {item}...")
            # Go to remote_dir first to be sure
            ftp.cwd('/')
            for part in remote_dir.split('/'):
                if part: ftp.cwd(part)
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {item}', f)
        elif os.path.isdir(local_path):
            upload_dir(ftp, local_path, remote_dir + '/' + item)
            # No need to go back up, we use ensure_remote_dir which resets at start

def deploy():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)
        print("Logged in.")
        
        # 1. Sync _next to root and /next
        if os.path.exists('_next'):
            upload_dir(ftp, '_next', 'findtorontoevents.ca/_next')
            upload_dir(ftp, '_next', 'findtorontoevents.ca/next/_next')
        
        # 2. Upload main files (only under findtorontoevents.ca/, never FTP root)
        files = [
            ('index.html', 'findtorontoevents.ca/index.html'),
            ('events.json', 'findtorontoevents.ca/next/events.json'),
            ('events.json', 'findtorontoevents.ca/events.json'),
            ('BREAK_FIX.MD', 'findtorontoevents.ca/BREAK_FIX.MD')
        ]
        
        for local, remote in files:
            print(f"Uploading {local} to {remote}...")
            ftp.cwd('/')
            remote_dir = os.path.dirname(remote)
            remote_file = os.path.basename(remote)
            if remote_dir:
                ensure_remote_dir(ftp, remote_dir)
            with open(local, 'rb') as f:
                ftp.storbinary(f'STOR {remote_file}', f)

if __name__ == "__main__":
    deploy()
