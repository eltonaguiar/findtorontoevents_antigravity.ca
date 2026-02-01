#!/usr/bin/env python3
"""Remove next/ directory from server if it exists"""
import ssl
from ftplib import FTP_TLS, error_perm

def remove_directory(ftp, path):
    """Recursively remove directory"""
    try:
        files = []
        dirs = []
        ftp.retrlines(f'LIST {path}', lambda line: files.append(line.split()[-1]) if line.startswith('-') else dirs.append(line.split()[-1]) if line.startswith('d') else None)
        
        # Remove files first
        for item in files:
            try:
                ftp.delete(f'{path}/{item}')
                print(f"Deleted file: {path}/{item}")
            except error_perm:
                pass
        
        # Remove subdirectories
        for item in dirs:
            if item not in ('.', '..'):
                remove_directory(ftp, f'{path}/{item}')
        
        # Remove directory itself
        try:
            ftp.rmd(path)
            print(f"Removed directory: {path}")
        except error_perm:
            pass
    except error_perm:
        pass

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        # Try to remove next directory
        print("\n=== Removing next/ directory ===")
        try:
            remove_directory(ftp, "next")
            print("Removed next/ directory successfully!")
        except Exception as e:
            print(f"Could not remove next/ directory: {e}")
            print("(This is OK if it doesn't exist)")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        try:
            ftp.quit()
        except:
            pass
    
    return 0

if __name__ == "__main__":
    exit(main())
