from ftplib import FTP_TLS, error_perm
import os
import ssl

def main():
    server = os.environ['FTP_SERVER']
    user = os.environ['FTP_USER']
    password = os.environ['FTP_PASS']
    
    files_to_sync = ['index.html', 'page_content.html', '.htaccess', 'js-proxy.php']

    context = ssl.create_default_context()
    ftps = FTP_TLS(context=context)
    ftps.connect(server)
    ftps.login(user, password)
    ftps.prot_p()
    
    # helper to upload
    def upload_to(cwd):
        print(f"Deployment target: {cwd}")
        try:
            ftps.cwd(cwd)
        except Exception as e:
            print(f"Cannot enter {cwd}: {e}")
            return

        for fname in files_to_sync:
            if not os.path.exists(fname): continue
            try:
                with open(fname, 'rb') as f:
                    ftps.storbinary(f'STOR {fname}', f)
                print(f"  Uploaded {fname}")
            except Exception as e:
                print(f"  Failed {fname}: {e}")
        
        # Check for public_html subfolder
        try:
            ftps.cwd('public_html')
            print(f"  Found public_html in {cwd} -> Entering")
            for fname in files_to_sync:
                if not os.path.exists(fname): continue
                with open(fname, 'rb') as f:
                    ftps.storbinary(f'STOR {fname}', f)
            ftps.cwd('..') # back to cwd
        except:
            pass # No public_html, that's fine

        # Go back to root (absolute) for next iteration is safer?
        # NO, we passed absolute path or relative?
        # Better: Reset to root each time.
        ftps.cwd('/')

    # 1. Get List of Directories in Root
    ftps.cwd('/')
    items = ftps.nlst()
    
    targets = []
    for item in items:
        if item in ['.', '..']: continue
        # Simple heuristic: if it has an extension like .org .com, it's a domain folder
        # OR just try to enter everything that isn't a file?
        # Nlst doesn't distinguish.
        # We'll just try to enter everything.
        targets.append(item)
    
    # 2. Spray
    for t in targets:
        # We reset to root
        ftps.cwd('/')
        # Try to treat as directory
        try:
            ftps.cwd(t)
            # If successful, it's a dir. Go back and add to valid list?
            # Or just call upload_to(t)
            ftps.cwd('/') # Reset
            upload_to(t)
        except:
            # It's a file, skip
            pass
            
    # 3. Also upload to Root /
    upload_to('/')

    ftps.quit()
    print("Spray Complete.")

if __name__ == "__main__":
    main()
