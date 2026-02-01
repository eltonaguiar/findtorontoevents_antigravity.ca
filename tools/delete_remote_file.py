import ftplib
import os

def delete_remote_file(filename):
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    with ftplib.FTP(host) as ftp:
        ftp.login(user, password)
        try:
            ftp.cwd('findtorontoevents.ca/favcreators')
            print(f"Deleting {filename}...")
            ftp.delete(filename)
            print("Deleted.")
        except Exception as e:
            print(f"Error deleting {filename}: {e}")

if __name__ == "__main__":
    delete_remote_file('api/google_callback.php')
