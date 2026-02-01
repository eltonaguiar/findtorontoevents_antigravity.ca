#!/usr/bin/env python3
"""List all files in next/_next/ directory including hidden files"""
import ssl
from ftplib import FTP_TLS

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
        print("Connected successfully!\n")
        
        # Change to next/_next directory
        print("=== Listing next/_next/ directory ===")
        try:
            ftp.cwd("next/_next")
            files = []
            ftp.retrlines('LIST -a', files.append)  # -a flag shows hidden files
            print(f"\nTotal items: {len(files)}\n")
            for f in files:
                print(f"  {f}")
            
            # Try to read .htaccess content
            print("\n=== Reading next/_next/.htaccess content ===")
            try:
                from io import BytesIO
                bio = BytesIO()
                ftp.retrbinary('RETR .htaccess', bio.write)
                content = bio.getvalue().decode('utf-8')
                print(content)
            except Exception as e:
                print(f"Error reading .htaccess: {e}")
            
        except Exception as e:
            print(f"Error accessing next/_next/: {e}")
            import traceback
            traceback.print_exc()
        
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
