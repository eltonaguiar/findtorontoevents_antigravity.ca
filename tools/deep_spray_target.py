from ftplib import FTP_TLS
import os
import ssl

def main():
    server = os.environ['FTP_SERVER']
    user = os.environ['FTP_USER']
    password = os.environ['FTP_PASS']
    
    # PRIORITIZED TARGETS
    targets = ['findtorontoevents.ca', 'aguiar1.50webs.org']
    
    root_files = ['index.html', 'page_content.html', '.htaccess', 'js-proxy.php', 'events.json']

    context = ssl.create_default_context()
    ftps = FTP_TLS(context=context)
    ftps.connect(server)
    ftps.login(user, password)
    ftps.prot_p()
    
    def upload_file(local_path, remote_name):
        if not os.path.exists(local_path): return
        try:
            with open(local_path, 'rb') as f:
                ftps.storbinary(f'STOR {remote_name}', f)
            print(f"      Uploaded {remote_name}")
        except Exception as e:
            print(f"      Error uploading {remote_name}: {e}")

    def deploy_to_target(target_root):
        print(f"Deploying to: {target_root}")
        try:
            ftps.cwd('/')
            ftps.cwd(target_root)
        except:
            print(f"  Skipping {target_root}, cannot enter.")
            return

        # 1. Root Files
        for f in root_files:
            upload_file(f, f)
            
        # 2. _next folder
        if os.path.exists('_next'):
            print("    Syncing _next folder...")
            try: ftps.mkd('_next') 
            except: pass
            
            # Simple Walker 
            for root, dirs, files in os.walk('_next'):
                 rel_path = os.path.relpath(root, '_next')
                 if rel_path == '.': remote_base = '_next'
                 else: remote_base = f"_next/{rel_path}".replace('\\', '/')
                 
                 for d in dirs:
                     try: ftps.mkd(f"{remote_base}/{d}")
                     except: pass
                     
                 for f in files:
                     local_f = os.path.join(root, f)
                     remote_f = f"{remote_base}/{f}"
                     try:
                        with open(local_f, 'rb') as lf:
                            ftps.storbinary(f'STOR {remote_f}', lf)
                     except Exception as e:
                         print(f"      Fail {remote_f}: {e}")

        # 3. next/events.json
        try: ftps.mkd('next')
        except: pass
        if os.path.exists('events.json'):
            print("    Uploading next/events.json...")
            try:
                ftps.cwd('next')
                with open('events.json', 'rb') as f:
                    ftps.storbinary('STOR events.json', f)
            except Exception as e:
                print(f"    Failed next/events.json: {e}")
        
        ftps.cwd('/')

    for t in targets:
        deploy_to_target(t)
        
    ftps.quit()
    print("Targeted Deployment Complete.")

if __name__ == "__main__":
    main()
