"""
Verify js-proxy.php was deployed correctly
"""
import os
import ftplib
import urllib.request

def verify():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    # Download the file from server
    print("Downloading js-proxy.php from server...")
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            ftp.cwd('/')
            
            with open('temp_server_proxy.php', 'wb') as f:
                ftp.retrbinary('RETR js-proxy.php', f.write)
        
        with open('temp_server_proxy.php', 'r', encoding='utf-8') as f:
            server_content = f.read()
        
        print("Server file content (first 300 chars):")
        print(server_content[:300])
        
        # Check for the problematic syntax
        if '??' in server_content:
            print("\nERROR: Server file still has '??' operator!")
        else:
            print("\nOK: Server file uses compatible syntax")
        
        # Check local file
        with open('js-proxy.php', 'r', encoding='utf-8') as f:
            local_content = f.read()
        
        if '??' in local_content:
            print("ERROR: Local file still has '??' operator!")
        else:
            print("OK: Local file uses compatible syntax")
        
        # Compare
        if server_content == local_content:
            print("\nOK: Server and local files match")
        else:
            print("\nWARNING: Server and local files differ")
            print(f"Server length: {len(server_content)}, Local length: {len(local_content)}")
        
        os.remove('temp_server_proxy.php')
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
