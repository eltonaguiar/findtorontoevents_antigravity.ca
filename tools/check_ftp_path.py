import os, ftplib

def list_ftp():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    print(f"Connecting to {host}...")
    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)
        print("Logged in successfully.")
        print("Root contents:")
        ftp.dir()
        
        # Check if findtorontoevents.ca exists
        if 'findtorontoevents.ca' in ftp.nlst():
            print("\nContents of findtorontoevents.ca:")
            ftp.cwd('findtorontoevents.ca')
            ftp.dir()
        else:
            print("\n'findtorontoevents.ca' directory NOT found at root.")

if __name__ == "__main__":
    list_ftp()
