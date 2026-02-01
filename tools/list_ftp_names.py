from ftplib import FTP_TLS
import os
import ssl

def list_names():
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
    
    print("Files in /:")
    files = ftps.nlst()
    print(files)
    
    # Check potential web roots
    candidates = ['public_html', 'htdocs', 'www', 'web', 'site', 'torontoevents']
    
    for f in files:
        if f in candidates or f.lower().startswith('tor'):
            try:
                print(f"Listing contents of {f}:")
                ftps.cwd(f)
                subfiles = ftps.nlst()
                print(subfiles)
                ftps.cwd('..')
            except Exception as e:
                print(f"Could not enter {f}: {e}")

    ftps.quit()

if __name__ == "__main__":
    list_names()
