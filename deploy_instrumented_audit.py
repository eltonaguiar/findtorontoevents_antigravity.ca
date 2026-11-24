import os, ftplib
from pathlib import Path

def deploy_audit():
    # 50webs deployment
    print("Deploying to 50webs...")
    try:
        ftp = ftplib.FTP('ftps2.50webs.com', timeout=60)
        ftp.login('ejaguiar1', os.getenv('FTP_PASS', ''))
        
        local_file = r'e:\findtorontoevents_antigravity.ca\audit_dashboard\index.html'
        
        # Upload to /findtorontoevents.ca/audit_dashboard/index.html
        remote_path1 = '/findtorontoevents.ca/audit_dashboard/index.html'
        ftp.cwd('/findtorontoevents.ca/audit_dashboard/')
        with open(local_file, 'rb') as f:
            ftp.storbinary('STOR index.html', f)
        print(f"  📤 {remote_path1}")
        
        # Upload to /findtorontoevents.ca/audit/index.html (likely the /audit/ alias)
        # Check if audit dir exists
        ftp.cwd('/findtorontoevents.ca/')
        try:
            ftp.cwd('audit')
        except:
            ftp.mkd('audit')
            ftp.cwd('audit')
        
        with open(local_file, 'rb') as f:
            ftp.storbinary('STOR index.html', f)
        print(f"  📤 /findtorontoevents.ca/audit/index.html")
        
        ftp.quit()
    except Exception as e:
        print(f"  ❌ 50webs deploy failed: {e}")

    # GoDaddy deployment
    print("\nDeploying to GoDaddy...")
    try:
        ftp2 = ftplib.FTP('162.210.101.36', timeout=60)
        ftp2.login('findtoro', os.getenv('FTP_PASS', ''))
        
        # Paths: /public_html/audit_dashboard/ and /public_html/audit/
        for remote_dir in ['/public_html/audit_dashboard', '/public_html/audit']:
            try:
                ftp2.cwd(remote_dir)
            except:
                ftp2.mkd(remote_dir)
                ftp2.cwd(remote_dir)
            
            with open(local_file, 'rb') as f:
                ftp2.storbinary('STOR index.html', f)
            print(f"  📤 {remote_dir}/index.html")
        
        ftp2.quit()
    except Exception as e:
        print(f"  ❌ GoDaddy deploy failed: {e}")

if __name__ == "__main__":
    deploy_audit()
