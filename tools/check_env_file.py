import ftplib
import os

def check_env():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)
        try:
            ftp.cwd('findtorontoevents.ca/cakephp')
            print("Entered cakephp directory.")
            
            # Try to retrieve .env
            print("Attempting to read .env...")
            def handle_line(line):
                print(line.strip())
            
            ftp.retrlines('RETR .env', handle_line)

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_env()
