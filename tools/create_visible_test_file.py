#!/usr/bin/env python3
"""Create a visible test file in next/_next/ to verify directory"""
import ssl
from ftplib import FTP_TLS
from io import BytesIO

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
        
        # Create a visible test file
        test_content = "This file confirms you are in the correct directory: next/_next/\nThe .htaccess file is also here but hidden (starts with a dot)."
        bio = BytesIO(test_content.encode('utf-8'))
        ftp.storbinary("STOR next/_next/README-TEST.txt", bio)
        print("\nCreated visible test file: next/_next/README-TEST.txt")
        print("If you see this file in FileZilla, you're in the right directory!")
        print("The .htaccess file is there but hidden - enable 'Show hidden files' in FileZilla.")
        
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
