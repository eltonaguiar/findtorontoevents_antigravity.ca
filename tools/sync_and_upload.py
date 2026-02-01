import os
import shutil
from ftplib import FTP_TLS, error_perm
import ssl

def main():
    # 1. Update index.html timestamp
    print("Updating index.html timestamp...")
    if os.path.exists('index.html'):
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'Last updated: <!-- -->Unknown' in content:
            content = content.replace('Last updated: <!-- -->Unknown', 'Last updated: Jan 31 Fix')
        elif 'Last updated: Jan 31 Fix' not in content:
             # Just append/inject if needed, or leave it. 
             # Assuming standard format
             pass
        
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)

    # 2. Sync to Subdirectories (Local)
    targets = [
        'TORONTOEVENTS_ANTIGRAVITY/index.html',
        'TORONTOEVENTS_ANTIGRAVITY/TORONTOEVENTS_ANTIGRAVITY/index.html'
    ]
    
    for tg in targets:
        dir_path = os.path.dirname(tg)
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
            except Exception as e:
                print(f"Skipping local creation of {dir_path}: {e}")
                continue
        
        shutil.copy('index.html', tg)
        print(f"Synced index.html to {tg}")

    # 3. Upload to FTP
    server = os.environ['FTP_SERVER']
    user = os.environ['FTP_USER']
    password = os.environ['FTP_PASS']

    context = ssl.create_default_context()
    ftps = FTP_TLS(context=context)
    
    print(f"Connecting to {server}...")
    ftps.connect(server)
    ftps.login(user, password)
    ftps.prot_p()
    print("Logged in.")

    # Paths to upload
    upload_paths = [
        ('index.html', 'index.html'),
        ('page_content.html', 'page_content.html'),
        ('TORONTOEVENTS_ANTIGRAVITY/index.html', 'TORONTOEVENTS_ANTIGRAVITY/index.html'),
        ('TORONTOEVENTS_ANTIGRAVITY/TORONTOEVENTS_ANTIGRAVITY/index.html', 'TORONTOEVENTS_ANTIGRAVITY/TORONTOEVENTS_ANTIGRAVITY/index.html')
    ]
    
    for local_path, remote_path in upload_paths:
        if os.path.exists(local_path):
            remote_dir = os.path.dirname(remote_path)
            filename = os.path.basename(remote_path)
            
            # Navigate to root first
            ftps.cwd('/')
            
            # Try to navigate/create remote dirs
            if remote_dir:
                parts = remote_dir.split('/')
                for part in parts:
                    if not part: continue
                    try:
                        ftps.cwd(part)
                    except error_perm:
                        print(f"Creating remote dir: {part}")
                        try:
                            ftps.mkd(part)
                            ftps.cwd(part)
                        except error_perm as e:
                            print(f"Failed to create/enter {part}: {e}")
                            break
            
            # Upload
            print(f"Uploading {local_path} to {remote_path}...")
            with open(local_path, 'rb') as f:
                ftps.storbinary(f'STOR {filename}', f)
            print("Success.")
        else:
            print(f"Local file missing: {local_path}")

    ftps.quit()
    print("All uploads complete.")

if __name__ == "__main__":
    main()
