import os, ftplib
import ssl
from pathlib import Path
from tools.ftp_credentials import get_ftp_credentials

def deploy_audit():
    # 50webs deployment
    print("Deploying to 50webs...")
    try:
        credentials = get_ftp_credentials()
        ftp = ftplib.FTP_TLS(credentials.host, timeout=60, context=ssl.create_default_context())
        ftp.login(credentials.user, credentials.password)
        ftp.prot_p()
        
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
        host = os.environ["FTPGODADDYHOST_TE_DOTNET"]
        user = os.environ["FTPGODADDYUSER"]
        password = os.environ["FTPGODADDYPASS"]
        ftp2 = ftplib.FTP_TLS(host, timeout=60, context=ssl.create_default_context())
        ftp2.login(user, password)
        ftp2.prot_p()
        
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
