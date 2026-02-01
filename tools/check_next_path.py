import os, ftplib

def check_next_subdir():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)
        print("Logged in.")
        # Check root
        dirs = ftp.nlst()
        print(f"Root items: {dirs}")
        
        # Check findtorontoevents.ca
        if 'findtorontoevents.ca' in dirs:
            ftp.cwd('findtorontoevents.ca')
            print(f"Inside findtorontoevents.ca, items: {ftp.nlst()}")
            
            # Check next
            if 'next' in ftp.nlst():
                ftp.cwd('next')
                print(f"Inside next/, items: {ftp.nlst()}")
            else:
                print("next/ DIR NOT FOUND inside findtorontoevents.ca")
        else:
            print("findtorontoevents.ca DIR NOT FOUND")

if __name__ == "__main__":
    check_next_subdir()
