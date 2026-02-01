from ftplib import FTP_TLS
import os
import ssl

def upload_files():
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

    # 1. Upload Root index.html
    if os.path.exists('index.html'):
        with open('index.html', 'rb') as f:
            print("Uploading index.html to / ...")
            ftps.storbinary('STOR index.html', f)

    # 2. Upload TORONTOEVENTS_ANTIGRAVITY/index.html
    # We need to change to that directory or specify path
    target_sub = 'TORONTOEVENTS_ANTIGRAVITY/index.html'
    local_sub = 'TORONTOEVENTS_ANTIGRAVITY/index.html'
    
    if os.path.exists(local_sub):
        # Ensure remote dir exists (it should)
        try:
            ftps.cwd('TORONTOEVENTS_ANTIGRAVITY')
            with open(local_sub, 'rb') as f:
                print("Uploading index.html to /TORONTOEVENTS_ANTIGRAVITY/ ...")
                ftps.storbinary('STOR index.html', f)
            ftps.cwd('..') # Go back
        except Exception as e:
            print(f"Error uploading subdirectory file: {e}")

    ftps.quit()
    print("Upload complete.")

if __name__ == "__main__":
    upload_files()
