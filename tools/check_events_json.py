#!/usr/bin/env python3
"""Check events.json on the server"""
import os
import ssl
import json
from ftplib import FTP_TLS
from pathlib import Path

def main():
    FTP_HOST = "ftps2.50webs.com"
    FTP_USER = "ejaguiar1"
    FTP_PASS = "$a^FzN7BqKapSQMsZxD&^FeTJ"
    
    workspace_root = Path(__file__).parent.parent
    download_path = workspace_root / "server_events.json"
    
    print("Connecting to FTP server...")
    context = ssl.create_default_context()
    ftp = FTP_TLS(context=context)
    
    try:
        ftp.connect(FTP_HOST, 21, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("Connected successfully!")
        
        # List files in current directory
        print("\n=== Files in server root ===")
        ftp.retrlines('LIST')
        
        print(f"\n=== Downloading events.json from server ===")
        try:
            with open(download_path, "wb") as f:
                ftp.retrbinary("RETR events.json", f.write)
            print(f"Downloaded to: {download_path}")
            print(f"File size: {download_path.stat().st_size / 1024:.1f} KB")
            
            # Verify JSON is valid using UTF-8 encoding
            with open(download_path, encoding='utf-8') as f:
                data = json.load(f)
                print(f"JSON is valid and contains {len(data)} events")
                
                # Compare with local events.json
                local_events_path = workspace_root / "data" / "events.json"
                if local_events_path.exists():
                    with open(local_events_path, encoding='utf-8') as f:
                        local_data = json.load(f)
                        print(f"\nLocal events.json contains {len(local_data)} events")
                        print(f"Files are {'identical' if local_data == data else 'different'}")
                
        except Exception as e:
            print(f"Error accessing events.json: {e}")
        
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
        
        # Cleanup downloaded file
        if download_path.exists():
            download_path.unlink()
    
    return 0

if __name__ == "__main__":
    exit(main())