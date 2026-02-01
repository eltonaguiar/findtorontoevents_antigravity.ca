from ftplib import FTP_TLS
import os
import ssl

def list_ftp():
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
    
    print("Listing Root Directory:")
    ftps.retrlines('LIST')
    
    # Check public_html if it manifests
    try:
        print("\nListing public_html (if exists):")
        ftps.cwd('public_html')
        ftps.retrlines('LIST')
    except Exception as e:
        print(f"Could not listing public_html: {e}")

    ftps.quit()

if __name__ == "__main__":
    list_ftp()
