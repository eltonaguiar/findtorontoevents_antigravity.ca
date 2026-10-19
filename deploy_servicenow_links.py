#!/usr/bin/env python3
"""Deploy updated ServiceNow documentation links to the live site via FTP.
This script uploads the modified HTML file for the ServiceNow AI Features page.
"""
import os, sys, ftplib

FTP_SERVER = os.getenv('FTPGODADDYHOST_TE_DOTNET', 'torontoevent.net')
FTP_USER = os.getenv('FTPGODADDYUSER', 'elton@torontoevent.net')
FTP_PASS = os.getenv('FTPGODADDYPASS', '')

FILES = [
    ('TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html', '/servicenow/AIFeaturesOct2026/index.html'),
    ('findtorontoevents.ca/servicenow/javascript/index.html', '/servicenow/javascript/index.html'),
]

def upload():
    ftp = ftplib.FTP(FTP_SERVER)
    ftp.login(FTP_USER, FTP_PASS)
    
    for local, remote in FILES:
        print(f"Uploading {local} to {remote}...")
        # Ensure remote directory exists
        ftp.cwd('/')
        dirs = remote.strip('/').split('/')[:-1]
        for d in dirs:
            try:
                ftp.cwd(d)
            except Exception:
                ftp.mkd(d)
                ftp.cwd(d)
        
        with open(local, 'rb') as f:
            filename = os.path.basename(remote)
            ftp.storbinary(f'STOR {filename}', f)
        print(f"OK: {remote}")
        
    ftp.quit()
    print('All uploads complete')

if __name__ == '__main__':
    upload()
