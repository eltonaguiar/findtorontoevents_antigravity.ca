import os, ftplib

def upload_to_path(ftp, local_path, remote_path):
    print(f"Uploading {local_path} to {remote_path}...")
    # Ensure directory exists
    parts = remote_path.split('/')
    remote_file = parts[-1]
    remote_dir = '/'.join(parts[:-1])
    
    ftp.cwd('/')
    for part in parts[:-1]:
        if not part: continue
        try:
            ftp.cwd(part)
        except:
            print(f"  Creating {part}")
            ftp.mkd(part)
            ftp.cwd(part)
            
    with open(local_path, 'rb') as f:
        ftp.storbinary(f'STOR {remote_file}', f)
    print("  Done.")

def main():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)
        print("Logged in.")
        
        # Mirroring important chunks and assets
        files = [
            ('index.html', 'findtorontoevents.ca/index.html'),
            ('index.html', 'index.html'),
            ('_next/static/chunks/a2ac3a6616d60872.js', 'findtorontoevents.ca/_next/static/chunks/a2ac3a6616d60872.js'),
            ('_next/static/chunks/a2ac3a6616d60872.js', 'findtorontoevents.ca/next/_next/static/chunks/a2ac3a6616d60872.js'),
            ('_next/static/chunks/a2ac3a6616d60872.js', '_next/static/chunks/a2ac3a6616d60872.js'),
            ('_next/static/chunks/a2ac3a6616d60872.js', 'next/_next/static/chunks/a2ac3a6616d60872.js'),
            ('_next/static/chunks/5540fc8a911e4742.js', 'findtorontoevents.ca/_next/static/chunks/5540fc8a911e4742.js'),
            ('_next/static/chunks/5540fc8a911e4742.js', 'findtorontoevents.ca/next/_next/static/chunks/5540fc8a911e4742.js'),
            ('_next/static/chunks/a7929c28dfcddcf5.js', 'findtorontoevents.ca/_next/static/chunks/a7929c28dfcddcf5.js'),
            ('_next/static/chunks/a7929c28dfcddcf5.js', 'findtorontoevents.ca/next/_next/static/chunks/a7929c28dfcddcf5.js')
        ]
        
        for local, remote in files:
            if os.path.exists(local):
                try:
                    upload_to_path(ftp, local, remote)
                except Exception as e:
                    print(f"  FAILED {remote}: {e}")
            else:
                print(f"  Local file {local} missng")

if __name__ == "__main__":
    main()
