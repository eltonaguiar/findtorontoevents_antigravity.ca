"""
Deploy the new js-proxy-v2.php file
"""
import os
import ftplib

def deploy():
    host = os.environ.get('FTP_SERVER')
    user = os.environ.get('FTP_USER')
    password = os.environ.get('FTP_PASS')
    
    if not all([host, user, password]):
        print("ERROR: Missing FTP credentials")
        return False
    
    # Deploy to both FTP root and findtorontoevents.ca (site document root)
    deployments = [
        [('js-proxy-v2.php', 'js-proxy-v2.php'), ('.htaccess', '.htaccess')],
        [('js-proxy-v2.php', 'findtorontoevents.ca/js-proxy-v2.php'), ('.htaccess', 'findtorontoevents.ca/.htaccess')],
    ]
    
    print("Deploying js-proxy-v2.php and updated .htaccess...")
    
    try:
        with ftplib.FTP(host) as ftp:
            ftp.login(user=user, passwd=password)
            
            def upload_to_remote(local_path, remote_path):
                if not os.path.exists(local_path):
                    print(f"ERROR: {local_path} not found")
                    return
                parts = remote_path.split('/')
                remote_file = parts[-1]
                remote_dir = parts[:-1]
                ftp.cwd('/')
                for part in remote_dir:
                    if part:
                        try:
                            ftp.cwd(part)
                        except ftplib.error_perm:
                            try:
                                ftp.mkd(part)
                                ftp.cwd(part)
                            except Exception:
                                pass
                with open(local_path, 'rb') as f:
                    ftp.storbinary(f'STOR {remote_file}', f)
                print(f"SUCCESS: {remote_path} deployed")

            for file_list in deployments:
                for local, remote in file_list:
                    upload_to_remote(local, remote)
            
            return True
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    deploy()
