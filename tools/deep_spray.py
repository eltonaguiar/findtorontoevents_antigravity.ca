from ftplib import FTP_TLS, error_perm
import os
import ssl

def main():
    server = os.environ['FTP_SERVER']
    user = os.environ['FTP_USER']
    password = os.environ['FTP_PASS']
    
    # 1. Define files to sync to ROOT of target
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

    def upload_folder_recursive(local_dir, remote_parent):
        # Uploads content of local_dir to remote_parent/dirname
        dir_name = os.path.basename(local_dir)
        remote_path = f"{remote_parent}/{dir_name}" if remote_parent else dir_name
        
        # Create remote dir
        try:
            ftps.mkd(remote_path)
        except:
            pass # Exists
        
        # Walk
        for item in os.listdir(local_dir):
            local_item = os.path.join(local_dir, item)
            if os.path.isdir(local_item):
                upload_folder_recursive(local_item, remote_path)
            else:
                # Upload file
                # Need to verify connection? FTPLib usually handles it unless timeout.
                # We assume smallish number of files or robust connection.
                # For _next, it's many files.
                # Use storbinary.
                remote_file = f"{remote_path}/{item}"
                try:
                     with open(local_item, 'rb') as f:
                        ftps.storbinary(f'STOR {remote_file}', f)
                except Exception as e:
                    print(f"      Err {remote_file}: {e}")

    def deploy_to_target(target_root):
        print(f"Deploying to: {target_root}")
        try:
            ftps.cwd(target_root)
        except:
            print(f"  Skipping {target_root}, cannot enter.")
            return

        # 1. Upload Root Files
        for f in root_files:
            upload_file(f, f)
            
        # 2. Upload _next folder (REQUIRED for JS)
        if os.path.exists('_next'):
            print("    Syncing _next folder...")
            # We want _next to be in target_root/_next
            # upload_folder_recursive('_next', '') -> creates ./_next
            # Note: Recursive function takes 'remote_parent'. Empty string = current cwd?
            # Or pass '.'?
            # Creating directory '_next' in current cwd.
            # Local dir is '_next'.
            
            # Custom recursion for this context to stay in CWD
            # Try to make '_next' directory
            try: ftps.mkd('_next') 
            except: pass
            
            # Now recurse from local _next into remote _next
            # We reuse the function but be careful with paths
            # Let's write a specific walker for _next to reuse logic
            # OR just use logic:
            
            for root, dirs, files in os.walk('_next'):
                 # root is like _next\static\chunks
                 # rel_path = static\chunks
                 rel_path = os.path.relpath(root, '_next')
                 
                 # Remote path base: ./_next
                 if rel_path == '.':
                     remote_base = '_next'
                 else:
                     remote_base = f"_next/{rel_path}".replace('\\', '/')
                 
                 # Create dirs
                 for d in dirs:
                     d_path = f"{remote_base}/{d}"
                     try: ftps.mkd(d_path)
                     except: pass
                 
                 # Upload files
                 for f in files:
                     local_f = os.path.join(root, f)
                     remote_f = f"{remote_base}/{f}"
                     try:
                        with open(local_f, 'rb') as lf:
                            ftps.storbinary(f'STOR {remote_f}', lf)
                        # print(f"      up: {remote_f}") # Verbose
                     except Exception as e:
                         print(f"      Fail {remote_f}: {e}")

        # 3. Create 'next' folder and upload 'events.json' (Legacy/Github path shim)
        try: ftps.mkd('next')
        except: pass
        if os.path.exists('events.json'):
            print("    Uploading next/events.json...")
            try:
                ftps.cwd('next')
                with open('events.json', 'rb') as f:
                    ftps.storbinary('STOR events.json', f)
                ftps.cwd('..')
            except Exception as e:
                print(f"    Failed next/events.json: {e}")
                ftps.cwd('..') # Try to recover
        
        # Reset to true root for next iteration
        ftps.cwd('/')

    # Scan and Spray
    ftps.cwd('/')
    items = ftps.nlst()
    targets = []
    
    # Filter candidates
    for item in items:
        if item in ['.', '..', '.ftpquota', '.git']: continue
        # Try to navigate to verify it's a dir
        try:
            ftps.cwd(item)
            ftps.cwd('/')
            targets.append(item)
        except:
            pass
            
    # Also Root itself? No, root is container.
    # But user saw old file on one of them.
    # We deploy to ALL detected directories.
    
    for t in targets:
        deploy_to_target(t)
        
    ftps.quit()
    print("Deployment Complete.")

if __name__ == "__main__":
    main()
