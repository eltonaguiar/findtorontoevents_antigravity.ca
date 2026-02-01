import os, ftplib

def deploy_favcreators():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    local_base = 'e:/findtorontoevents_antigravity.ca/favcreators/docs'
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)
        print("Logged in.")
        
        # Ensure favcreators directory exists
        try:
            ftp.cwd('findtorontoevents.ca/favcreators')
        except:
            print("Creating findtorontoevents.ca/favcreators")
            try:
                ftp.mkd('findtorontoevents.ca/favcreators')
                ftp.cwd('findtorontoevents.ca/favcreators')
            except:
                # Fallback if inside findtorontoevents.ca root
                ftp.mkd('favcreators')
                ftp.cwd('favcreators')
                
        # Upload index.html
        print("Uploading index.html...")
        with open(f'{local_base}/index.html', 'rb') as f:
            ftp.storbinary('STOR index.html', f)

        # Upload PHP files if present
        # Upload local PHP files in root (if any remain)
        for file in os.listdir(local_base):
            if file.endswith('.php') and os.path.isfile(f'{local_base}/{file}'):
                print(f"Uploading {file}...")
                with open(f'{local_base}/{file}', 'rb') as f:
                    ftp.storbinary(f'STOR {file}', f)

        # Upload API folder
        api_dir = f'{local_base}/api'
        if os.path.exists(api_dir):
            try:
                ftp.cwd('api')
            except:
                ftp.mkd('api')
                ftp.cwd('api')
            
            for file in os.listdir(api_dir):
                print(f"Uploading api/{file}...")
                with open(f'{api_dir}/{file}', 'rb') as f:
                     ftp.storbinary(f'STOR {file}', f)
            
            # Go back to favcreators root
            ftp.cwd('..')

        # Ensure assets directory
        try:
            ftp.cwd('assets')
        except:
            ftp.mkd('assets')
            ftp.cwd('assets')
            
        # Upload assets
        assets_dir = f'{local_base}/assets'
        if os.path.exists(assets_dir):
            for asset in os.listdir(assets_dir):
                print(f"Uploading assets/{asset}...")
                with open(f'{assets_dir}/{asset}', 'rb') as f:
                    ftp.storbinary(f'STOR {asset}', f)
        
        print("FavCreators deployment complete.")

if __name__ == "__main__":
    deploy_favcreators()
