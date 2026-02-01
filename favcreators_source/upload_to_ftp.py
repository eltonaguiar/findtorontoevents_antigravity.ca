
import os
import ftplib
import sys
import ssl

def upload_directory(local_dir, remote_dir, host, username, password):
    ftp = None
    try:
        print(f"Attempting secure connection to {host}...")
        # Use FTP_TLS for explicit FTPS
        ftp = ftplib.FTP_TLS()
        # Higher timeout
        ftp.connect(host, 21, timeout=30)
        ftp.login(username, password)
        print("Logged in successfully.")
        
        # Switch to secure data connection (CRITICAL for FTPS)
        ftp.prot_p()
        print("Secure data connection established.")

        def ensure_dir(path):
            parts = [p for p in path.split('/') if p]
            current = ""
            for part in parts:
                current += "/" + part
                try:
                    ftp.mkd(current)
                    print(f"Created directory: {current}")
                except ftplib.error_perm as e:
                    # 550 usually means directory exists
                    if not str(e).startswith('550'):
                        print(f"Warning on mkd {current}: {e}")

        ensure_dir(remote_dir)

        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                rel_path = os.path.relpath(local_path, local_dir).replace('\\', '/')
                remote_path = remote_dir + "/" + rel_path
                
                remote_file_dir = os.path.dirname(remote_path)
                ensure_dir(remote_file_dir)
                
                print(f"Uploading {local_path} to {remote_path}...")
                with open(local_path, 'rb') as f:
                    # Use storbinary for binary files
                    ftp.storbinary(f'STOR {remote_path}', f)
        
        ftp.quit()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        if ftp:
            try:
                ftp.quit()
            except:
                pass
        sys.exit(1)

if __name__ == "__main__":
    local_directory = "docs"
    remote_directory = "/FAVCREATORS_TRACKER"
    host = "ftps2.50webs.com"
    username = "ejaguiar1"
    password = r"CxH1Uh*#0QkIVg@KxgMZXn7Hp"
    
    upload_directory(local_directory, remote_directory, host, username, password)
